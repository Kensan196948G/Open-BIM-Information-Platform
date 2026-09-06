"""External share request workflow (Issue #55).

A project member requests an external share for a container. A reviewer (or
higher) approves or rejects the request. On approval a cryptographically
random, time-limited token is issued; the (unauthenticated) public download
endpoint accepts that token and streams the container's most recent file.

Security notes:
  - Tokens are generated with ``secrets.token_urlsafe`` (CSPRNG).
  - The public download endpoint returns 404 for any invalid, expired, or
    revoked token — never a distinct "forbidden"/"gone" status — so token
    guessing cannot be used to enumerate valid-but-inactive requests.
  - Only the first 8 characters of a token are ever written to the audit
    log; the full token is never logged.
"""

import re
import secrets
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import DB, CurrentUser
from app.db.base import get_db
from app.models.container import ContainerFile, InformationContainer
from app.models.project import Project
from app.models.share_request import ShareRequest, ShareRequestStatus
from app.models.user import UserOrganization
from app.schemas.share_request import (
    ShareRequestApprove,
    ShareRequestApproveResponse,
    ShareRequestCreate,
    ShareRequestListResponse,
    ShareRequestReject,
    ShareRequestResponse,
)
from app.services import storage as storage_svc
from app.services.audit import enum_value, record_audit
from app.services.rbac import (
    P_CONTAINER_READ,
    P_SHARE_REQUEST_MANAGE,
    require_permission,
)

router = APIRouter(
    prefix="/projects/{project_id}/containers/{container_id}/share-requests",
    tags=["share-requests"],
)

# Unauthenticated router — must NOT depend on CurrentUser/DB (app.core.deps).
public_router = APIRouter(prefix="/public", tags=["share-requests-public"])


def _client_ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _is_expired(expires_at: datetime | None) -> bool:
    """True if ``expires_at`` is unset or in the past.

    SQLite (used in the test suite) does not preserve timezone info on
    ``DateTime(timezone=True)`` columns, returning naive datetimes on
    read-back. Treat naive values as UTC so comparisons never raise.
    """
    if expires_at is None:
        return True
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    return expires_at <= datetime.now(UTC)


async def _get_container_or_404(
    project_id: str, container_id: str, current_user, db
) -> InformationContainer:
    proj_result = await db.execute(select(Project).where(Project.id == project_id))
    project = proj_result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )

    if not current_user.is_platform_admin:
        member = await db.execute(
            select(UserOrganization).where(
                UserOrganization.user_id == current_user.id,
                UserOrganization.organization_id == project.organization_id,
            )
        )
        if not member.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
            )

    result = await db.execute(
        select(InformationContainer).where(
            InformationContainer.id == container_id,
            InformationContainer.project_id == project_id,
            InformationContainer.is_deleted.is_(False),
        )
    )
    container = result.scalar_one_or_none()
    if not container:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Container not found"
        )
    return container


async def _get_project(project_id: str, db) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        )
    return project


async def _get_share_request_or_404(
    container_id: str, share_request_id: str, db
) -> ShareRequest:
    result = await db.execute(
        select(ShareRequest).where(
            ShareRequest.id == share_request_id,
            ShareRequest.container_id == container_id,
        )
    )
    share_request = result.scalar_one_or_none()
    if not share_request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Share request not found"
        )
    return share_request


@router.post(
    "",
    response_model=ShareRequestResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_share_request(
    request: Request,
    project_id: str,
    container_id: str,
    body: ShareRequestCreate,
    current_user: CurrentUser,
    db: DB,
) -> ShareRequestResponse:
    container = await _get_container_or_404(project_id, container_id, current_user, db)
    project = await _get_project(project_id, db)
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=P_CONTAINER_READ,
    )

    share_request = ShareRequest(
        container_id=container.id,
        requested_by_user_id=current_user.id,
        reason=body.reason,
        status=ShareRequestStatus.pending,
    )
    db.add(share_request)
    await db.flush()
    record_audit(
        db,
        event_type="share_request.created",
        operation="create",
        target_type="share_request",
        target_id=share_request.id,
        actor_id=current_user.id,
        actor_ip=_client_ip(request),
        after_json={
            "container_id": container.id,
            "reason": share_request.reason,
            "status": enum_value(share_request.status),
        },
        result="success",
    )
    await db.commit()
    await db.refresh(share_request)
    return ShareRequestResponse.model_validate(share_request)


@router.get("", response_model=ShareRequestListResponse)
async def list_share_requests(
    project_id: str,
    container_id: str,
    current_user: CurrentUser,
    db: DB,
) -> ShareRequestListResponse:
    container = await _get_container_or_404(project_id, container_id, current_user, db)
    project = await _get_project(project_id, db)
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=P_CONTAINER_READ,
    )
    result = await db.execute(
        select(ShareRequest)
        .where(ShareRequest.container_id == container.id)
        .order_by(ShareRequest.created_at.desc())
    )
    items = result.scalars().all()

    # Lazily reflect expiry in the displayed status — no background job
    # required; the public download endpoint already denies access based on
    # expires_at regardless of this flag.
    expired_any = False
    for sr in items:
        if sr.status == ShareRequestStatus.approved and _is_expired(sr.expires_at):
            sr.status = ShareRequestStatus.expired
            expired_any = True
    if expired_any:
        await db.commit()

    return ShareRequestListResponse(
        items=[ShareRequestResponse.model_validate(sr) for sr in items],
        total=len(items),
    )


