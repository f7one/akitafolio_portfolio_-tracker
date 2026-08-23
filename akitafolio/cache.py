"""
Caching layer for Akitafolio.

Provides in-memory caching with TTL support for API responses
to reduce external API calls and improve performance.
"""

import asyncio
import hashlib
import logging
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


@dataclass
class CacheEntry:
    """Single cache entry with value and expiration."""

    value: Any
    expires_at: float
    created_at: float = field(default_factory=time.monotonic)
    hits: int = 0

    @property
    def is_expired(self) -> bool:
        return time.monotonic() > self.expires_at

    def touch(self) -> None:
        self.hits += 1


class TTLCache:
    """
    Thread-safe TTL cache with LRU eviction.

    Features:
    - Time-to-live (TTL) for entries
    - Maximum size with LRU eviction
    - Async-safe operations
    - Statistics tracking
    """

    def __init__(self, default_ttl: float = 60.0, max_size: int = 1000):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = asyncio.Lock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0, "expirations": 0}

    def _generate_key(self, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_data = f"{args}:{sorted(kwargs.items())}"
        return hashlib.md5(key_data.encode()).hexdigest()

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        async with self._lock:
            entry = self._cache.get(key)

            if entry is None:
                self._stats["misses"] += 1
                return None

            if entry.is_expired:
                del self._cache[key]
                self._stats["expirations"] += 1
                self._stats["misses"] += 1
                return None

            # Move to end (LRU)
            self._cache.move_to_end(key)
            entry.touch()
            self._stats["hits"] += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Set value in cache."""
        ttl = ttl or self.default_ttl

        async with self._lock:
            # Evict if at max size
            while len(self._cache) >= self.max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                self._stats["evictions"] += 1

            self._cache[key] = CacheEntry(value=value, expires_at=time.monotonic() + ttl)

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        async with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    async def clear(self) -> int:
        """Clear all cache entries."""
        async with self._lock:
            count = len(self._cache)
            self._cache.clear()
            return count

    async def cleanup_expired(self) -> int:
        """Remove all expired entries."""
        async with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired]
            for key in expired_keys:
                del self._cache[key]
            self._stats["expirations"] += len(expired_keys)
            return len(expired_keys)

    @property
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total = self._stats["hits"] + self._stats["misses"]
        hit_rate = (self._stats["hits"] / total * 100) if total > 0 else 0
        return {**self._stats, "size": len(self._cache), "hit_rate": f"{hit_rate:.1f}%"}


# Global cache instances with different TTLs
price_cache = TTLCache(default_ttl=30.0, max_size=100)  # Prices: 30s TTL
balance_cache = TTLCache(default_ttl=60.0, max_size=500)  # Balances: 60s TTL
defi_cache = TTLCache(default_ttl=120.0, max_size=200)  # DeFi: 2min TTL
token_cache = TTLCache(default_ttl=60.0, max_size=500)  # Tokens: 60s TTL


def cached(cache: TTLCache, ttl: Optional[float] = None, key_prefix: str = ""):
    """
    Decorator for caching async function results.

    Args:
        cache: TTLCache instance to use
        ttl: Optional TTL override
        key_prefix: Prefix for cache keys
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Generate cache key
            key_data = f"{key_prefix}:{func.__name__}:{args}:{sorted(kwargs.items())}"
            cache_key = hashlib.md5(key_data.encode()).hexdigest()

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for {func.__name__}")
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            await cache.set(cache_key, result, ttl)
            logger.debug(f"Cache miss for {func.__name__}, stored result")

            return result

        return wrapper

    return decorator


class CacheManager:
    """
    Centralized cache management.

    Provides unified access to all cache instances
    and periodic cleanup.
    """

    def __init__(self):
        self.caches = {
            "prices": price_cache,
            "balances": balance_cache,
            "defi": defi_cache,
            "tokens": token_cache,
        }
        self._cleanup_task: Optional[asyncio.Task] = None

    async def start_cleanup_task(self, interval: float = 300.0) -> None:
        """Start periodic cache cleanup."""

        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval)
                for name, cache in self.caches.items():
                    expired = await cache.cleanup_expired()
                    if expired > 0:
                        logger.info(f"Cleaned up {expired} expired entries from {name} cache")

        self._cleanup_task = asyncio.create_task(cleanup_loop())

    async def stop_cleanup_task(self) -> None:
        """Stop cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def clear_all(self) -> Dict[str, int]:
        """Clear all caches."""
        results = {}
        for name, cache in self.caches.items():
            results[name] = await cache.clear()
        return results

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get statistics for all caches."""
        return {name: cache.stats for name, cache in self.caches.items()}


# Global cache manager
cache_manager = CacheManager()
