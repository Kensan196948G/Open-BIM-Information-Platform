from fastapi import APIRouter, Query
from sqlalchemy import select

from app.core.deps import CurrentUser, DB
from app.models.audit_log import AuditLog
from app.schemas.audit_log import AuditLogListResponse, AuditLogResponse

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])


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
    q = select(AuditLog).order_by(AuditLog.occurred_at.desc())
    if event_type:
        q = q.where(AuditLog.event_type == event_type)
    if target_type:
        q = q.where(AuditLog.target_type == target_type)
    if target_id:
        q = q.where(AuditLog.target_id == target_id)
    result = await db.execute(q.offset((page - 1) * size).limit(size))
    items = result.scalars().all()
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in items],
        total=len(items),
        page=page,
        size=size,
    )
