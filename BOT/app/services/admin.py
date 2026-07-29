from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func, text
from sqlalchemy.orm import selectinload
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from decimal import Decimal
import structlog

from app.models.admin import (
    AdminUser, AdminActionLog, SystemConfig, Announcement, SupportTicket,
    SupportMessage, SystemStats, MaintenanceMode,
    AdminRole, AdminPermission, ActionType
)
from app.models.user import User
from app.models.wallet import WalletBalance
from app.models.transaction import Transaction
from app.models.blockchain import BlockchainTransaction, WithdrawalRequest
from app.models.p2p import P2POrder
from app.models.exchange import Exchange
from app.models.api import ApiRequest
from app.config import settings
from app.utils.exceptions import ValidationError, PermissionError

logger = structlog.get_logger(__name__)


class AdminService:
    async def create_admin_user(
        self,
        db: AsyncSession,
        user_id: int,
        role: AdminRole,
        permissions: List[AdminPermission],
        created_by_admin_id: int,
        notes: Optional[str] = None
    ) -> AdminUser:
        try:
            user = await db.get(User, user_id)
            if not user:
                raise ValidationError("Пользователь не найден")

            existing_admin = await self.get_admin_by_user_id(db, user_id)
            if existing_admin:
                raise ValidationError("Пользователь уже является администратором")

            admin_user = AdminUser(
                user_id=user_id,
                role=role,
                permissions=[perm.value for perm in permissions],
                created_by=created_by_admin_id,
                notes=notes,
                is_super_admin=(role == AdminRole.SUPER_ADMIN)
            )

            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)

            await self.log_admin_action(
                db=db,
                admin_user_id=created_by_admin_id,
                action_type=ActionType.USER_CREATED,
                description=f"Created admin user with role {role.value}",
                target_type="admin_user",
                target_id=str(admin_user.id),
                new_data={"role": role.value, "permissions": [p.value for p in permissions]}
            )

            logger.info(
                "Admin user created",
                admin_id=admin_user.id,
                user_id=user_id,
                role=role.value,
                created_by=created_by_admin_id
            )

            return admin_user

        except Exception as e:
            await db.rollback()
            logger.error("Failed to create admin user", error=str(e), exc_info=True)
            raise

    async def get_admin_by_user_id(self, db: AsyncSession, user_id: int) -> Optional[AdminUser]:
        result = await db.execute(
            select(AdminUser)
            .options(selectinload(AdminUser.user))
            .where(AdminUser.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_admin_users(
        self,
        db: AsyncSession,
        role: Optional[AdminRole] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AdminUser]:
        query = select(AdminUser).options(selectinload(AdminUser.user))

        if role:
            query = query.where(AdminUser.role == role)

        if is_active is not None:
            query = query.where(AdminUser.is_active == is_active)

        query = query.order_by(desc(AdminUser.created_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        return result.scalars().all()

    async def update_admin_permissions(
        self,
        db: AsyncSession,
        admin_id: int,
        permissions: List[AdminPermission],
        updated_by_admin_id: int
    ) -> AdminUser:
        try:
            admin_user = await db.get(AdminUser, admin_id)
            if not admin_user:
                raise ValidationError("Администратор не найден")

            old_permissions = admin_user.permissions.copy()
            admin_user.permissions = [perm.value for perm in permissions]
            admin_user.updated_at = datetime.utcnow()

            await db.commit()
            await db.refresh(admin_user)

            await self.log_admin_action(
                db=db,
                admin_user_id=updated_by_admin_id,
                action_type=ActionType.USER_UPDATED,
                description=f"Updated admin permissions",
                target_type="admin_user",
                target_id=str(admin_id),
                old_data={"permissions": old_permissions},
                new_data={"permissions": admin_user.permissions}
            )

            return admin_user

        except Exception as e:
            await db.rollback()
            logger.error("Failed to update admin permissions", error=str(e), exc_info=True)
            raise


    async def log_admin_action(
        self,
        db: AsyncSession,
        admin_user_id: int,
        action_type: ActionType,
        description: str,
        target_type: Optional[str] = None,
        target_id: Optional[str] = None,
        old_data: Optional[Dict[str, Any]] = None,
        new_data: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> AdminActionLog:
        try:
            action_log = AdminActionLog(
                admin_user_id=admin_user_id,
                action_type=action_type,
                description=description,
                target_type=target_type,
                target_id=target_id,
                old_data=old_data,
                new_data=new_data,
                metadata=metadata,
                ip_address=ip_address,
                user_agent=user_agent
            )

            db.add(action_log)
            await db.commit()
            await db.refresh(action_log)

            return action_log

        except Exception as e:
            logger.error("Failed to log admin action", error=str(e), exc_info=True)
            return None

    async def get_admin_action_logs(
        self,
        db: AsyncSession,
        admin_user_id: Optional[int] = None,
        action_type: Optional[ActionType] = None,
        target_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[AdminActionLog]:
        query = select(AdminActionLog).options(selectinload(AdminActionLog.admin_user))

        conditions = []

        if admin_user_id:
            conditions.append(AdminActionLog.admin_user_id == admin_user_id)

        if action_type:
            conditions.append(AdminActionLog.action_type == action_type)

        if target_type:
            conditions.append(AdminActionLog.target_type == target_type)

        if start_date:
            conditions.append(AdminActionLog.created_at >= start_date)

        if end_date:
            conditions.append(AdminActionLog.created_at <= end_date)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(AdminActionLog.created_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        return result.scalars().all()


    async def get_system_config(self, db: AsyncSession, key: str) -> Optional[SystemConfig]:
        result = await db.execute(
            select(SystemConfig).where(SystemConfig.key == key)
        )
        return result.scalar_one_or_none()

    async def set_system_config(
        self,
        db: AsyncSession,
        key: str,
        value: Any,
        description: Optional[str] = None,
        category: str = "general",
        value_type: str = "json",
        updated_by_admin_id: Optional[int] = None
    ) -> SystemConfig:
        try:
            config = await self.get_system_config(db, key)
            old_value = config.value if config else None

            if config:
                config.value = value
                config.description = description or config.description
                config.updated_by = updated_by_admin_id
                config.updated_at = datetime.utcnow()
            else:
                config = SystemConfig(
                    key=key,
                    value=value,
                    description=description,
                    category=category,
                    value_type=value_type,
                    updated_by=updated_by_admin_id
                )
                db.add(config)

            await db.commit()
            await db.refresh(config)

            if updated_by_admin_id:
                await self.log_admin_action(
                    db=db,
                    admin_user_id=updated_by_admin_id,
                    action_type=ActionType.SYSTEM_CONFIG_CHANGED,
                    description=f"Changed system config: {key}",
                    target_type="system_config",
                    target_id=key,
                    old_data={"value": old_value},
                    new_data={"value": value}
                )

            return config

        except Exception as e:
            await db.rollback()
            logger.error("Failed to set system config", error=str(e), exc_info=True)
            raise

    async def get_all_system_configs(
        self,
        db: AsyncSession,
        category: Optional[str] = None,
        is_public: Optional[bool] = None
    ) -> List[SystemConfig]:
        query = select(SystemConfig)

        conditions = []

        if category:
            conditions.append(SystemConfig.category == category)

        if is_public is not None:
            conditions.append(SystemConfig.is_public == is_public)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(SystemConfig.category, SystemConfig.key)

        result = await db.execute(query)
        return result.scalars().all()


    async def create_announcement(
        self,
        db: AsyncSession,
        title: str,
        content: str,
        type: str,
        created_by_admin_id: int,
        priority: str = "normal",
        target_audience: Optional[Dict[str, Any]] = None,
        published_at: Optional[datetime] = None,
        expires_at: Optional[datetime] = None
    ) -> Announcement:
        try:
            announcement = Announcement(
                title=title,
                content=content,
                type=type,
                priority=priority,
                target_audience=target_audience,
                published_at=published_at,
                expires_at=expires_at,
                created_by=created_by_admin_id,
                is_published=published_at is not None
            )

            db.add(announcement)
            await db.commit()
            await db.refresh(announcement)

            await self.log_admin_action(
                db=db,
                admin_user_id=created_by_admin_id,
                action_type=ActionType.ANNOUNCEMENT_CREATED,
                description=f"Created announcement: {title}",
                target_type="announcement",
                target_id=str(announcement.id),
                new_data={"title": title, "type": type, "priority": priority}
            )

            return announcement

        except Exception as e:
            await db.rollback()
            logger.error("Failed to create announcement", error=str(e), exc_info=True)
            raise

    async def get_announcements(
        self,
        db: AsyncSession,
        type: Optional[str] = None,
        is_published: Optional[bool] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Announcement]:
        query = select(Announcement)

        conditions = []

        if type:
            conditions.append(Announcement.type == type)

        if is_published is not None:
            conditions.append(Announcement.is_published == is_published)

        if is_active is not None:
            now = datetime.utcnow()
            if is_active:
                conditions.extend([
                    Announcement.is_published == True,
                    or_(Announcement.published_at.is_(None), Announcement.published_at <= now),
                    or_(Announcement.expires_at.is_(None), Announcement.expires_at > now)
                ])
            else:
                conditions.append(
                    or_(
                        Announcement.is_published == False,
                        and_(Announcement.published_at.is_not(None), Announcement.published_at > now),
                        and_(Announcement.expires_at.is_not(None), Announcement.expires_at <= now)
                    )
                )

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(Announcement.is_pinned), desc(Announcement.created_at))
        query = query.limit(limit).offset(offset)

        result = await db.execute(query)
        return result.scalars().all()


    async def get_support_tickets(
        self,
        db: AsyncSession,
        status: Optional[str] = None,
        priority: Optional[str] = None,
        category: Optional[str] = None,
        assigned_to: Optional[int] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[SupportTicket]:
        query = select(SupportTicket).options(
            selectinload(SupportTicket.user),
            selectinload(SupportTicket.assigned_admin)
        )

        conditions = []

        if status:
            conditions.append(SupportTicket.status == status)

        if priority:
            conditions.append(SupportTicket.priority == priority)

        if category:
            conditions.append(SupportTicket.category == category)

        if assigned_to:
            conditions.append(SupportTicket.assigned_to == assigned_to)

        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(desc(SupportTicket.created_at)).limit(limit).offset(offset)

        result = await db.execute(query)
        return result.scalars().all()

    async def assign_support_ticket(
        self,
        db: AsyncSession,
        ticket_id: int,
        admin_user_id: int,
        assigned_by_admin_id: int
    ) -> SupportTicket:
        try:
            ticket = await db.get(SupportTicket, ticket_id)
            if not ticket:
                raise ValidationError("Тикет не найден")

            old_assigned_to = ticket.assigned_to
            ticket.assigned_to = admin_user_id
            ticket.updated_at = datetime.utcnow()

            if ticket.status == "open":
                ticket.status = "in_progress"

            await db.commit()
            await db.refresh(ticket)

            await self.log_admin_action(
                db=db,
                admin_user_id=assigned_by_admin_id,
                action_type=ActionType.USER_UPDATED,
                description=f"Assigned support ticket #{ticket_id}",
                target_type="support_ticket",
                target_id=str(ticket_id),
                old_data={"assigned_to": old_assigned_to},
                new_data={"assigned_to": admin_user_id}
            )

            return ticket

        except Exception as e:
            await db.rollback()
            logger.error("Failed to assign support ticket", error=str(e), exc_info=True)
            raise


    async def generate_daily_stats(self, db: AsyncSession, date: datetime) -> SystemStats:
        try:
            start_date = date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = start_date + timedelta(days=1)

            total_users_result = await db.execute(select(func.count(User.id)))
            total_users = total_users_result.scalar() or 0

            new_users_result = await db.execute(
                select(func.count(User.id))
                .where(and_(User.created_at >= start_date, User.created_at < end_date))
            )
            new_users = new_users_result.scalar() or 0

            transactions_result = await db.execute(
                select(func.count(Transaction.id), func.sum(Transaction.amount))
                .where(and_(Transaction.created_at >= start_date, Transaction.created_at < end_date))
            )
            transactions_data = transactions_result.first()
            total_transactions = transactions_data[0] or 0
            transaction_volume = transactions_data[1] or Decimal('0')

            deposits_result = await db.execute(
                select(func.count(BlockchainTransaction.id), func.sum(BlockchainTransaction.amount))
                .where(and_(
                    BlockchainTransaction.created_at >= start_date,
                    BlockchainTransaction.created_at < end_date,
                    BlockchainTransaction.from_address != ""
                ))
            )
            deposits_data = deposits_result.first()
            deposits_count = deposits_data[0] or 0
            deposits_volume = deposits_data[1] or Decimal('0')

            withdrawals_result = await db.execute(
                select(func.count(WithdrawalRequest.id), func.sum(WithdrawalRequest.amount))
                .where(and_(
                    WithdrawalRequest.created_at >= start_date,
                    WithdrawalRequest.created_at < end_date
                ))
            )
            withdrawals_data = withdrawals_result.first()
            withdrawals_count = withdrawals_data[0] or 0
            withdrawals_volume = withdrawals_data[1] or Decimal('0')

            p2p_result = await db.execute(
                select(func.count(P2POrder.id), func.sum(P2POrder.amount))
                .where(and_(
                    P2POrder.created_at >= start_date,
                    P2POrder.created_at < end_date
                ))
            )
            p2p_data = p2p_result.first()
            p2p_orders_count = p2p_data[0] or 0
            p2p_volume = p2p_data[1] or Decimal('0')

            exchanges_result = await db.execute(
                select(func.count(Exchange.id), func.sum(Exchange.from_amount))
                .where(and_(
                    Exchange.created_at >= start_date,
                    Exchange.created_at < end_date
                ))
            )
            exchanges_data = exchanges_result.first()
            exchanges_count = exchanges_data[0] or 0
            exchange_volume = exchanges_data[1] or Decimal('0')

            api_requests_result = await db.execute(
                select(func.count(ApiRequest.id))
                .where(and_(
                    ApiRequest.created_at >= start_date,
                    ApiRequest.created_at < end_date
                ))
            )
            api_requests_count = api_requests_result.scalar() or 0

            stats = SystemStats(
                date=start_date,
                total_users=total_users,
                new_users=new_users,
                total_transactions=total_transactions,
                transaction_volume=transaction_volume,
                deposits_count=deposits_count,
                deposits_volume=deposits_volume,
                withdrawals_count=withdrawals_count,
                withdrawals_volume=withdrawals_volume,
                p2p_orders_count=p2p_orders_count,
                p2p_volume=p2p_volume,
                exchanges_count=exchanges_count,
                exchange_volume=exchange_volume,
                api_requests_count=api_requests_count
            )

            db.add(stats)
            await db.commit()
            await db.refresh(stats)

            return stats

        except Exception as e:
            await db.rollback()
            logger.error("Failed to generate daily stats", error=str(e), exc_info=True)
            raise

    async def get_dashboard_stats(self, db: AsyncSession) -> Dict[str, Any]:
        try:
            now = datetime.utcnow()
            today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
            week_start = today_start - timedelta(days=7)
            month_start = today_start - timedelta(days=30)

            total_users = await db.scalar(select(func.count(User.id)))
            total_transactions = await db.scalar(select(func.count(Transaction.id)))

            today_users = await db.scalar(
                select(func.count(User.id))
                .where(User.created_at >= today_start)
            ) or 0

            today_transactions = await db.scalar(
                select(func.count(Transaction.id))
                .where(Transaction.created_at >= today_start)
            ) or 0

            week_users = await db.scalar(
                select(func.count(User.id))
                .where(User.created_at >= week_start)
            ) or 0

            active_tickets = await db.scalar(
                select(func.count(SupportTicket.id))
                .where(SupportTicket.status.in_(["open", "in_progress"]))
            ) or 0

            return {
                "total_users": total_users or 0,
                "total_transactions": total_transactions or 0,
                "today_users": today_users,
                "today_transactions": today_transactions,
                "week_users": week_users,
                "active_tickets": active_tickets,
                "system_status": "operational"
            }

        except Exception as e:
            logger.error("Failed to get dashboard stats", error=str(e), exc_info=True)
            return {}


    async def enable_maintenance_mode(
        self,
        db: AsyncSession,
        title: str,
        message: str,
        admin_user_id: int,
        estimated_end_at: Optional[datetime] = None,
        allowed_users: Optional[List[int]] = None
    ) -> MaintenanceMode:
        try:
            await db.execute(
                text("UPDATE maintenance_mode SET is_enabled = false, ended_at = :now WHERE is_enabled = true")
                .bindparam(now=datetime.utcnow())
            )

            maintenance = MaintenanceMode(
                is_enabled=True,
                title=title,
                message=message,
                started_at=datetime.utcnow(),
                estimated_end_at=estimated_end_at,
                allowed_users=allowed_users or [],
                created_by=admin_user_id
            )

            db.add(maintenance)
            await db.commit()
            await db.refresh(maintenance)

            await self.log_admin_action(
                db=db,
                admin_user_id=admin_user_id,
                action_type=ActionType.MAINTENANCE_STARTED,
                description="Enabled maintenance mode",
                target_type="maintenance_mode",
                target_id=str(maintenance.id),
                new_data={"title": title, "estimated_end_at": estimated_end_at.isoformat() if estimated_end_at else None}
            )

            return maintenance

        except Exception as e:
            await db.rollback()
            logger.error("❌ Не удалось включить режим обслуживания", error=str(e), exc_info=True)
            raise

    async def disable_maintenance_mode(self, db: AsyncSession, admin_user_id: int) -> bool:
        try:
            result = await db.execute(
                text("UPDATE maintenance_mode SET is_enabled = false, ended_at = :now WHERE is_enabled = true")
                .bindparam(now=datetime.utcnow())
            )

            await db.commit()

            if result.rowcount > 0:
                await self.log_admin_action(
                    db=db,
                    admin_user_id=admin_user_id,
                    action_type=ActionType.MAINTENANCE_ENDED,
                    description="Disabled maintenance mode",
                    target_type="maintenance_mode"
                )

            return result.rowcount > 0

        except Exception as e:
            await db.rollback()
            logger.error("❌ Не удалось отключить режим обслуживания", error=str(e), exc_info=True)
            raise

    async def get_current_maintenance_mode(self, db: AsyncSession) -> Optional[MaintenanceMode]:
        result = await db.execute(
            select(MaintenanceMode)
            .where(MaintenanceMode.is_enabled == True)
            .order_by(desc(MaintenanceMode.created_at))
        )
        return result.scalar_one_or_none()


admin_service = AdminService()
