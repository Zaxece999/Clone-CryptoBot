import aiohttp
from typing import Optional
import structlog
from decimal import Decimal
import os
from app.config import settings

logger = structlog.get_logger(__name__)

class ExchangeRateService:
    def __init__(self):
        self.logger = logger
        self.base_url = settings.coinmarketcap_base_url
        self.api_key = settings.coinmarketcap_api_key

    async def _fetch_cmc_price(self, session: aiohttp.ClientSession, symbol: str, convert: str) -> Optional[float]:
        url = f"{self.base_url}/cryptocurrency/quotes/latest"
        headers = {"X-CMC_PRO_API_KEY": self.api_key}
        params = {"symbol": symbol, "convert": convert}
        try:
            async with session.get(url, headers=headers, params=params, timeout=15) as resp:
                data = await resp.json()
                price = data["data"][symbol]["quote"][convert]["price"]
                return float(price)
        except Exception as e:
            self.logger.warning("CMC fetch failed, fallback to static", error=str(e))
            return None

    async def get_exchange_rate(self, crypto_currency: str, fiat_currency: str = "USD") -> Optional[float]:
        crypto = crypto_currency.upper()
        fiat = fiat_currency.upper()
        try:
            if self.api_key:
                async with aiohttp.ClientSession() as session:
                    price = await self._fetch_cmc_price(session, crypto, fiat)
                    if price is not None:
                        return price
            rates = {
                "BTC": 45000.0,
                "ETH": 3000.0,
                "USDT": 1.0,
                "LTC": 150.0,
                "BNB": 350.0,
                "TRX": 0.10,
                "TON": 2.0
            }
            return rates.get(crypto, 0.0)
        except Exception as e:
            self.logger.error(
                "Failed to get exchange rate",
                crypto=crypto,
                fiat=fiat,
                error=str(e)
            )
            return None

    async def get_multiple_rates(self, symbols: list, fiat_currency: str = "USD") -> dict:
        result = {}
        fiat = fiat_currency.upper()
        if self.api_key:
            async with aiohttp.ClientSession() as session:
                for sym in symbols:
                    price = await self._fetch_cmc_price(session, sym.upper(), fiat)
                    if price is None:
                        price = await self.get_exchange_rate(sym, fiat)
                    result[sym.upper()] = float(price) if price is not None else 0.0
            return result
        for sym in symbols:
            price = await self.get_exchange_rate(sym, fiat)
            result[sym.upper()] = float(price) if price is not None else 0.0
        return result

exchange_rate_service = ExchangeRateService()
