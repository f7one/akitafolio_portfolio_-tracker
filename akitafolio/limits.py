"""Small in-process safety limits for public bot requests and RPC calls."""

import asyncio
import time
from collections.abc import Callable
from typing import Any, TypeVar

from akitafolio.config import settings

T = TypeVar("T")


class UserRequestLimiter:
    """Token-bucket limiter with a single in-flight expensive request per user."""

    def __init__(self, requests_per_minute: int, burst_size: int, idle_ttl: int = 3600):
        self.requests_per_minute = requests_per_minute
        self.burst_size = burst_size
        self.idle_ttl = idle_ttl
        self._buckets: dict[int, tuple[float, float]] = {}
        self._in_flight: set[int] = set()
        self._lock = asyncio.Lock()

    async def try_acquire(self, user_id: int) -> bool:
        """Reserve a request slot; return false instead of queuing an expensive job."""
        now = time.monotonic()
        refill_rate = self.requests_per_minute / 60
        async with self._lock:
            self._buckets = {
                uid: bucket
                for uid, bucket in self._buckets.items()
                if now - bucket[1] <= self.idle_ttl
            }
            if user_id in self._in_flight:
                return False
            tokens, last_seen = self._buckets.get(user_id, (float(self.burst_size), now))
            tokens = min(self.burst_size, tokens + (now - last_seen) * refill_rate)
            if tokens < 1:
                self._buckets[user_id] = (tokens, now)
                return False
            self._buckets[user_id] = (tokens - 1, now)
            self._in_flight.add(user_id)
            return True

    async def release(self, user_id: int) -> None:
        async with self._lock:
            self._in_flight.discard(user_id)


class RpcExecutor:
    """Bound blocking Web3 calls and keep them out of the asyncio event loop."""

    def __init__(self, max_concurrency: int):
        self._semaphore = asyncio.Semaphore(max_concurrency)

    async def run(self, function: Callable[..., T], /, *args: Any, **kwargs: Any) -> T:
        async with self._semaphore:
            return await asyncio.to_thread(function, *args, **kwargs)


user_request_limiter = UserRequestLimiter(
    requests_per_minute=settings.user_requests_per_minute,
    burst_size=settings.user_request_burst_size,
)
rpc_executor = RpcExecutor(settings.rpc_max_concurrency)
