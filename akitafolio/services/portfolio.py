"""
Portfolio service for aggregating all portfolio data.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

from akitafolio.models import (
    ChainBalance,
    DefiPortfolio,
    Portfolio,
    PortfolioChange,
    PortfolioSnapshot,
    TokenPortfolio,
    UserAddresses,
)
from akitafolio.services.bitcoin import BitcoinService
from akitafolio.services.blockchain import BlockchainService
from akitafolio.services.defi import DefiService
from akitafolio.services.prices import PriceService
from akitafolio.services.tokens import TokenService
from akitafolio.storage import load_portfolio_history, save_portfolio_snapshot

logger = logging.getLogger(__name__)


class PortfolioService:
    """Service for aggregating portfolio data from all sources."""

    @classmethod
    async def get_portfolio(
        cls, addresses: UserAddresses, include_tokens: bool = True, include_defi: bool = True
    ) -> Portfolio:
        """
        Fetch complete portfolio data for a user.

        Args:
            addresses: User's saved addresses
            include_tokens: Whether to include ERC20 token balances
            include_defi: Whether to include DeFi positions

        Returns:
            Complete Portfolio object with all data
        """
        # Fetch prices first
        prices = await PriceService.get_crypto_prices()

        # Prepare tasks for parallel execution
        tasks = {}

        # ETH balances (always fetch if addresses exist)
        if addresses.eth:
            tasks["eth"] = asyncio.create_task(cls._get_eth_balances(addresses.eth))

        # BTC balances
        if addresses.btc or addresses.xpub:
            tasks["btc"] = asyncio.create_task(
                BitcoinService.get_total_btc_balance(addresses.btc, addresses.xpub)
            )

        # Token balances
        if include_tokens and addresses.eth:
            tasks["tokens"] = asyncio.create_task(
                TokenService.get_all_token_balances(addresses.eth, addresses.tokens)
            )

        # DeFi positions
        if include_defi and addresses.track_defi and addresses.eth:
            tasks["defi"] = asyncio.create_task(DefiService.get_all_defi_positions(addresses.eth))

        # Wait for all tasks
        results = {}
        errors: list[str] = []
        for name, task in tasks.items():
            try:
                results[name] = await task
            except Exception:
                logger.error("Error fetching portfolio source: %s", name)
                results[name] = None
                errors.append(f"{name} data is unavailable")

        if prices.error:
            errors.append(prices.error)

        # Process ETH results
        total_eth = 0.0
        chain_balances: List[ChainBalance] = []

        if "eth" in results and results["eth"]:
            for addr_result in results["eth"]:
                if addr_result.error:
                    errors.append("Some network balances are unavailable")
                if addr_result.error is None:
                    total_eth += addr_result.total_eth
                    chain_balances.extend(addr_result.chain_balances)

        # Process BTC results
        total_btc_single = 0.0
        total_btc_xpub = 0.0

        if "btc" in results and results["btc"]:
            btc_data = results["btc"]
            if btc_data.get("errors"):
                errors.append("Some Bitcoin balances are unavailable")
            total_btc_single = btc_data.get("total_single", 0)
            total_btc_xpub = btc_data.get("total_xpub", 0)

        total_btc = total_btc_single + total_btc_xpub

        # Calculate USD values
        total_eth_usd = total_eth * prices.eth
        total_btc_usd = total_btc * prices.btc
        total_portfolio_usd = total_eth_usd + total_btc_usd

        # Process tokens
        tokens: Optional[TokenPortfolio] = None
        if "tokens" in results and results["tokens"]:
            tokens = results["tokens"]
            if tokens.errors:
                errors.append("Some token balances are unavailable")
            total_portfolio_usd += tokens.total_value_usd

        # Process DeFi
        defi: Optional[DefiPortfolio] = None
        if "defi" in results and results["defi"]:
            defi = results["defi"]
            if defi.errors:
                errors.append("Some DeFi positions are unavailable")
            total_portfolio_usd += defi.total_net_value_usd

        return Portfolio(
            total_eth=total_eth,
            total_btc_single=total_btc_single,
            total_btc_xpub=total_btc_xpub,
            total_btc_combined=total_btc,
            total_eth_usd=total_eth_usd,
            total_btc_usd=total_btc_usd,
            total_portfolio_usd=total_portfolio_usd,
            eth_price=prices.eth,
            btc_price=prices.btc,
            chain_balances=chain_balances,
            tokens=tokens,
            defi=defi,
            errors=list(dict.fromkeys(errors)),
            is_complete=not errors,
        )

    @classmethod
    async def _get_eth_balances(cls, addresses: List[str]):
        """Get ETH balances for multiple addresses."""
        tasks = [BlockchainService.get_all_chain_balances(addr) for addr in addresses]
        return await asyncio.gather(*tasks)

    @classmethod
    def calculate_24h_change(cls, user_id: int, current_value_usd: float) -> PortfolioChange:
        """Calculate 24h portfolio value change."""
        try:
            history = load_portfolio_history(user_id)

            if not history or len(history) < 2:
                return PortfolioChange(has_data=False)

            # Find snapshot closest to 24 hours ago
            now = datetime.now()
            target_time = now - timedelta(hours=24)

            closest_snapshot: Optional[PortfolioSnapshot] = None
            min_diff = float("inf")

            for snapshot in history:
                time_diff = abs((target_time - snapshot.timestamp).total_seconds())
                if time_diff < min_diff:
                    min_diff = time_diff
                    closest_snapshot = snapshot

            if not closest_snapshot:
                return PortfolioChange(has_data=False)

            old_value = closest_snapshot.total_value_usd
            change_usd = current_value_usd - old_value
            change_percent = (change_usd / old_value * 100) if old_value > 0 else 0

            return PortfolioChange(
                has_data=True,
                change_usd=change_usd,
                change_percent=change_percent,
                old_value=old_value,
                hours_ago=min_diff / 3600,
            )
        except Exception as e:
            logger.error(f"Error calculating 24h change: {e}")
            return PortfolioChange(has_data=False)

    @classmethod
    def save_snapshot(cls, user_id: int, portfolio: Portfolio) -> bool:
        """Save portfolio snapshot for historical tracking."""
        return save_portfolio_snapshot(
            user_id=user_id,
            total_value_usd=portfolio.total_portfolio_usd,
            eth_amount=portfolio.total_eth,
            btc_amount=portfolio.total_btc_combined,
            eth_price=portfolio.eth_price,
            btc_price=portfolio.btc_price,
        )
