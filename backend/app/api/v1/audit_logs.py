from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import func, select

from app.core.deps import DB, CurrentUser
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
    # Audit logs contain sensitive data — restrict to platform admins only
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Audit log access requires platform administrator role.",
        )
    q = select(AuditLog).order_by(AuditLog.occurred_at.desc())
    if event_type:
        q = q.where(AuditLog.event_type == event_type)
    if target_type:
        q = q.where(AuditLog.target_type == target_type)
    if target_id:
        q = q.where(AuditLog.target_id == target_id)
    total = (await db.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    result = await db.execute(q.offset((page - 1) * size).limit(size))
    items = result.scalars().all()
    return AuditLogListResponse(
        items=[AuditLogResponse.model_validate(log) for log in items],
        total=total,
        page=page,
        size=size,
    )
