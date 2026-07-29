from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timedelta
import asyncio
import json
import hashlib
import hmac
import aiohttp
import structlog
from jinja2 import Template

from app.models.notification import (
    Notification, NotificationDeliveryLog, NotificationTemplate,
    NotificationSettings, NotificationQueue, WebhookEndpoint,
    NotificationType, NotificationChannel, NotificationStatus, NotificationPriority
)
from app.models.user import User
from app.config import settings
from app.utils.exceptions import ValidationError

logger = structlog.get_logger(__name__)


class NotificationService:
    def __init__(self):
        self.default_templates = self._load_default_templates()


    async def create_notification(
        self,
        db: AsyncSession,
        user_id: int,
        notification_type: NotificationType,
        title: str,
        message: str,
        channels: Optional[List[NotificationChannel]] = None,
        priority: NotificationPriority = NotificationPriority.NORMAL,
        data: Optional[Dict[str, Any]] = None,
        template_id: Optional[str] = None,
        scheduled_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None
    ) -> Notification:
        try:
            user_settings = await self.get_user_settings(db, user_id)

            if not user_settings.is_type_enabled(notification_type):
                logger.info("Notification type disabled for user", user_id=user_id, type=notification_type.value)
                return None

            if channels is None:
                channels = self._get_default_channels(notification_type)

            enabled_channels = [
                channel for channel in channels
                if user_settings.is_channel_enabled(channel)
            ]

            if not enabled_channels:
                logger.info("No enabled channels for user", user_id=user_id, type=notification_type.value)
                return None

            notification = Notification(
                user_id=user_id,
                type=notification_type,
                title=title,
                message=message,
                channels=enabled_channels,
                priority=priority,
                data=data or {},
                template_id=template_id,
                scheduled_at=scheduled_at or datetime.utcnow(),
                expires_at=expires_at
            )

            db.add(notification)
            await db.commit()
            await db.refresh(notification)

            await self._queue_notification(db, notification)

            logger.info(
                "Notification created",
                notification_id=notification.id,
                user_id=user_id,
                type=notification_type.value,
                channels=enabled_channels
            )

            return notification

        except Exception as e:
            await db.rollback()
            logger.error("Failed to create notification", error=str(e), exc_info=True)
            raise ValidationError("Не удалось создать уведомление")

    async def create_from_template(
        self,
        db: AsyncSession,
        user_id: int,
        template_id: str,
        data: Dict[str, Any],
        channels: Optional[List[NotificationChannel]] = None,
        scheduled_at: Optional[datetime] = None
    ) -> Optional[Notification]:
        try:
            template = await self.get_template(db, template_id)
            if not template or not template.is_active:
                logger.warning("Template not found or inactive", template_id=template_id)
                return None

            rendered = await self._render_template(template, data, NotificationChannel.TELEGRAM)
            if not rendered:
                logger.error("Failed to render template", template_id=template_id)
                return None

            return await self.create_notification(
                db=db,
                user_id=user_id,
                notification_type=template.type,
                title=rendered.get("title", ""),
                message=rendered.get("message", ""),
                channels=channels or template.supported_channels,
                priority=template.priority,
                data=data,
                template_id=template_id,
                scheduled_at=scheduled_at
            )

        except Exception as e:
            logger.error("Failed to create notification from template", error=str(e), exc_info=True)
            return None


    async def send_notification(self, db: AsyncSession, notification_id: int) -> bool:
        try:
            result = await db.execute(
                select(Notification)
                .options(selectinload(Notification.user))
                .where(Notification.id == notification_id)
            )
            notification = result.scalar_one_or_none()

            if not notification:
                logger.warning("Notification not found", notification_id=notification_id)
                return False

            if notification.status != NotificationStatus.PENDING:
                logger.info("Notification already processed", notification_id=notification_id, status=notification.status.value)
                return True

            if notification.is_expired:
                notification.status = NotificationStatus.CANCELLED
                await db.commit()
                logger.info("Notification expired", notification_id=notification_id)
                return False

            success_count = 0
            total_channels = len(notification.channels)

            for channel in notification.channels:
                try:
                    success = await self._send_to_channel(db, notification, channel)
                    if success:
                        success_count += 1
                except Exception as e:
                    logger.error("Failed to send to channel", channel=channel.value, error=str(e))

            if success_count > 0:
                notification.status = NotificationStatus.SENT
                notification.delivered_at = datetime.utcnow()

                if success_count == total_channels:
                    notification.status = NotificationStatus.DELIVERED
            else:
                notification.status = NotificationStatus.FAILED
                notification.failed_at = datetime.utcnow()
                notification.attempts += 1

            await db.commit()

            logger.info(
                "Notification processing completed",
                notification_id=notification_id,
                success_count=success_count,
                total_channels=total_channels,
                status=notification.status.value
            )

            return success_count > 0

        except Exception as e:
            logger.error("Failed to send notification", error=str(e), exc_info=True)
            return False

    async def _send_to_channel(
        self,
        db: AsyncSession,
        notification: Notification,
        channel: NotificationChannel
    ) -> bool:
        try:
            delivery_log = NotificationDeliveryLog(
                notification_id=notification.id,
                channel=channel,
                status=NotificationStatus.PENDING
            )
            db.add(delivery_log)
            await db.commit()
            await db.refresh(delivery_log)

            success = False

            if channel == NotificationChannel.TELEGRAM:
                success = await self._send_telegram(notification, delivery_log)
            elif channel == NotificationChannel.EMAIL:
                success = await self._send_email(notification, delivery_log)
            elif channel == NotificationChannel.PUSH:
                success = await self._send_push(notification, delivery_log)
            elif channel == NotificationChannel.SMS:
                success = await self._send_sms(notification, delivery_log)
            elif channel == NotificationChannel.WEBHOOK:
                success = await self._send_webhook(db, notification, delivery_log)

            delivery_log.status = NotificationStatus.SENT if success else NotificationStatus.FAILED
            if success:
                delivery_log.delivered_at = datetime.utcnow()
            else:
                delivery_log.failed_at = datetime.utcnow()

            await db.commit()
            return success

        except Exception as e:
            logger.error("Failed to send to channel", channel=channel.value, error=str(e))
            delivery_log.status = NotificationStatus.FAILED
            delivery_log.failed_at = datetime.utcnow()
            delivery_log.error_message = str(e)
            await db.commit()
            return False

    async def _send_telegram(self, notification: Notification, delivery_log: NotificationDeliveryLog) -> bool:
        try:
            delivery_log.recipient = str(notification.user.telegram_id)
            delivery_log.provider = "telegram"
            delivery_log.sent_at = datetime.utcnow()

            logger.info(
                "Telegram notification sent",
                notification_id=notification.id,
                user_id=notification.user_id,
                telegram_id=notification.user.telegram_id
            )

            return True

        except Exception as e:
            logger.error("Failed to send Telegram notification", error=str(e))
            delivery_log.error_message = str(e)
            return False

    async def _send_email(self, notification: Notification, delivery_log: NotificationDeliveryLog) -> bool:
        try:
            user_settings = notification.user.notification_settings
            if not user_settings or not user_settings.email:
                return False

            delivery_log.recipient = user_settings.email
            delivery_log.provider = "email"
            delivery_log.error_message = "Email sending not implemented"

            return False

        except Exception as e:
            logger.error("Failed to send email notification", error=str(e))
            delivery_log.error_message = str(e)
            return False

    async def _send_push(self, notification: Notification, delivery_log: NotificationDeliveryLog) -> bool:
        try:
            delivery_log.provider = "push"
            delivery_log.error_message = "Push notifications not implemented"

            return False

        except Exception as e:
            logger.error("Failed to send push notification", error=str(e))
            delivery_log.error_message = str(e)
            return False

    async def _send_sms(self, notification: Notification, delivery_log: NotificationDeliveryLog) -> bool:
        try:
            user_settings = notification.user.notification_settings
            if not user_settings or not user_settings.phone:
                return False

            delivery_log.recipient = user_settings.phone
            delivery_log.provider = "sms"
            delivery_log.error_message = "SMS sending not implemented"

            return False

        except Exception as e:
            logger.error("Failed to send SMS notification", error=str(e))
            delivery_log.error_message = str(e)
            return False

    async def _send_webhook(
        self,
        db: AsyncSession,
        notification: Notification,
        delivery_log: NotificationDeliveryLog
    ) -> bool:
        try:
            result = await db.execute(
                select(WebhookEndpoint)
                .where(
                    and_(
                        WebhookEndpoint.user_id == notification.user_id,
                        WebhookEndpoint.is_active == True
                    )
                )
            )
            webhooks = result.scalars().all()

            if not webhooks:
                return False

            success_count = 0
            for webhook in webhooks:
                if notification.type.value not in webhook.event_types:
                    continue

                try:
                    success = await self._send_single_webhook(webhook, notification)
                    if success:
                        success_count += 1

                    webhook.total_requests += 1
                    webhook.last_request_at = datetime.utcnow()

                    if success:
                        webhook.successful_requests += 1
                        webhook.last_success_at = datetime.utcnow()
                    else:
                        webhook.failed_requests += 1
                        webhook.last_failure_at = datetime.utcnow()

                except Exception as e:
                    logger.error("Failed to send webhook", webhook_id=webhook.id, error=str(e))
                    webhook.total_requests += 1
                    webhook.failed_requests += 1
                    webhook.last_request_at = datetime.utcnow()
                    webhook.last_failure_at = datetime.utcnow()
                    webhook.last_error_message = str(e)

            await db.commit()

            delivery_log.provider = "webhook"
            delivery_log.response_data = {"webhooks_sent": success_count, "total_webhooks": len(webhooks)}

            return success_count > 0

        except Exception as e:
            logger.error("Failed to send webhook notifications", error=str(e))
            delivery_log.error_message = str(e)
            return False

    async def _send_single_webhook(self, webhook: WebhookEndpoint, notification: Notification) -> bool:
        try:
            payload = {
                "event_type": notification.type.value,
                "notification_id": notification.id,
                "user_id": notification.user_id,
                "title": notification.title,
                "message": notification.message,
                "data": notification.data,
                "created_at": notification.created_at.isoformat(),
                "priority": notification.priority.value
            }

            headers = {"Content-Type": "application/json"}
            if webhook.secret:
                signature = self._create_webhook_signature(json.dumps(payload), webhook.secret)
                headers["X-Webhook-Signature"] = signature

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=webhook.timeout_seconds)) as session:
                async with session.post(webhook.url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        logger.info("Webhook sent successfully", webhook_id=webhook.id, url=webhook.url)
                        return True
                    else:
                        logger.warning("Webhook failed", webhook_id=webhook.id, status=response.status)
                        return False

        except Exception as e:
            logger.error("Failed to send single webhook", webhook_id=webhook.id, error=str(e))
            return False

    def _create_webhook_signature(self, payload: str, secret: str) -> str:
        return hmac.new(
            secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()


    async def get_user_settings(self, db: AsyncSession, user_id: int) -> NotificationSettings:
        result = await db.execute(
            select(NotificationSettings)
            .where(NotificationSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            settings = NotificationSettings(user_id=user_id)
            db.add(settings)
            await db.commit()
            await db.refresh(settings)

        return settings

    async def update_user_settings(
        self,
        db: AsyncSession,
        user_id: int,
        settings_data: Dict[str, Any]
    ) -> NotificationSettings:
        try:
            settings = await self.get_user_settings(db, user_id)

            for field, value in settings_data.items():
                if hasattr(settings, field):
                    setattr(settings, field, value)

            settings.updated_at = datetime.utcnow()
            await db.commit()
            await db.refresh(settings)

            logger.info("User notification settings updated", user_id=user_id)
            return settings

        except Exception as e:
            await db.rollback()
            logger.error("Failed to update user settings", error=str(e), exc_info=True)
            raise ValidationError("Не удалось обновить настройки")


    async def get_template(self, db: AsyncSession, template_id: str) -> Optional[NotificationTemplate]:
        result = await db.execute(
            select(NotificationTemplate)
            .where(
                and_(
                    NotificationTemplate.template_id == template_id,
                    NotificationTemplate.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()

    async def _render_template(
        self,
        template: NotificationTemplate,
        data: Dict[str, Any],
        channel: NotificationChannel
    ) -> Optional[Dict[str, str]]:
        try:
            channel_template = None

            if channel == NotificationChannel.TELEGRAM:
                channel_template = template.telegram_template
            elif channel == NotificationChannel.EMAIL:
                channel_template = template.email_template
            elif channel == NotificationChannel.PUSH:
                channel_template = template.push_template
            elif channel == NotificationChannel.SMS:
                channel_template = template.sms_template

            if not channel_template:
                return None

            rendered = {}
            for key, template_str in channel_template.items():
                if isinstance(template_str, str):
                    template_obj = Template(template_str)
                    rendered[key] = template_obj.render(**data)
                else:
                    rendered[key] = template_str

            return rendered

        except Exception as e:
            logger.error("Failed to render template", error=str(e))
            return None


    async def _queue_notification(self, db: AsyncSession, notification: Notification):
        try:
            priority_mapping = {
                NotificationPriority.URGENT: 1000,
                NotificationPriority.HIGH: 100,
                NotificationPriority.NORMAL: 10,
                NotificationPriority.LOW: 1
            }

            queue_item = NotificationQueue(
                notification_id=notification.id,
                priority=priority_mapping.get(notification.priority, 10),
                scheduled_at=notification.scheduled_at or datetime.utcnow()
            )

            db.add(queue_item)
            await db.commit()

        except Exception as e:
            logger.error("Failed to queue notification", error=str(e))

    async def process_notification_queue(self, db: AsyncSession, limit: int = 100) -> int:
        try:
            result = await db.execute(
                select(NotificationQueue)
                .where(
                    and_(
                        NotificationQueue.status == "pending",
                        NotificationQueue.scheduled_at <= datetime.utcnow()
                    )
                )
                .order_by(desc(NotificationQueue.priority), NotificationQueue.scheduled_at)
                .limit(limit)
            )
            queue_items = result.scalars().all()

            processed_count = 0
            for item in queue_items:
                try:
                    item.status = "processing"
                    item.processing_started_at = datetime.utcnow()
                    await db.commit()

                    success = await self.send_notification(db, item.notification_id)

                    item.status = "completed" if success else "failed"
                    item.processed_at = datetime.utcnow()
                    item.attempts += 1

                    if not success:
                        item.error_message = "Failed to send notification"

                    await db.commit()
                    processed_count += 1

                except Exception as e:
                    logger.error("Failed to process queue item", item_id=item.id, error=str(e))
                    item.status = "failed"
                    item.processed_at = datetime.utcnow()
                    item.attempts += 1
                    item.error_message = str(e)
                    await db.commit()

            logger.info("Notification queue processed", processed_count=processed_count, total_items=len(queue_items))
            return processed_count

        except Exception as e:
            logger.error("Failed to process notification queue", error=str(e))
            return 0


    def _get_default_channels(self, notification_type: NotificationType) -> List[NotificationChannel]:
        if notification_type in [NotificationType.SECURITY_ALERT, NotificationType.WITHDRAWAL_FAILED]:
            return [NotificationChannel.TELEGRAM, NotificationChannel.EMAIL]

        return [NotificationChannel.TELEGRAM]

    def _load_default_templates(self) -> Dict[str, Dict]:
        return {
            "deposit_received": {
                "telegram": {
                    "title": "💰 Пополнение получено",
                    "message": "На ваш кошелек поступило {{ amount }} {{ currency }}\n\nТранзакция: {{ tx_hash }}"
                }
            },
            "withdrawal_completed": {
                "telegram": {
                    "title": "✅ Вывод выполнен",
                    "message": "Вывод {{ amount }} {{ currency }} успешно выполнен\n\nАдрес: {{ address }}\nТранзакция: {{ tx_hash }}"
                }
            },
            "invoice_paid": {
                "telegram": {
                    "title": "💳 Инвойс оплачен",
                    "message": "Ваш инвойс на {{ amount }} {{ currency }} был оплачен"
                }
            }
        }


notification_service = NotificationService()
