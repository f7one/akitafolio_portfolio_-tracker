"""
Blockchain service for EVM chain interactions.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from web3 import Web3

from akitafolio.cache import balance_cache, cached
from akitafolio.config import settings
from akitafolio.exceptions import ValidationError
from akitafolio.models import AggregatedBalance, ChainBalance

logger = logging.getLogger(__name__)


class BlockchainService:
    """Service for interacting with EVM blockchains."""

    _web3_instances: Optional[Dict[str, Web3]] = None

    @classmethod
    def get_web3_instances(cls) -> Dict[str, Web3]:
        """Get or create Web3 instances for all chains."""
        if cls._web3_instances is None:
            all_chains = settings.get_all_chains()
            cls._web3_instances = {
                chain: Web3(Web3.HTTPProvider(config["rpc_url"]))
                for chain, config in all_chains.items()
            }
        return cls._web3_instances

    @staticmethod
    def is_valid_address(address: str) -> bool:
        """Validate Ethereum address format."""
        try:
            if not address:
                return False
            return Web3.is_address(address)
        except Exception:
            return False

    @staticmethod
    def checksum_address(address: str) -> str:
        """Convert address to checksum format."""
        if not BlockchainService.is_valid_address(address):
            raise ValidationError(f"Invalid Ethereum address: {address}")
        return Web3.to_checksum_address(address)

    @classmethod
    @cached(cache=balance_cache, ttl=60.0, key_prefix="chain_balance")
    async def get_chain_balance(cls, address: str, chain: str) -> ChainBalance:
        """Fetch balance for address on a specific chain."""
        all_chains = settings.get_all_chains()

        if chain not in all_chains:
            return ChainBalance(
                chain=chain,
                address=address,
                balance=0.0,
                currency="",
                network=chain,
                emoji="❓",
                error=f"Unsupported chain: {chain}",
            )

        try:
            chain_config = all_chains[chain]
            w3 = cls.get_web3_instances()[chain]

            checksum_addr = Web3.to_checksum_address(address)
            balance_wei = w3.eth.get_balance(checksum_addr)
            balance = float(w3.from_wei(balance_wei, "ether"))

            return ChainBalance(
                chain=chain,
                address=address,
                balance=balance,
                currency=chain_config["symbol"],
                network=chain_config["name"],
                emoji=chain_config["emoji"],
                counts_as_eth=chain_config["counts_as_eth"],
            )
        except Exception as e:
            logger.error(f"Error fetching {chain} balance for {address}: {e}")
            chain_config = all_chains.get(chain, {})
            return ChainBalance(
                chain=chain,
                address=address,
                balance=0.0,
                currency=chain_config.get("symbol", ""),
                network=chain_config.get("name", chain),
                emoji=chain_config.get("emoji", "❓"),
                counts_as_eth=chain_config.get("counts_as_eth", False),
                error=str(e),
            )

    @classmethod
    async def get_all_chain_balances(cls, address: str) -> AggregatedBalance:
        """Fetch balances from all chains and aggregate."""
        if not cls.is_valid_address(address):
            return AggregatedBalance(address=address, error="Invalid address format")

        all_chains = settings.get_all_chains()

        # Fetch all chain balances in parallel
        tasks = [cls.get_chain_balance(address, chain) for chain in all_chains.keys()]
        results = await asyncio.gather(*tasks)

        # Aggregate ETH balances
        total_eth = 0.0
        chain_balances = []

        for result in results:
            chain_balances.append(result)
            if result.counts_as_eth and result.error is None:
                total_eth += result.balance

        return AggregatedBalance(
            address=address, total_eth=total_eth, chain_balances=chain_balances
        )

    @classmethod
    async def get_multi_address_balances(cls, addresses: List[str]) -> Dict[str, AggregatedBalance]:
        """Fetch balances for multiple addresses."""
        tasks = [cls.get_all_chain_balances(addr) for addr in addresses]
        results = await asyncio.gather(*tasks)
        return {addr: result for addr, result in zip(addresses, results)}
