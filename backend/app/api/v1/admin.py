"""Platform-admin user and organization management endpoints.

These endpoints let a small IT/DX team (7 people) operate a few hundred
users without direct database access: list/search users, activate/deactivate,
promote platform admins, and manage organization memberships.
"""

import uuid
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, or_, select

from app.core.deps import DB, CurrentUser
from app.models.organization import Organization
from app.models.user import User, UserOrganization
from app.services.audit import record_audit

router = APIRouter(prefix="/admin", tags=["admin"])


class UserAdminResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    username: str
    full_name: str
    is_active: bool
    is_platform_admin: bool
    oidc_sub: str | None = None
    created_at: Any = None
    organizations: list[dict[str, Any]] = Field(default_factory=list)


class UserAdminListResponse(BaseModel):
    items: list[UserAdminResponse]
    total: int
    page: int
    size: int


class UserAdminUpdate(BaseModel):
    is_active: bool | None = None
    is_platform_admin: bool | None = None
    organization_id: str | None = None
    is_org_admin: bool | None = None
    remove_organization_id: str | None = None


async def _require_platform_admin(current_user: User) -> None:
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Platform administrator role required.",
        )


async def _user_organizations(user_id: str, db) -> list[dict[str, Any]]:
    result = await db.execute(
        select(Organization, UserOrganization)
        .join(UserOrganization, UserOrganization.organization_id == Organization.id)
        .where(UserOrganization.user_id == user_id)
    )
    return [
        {
            "organization_id": org.id,
            "organization_name": org.name,
            "role_in_org": membership.role_in_org,
            "is_org_admin": membership.is_org_admin,
        }
        for org, membership in result.all()
    ]


@router.get("/users", response_model=UserAdminListResponse)
async def list_users(
    current_user: CurrentUser,
    db: DB,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    q: str | None = Query(None, max_length=200),
) -> UserAdminListResponse:
    """Search users (platform admin only)."""
    await _require_platform_admin(current_user)
    base = select(User)
    if q:
        like = f"%{q.strip()}%"
        base = base.where(
            or_(
                User.email.ilike(like),
                User.username.ilike(like),
                User.full_name.ilike(like),
            )
        )
    total = (
        await db.execute(select(func.count()).select_from(base.subquery()))
    ).scalar_one()
    result = await db.execute(
        base.order_by(User.created_at.desc()).offset((page - 1) * size).limit(size)
    )
    users = result.scalars().all()
    items: list[UserAdminResponse] = []
    for user in users:
        orgs = await _user_organizations(user.id, db)
        items.append(
            UserAdminResponse(
                id=user.id,
                email=user.email,
                username=user.username,
                full_name=user.full_name,
                is_active=user.is_active,
                is_platform_admin=user.is_platform_admin,
                oidc_sub=user.oidc_sub,
                created_at=user.created_at,
                organizations=orgs,
            )
        )
    return UserAdminListResponse(items=items, total=total, page=page, size=size)


@router.patch("/users/{user_id}", response_model=UserAdminResponse)
async def update_user(
    request: Request,
    user_id: str,
    body: UserAdminUpdate,
    current_user: CurrentUser,
    db: DB,
) -> UserAdminResponse:
    """Update a user's account state and organization memberships (platform admin)."""
    await _require_platform_admin(current_user)
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    # Prevent the last platform admin from locking the platform out.
    if user_id == current_user.id:
        if body.is_platform_admin is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot remove your own platform administrator role",
            )
        if body.is_active is False:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot deactivate your own account",
            )

    before_json = {
        "is_active": user.is_active,
        "is_platform_admin": user.is_platform_admin,
    }
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.is_platform_admin is not None:
        user.is_platform_admin = body.is_platform_admin

    if body.organization_id:
        org_result = await db.execute(
            select(Organization).where(
                Organization.id == body.organization_id,
                Organization.is_active.is_(True),
            )
        )
        if not org_result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )
        existing = await db.execute(
            select(UserOrganization).where(
                UserOrganization.user_id == user_id,
                UserOrganization.organization_id == body.organization_id,
            )
        )
        membership = existing.scalar_one_or_none()
        if membership is None:
            membership = UserOrganization(
                id=str(uuid.uuid4()),
                user_id=user_id,
                organization_id=body.organization_id,
                role_in_org="member",
                is_org_admin=bool(body.is_org_admin),
            )
            db.add(membership)
        elif body.is_org_admin is not None:
            membership.is_org_admin = body.is_org_admin

    if body.remove_organization_id:
        existing = await db.execute(
            select(UserOrganization).where(
                UserOrganization.user_id == user_id,
                UserOrganization.organization_id == body.remove_organization_id,
            )
        )
        membership = existing.scalar_one_or_none()
        if membership is not None:
            await db.delete(membership)

    record_audit(
        db,
        event_type="admin.user_updated",
        operation="update",
        target_type="user",
        target_id=user.id,
        actor_id=current_user.id,
        actor_ip=request.client.host if request.client else None,
        before_json=before_json,
        after_json={
            "is_active": user.is_active,
            "is_platform_admin": user.is_platform_admin,
            "organization_id": body.organization_id,
            "remove_organization_id": body.remove_organization_id,
        },
        result="success",
    )
    await db.commit()
    await db.refresh(user)
    orgs = await _user_organizations(user.id, db)
    return UserAdminResponse(
        id=user.id,
        email=user.email,
        username=user.username,
        full_name=user.full_name,
        is_active=user.is_active,
        is_platform_admin=user.is_platform_admin,
        oidc_sub=user.oidc_sub,
        created_at=user.created_at,
        organizations=orgs,
    )
