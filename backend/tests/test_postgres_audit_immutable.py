"""PostgreSQL-only: audit_logs must reject UPDATE/DELETE at the DB layer."""

import uuid

import pytest
from sqlalchemy import delete, text, update

from app.models.audit_log import AuditLog

pytestmark = pytest.mark.skipif(
    not __import__("tests.conftest", fromlist=["IS_POSTGRES"]).IS_POSTGRES,
    reason="Requires PostgreSQL (set TEST_DATABASE_URL)",
)


@pytest.mark.asyncio
async def test_audit_log_update_rejected_by_trigger(db_session):
    log_id = str(uuid.uuid4())
    async with db_session() as session:
        session.add(
            AuditLog(
                id=log_id,
                occurred_at="2026-08-05T00:00:00Z",
                event_type="test.event",
                target_type="test",
                operation="create",
                result="success",
            )
        )
        await session.commit()

        with pytest.raises(Exception, match="immutable"):
            await session.execute(
                update(AuditLog).where(AuditLog.id == log_id).values(result="tampered")
            )
            await session.commit()


@pytest.mark.asyncio
async def test_audit_log_delete_rejected_by_trigger(db_session):
    log_id = str(uuid.uuid4())
    async with db_session() as session:
        session.add(
            AuditLog(
                id=log_id,
                occurred_at="2026-08-05T00:00:00Z",
                event_type="test.event",
                target_type="test",
                operation="create",
                result="success",
            )
        )
        await session.commit()

        with pytest.raises(Exception, match="immutable"):
            await session.execute(delete(AuditLog).where(AuditLog.id == log_id))
            await session.commit()


@pytest.mark.asyncio
async def test_trigger_exists(db_session):
    async with db_session() as session:
        result = await session.execute(
            text("SELECT tgname FROM pg_trigger WHERE tgname = 'audit_logs_no_modify'")
        )
        assert result.scalar_one_or_none() == "audit_logs_no_modify"
