from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.core.deps import DB, CurrentUser
from app.models.organization import Organization
from app.models.role import Permission, Role, RolePermission
from app.models.user import UserOrganization
from app.schemas.rbac import (
    PermissionCreate,
    PermissionResponse,
    RoleCreate,
    RolePermissionAssign,
    RoleResponse,
    RoleUpdate,
    RoleWithPermissionsResponse,
)

router = APIRouter(tags=["rbac"])


async def _require_org_membership(org_id: str, current_user, db) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    if not current_user.is_platform_admin:
        mem = await db.execute(
            select(UserOrganization).where(
                UserOrganization.user_id == current_user.id,
                UserOrganization.organization_id == org_id,
            )
        )
        if not mem.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
            )

    return org


async def _require_org_admin(org_id: str, current_user, db) -> Organization:
    result = await db.execute(select(Organization).where(Organization.id == org_id))
    org = result.scalar_one_or_none()
    if not org:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found"
        )

    if not current_user.is_platform_admin:
        mem = await db.execute(
            select(UserOrganization).where(
                UserOrganization.user_id == current_user.id,
                UserOrganization.organization_id == org_id,
                UserOrganization.is_org_admin == True,  # noqa: E712
            )
        )
        if not mem.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Organization admin required",
            )

    return org


async def _get_role_with_access(
    role_id: str, current_user, db, require_admin: bool = False
) -> Role:
    result = await db.execute(select(Role).where(Role.id == role_id))
    role = result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Role not found"
        )

    if current_user.is_platform_admin:
        return role

    if role.organization_id:
        mem_q = select(UserOrganization).where(
            UserOrganization.user_id == current_user.id,
            UserOrganization.organization_id == role.organization_id,
        )
        if require_admin:
            mem_q = mem_q.where(UserOrganization.is_org_admin == True)  # noqa: E712

        mem = await db.execute(mem_q)
        if not mem.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN
                if require_admin
                else status.HTTP_404_NOT_FOUND,
                detail="Role not found"
                if not require_admin
                else "Organization admin required",
            )

    return role


# ─── Permissions ──────────────────────────────────────────────────────────────


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    current_user: CurrentUser, db: DB
) -> list[PermissionResponse]:
    result = await db.execute(
        select(Permission).order_by(Permission.category, Permission.code)
    )
    return [PermissionResponse.model_validate(p) for p in result.scalars().all()]


@router.post(
    "/permissions",
    response_model=PermissionResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_permission(
    body: PermissionCreate,
    current_user: CurrentUser,
    db: DB,
) -> PermissionResponse:
    if not current_user.is_platform_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Platform admin required"
        )

    existing = await db.execute(select(Permission).where(Permission.code == body.code))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Permission code already exists",
        )

    perm = Permission(**body.model_dump())
    db.add(perm)
    await db.commit()
    await db.refresh(perm)
    return PermissionResponse.model_validate(perm)


# ─── Roles ────────────────────────────────────────────────────────────────────


@router.get(
    "/organizations/{org_id}/roles",
    response_model=list[RoleWithPermissionsResponse],
)
async def list_roles(
    org_id: str,
    current_user: CurrentUser,
    db: DB,
) -> list[RoleWithPermissionsResponse]:
    await _require_org_membership(org_id, current_user, db)
    result = await db.execute(select(Role).where(Role.organization_id == org_id))
    roles = result.scalars().all()

    out = []
    for role in roles:
        perms_result = await db.execute(
            select(Permission)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == role.id)
        )
        perms = [
            PermissionResponse.model_validate(p) for p in perms_result.scalars().all()
        ]
        out.append(
            RoleWithPermissionsResponse(
                **RoleResponse.model_validate(role).model_dump(),
                permissions=perms,
            )
        )
    return out


@router.post(
    "/organizations/{org_id}/roles",
    response_model=RoleWithPermissionsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_role(
    org_id: str,
    body: RoleCreate,
    current_user: CurrentUser,
    db: DB,
) -> RoleWithPermissionsResponse:
    await _require_org_admin(org_id, current_user, db)
    role = Role(organization_id=org_id, **body.model_dump())
    db.add(role)
    await db.commit()
    await db.refresh(role)
    return RoleWithPermissionsResponse(**RoleResponse.model_validate(role).model_dump())


@router.get("/roles/{role_id}", response_model=RoleWithPermissionsResponse)
async def get_role(
    role_id: str,
    current_user: CurrentUser,
    db: DB,
) -> RoleWithPermissionsResponse:
    role = await _get_role_with_access(role_id, current_user, db, require_admin=False)
    perms_result = await db.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
    )
    perms = [PermissionResponse.model_validate(p) for p in perms_result.scalars().all()]
    return RoleWithPermissionsResponse(
        **RoleResponse.model_validate(role).model_dump(),
        permissions=perms,
    )


@router.patch("/roles/{role_id}", response_model=RoleWithPermissionsResponse)
async def update_role(
    role_id: str,
    body: RoleUpdate,
    current_user: CurrentUser,
    db: DB,
) -> RoleWithPermissionsResponse:
    role = await _get_role_with_access(role_id, current_user, db, require_admin=True)
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify system roles"
        )

    for field, value in body.model_dump(exclude_none=True).items():
        setattr(role, field, value)
    await db.commit()
    await db.refresh(role)
    return RoleWithPermissionsResponse(**RoleResponse.model_validate(role).model_dump())


@router.delete("/roles/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    role_id: str,
    current_user: CurrentUser,
    db: DB,
) -> None:
    role = await _get_role_with_access(role_id, current_user, db, require_admin=True)
    if role.is_system_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete system roles"
        )
    await db.delete(role)
    await db.commit()


# ─── Role ↔ Permission ────────────────────────────────────────────────────────


@router.post(
    "/roles/{role_id}/permissions",
    response_model=RoleWithPermissionsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def assign_permission_to_role(
    role_id: str,
    body: RolePermissionAssign,
    current_user: CurrentUser,
    db: DB,
) -> RoleWithPermissionsResponse:
    await _get_role_with_access(role_id, current_user, db, require_admin=True)

    perm_result = await db.execute(
        select(Permission).where(Permission.id == body.permission_id)
    )
    if not perm_result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not found"
        )

    existing = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == body.permission_id,
        )
    )
    if not existing.scalar_one_or_none():
        db.add(RolePermission(role_id=role_id, permission_id=body.permission_id))
        await db.commit()

    return await get_role(role_id, current_user, db)


@router.delete(
    "/roles/{role_id}/permissions/{permission_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def revoke_permission_from_role(
    role_id: str,
    permission_id: str,
    current_user: CurrentUser,
    db: DB,
) -> None:
    await _get_role_with_access(role_id, current_user, db, require_admin=True)

    result = await db.execute(
        select(RolePermission).where(
            RolePermission.role_id == role_id,
            RolePermission.permission_id == permission_id,
        )
    )
    rp = result.scalar_one_or_none()
    if not rp:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Permission not assigned"
        )
    await db.delete(rp)
    await db.commit()