@router.post(
    "/{share_request_id}/approve",
    response_model=ShareRequestApproveResponse,
)
async def approve_share_request(
    request: Request,
    project_id: str,
    container_id: str,
    share_request_id: str,
    body: ShareRequestApprove,
    current_user: CurrentUser,
    db: DB,
) -> ShareRequestApproveResponse:
    container = await _get_container_or_404(project_id, container_id, current_user, db)
    project = await _get_project(project_id, db)
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=P_SHARE_REQUEST_MANAGE,
    )
    share_request = await _get_share_request_or_404(container.id, share_request_id, db)
    if share_request.status != ShareRequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Share request is '{share_request.status.value}', not pending",
        )

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(UTC) + timedelta(hours=body.expires_in_hours)

    share_request.status = ShareRequestStatus.approved
    share_request.approved_by_user_id = current_user.id
    share_request.token = token
    share_request.expires_at = expires_at

    record_audit(
        db,
        event_type="share_request.approved",
        operation="approve",
        target_type="share_request",
        target_id=share_request.id,
        actor_id=current_user.id,
        actor_ip=_client_ip(request),
        after_json={
            "container_id": container.id,
            "expires_at": expires_at.isoformat(),
            "token_prefix": token[:8],
        },
        result="success",
    )
    await db.commit()
    await db.refresh(share_request)
    return ShareRequestApproveResponse(
        **ShareRequestResponse.model_validate(share_request).model_dump(),
        token=token,
        share_url_path=f"/api/v1/public/shared/{token}",
    )


@router.post(
    "/{share_request_id}/reject",
    response_model=ShareRequestResponse,
)
async def reject_share_request(
    request: Request,
    project_id: str,
    container_id: str,
    share_request_id: str,
    body: ShareRequestReject,
    current_user: CurrentUser,
    db: DB,
) -> ShareRequestResponse:
    container = await _get_container_or_404(project_id, container_id, current_user, db)
    project = await _get_project(project_id, db)
    await require_permission(
        db,
        user=current_user,
        organization_id=project.organization_id,
        permission_code=P_SHARE_REQUEST_MANAGE,
    )
    share_request = await _get_share_request_or_404(container.id, share_request_id, db)
    if share_request.status != ShareRequestStatus.pending:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Share request is '{share_request.status.value}', not pending",
        )

    share_request.status = ShareRequestStatus.rejected
    share_request.approved_by_user_id = current_user.id
    record_audit(
        db,
        event_type="share_request.rejected",
        operation="reject",
        target_type="share_request",
        target_id=share_request.id,
        actor_id=current_user.id,
        actor_ip=_client_ip(request),
        reason=body.reason,
        result="success",
    )
    await db.commit()
    await db.refresh(share_request)
    return ShareRequestResponse.model_validate(share_request)


@router.post(
    "/{share_request_id}/revoke",
    response_model=ShareRequestResponse,
)
async def revoke_share_request(
    request: Request,
    project_id: str,
    container_id: str,
    share_request_id: str,
    current_user: CurrentUser,
    db: DB,
) -> ShareRequestResponse:
    container = await _get_container_or_404(project_id, container_id, current_user, db)
    project = await _get_project(project_id, db)
    share_request = await _get_share_request_or_404(container.id, share_request_id, db)

    is_requester = share_request.requested_by_user_id == current_user.id
    if not is_requester:
        await require_permission(
            db,
            user=current_user,
            organization_id=project.organization_id,
            permission_code=P_SHARE_REQUEST_MANAGE,
        )

    if share_request.status not in (
        ShareRequestStatus.pending,
        ShareRequestStatus.approved,
    ):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Share request is '{share_request.status.value}' and cannot be revoked",
        )

    share_request.status = ShareRequestStatus.revoked
    record_audit(
        db,
        event_type="share_request.revoked",
        operation="revoke",
        target_type="share_request",
        target_id=share_request.id,
        actor_id=current_user.id,
        actor_ip=_client_ip(request),
        result="success",
    )
    await db.commit()
    await db.refresh(share_request)
    return ShareRequestResponse.model_validate(share_request)


@public_router.get("/shared/{token}")
async def get_shared_container(
    token: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """Unauthenticated download of a container's latest file via share token.

    Deliberately bypasses ``app.core.deps.CurrentUser`` — no bearer token is
    required or accepted here; the share ``token`` itself is the credential.

    Returns 404 uniformly for invalid, expired, or revoked tokens so token
    guessing cannot distinguish "wrong token" from "expired/revoked token".
    """
    not_found = HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not found")
    if not token or len(token) < 16:
        raise not_found

    result = await db.execute(select(ShareRequest).where(ShareRequest.token == token))
    share_request = result.scalar_one_or_none()

    if share_request is None:
        raise not_found
    if share_request.status != ShareRequestStatus.approved:
        raise not_found
    if _is_expired(share_request.expires_at):
        raise not_found

    file_result = await db.execute(
        select(ContainerFile)
        .where(ContainerFile.container_id == share_request.container_id)
        .order_by(ContainerFile.created_at.desc())
    )
    latest_file = file_result.scalars().first()
    if latest_file is None:
        raise not_found

    try:
        data = storage_svc.download_file(latest_file.storage_key)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Storage service unavailable: {exc}",
        ) from exc

    record_audit(
        db,
        event_type="share_request.downloaded",
        operation="download",
        target_type="share_request",
        target_id=share_request.id,
        actor_id=None,
        actor_ip=_client_ip(request),
        after_json={
            "container_id": share_request.container_id,
            "token_prefix": token[:8],
        },
        result="success",
    )
    await db.commit()

    safe_name = re.sub(r"[^\w.\-]", "_", latest_file.original_filename)[:200]
    return Response(
        content=data,
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}"'},
    )
