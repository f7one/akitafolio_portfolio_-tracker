"""
Pydantic data models for Akitafolio.

Provides type-safe data structures for all domain objects.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any, ClassVar, Pattern
from pydantic import BaseModel, Field, field_validator, ConfigDict
from web3 import Web3
import re


# ============================================================================
# ADDRESS MODELS
# ============================================================================

class EthAddress(BaseModel):
    """Validated Ethereum address."""
    model_config = ConfigDict(frozen=True)
    
    address: str
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not v:
            raise ValueError("Address cannot be empty")
        if not Web3.is_address(v):
            raise ValueError(f"Invalid Ethereum address: {v}")
        return Web3.to_checksum_address(v)


class BtcAddress(BaseModel):
    """Validated Bitcoin address."""
    model_config = ConfigDict(frozen=True)
    
    address: str
    
    BTC_LEGACY_PATTERN: ClassVar[Pattern] = re.compile(r'^[13][a-km-zA-HJ-NP-Z1-9]{25,34}$')
    BTC_SEGWIT_PATTERN: ClassVar[Pattern] = re.compile(r'^bc1[a-z0-9]{39,59}$', re.IGNORECASE)
    
    @field_validator('address')
    @classmethod
    def validate_address(cls, v: str) -> str:
        if not v:
            raise ValueError("Address cannot be empty")
        if cls.BTC_LEGACY_PATTERN.match(v) or cls.BTC_SEGWIT_PATTERN.match(v):
            return v
        raise ValueError(f"Invalid Bitcoin address: {v}")


class XPub(BaseModel):
    """Validated xpub/ypub/zpub."""
    model_config = ConfigDict(frozen=True)
    
    xpub: str
    
    VALID_PREFIXES: ClassVar[tuple] = ('xpub', 'ypub', 'zpub', 'tpub', 'upub', 'vpub')
    
    @field_validator('xpub')
    @classmethod
    def validate_xpub(cls, v: str) -> str:
        if not v:
            raise ValueError("xpub cannot be empty")
        if not any(v.startswith(prefix) for prefix in cls.VALID_PREFIXES):
            raise ValueError(f"Invalid xpub prefix. Must start with: {', '.join(cls.VALID_PREFIXES)}")
        if not (100 <= len(v) <= 120):
            raise ValueError(f"Invalid xpub length: {len(v)}")
        return v


# ============================================================================
# CHAIN MODELS
# ============================================================================

class ChainConfig(BaseModel):
    """Configuration for a blockchain."""
    model_config = ConfigDict(frozen=True)
    
    name: str
    rpc_url: str
    symbol: str
    emoji: str
    counts_as_eth: bool = False


class ChainBalance(BaseModel):
    """Balance on a specific chain."""
    chain: str
    address: str
    balance: float = 0.0
    currency: str
    network: str
    emoji: str
    counts_as_eth: bool = False
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.error is None


class AggregatedBalance(BaseModel):
    """Aggregated balances across multiple chains."""
    address: str
    total_eth: float = 0.0
    chain_balances: List[ChainBalance] = Field(default_factory=list)
    error: Optional[str] = None


# ============================================================================
# TOKEN MODELS
# ============================================================================

class TokenConfig(BaseModel):
    """Configuration for an ERC20 token."""
    model_config = ConfigDict(frozen=True)
    
    symbol: str
    address: str
    decimals: int
    coingecko_id: str
    chain: str = "ethereum"


class TokenBalance(BaseModel):
    """Balance of a specific token."""
    symbol: str
    address: str
    chain: str
    balance: float = 0.0
    decimals: int
    value_usd: float = 0.0
    price_usd: float = 0.0
    error: Optional[str] = None


class TokenPortfolio(BaseModel):
    """Aggregated token balances."""
    total_value_usd: float = 0.0
    token_count: int = 0
    tokens: List[TokenBalance] = Field(default_factory=list)
    top_holdings: List[TokenBalance] = Field(default_factory=list)


# ============================================================================
# DEFI MODELS
# ============================================================================

class DefiPosition(BaseModel):
    """DeFi position on a protocol."""
    protocol: str
    chain: str
    address: str
    collateral_usd: float = 0.0
    debt_usd: float = 0.0
    net_value_usd: float = 0.0
    health_factor: Optional[float] = None
    health_factor_display: str = "N/A"
    available_borrows_usd: float = 0.0
    ltv: float = 0.0
    liquidation_threshold: float = 0.0
    error: Optional[str] = None
    
    @property
    def has_position(self) -> bool:
        return self.collateral_usd > 0 or self.debt_usd > 0


class DefiPortfolio(BaseModel):
    """Aggregated DeFi positions."""
    total_collateral_usd: float = 0.0
    total_debt_usd: float = 0.0
    total_net_value_usd: float = 0.0
    position_count: int = 0
    positions: List[DefiPosition] = Field(default_factory=list)


# ============================================================================
# PORTFOLIO MODELS
# ============================================================================

class CryptoPrices(BaseModel):
    """Current cryptocurrency prices."""
    eth: float = 0.0
    btc: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class PortfolioSnapshot(BaseModel):
    """Snapshot of portfolio value at a point in time."""
    timestamp: datetime = Field(default_factory=datetime.now)
    total_value_usd: float
    eth_amount: float = 0.0
    btc_amount: float = 0.0
    eth_price: float = 0.0
    btc_price: float = 0.0


class PortfolioChange(BaseModel):
    """24h portfolio value change."""
    has_data: bool = False
    change_usd: float = 0.0
    change_percent: float = 0.0
    old_value: Optional[float] = None
    hours_ago: Optional[float] = None


class Portfolio(BaseModel):
    """Complete portfolio data."""
    total_eth: float = 0.0
    total_btc_single: float = 0.0
    total_btc_xpub: float = 0.0
    total_btc_combined: float = 0.0
    total_eth_usd: float = 0.0
    total_btc_usd: float = 0.0
    total_portfolio_usd: float = 0.0
    eth_price: float = 0.0
    btc_price: float = 0.0
    chain_balances: List[ChainBalance] = Field(default_factory=list)
    tokens: Optional[TokenPortfolio] = None
    defi: Optional[DefiPortfolio] = None
    change_24h: Optional[PortfolioChange] = None


# ============================================================================
# USER DATA MODELS
# ============================================================================

class UserAddresses(BaseModel):
    """User's saved addresses."""
    eth: List[str] = Field(default_factory=list)
    btc: List[str] = Field(default_factory=list)
    xpub: List[str] = Field(default_factory=list)
    tokens: List[Dict[str, Any]] = Field(default_factory=list)
    track_defi: bool = True
    
    def has_addresses(self) -> bool:
        return bool(self.eth or self.btc or self.xpub)


class UserHistory(BaseModel):
    """User's portfolio history."""
    snapshots: List[PortfolioSnapshot] = Field(default_factory=list)
