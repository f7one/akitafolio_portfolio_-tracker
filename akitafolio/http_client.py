"""
HTTP client with rate limiting and retry logic for Akitafolio.
"""

import asyncio
import time
import logging
import re
from typing import Optional, Dict, List, Any, Callable
from functools import wraps
from collections import defaultdict

import aiohttp

from akitafolio.config import settings
from akitafolio.exceptions import APIError, RateLimitError

logger = logging.getLogger(__name__)


# ============================================================================
# SECRETS FILTER FOR LOGGING
# ============================================================================

class SecretsFilter(logging.Filter):
    """Filter to mask sensitive data in logs."""
    
    SENSITIVE_PATTERNS = [
        (re.compile(r'(bot|token)[=:\s]*["\']?([a-zA-Z0-9_-]{30,})["\']?', re.IGNORECASE), r'\1=***MASKED***'),
        (re.compile(r'(api[_-]?key|secret|password|infura)[=:\s]*["\']?([a-zA-Z0-9_-]{10,})["\']?', re.IGNORECASE), r'\1=***MASKED***'),
        (re.compile(r'(0x[a-fA-F0-9]{40})', re.IGNORECASE), lambda m: m.group(1)[:10] + '...' + m.group(1)[-4:]),
    ]
    
    def filter(self, record):
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                if callable(replacement):
                    record.msg = pattern.sub(replacement, record.msg)
                else:
                    record.msg = pattern.sub(replacement, record.msg)
        return True


# ============================================================================
# RATE LIMITER
# ============================================================================

class RateLimiter:
    """Token bucket rate limiter for API calls."""
    
    def __init__(
        self,
        calls_per_second: float = 5.0,
        burst_size: int = 10,
        endpoint_limits: Optional[Dict[str, tuple]] = None
    ):
        self.calls_per_second = calls_per_second
        self.burst_size = burst_size
        self._tokens = float(burst_size)
        self._last_refill = time.monotonic()
        self._lock = asyncio.Lock()
        
        # Per-endpoint rate limiting
        self._endpoint_calls: Dict[str, List[float]] = defaultdict(list)
        self._endpoint_limits = endpoint_limits or {
            'coingecko': (10, 60),    # 10 calls per 60 seconds
            'blockchain': (30, 60),    # 30 calls per 60 seconds
            'infura': (100, 1),        # 100 calls per second
        }
    
    def _get_endpoint_type(self, url: str) -> Optional[str]:
        """Identify endpoint type from URL."""
        if 'coingecko' in url:
            return 'coingecko'
        elif 'blockchain.info' in url:
            return 'blockchain'
        elif 'infura.io' in url:
            return 'infura'
        return None
    
    async def acquire(self, url: str = "") -> bool:
        """Acquire a rate limit token."""
        async with self._lock:
            now = time.monotonic()
            
            # Refill tokens based on time passed
            time_passed = now - self._last_refill
            self._tokens = min(
                float(self.burst_size),
                self._tokens + time_passed * self.calls_per_second
            )
            self._last_refill = now
            
            # Check per-endpoint limits
            endpoint_type = self._get_endpoint_type(url)
            if endpoint_type:
                limit, window = self._endpoint_limits[endpoint_type]
                cutoff = now - window
                
                # Clean old entries
                self._endpoint_calls[endpoint_type] = [
                    t for t in self._endpoint_calls[endpoint_type] if t > cutoff
                ]
                
                if len(self._endpoint_calls[endpoint_type]) >= limit:
                    wait_time = self._endpoint_calls[endpoint_type][0] - cutoff
                    logger.warning(f"Rate limit for {endpoint_type}: waiting {wait_time:.2f}s")
                    await asyncio.sleep(wait_time + 0.1)
                
                self._endpoint_calls[endpoint_type].append(now)
            
            # Check global bucket
            if self._tokens < 1:
                wait_time = (1 - self._tokens) / self.calls_per_second
                logger.warning(f"Global rate limit: waiting {wait_time:.2f}s")
                await asyncio.sleep(wait_time)
                self._tokens = 1.0
            
            self._tokens -= 1
            return True


