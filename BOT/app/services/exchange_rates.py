import structlog
import asyncio
import aiohttp
from typing import Dict, Optional, List
from decimal import Decimal
from datetime import datetime, timedelta

logger = structlog.get_logger(__name__)

class ExchangeRateService:
    def __init__(self):
        self.cache = {}
        self.cache_time = {}
        self.cache_ttl = 300

    async def get_exchange_rate(self, from_currency: str, to_currency: str = "USD") -> Optional[float]:
        cache_key = f"{from_currency}_{to_currency}"

        if (cache_key in self.cache_time and
            (datetime.now() - self.cache_time[cache_key]).total_seconds() < self.cache_ttl):
            logger.debug(
                "Using cached exchange rate",
                from_currency=from_currency,
                to_currency=to_currency,
                rate=self.cache[cache_key]
            )
            return self.cache[cache_key]

        try:
            async with aiohttp.ClientSession() as session:
                coin_ids = {
                    "BTC": "bitcoin",
                    "ETH": "ethereum",
                    "LTC": "litecoin",
                    "USDT": "tether",
                    "USDC": "usd-coin",
                    "BNB": "binancecoin",
                    "TRX": "tron",
                    "TON": "the-open-network",
                    "DOGE": "dogecoin",
                    "SOL": "solana",
                    "NOT": "notcoin",
                    "TRUMP": "trump",
                    "MELANIA": "melania-coin",
                    "PEPE": "pepe",
                    "WIF": "dogwifhat",
                    "BONK": "bonk",
                    "MAJOR": "major",
                    "MY": "mytoken",
                    "DOGS": "dogs",
                    "MEMHASH": "memhash",
                    "HMSTR": "hamster-kombat",
                    "CATI": "catizen",
                    "GRAM": "gram-token"
                }

                coin_id = coin_ids.get(from_currency.upper())
                if not coin_id:
                    logger.warning("Unknown currency", currency=from_currency)
                    return None

                url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies={to_currency.lower()}"

                async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        data = await response.json()

                        if coin_id in data and to_currency.lower() in data[coin_id]:
                            rate = float(data[coin_id][to_currency.lower()])

                            self.cache[cache_key] = rate
                            self.cache_time[cache_key] = datetime.now()

                            logger.info(
                                "Exchange rate retrieved",
                                from_currency=from_currency,
                                to_currency=to_currency,
                                rate=rate
                            )

                            return rate
                        else:
                            logger.warning(
                                "Rate not found in response",
                                from_currency=from_currency,
                                to_currency=to_currency,
                                response=data
                            )
                            return None
                    else:
                        logger.error(
                            "Failed to get exchange rate",
                            from_currency=from_currency,
                            to_currency=to_currency,
                            status=response.status,
                            response=await response.text()
                        )
                        return None

        except Exception as e:
            logger.error(
                "Error getting exchange rate",
                from_currency=from_currency,
                to_currency=to_currency,
                error=str(e)
            )
            return None

    async def get_multiple_rates(self, currencies: List[str], to_currency: str = "USD") -> Dict[str, float]:
        results = {}

        tasks = [self.get_exchange_rate(currency, to_currency) for currency in currencies]
        rates = await asyncio.gather(*tasks, return_exceptions=True)

        for currency, rate in zip(currencies, rates):
            if isinstance(rate, Exception):
                logger.error("Failed to get rate", currency=currency, error=str(rate))
            elif rate is not None:
                results[currency] = rate

        return results

    def clear_cache(self):
        self.cache.clear()
        self.cache_time.clear()
        logger.info("🧹 Кэш курсов валют очищен")


exchange_rate_service = ExchangeRateService()
