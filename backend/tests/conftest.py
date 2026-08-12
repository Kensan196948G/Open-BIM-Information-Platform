import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.core.ratelimit import rate_limiter
from app.db.base import Base, get_db
from app.main import app

# Default: in-memory SQLite (fast local runs).
# CI sets TEST_DATABASE_URL to PostgreSQL so the full suite exercises
# Postgres-specific behaviour (row locks, enums, immutable audit trigger).
TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL", "sqlite+aiosqlite:///:memory:")
IS_POSTGRES = TEST_DATABASE_URL.startswith("postgres")

if IS_POSTGRES:
    engine_test = create_async_engine(TEST_DATABASE_URL, echo=False)
else:
    engine_test = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
TestSessionLocal = async_sessionmaker(
    engine_test, class_=AsyncSession, expire_on_commit=False
)

POSTGRES_AUDIT_FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'audit_logs are immutable — DELETE and UPDATE are forbidden';
END;
$$ LANGUAGE plpgsql;
"""

POSTGRES_AUDIT_TRIGGER_SQL = """
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'audit_logs_no_modify') THEN
    CREATE TRIGGER audit_logs_no_modify
    BEFORE UPDATE OR DELETE ON audit_logs
    FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
  END IF;
END $$;
"""


async def override_get_db():
    async with TestSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture(autouse=True)
async def setup_db(request):
    rate_limiter.clear()
    # Deterministic tests: never depend on a local Redis instance.
    from app.core.config import settings

    settings.RATE_LIMIT_BACKEND = "memory"
    if request.node.get_closest_marker("no_db"):
        yield
        return
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        if IS_POSTGRES:
            await conn.execute(text(POSTGRES_AUDIT_FUNCTION_SQL))
            await conn.execute(text(POSTGRES_AUDIT_TRIGGER_SQL))
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def client():
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    """Session factory for direct DB manipulation in tests."""
    return TestSessionLocal


@pytest.fixture
def mock_s3(monkeypatch):
    """Moto-mocked S3 environment. Skips automatically if moto is unavailable."""
    try:
        import boto3
        import moto
    except ImportError:
        pytest.skip("moto[s3] not installed")

    from app import services

    with moto.mock_aws():
        mock_client = boto3.client(
            "s3",
            region_name="us-east-1",
            aws_access_key_id="testing",
            aws_secret_access_key="testing",
        )
        mock_client.create_bucket(Bucket="bim-containers")

        monkeypatch.setattr(services.storage, "get_s3_client", lambda: mock_client)
        monkeypatch.setattr(services.storage, "_s3_client", None)

        yield

        monkeypatch.setattr(services.storage, "_s3_client", None)