# ============================================================================
# RETRY DECORATOR
# ============================================================================

def retry_async(
    max_retries: int = 3,
    backoff_factor: float = 1.5,
    exceptions: tuple = (Exception,)
):
    """Decorator for retrying async functions with exponential backoff."""
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        wait_time = backoff_factor ** attempt
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {wait_time:.1f}s..."
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(f"All {max_retries} attempts failed for {func.__name__}: {e}")
            raise last_exception
        return wrapper
    return decorator


# ============================================================================
# TIMEOUT CONFIG
# ============================================================================

class TimeoutConfig:
    """Centralized timeout configuration."""
    
    @classmethod
    def get_timeout(cls, timeout: Optional[int] = None) -> aiohttp.ClientTimeout:
        """Get aiohttp ClientTimeout with consistent settings."""
        total = timeout or settings.timeout_default
        return aiohttp.ClientTimeout(
            total=total,
            connect=min(5, total),
            sock_read=total
        )


# ============================================================================
# HTTP CLIENT
# ============================================================================

class HTTPClient:
    """
    Singleton HTTP client with connection pooling and rate limiting.
    
    Features:
    - Connection pooling
    - Rate limiting (global and per-endpoint)
    - Automatic retries with exponential backoff
    - Configurable timeouts
    - 429 handling with Retry-After support
    """
    
    _session: Optional[aiohttp.ClientSession] = None
    _rate_limiter: Optional[RateLimiter] = None
    
    @classmethod
    def _get_rate_limiter(cls) -> RateLimiter:
        if cls._rate_limiter is None:
            cls._rate_limiter = RateLimiter(
                calls_per_second=settings.rate_limit_calls_per_second,
                burst_size=settings.rate_limit_burst_size
            )
        return cls._rate_limiter
    
    @classmethod
    async def get_session(cls) -> aiohttp.ClientSession:
        if cls._session is None or cls._session.closed:
            connector = aiohttp.TCPConnector(
                limit=50,
                limit_per_host=10,
                ttl_dns_cache=300
            )
            cls._session = aiohttp.ClientSession(
                timeout=TimeoutConfig.get_timeout(),
                connector=connector
            )
        return cls._session
    
    @classmethod
    async def close(cls) -> None:
        """Close the HTTP session."""
        if cls._session and not cls._session.closed:
            await cls._session.close()
            cls._session = None
    
    @classmethod
    @retry_async(max_retries=3, backoff_factor=1.5, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def get(cls, url: str, timeout: Optional[int] = None) -> Dict[str, Any]:
        """Make async GET request with retry logic and rate limiting."""
        await cls._get_rate_limiter().acquire(url)
        session = await cls.get_session()
        
        try:
            async with session.get(url, timeout=TimeoutConfig.get_timeout(timeout)) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited by server, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise aiohttp.ClientError("Rate limited, retry")
                response.raise_for_status()
                return await response.json()
        except aiohttp.ContentTypeError as e:
            logger.error(f"Invalid JSON response from {url}: {e}")
            raise APIError(f"Invalid JSON response: {e}") from e
    
    @classmethod
    @retry_async(max_retries=3, backoff_factor=1.5, exceptions=(aiohttp.ClientError, asyncio.TimeoutError))
    async def get_text(cls, url: str, timeout: Optional[int] = None) -> str:
        """Make async GET request returning text with retry logic and rate limiting."""
        await cls._get_rate_limiter().acquire(url)
        session = await cls.get_session()
        
        try:
            async with session.get(url, timeout=TimeoutConfig.get_timeout(timeout)) as response:
                if response.status == 429:
                    retry_after = int(response.headers.get('Retry-After', 5))
                    logger.warning(f"Rate limited by server, waiting {retry_after}s")
                    await asyncio.sleep(retry_after)
                    raise aiohttp.ClientError("Rate limited, retry")
                response.raise_for_status()
                return await response.text()
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error for {url}: {e}")
            raise APIError(f"HTTP request failed: {e}") from e
