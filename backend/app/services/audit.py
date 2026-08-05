"""Audit log writer.

All business operations that need an evidence trail call ``record_audit``
before committing so the audit row is part of the same transaction.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog


def enum_value(value):
    """Return enum member value or the value itself (flush may yield str)."""
    return value.value if hasattr(value, "value") else value


def record_audit(
    db: AsyncSession,
    *,
    event_type: str,
    operation: str,
    target_type: str,
    target_id: str | None = None,
    actor_id: str | None = None,
    actor_ip: str | None = None,
    before_json: dict[str, Any] | None = None,
    after_json: dict[str, Any] | None = None,
    reason: str | None = None,
    result: str = "success",
    workflow_instance_id: str | None = None,
) -> None:
    """Queue an audit log row on the active session (committed by caller)."""
    db.add(
        AuditLog(
            id=str(uuid.uuid4()),
            occurred_at=datetime.now(UTC).isoformat(),
            event_type=event_type,
            actor_id=actor_id,
            actor_ip=actor_ip,
            target_type=target_type,
            target_id=target_id,
            operation=operation,
            before_json=before_json,
            after_json=after_json,
            reason=reason,
            result=result,
            workflow_instance_id=workflow_instance_id,
        )
    )
