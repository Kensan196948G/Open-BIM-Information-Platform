"""Rate limiter tests: Redis shared store + in-process fallback."""

import pytest

from app.core.ratelimit import RedisBackedRateLimiter, SlidingWindowRateLimiter


class FakePipeline:
    def __init__(self, count_after_clean: int):
        self._count = count_after_clean

    def zremrangebyscore(self, *args, **kwargs):
        return self

    def zcard(self, *args, **kwargs):
        return self

    def zadd(self, *args, **kwargs):
        return self

    def expire(self, *args, **kwargs):
        return self

    async def execute(self):
        return [0, self._count, 1, 1]


class FakeRedis:
    def __init__(self, count_after_clean: int):
        self._count = count_after_clean
        self.closed = False

    def pipeline(self, transaction=True):
        return FakePipeline(self._count)

    async def aclose(self):
        self.closed = True


class FailingRedis:
    def pipeline(self, transaction=True):
        raise ConnectionError("redis down")

    async def aclose(self):
        pass


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_redis_backend_allows_below_limit(monkeypatch):
    monkeypatch.setattr("app.core.ratelimit.settings.RATE_LIMIT_BACKEND", "redis")
    limiter = RedisBackedRateLimiter()
    monkeypatch.setattr(
        limiter, "_redis_client", lambda: FakeRedis(count_after_clean=2)
    )

    allowed = await limiter.allow(("1.2.3.4", "login"), limit=5, window_seconds=60)
    assert allowed is True


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_redis_backend_blocks_at_limit(monkeypatch):
    monkeypatch.setattr("app.core.ratelimit.settings.RATE_LIMIT_BACKEND", "redis")
    limiter = RedisBackedRateLimiter()
    monkeypatch.setattr(
        limiter, "_redis_client", lambda: FakeRedis(count_after_clean=5)
    )

    allowed = await limiter.allow(("1.2.3.4", "login"), limit=5, window_seconds=60)
    assert allowed is False


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_redis_unavailable_falls_back_to_memory(monkeypatch):
    monkeypatch.setattr("app.core.ratelimit.settings.RATE_LIMIT_BACKEND", "redis")
    limiter = RedisBackedRateLimiter()
    monkeypatch.setattr(limiter, "_redis_client", FailingRedis)

    # First call hits Redis failure → memory fallback starts.
    assert await limiter.allow(("1.2.3.4", "login"), limit=2, window_seconds=60)
    # Second call is served from memory.
    assert await limiter.allow(("1.2.3.4", "login"), limit=2, window_seconds=60)
    # Third call exceeds the in-memory limit.
    assert not await limiter.allow(("1.2.3.4", "login"), limit=2, window_seconds=60)


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_memory_backend_ignores_redis(monkeypatch):
    monkeypatch.setattr("app.core.ratelimit.settings.RATE_LIMIT_BACKEND", "memory")
    limiter = RedisBackedRateLimiter()

    assert await limiter.allow(("1.2.3.4", "login"), limit=1, window_seconds=60)
    assert not await limiter.allow(("1.2.3.4", "login"), limit=1, window_seconds=60)


@pytest.mark.no_db
@pytest.mark.asyncio
async def test_in_process_limiter_sliding_window():
    limiter = SlidingWindowRateLimiter()
    limiter.clear()
    for _ in range(3):
        assert await limiter.allow(("k", "b"), limit=3, window_seconds=60)
    assert not await limiter.allow(("k", "b"), limit=3, window_seconds=60)
