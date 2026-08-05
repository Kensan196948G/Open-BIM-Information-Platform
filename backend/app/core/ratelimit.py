"""Simple in-process sliding-window rate limiter.

Designed for single-worker pilot deployments. Replace with a shared store
(Redis) when running multiple workers or instances.
"""

import asyncio
import time


class SlidingWindowRateLimiter:
    def __init__(self) -> None:
        self._hits: dict[tuple[str, str], list[float]] = {}
        self._lock = asyncio.Lock()

    async def allow(
        self, key: tuple[str, str], limit: int, window_seconds: int
    ) -> bool:
        now = time.monotonic()
        async with self._lock:
            timestamps = self._hits.setdefault(key, [])
            cutoff = now - window_seconds
            timestamps[:] = [t for t in timestamps if t > cutoff]
            if len(timestamps) >= limit:
                return False
            timestamps.append(now)
            return True

    def clear(self) -> None:
        self._hits.clear()


rate_limiter = SlidingWindowRateLimiter()
