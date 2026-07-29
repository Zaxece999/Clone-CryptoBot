import structlog
import aiohttp
import asyncio
from typing import Dict, Optional
from decimal import Decimal
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.services.balance_checker import get_all_wallets_balances

logger = structlog.get_logger(__name__)

class BalanceSyncService:
    def __init__(self):
        self.webapp_url = getattr(settings, 'webapp_url', 'http://127.0.0.1:5000')
        self.sync_timeout = 10

    async def sync_user_balances_to_webapp(self, db: AsyncSession, user_id: int) -> bool:
        try:
            logger.info("Starting balance sync to webapp", user_id=user_id)

            balances = await get_all_wallets_balances(db, user_id)

            if not balances:
                logger.info("No balances found for user", user_id=user_id)
                return True

            sync_data = {}
            for currency, (balance, usd_value, frozen_balance) in balances.items():
                if balance != "ERROR":
                    try:
                        sync_data[currency] = float(balance)
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to convert balance for {currency}", error=str(e))
                        continue

            if not sync_data:
                logger.info("No valid balances to sync", user_id=user_id)
                return True

            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.sync_timeout)) as session:
                url = f"{self.webapp_url}/api/balances/sync"
                payload = {
                    "user_id": user_id,
                    "balances": sync_data
                }

                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(
                            "Balance sync successful",
                            user_id=user_id,
                            currencies=list(sync_data.keys()),
                            result=result
                        )
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(
                            "Balance sync failed",
                            user_id=user_id,
                            status=response.status,
                            error=error_text
                        )
                        return False

        except asyncio.TimeoutError:
            logger.error("Balance sync timeout", user_id=user_id, timeout=self.sync_timeout)
            return False
        except Exception as e:
            logger.error("Balance sync error", user_id=user_id, error=str(e))
            return False

    async def get_webapp_balances(self, user_id: int) -> Optional[Dict[str, float]]:
        try:
            async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=self.sync_timeout)) as session:
                url = f"{self.webapp_url}/api/balances/user/{user_id}"

                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get('balances', {})
                    else:
                        logger.error(
                            "Failed to get webapp balances",
                            user_id=user_id,
                            status=response.status
                        )
                        return None

        except Exception as e:
            logger.error("Error getting webapp balances", user_id=user_id, error=str(e))
            return None

    async def sync_balances_bidirectional(self, db: AsyncSession, user_id: int) -> bool:
        try:
            bot_to_webapp_success = await self.sync_user_balances_to_webapp(db, user_id)

            if not bot_to_webapp_success:
                logger.warning("Bot to webapp sync failed", user_id=user_id)
                return False

            logger.info("Bidirectional balance sync completed", user_id=user_id)
            return True

        except Exception as e:
            logger.error("Bidirectional sync error", user_id=user_id, error=str(e))
            return False

balance_sync_service = BalanceSyncService()
