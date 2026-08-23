"""
Price service for fetching cryptocurrency prices.
"""

import logging
from typing import Dict

from akitafolio.cache import cached, price_cache
from akitafolio.http_client import HTTPClient
from akitafolio.models import CryptoPrices

logger = logging.getLogger(__name__)


class PriceService:
    """Service for fetching cryptocurrency prices from CoinGecko."""

    COINGECKO_BASE_URL = "https://api.coingecko.com/api/v3"

    @staticmethod
    @cached(cache=price_cache, ttl=30.0, key_prefix="prices")
    async def get_crypto_prices() -> CryptoPrices:
        """Fetch current ETH and BTC prices in USD."""
        try:
            url = f"{PriceService.COINGECKO_BASE_URL}/simple/price?ids=ethereum,bitcoin&vs_currencies=usd"
            data = await HTTPClient.get(url, timeout=10)
            return CryptoPrices(
                eth=float(data.get("ethereum", {}).get("usd", 0)),
                btc=float(data.get("bitcoin", {}).get("usd", 0)),
            )
        except Exception as e:
            logger.error(f"Error fetching crypto prices: {e}")
            return CryptoPrices()

    @staticmethod
    @cached(cache=price_cache, ttl=30.0, key_prefix="token_price")
    async def get_token_price(coingecko_id: str) -> float:
        """Fetch price for a specific token by CoinGecko ID."""
        try:
            url = f"{PriceService.COINGECKO_BASE_URL}/simple/price?ids={coingecko_id}&vs_currencies=usd"
            data = await HTTPClient.get(url, timeout=10)
            return float(data.get(coingecko_id, {}).get("usd", 0))
        except Exception as e:
            logger.error(f"Error fetching price for {coingecko_id}: {e}")
            return 0.0

    @staticmethod
    @cached(cache=price_cache, ttl=60.0, key_prefix="multi_prices")
    async def get_multiple_prices(coingecko_ids: tuple) -> Dict[str, float]:
        """Fetch prices for multiple tokens at once."""
        try:
            ids_param = ",".join(coingecko_ids)
            url = (
                f"{PriceService.COINGECKO_BASE_URL}/simple/price?ids={ids_param}&vs_currencies=usd"
            )
            data = await HTTPClient.get(url, timeout=15)
            return {coin_id: float(prices.get("usd", 0)) for coin_id, prices in data.items()}
        except Exception as e:
            logger.error(f"Error fetching multiple prices: {e}")
            return {}
