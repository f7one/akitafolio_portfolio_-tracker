"""
DeFi service for protocol position fetching.
"""

import asyncio
import logging
from typing import List, Optional

from web3 import Web3

from akitafolio.cache import cached, defi_cache
from akitafolio.config import settings
from akitafolio.limits import rpc_executor
from akitafolio.models import DefiPortfolio, DefiPosition
from akitafolio.services.blockchain import BlockchainService

logger = logging.getLogger(__name__)


# Aave V3 Pool ABI
AAVE_V3_POOL_ABI = [
    {
        "inputs": [{"internalType": "address", "name": "user", "type": "address"}],
        "name": "getUserAccountData",
        "outputs": [
            {"internalType": "uint256", "name": "totalCollateralBase", "type": "uint256"},
            {"internalType": "uint256", "name": "totalDebtBase", "type": "uint256"},
            {"internalType": "uint256", "name": "availableBorrowsBase", "type": "uint256"},
            {"internalType": "uint256", "name": "currentLiquidationThreshold", "type": "uint256"},
            {"internalType": "uint256", "name": "ltv", "type": "uint256"},
            {"internalType": "uint256", "name": "healthFactor", "type": "uint256"},
        ],
        "stateMutability": "view",
        "type": "function",
    }
]


class DefiService:
    """Service for DeFi protocol interactions."""

    @classmethod
    def _format_health_factor(cls, health_factor_raw: int) -> tuple[Optional[float], str]:
        """Format health factor from raw value."""
        # Health factor is in 1e18 format
        health_factor = health_factor_raw / 1e18

        # Very high value indicates no debt (infinity)
        if health_factor > 1e10:
            return None, "∞ (No Debt)"

        # Format with risk indicator
        if health_factor >= 2.0:
            return health_factor, f"✅ {health_factor:.2f} (Safe)"
        elif health_factor >= 1.5:
            return health_factor, f"⚠️ {health_factor:.2f} (Low)"
        else:
            return health_factor, f"🚨 {health_factor:.2f} (RISKY!)"

    @classmethod
    @cached(cache=defi_cache, ttl=120.0, key_prefix="aave_position")
    async def get_aave_v3_position(cls, address: str, chain: str) -> DefiPosition:
        """Fetch Aave V3 position for an address on a chain."""
        defi_protocols = settings.get_defi_protocols()

        if chain not in defi_protocols:
            return DefiPosition(
                protocol="Aave V3",
                chain=chain,
                address=address,
                error=f"Aave V3 not supported on {chain}",
            )

        try:
            web3_instances = BlockchainService.get_web3_instances()
            w3 = web3_instances[chain]

            pool_address = defi_protocols[chain]["aave_v3_pool"]
            pool_contract = w3.eth.contract(
                address=Web3.to_checksum_address(pool_address), abi=AAVE_V3_POOL_ABI
            )

            checksum_addr = Web3.to_checksum_address(address)
            account_data = await rpc_executor.run(
                pool_contract.functions.getUserAccountData(checksum_addr).call
            )

            # Parse response (values are in 8 decimal base currency - USD)
            collateral_usd = account_data[0] / 1e8
            debt_usd = account_data[1] / 1e8
            available_borrows = account_data[2] / 1e8
            liquidation_threshold = account_data[3] / 100  # Convert to percentage
            ltv = account_data[4] / 100  # Convert to percentage
            health_factor_raw = account_data[5]

            health_factor, health_factor_display = cls._format_health_factor(health_factor_raw)

            return DefiPosition(
                protocol="Aave V3",
                chain=chain,
                address=address,
                collateral_usd=collateral_usd,
                debt_usd=debt_usd,
                net_value_usd=collateral_usd - debt_usd,
                health_factor=health_factor,
                health_factor_display=health_factor_display,
                available_borrows_usd=available_borrows,
                ltv=ltv,
                liquidation_threshold=liquidation_threshold,
            )
        except Exception as e:
            logger.error(f"Error fetching Aave V3 position on {chain}: {e}")
            return DefiPosition(protocol="Aave V3", chain=chain, address=address, error=str(e))

    @classmethod
    async def get_all_defi_positions(cls, addresses: List[str]) -> DefiPortfolio:
        """Fetch all DeFi positions for user's addresses."""
        defi_protocols = settings.get_defi_protocols()
        supported_chains = list(defi_protocols.keys())

        # Fetch positions in parallel
        tasks = []
        for address in addresses:
            for chain in supported_chains:
                tasks.append(cls.get_aave_v3_position(address, chain))

        positions: List[DefiPosition] = []
        errors: List[str] = []

        if tasks:
            results = await asyncio.gather(*tasks)

            # Filter to positions with actual value
            for result in results:
                if result.error:
                    errors.append(result.error)
                if result.has_position and result.error is None:
                    positions.append(result)

        # Calculate totals
        total_collateral = sum(p.collateral_usd for p in positions)
        total_debt = sum(p.debt_usd for p in positions)
        total_net = sum(p.net_value_usd for p in positions)

        return DefiPortfolio(
            total_collateral_usd=total_collateral,
            total_debt_usd=total_debt,
            total_net_value_usd=total_net,
            position_count=len(positions),
            positions=positions,
            errors=errors,
        )
