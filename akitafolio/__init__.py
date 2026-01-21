"""
Akitafolio - Multi-Chain Crypto Portfolio Tracker

A Telegram bot for tracking cryptocurrency portfolios across multiple EVM chains,
Bitcoin addresses, and DeFi positions.
"""

__version__ = "2.0.0"
__author__ = "Akitafolio Team"

from akitafolio.config import settings
from akitafolio.exceptions import (
    BotError,
    RateLimitError,
    APIError,
    StorageError,
    ConfigurationError,
    ValidationError,
)

__all__ = [
    "settings",
    "BotError",
    "RateLimitError", 
    "APIError",
    "StorageError",
    "ConfigurationError",
    "ValidationError",
]
