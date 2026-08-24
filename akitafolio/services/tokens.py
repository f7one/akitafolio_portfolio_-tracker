"""
Token service for ERC20 token balance fetching.
"""

import asyncio
import logging
from typing import Dict, List, Optional

from web3 import Web3

from akitafolio.cache import cached, token_cache
from akitafolio.config import settings
from akitafolio.limits import rpc_executor
from akitafolio.models import TokenBalance, TokenPortfolio
from akitafolio.services.blockchain import BlockchainService
from akitafolio.services.prices import PriceService

logger = logging.getLogger(__name__)


# Minimal ERC20 ABI
ERC20_ABI = [
    {
        "constant": True,
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "type": "function",
    },
    {
        "constant": True,
        "inputs": [],
        "name": "symbol",
        "outputs": [{"name": "", "type": "string"}],
        "type": "function",
    },
]


class TokenService:
    """Service for ERC20 token operations."""

    @classmethod
    @cached(cache=token_cache, ttl=60.0, key_prefix="token_balance")
    async def get_token_balance(
        cls,
        address: str,
        token_address: str,
        chain: str,
        decimals: int,
        symbol: str,
        coingecko_id: str,
    ) -> TokenBalance:
        """Fetch ERC20 token balance for an address."""
        try:
            web3_instances = BlockchainService.get_web3_instances()

            if chain not in web3_instances:
                return TokenBalance(
                    symbol=symbol,
                    address=token_address,
                    chain=chain,
                    decimals=decimals,
                    error=f"Unsupported chain: {chain}",
                )

            w3 = web3_instances[chain]
            checksum_addr = Web3.to_checksum_address(address)
            token_checksum = Web3.to_checksum_address(token_address)

            contract = w3.eth.contract(address=token_checksum, abi=ERC20_ABI)
            balance_raw = await rpc_executor.run(contract.functions.balanceOf(checksum_addr).call)
            balance = balance_raw / (10**decimals)

            # Get price if balance > 0
            price = 0.0
            value_usd = 0.0
            if balance > 0:
                price = await PriceService.get_token_price(coingecko_id)
                value_usd = balance * price

            return TokenBalance(
                symbol=symbol,
                address=token_address,
                chain=chain,
                balance=balance,
                decimals=decimals,
                price_usd=price,
                value_usd=value_usd,
            )
        except Exception as e:
            logger.error(f"Error fetching {symbol} balance on {chain}: {e}")
            return TokenBalance(
                symbol=symbol, address=token_address, chain=chain, decimals=decimals, error=str(e)
            )

    @classmethod
    async def get_all_token_balances(
        cls, addresses: List[str], custom_tokens: Optional[List[Dict]] = None
    ) -> TokenPortfolio:
        """Fetch all token balances for user's addresses."""
        default_tokens = settings.get_default_tokens()
        all_tokens: List[TokenBalance] = []

        # Build list of all tokens to check
        tokens_to_check = []

        # Add default tokens
        for chain, tokens in default_tokens.items():
            for token in tokens:
                tokens_to_check.append({**token, "chain": chain})

        # Add custom tokens
        if custom_tokens:
            for token in custom_tokens:
                if all(
                    k in token for k in ["address", "chain", "decimals", "symbol", "coingecko_id"]
                ):
                    tokens_to_check.append(token)

        # Trust configured defaults over custom duplicates and avoid duplicate RPC calls.
        unique_tokens: dict[tuple[str, str], Dict] = {}
        for token in tokens_to_check:
            key = (token["chain"].lower(), token["address"].lower())
            unique_tokens.setdefault(key, token)

        # Fetch all balances in parallel; the RPC executor bounds blocking calls.
        tasks = []
        for address in addresses:
            for token in unique_tokens.values():
                tasks.append(
                    cls.get_token_balance(
                        address=address,
                        token_address=token["address"],
                        chain=token["chain"],
                        decimals=token["decimals"],
                        symbol=token["symbol"],
                        coingecko_id=token["coingecko_id"],
                    )
                )

        errors: list[str] = []
        if tasks:
            results = await asyncio.gather(*tasks)
            errors = [result.error for result in results if result.error]

            # Aggregate by token (sum balances across addresses)
            token_aggregated: Dict[str, TokenBalance] = {}

            for result in results:
                if result.balance > 0 and result.error is None:
                    key = f"{result.chain}:{result.address}"
                    if key in token_aggregated:
                        # Add to existing
                        existing = token_aggregated[key]
                        token_aggregated[key] = TokenBalance(
                            symbol=existing.symbol,
                            address=existing.address,
                            chain=existing.chain,
                            balance=existing.balance + result.balance,
                            decimals=existing.decimals,
                            price_usd=result.price_usd,
                            value_usd=existing.value_usd + result.value_usd,
                        )
                    else:
                        token_aggregated[key] = result

            all_tokens = list(token_aggregated.values())

        # Calculate totals (including dust)
        total_value = sum(t.value_usd for t in all_tokens)

        # Filter out dust tokens (< $1 USD) from display
        dust_threshold = 1.0
        visible_tokens = [t for t in all_tokens if t.value_usd >= dust_threshold]
        dust_tokens = [t for t in all_tokens if t.value_usd < dust_threshold]
        hidden_dust_value = sum(t.value_usd for t in dust_tokens)

        # Sort by value and get top holdings
        visible_tokens.sort(key=lambda x: x.value_usd, reverse=True)
        top_holdings = visible_tokens[:5]

        return TokenPortfolio(
            total_value_usd=total_value,
            token_count=len(visible_tokens),
            tokens=visible_tokens,
            top_holdings=top_holdings,
            hidden_dust_count=len(dust_tokens),
            hidden_dust_value_usd=hidden_dust_value,
            errors=errors,
        )

    @classmethod
    async def get_token_metadata(cls, token_address: str, chain: str) -> tuple[int, str]:
        """Read token metadata once before persisting a user-provided contract."""
        web3_instances = BlockchainService.get_web3_instances()
        if chain not in web3_instances:
            raise ValueError("Unsupported chain")
        token_checksum = Web3.to_checksum_address(token_address)
        contract = web3_instances[chain].eth.contract(address=token_checksum, abi=ERC20_ABI)
        decimals, symbol = await asyncio.gather(
            rpc_executor.run(contract.functions.decimals().call),
            rpc_executor.run(contract.functions.symbol().call),
        )
        if not isinstance(decimals, int) or not 0 <= decimals <= 36:
            raise ValueError("Token contract returned unsupported decimals")
        if not isinstance(symbol, str) or not symbol.strip() or len(symbol) > 32:
            raise ValueError("Token contract returned unsupported symbol")
        return decimals, symbol.strip()
