"""Rate limiting with Redis-backed shared store and in-process fallback.

Single-worker deployments may use the in-process limiter. When the backend
runs multiple workers (``APP_WORKERS > 1``), the Redis-backed limiter keeps
login/registration limits correct across workers. If Redis is unavailable,
the limiter degrades to the in-process store for 30 seconds (documented
trade-off: limits are per-process while Redis is down).
"""

import asyncio
import time
import uuid

from app.core.config import settings


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


class RedisBackedRateLimiter:
    """Composite limiter: Redis when available, in-process fallback otherwise."""

    def __init__(self) -> None:
        self._memory = SlidingWindowRateLimiter()
        self._redis_down_until = 0.0

    def _redis_client(self):
        from redis.asyncio import from_url

        return from_url(
            settings.REDIS_URL,
            socket_connect_timeout=1,
            socket_timeout=2,
        )

    async def allow(
        self, key: tuple[str, str], limit: int, window_seconds: int
    ) -> bool:
        if settings.RATE_LIMIT_BACKEND == "memory":
            return await self._memory.allow(key, limit, window_seconds)
        if time.monotonic() < self._redis_down_until:
            return await self._memory.allow(key, limit, window_seconds)

        client = None
        try:
            client = self._redis_client()
            now = time.time()
            zkey = f"bim:rl:{key[0]}:{key[1]}"
            pipe = client.pipeline(transaction=True)
            pipe.zremrangebyscore(zkey, 0, now - window_seconds)
            pipe.zcard(zkey)
            pipe.zadd(zkey, {str(uuid.uuid4()): now})
            pipe.expire(zkey, window_seconds + 10)
            _, count_before_add, _, _ = await pipe.execute()
            return int(count_before_add) < limit
        except Exception:
            # Redis is unavailable — degrade to in-process limits for a short
            # window to avoid per-request connection attempts.
            self._redis_down_until = time.monotonic() + 30
            return await self._memory.allow(key, limit, window_seconds)
        finally:
            if client is not None:
                try:
                    await client.aclose()
                except Exception:
                    pass

    def clear(self) -> None:
        self._memory.clear()


rate_limiter = RedisBackedRateLimiter()
