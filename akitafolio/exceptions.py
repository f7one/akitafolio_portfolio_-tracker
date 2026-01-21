"""
Custom exceptions for Akitafolio.
"""


class BotError(Exception):
    """Base exception for bot errors."""
    pass


class RateLimitError(BotError):
    """Raised when rate limit is exceeded."""
    pass


class APIError(BotError):
    """Raised when an external API call fails."""
    pass


class StorageError(BotError):
    """Raised when storage operations fail."""
    pass


class ConfigurationError(BotError):
    """Raised when configuration is invalid."""
    pass


class ValidationError(BotError):
    """Raised when input validation fails."""
    pass
