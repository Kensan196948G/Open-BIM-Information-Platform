import csv
import io

from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select

from app.core.deps import DB, CurrentUser
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


def _build_query(
    event_type: str | None, target_type: str | None, target_id: str | None
):
    q = select(AuditLog).order_by(AuditLog.occurred_at.desc())
    if event_type:
        q = q.where(AuditLog.event_type == event_type)
    if target_type:
        q = q.where(AuditLog.target_type == target_type)
    if target_id:
        q = q.where(AuditLog.target_id == target_id)
    return q


@router.get("/export.csv")
async def export_audit_logs_csv(
    current_user: CurrentUser,
    db: DB,
    event_type: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
) -> StreamingResponse:
    """Export audit logs as CSV (platform admins only, UTF-8 BOM for Excel)."""
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit log access requires platform administrator role.",
        )
    q = _build_query(event_type, target_type, target_id)
    result = await db.execute(q)
    logs = result.scalars().all()

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "occurred_at",
            "event_type",
            "operation",
            "actor_id",
            "actor_ip",
            "target_type",
            "target_id",
            "result",
            "reason",
            "workflow_instance_id",
            "before_json",
            "after_json",
        ]
    )
    for log in logs:
        writer.writerow(
            [
                log.occurred_at,
                log.event_type,
                log.operation,
                log.actor_id,
                log.actor_ip,
                log.target_type,
                log.target_id,
                log.result,
                log.reason,
                log.workflow_instance_id,
                log.before_json,
                log.after_json,
            ]
        )

    data = "\ufeff" + buf.getvalue()
    return StreamingResponse(
        iter([data.encode("utf-8")]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": "attachment; filename=audit-logs.csv",
            "Cache-Control": "no-store",
        },
    )


@router.get("", response_model=AuditLogListResponse)
async def list_audit_logs(
    current_user: CurrentUser,
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    event_type: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
) -> AuditLogListResponse:
    # Audit logs contain sensitive data — restrict to platform admins only
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit log access requires platform administrator role.",
        )
    q = _build_query(event_type, target_type, target_id)
    total = (
        await db.execute(select(func.count()).select_from(q.subquery()))
    ).scalar_one()
    result = await db.execute(q.offset((page - 1) * size).limit(size))
    items = result.scalars().all()
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in items],
        total=total,
        page=page,
        size=size,
    )
