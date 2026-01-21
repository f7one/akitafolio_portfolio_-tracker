"""
Configuration management for Akitafolio.

Uses Pydantic Settings for type-safe configuration with environment variable support.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import Field
from pydantic_settings import BaseSettings
from functools import lru_cache


class ChainSettings(BaseSettings):
    """Chain-specific configuration."""
    name: str
    rpc_url: str
    symbol: str
    emoji: str
    counts_as_eth: bool = False


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    All settings can be overridden via environment variables with
    the AKITAFOLIO_ prefix (e.g., AKITAFOLIO_DEBUG=true).
    """
    
    # Core settings
    telegram_bot_token: str = Field(default="", alias="TELEGRAM_BOT_TOKEN")
    infura_project_id: str = Field(default="", alias="INFURA_PROJECT_ID")
    
    # Application settings
    debug: bool = Field(default=False)
    log_level: str = Field(default="INFO")
    
    # Storage paths
    storage_dir: Path = Field(default=Path(__file__).parent.parent)
    addresses_file: str = Field(default="saved_addresses.json")
    history_file: str = Field(default="portfolio_history.json")
    
    # Rate limiting
    rate_limit_calls_per_second: float = Field(default=10.0)
    rate_limit_burst_size: int = Field(default=20)
    
    # Cache TTLs (in seconds)
    cache_ttl_prices: float = Field(default=30.0)
    cache_ttl_balances: float = Field(default=60.0)
    cache_ttl_defi: float = Field(default=120.0)
    cache_ttl_tokens: float = Field(default=60.0)
    
    # Timeouts (in seconds)
    timeout_default: int = Field(default=15)
    timeout_fast: int = Field(default=10)
    timeout_slow: int = Field(default=30)
    timeout_rpc: int = Field(default=20)
    
    # History retention
    history_retention_days: int = Field(default=30)
    
    model_config = {
        "env_prefix": "AKITAFOLIO_",
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }
    
    @property
    def storage_path(self) -> Path:
        """Get resolved storage directory path."""
        return self.storage_dir.resolve()
    
    @property
    def addresses_path(self) -> Path:
        """Get path to addresses file."""
        return self.storage_path / self.addresses_file
    
    @property
    def history_path(self) -> Path:
        """Get path to history file."""
        return self.storage_path / self.history_file
    
    def validate_required(self) -> List[str]:
        """Validate required configuration and return list of errors."""
        errors = []
        if not self.telegram_bot_token:
            errors.append("TELEGRAM_BOT_TOKEN is required")
        if not self.infura_project_id:
            errors.append("INFURA_PROJECT_ID is required")
        return errors
    
    def get_eth_chains(self) -> Dict[str, dict]:
        """Get ETH-based chain configurations."""
        return {
            'ethereum': {
                'name': 'Ethereum',
                'rpc_url': f'https://mainnet.infura.io/v3/{self.infura_project_id}',
                'symbol': 'ETH',
                'emoji': '⟠',
                'counts_as_eth': True
            },
            'base': {
                'name': 'Base',
                'rpc_url': f'https://base-mainnet.infura.io/v3/{self.infura_project_id}',
                'symbol': 'ETH',
                'emoji': '🔵',
                'counts_as_eth': True
            },
            'linea': {
                'name': 'Linea',
                'rpc_url': f'https://linea-mainnet.infura.io/v3/{self.infura_project_id}',
                'symbol': 'ETH',
                'emoji': '🟢',
                'counts_as_eth': True
            },
            'optimism': {
                'name': 'Optimism',
                'rpc_url': f'https://optimism-mainnet.infura.io/v3/{self.infura_project_id}',
                'symbol': 'ETH',
                'emoji': '🔴',
                'counts_as_eth': True
            },
            'arbitrum': {
                'name': 'Arbitrum',
                'rpc_url': f'https://arbitrum-mainnet.infura.io/v3/{self.infura_project_id}',
                'symbol': 'ETH',
                'emoji': '🔷',
                'counts_as_eth': True
            },
            'unichain': {
                'name': 'Unichain',
                'rpc_url': f'https://unichain-mainnet.infura.io/v3/{self.infura_project_id}',
                'symbol': 'ETH',
                'emoji': '🦄',
                'counts_as_eth': True
            }
        }
    
    def get_other_chains(self) -> Dict[str, dict]:
        """Get non-ETH chain configurations."""
        return {
            'polygon': {
                'name': 'Polygon',
                'rpc_url': f'https://polygon-mainnet.infura.io/v3/{self.infura_project_id}',
                'symbol': 'MATIC',
                'emoji': '🟣',
                'counts_as_eth': False
            },
            'bsc': {
                'name': 'BSC',
                'rpc_url': f'https://bsc-mainnet.infura.io/v3/{self.infura_project_id}',
                'symbol': 'BNB',
                'emoji': '🟡',
                'counts_as_eth': False
            }
        }
    
    def get_all_chains(self) -> Dict[str, dict]:
        """Get all chain configurations."""
        return {**self.get_eth_chains(), **self.get_other_chains()}
    
    def get_defi_protocols(self) -> Dict[str, dict]:
        """Get DeFi protocol addresses."""
        return {
            'ethereum': {'aave_v3_pool': '0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2'},
            'arbitrum': {'aave_v3_pool': '0x794a61358D6845594F94dc1DB02A252b5b4814aD'},
            'optimism': {'aave_v3_pool': '0x794a61358D6845594F94dc1DB02A252b5b4814aD'},
            'base': {'aave_v3_pool': '0xA238Dd80C259a72e81d7e4664a9801593F98d1c5'},
            'polygon': {'aave_v3_pool': '0x794a61358D6845594F94dc1DB02A252b5b4814aD'},
        }
    
    def get_default_tokens(self) -> Dict[str, List[dict]]:
        """Get default tokens to track."""
        return {
            'ethereum': [
                {'symbol': 'USDT', 'address': '0xdAC17F958D2ee523a2206206994597C13D831ec7', 'decimals': 6, 'coingecko_id': 'tether'},
                {'symbol': 'USDC', 'address': '0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48', 'decimals': 6, 'coingecko_id': 'usd-coin'},
                {'symbol': 'DAI', 'address': '0x6B175474E89094C44Da98b954EedeAC495271d0F', 'decimals': 18, 'coingecko_id': 'dai'},
                {'symbol': 'WETH', 'address': '0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2', 'decimals': 18, 'coingecko_id': 'weth'},
                {'symbol': 'WBTC', 'address': '0x2260FAC5E5542a773Aa44fBCfeDf7C193bc2C599', 'decimals': 8, 'coingecko_id': 'wrapped-bitcoin'},
                {'symbol': 'LINK', 'address': '0x514910771AF9Ca656af840dff83E8264EcF986CA', 'decimals': 18, 'coingecko_id': 'chainlink'},
                {'symbol': 'UNI', 'address': '0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984', 'decimals': 18, 'coingecko_id': 'uniswap'},
                {'symbol': 'AAVE', 'address': '0x7Fc66500c84A76Ad7e9c93437bFc5Ac33E2DDaE9', 'decimals': 18, 'coingecko_id': 'aave'},
            ],
            'base': [
                {'symbol': 'USDC', 'address': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913', 'decimals': 6, 'coingecko_id': 'usd-coin'},
            ],
            'arbitrum': [
                {'symbol': 'USDC', 'address': '0xaf88d065e77c8cC2239327C5EDb3A432268e5831', 'decimals': 6, 'coingecko_id': 'usd-coin'},
                {'symbol': 'USDT', 'address': '0xFd086bC7CD5C481DCC9C85ebE478A1C0b69FCbb9', 'decimals': 6, 'coingecko_id': 'tether'},
            ],
            'optimism': [
                {'symbol': 'USDC', 'address': '0x0b2C639c533813f4Aa9D7837CAf62653d097Ff85', 'decimals': 6, 'coingecko_id': 'usd-coin'},
                {'symbol': 'USDT', 'address': '0x94b008aA00579c1307B0EF2c499aD98a8ce58e58', 'decimals': 6, 'coingecko_id': 'tether'},
            ],
            'polygon': [
                {'symbol': 'USDC', 'address': '0x3c499c542cEF5E3811e1192ce70d8cC03d5c3359', 'decimals': 6, 'coingecko_id': 'usd-coin'},
                {'symbol': 'USDT', 'address': '0xc2132D05D31c914a87C6611C10748AEb04B58e8F', 'decimals': 6, 'coingecko_id': 'tether'},
            ],
        }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    from dotenv import load_dotenv
    load_dotenv()
    return Settings()


# Global settings instance
settings = get_settings()
