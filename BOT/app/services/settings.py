from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
import structlog

from app.models.user import User
from app.models.settings import (
    UserSettings,
    ReferralStats,
    NotificationPreferences,
    ReferralPeriod,
    NotificationSubtype
)

logger = structlog.get_logger(__name__)


class SettingsService:
    async def get_or_create_user_settings(
        self,
        db: AsyncSession,
        user_id: int
    ) -> UserSettings:

        result = await db.execute(
            select(UserSettings)
            .options(selectinload(UserSettings.notification_preferences))
            .where(UserSettings.user_id == user_id)
        )
        settings = result.scalar_one_or_none()

        if not settings:
            settings = UserSettings(user_id=user_id)
            db.add(settings)
            await db.flush()

            notification_prefs = NotificationPreferences(user_settings_id=settings.id)
            db.add(notification_prefs)
            await db.commit()

            result = await db.execute(
                select(UserSettings)
                .options(selectinload(UserSettings.notification_preferences))
                .where(UserSettings.id == settings.id)
            )
            settings = result.scalar_one()

            logger.info(
                "User settings created",
                user_id=user_id,
                settings_id=settings.id
            )

        return settings

    async def update_user_settings(
        self,
        db: AsyncSession,
        user_id: int,
        **kwargs
    ) -> UserSettings:

        settings = await self.get_or_create_user_settings(db, user_id)

        for field, value in kwargs.items():
            if hasattr(settings, field):
                setattr(settings, field, value)

        await db.commit()

        logger.info(
            "User settings updated",
            user_id=user_id,
            updated_fields=list(kwargs.keys())
        )

        return settings

    async def get_user_with_settings(
        self,
        db: AsyncSession,
        user_id: int
    ) -> Optional[User]:

        result = await db.execute(
            select(User)
            .options(
                selectinload(User.user_settings).selectinload(UserSettings.notification_preferences)
            )
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def generate_referral_links(
        self,
        user: User
    ) -> Dict[str, str]:

        if not user.referral_code:
            user.generate_referral_code()

        referral_code = user.referral_code.replace('REF', '').lower()

        return {
            'basic': f't.me/send?start=r-{referral_code}',
            'market': f't.me/send?start=r-{referral_code}-market',
            'exchange': f't.me/send?start=r-{referral_code}-exchange'
        }

    async def get_referral_stats(
        self,
        db: AsyncSession,
        user_id: int,
        period: ReferralPeriod = ReferralPeriod.ALL_TIME
    ) -> Dict[str, Any]:

        result = await db.execute(
            select(ReferralStats).where(
                and_(
                    ReferralStats.user_id == user_id,
                    ReferralStats.period == period
                )
            )
        )
        stats = result.scalar_one_or_none()

        if not stats:
            now = datetime.utcnow()
            period_start, period_end = self._get_period_dates(period, now)

            stats = ReferralStats(
                user_id=user_id,
                period=period,
                period_start=period_start,
                period_end=period_end
            )
            db.add(stats)
            await db.commit()

        return {
            'invited_count': stats.invited_count,
            'active_users_count': stats.active_users_count,
            'earnings_usd': stats.earnings_usd,
            'period': period.value
        }

    async def update_notification_preference(
        self,
        db: AsyncSession,
        user_id: int,
        subtype: NotificationSubtype,
        enabled: Optional[bool] = None,
        sound: Optional[bool] = None
    ) -> NotificationPreferences:

        settings = await self.get_or_create_user_settings(db, user_id)

        if not settings.notification_preferences:
            notification_prefs = NotificationPreferences(user_settings_id=settings.id)
            db.add(notification_prefs)
            await db.flush()
            settings.notification_preferences = notification_prefs

        settings.notification_preferences.update_notification_setting(
            subtype, enabled, sound
        )

        await db.commit()

        logger.info(
            "Notification preference updated",
            user_id=user_id,
            subtype=subtype.value,
            enabled=enabled,
            sound=sound
        )

        return settings.notification_preferences

    async def get_notification_preference(
        self,
        db: AsyncSession,
        user_id: int,
        subtype: NotificationSubtype
    ) -> Dict[str, bool]:

        settings = await self.get_or_create_user_settings(db, user_id)

        if not settings.notification_preferences:
            return {'enabled': True, 'sound': True}

        return settings.notification_preferences.get_notification_setting(subtype)

    def _get_period_dates(self, period: ReferralPeriod, now: datetime) -> tuple:
        if period == ReferralPeriod.ALL_TIME:
            return datetime(2020, 1, 1), now
        elif period == ReferralPeriod.YESTERDAY:
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
            end = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
            return start, end
        elif period == ReferralPeriod.WEEK:
            week_start = now - timedelta(days=now.weekday())
            start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            return start, now
        elif period == ReferralPeriod.MONTH:
            month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            return month_start, now

        return now, now

    async def get_supported_currencies(self) -> List[str]:
        return [
            "RUB", "USD", "EUR", "BYN",
            "UAH", "GBP", "CNY", "KZT",
            "UZS", "GEL", "TRY", "AMD",
            "THB", "INR", "BRL", "IDR",
            "AZN", "AED", "PLN", "ILS",
            "KGS", "TJS"
        ]

    async def get_supported_languages(self) -> List[Dict[str, str]]:
        return [
            {"code": "en", "name": "English", "flag": "🇺🇸"},
            {"code": "ru", "name": "Русский", "flag": "🇷🇺"}
        ]


settings_service = SettingsService()
