"""Endpoint-level RBAC enforcement.

Roles are stored in the ``roles`` table (system roles have
``organization_id IS NULL``) and linked to permissions via
``role_permissions``. For fresh installs / test databases that have not run
the seed migration, a built-in fallback matrix keeps behavior deterministic.

Authorization rules:
  - platform admin: everything
  - org admin (UserOrganization.is_org_admin): everything within the org
  - otherwise: permissions granted to the system role matching
    ``UserOrganization.role_in_org`` (or the fallback matrix).
"""

from fastapi import HTTPException, status
from sqlalchemy import select

from app.models.role import Permission, Role, RolePermission
from app.models.user import User, UserOrganization

# ─── Permission codes ─────────────────────────────────────────────────────────

P_CONTAINER_READ = "container.read"
P_CONTAINER_CREATE = "container.create"
P_CONTAINER_UPDATE = "container.update"
P_CONTAINER_SUBMIT = "container.submit"
P_CONTAINER_APPROVE = "container.approve"
P_CONTAINER_RETURN = "container.return"
P_CONTAINER_REVISE = "container.revise"
P_CONTAINER_ARCHIVE = "container.archive"
P_FILE_UPLOAD = "file.upload"
P_FILE_DELETE = "file.delete"
P_WORKFLOW_START = "workflow.start"
P_WORKFLOW_ACT = "workflow.act"
P_PROJECT_CREATE = "project.create"
P_PROJECT_UPDATE = "project.update"
P_NAMING_RULE_MANAGE = "naming_rule.manage"
P_REQUIREMENTS_READ = "requirements.read"
P_REQUIREMENTS_MANAGE = "requirements.manage"
P_REPORTS_READ = "reports.read"


ALL_PERMISSIONS: dict[str, tuple[str, str]] = {
    P_CONTAINER_READ: ("container", "情報コンテナの閲覧"),
    P_CONTAINER_CREATE: ("container", "情報コンテナの作成"),
    P_CONTAINER_UPDATE: ("container", "WIPコンテナの更新"),
    P_CONTAINER_SUBMIT: ("container", "Sharedへ提出"),
    P_CONTAINER_APPROVE: ("container", "Publishedへ承認・公開"),
    P_CONTAINER_RETURN: ("container", "WIPへ差戻し"),
    P_CONTAINER_REVISE: ("container", "改訂の開始"),
    P_CONTAINER_ARCHIVE: ("container", "保管"),
    P_FILE_UPLOAD: ("file", "ファイルのアップロード"),
    P_FILE_DELETE: ("file", "WIPファイルの削除"),
    P_WORKFLOW_START: ("workflow", "承認ワークフローの開始"),
    P_WORKFLOW_ACT: ("workflow", "承認・却下・差戻しの実行"),
    P_PROJECT_CREATE: ("project", "プロジェクトの作成"),
    P_PROJECT_UPDATE: ("project", "プロジェクトの更新"),
    P_NAMING_RULE_MANAGE: ("naming_rule", "命名規則の管理"),
    P_REQUIREMENTS_READ: ("requirements", "要求文書の閲覧"),
    P_REQUIREMENTS_MANAGE: ("requirements", "要求文書の管理"),
    P_REPORTS_READ: ("reports", "監査・コンプライアンスレポートの閲覧"),
}


MEMBER_PERMISSIONS = frozenset(
    {
        P_CONTAINER_READ,
        P_CONTAINER_CREATE,
        P_CONTAINER_UPDATE,
        P_CONTAINER_SUBMIT,
        P_CONTAINER_REVISE,
        P_FILE_UPLOAD,
        P_FILE_DELETE,
        P_WORKFLOW_START,
        P_REQUIREMENTS_READ,
        P_REQUIREMENTS_MANAGE,
    }
)

REVIEWER_PERMISSIONS = MEMBER_PERMISSIONS | frozenset(
    {
        P_CONTAINER_APPROVE,
        P_CONTAINER_RETURN,
        P_CONTAINER_ARCHIVE,
        P_WORKFLOW_ACT,
        P_REPORTS_READ,
    }
)

ORG_ADMIN_PERMISSIONS = REVIEWER_PERMISSIONS | frozenset(
    {P_PROJECT_CREATE, P_PROJECT_UPDATE, P_NAMING_RULE_MANAGE}
)

DEFAULT_ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    "member": MEMBER_PERMISSIONS,
    "reviewer": REVIEWER_PERMISSIONS,
    "org_admin": ORG_ADMIN_PERMISSIONS,
}


async def _system_role_permissions(db, role_name: str) -> set[str] | None:
    """Return permissions of the matching system role, or None if absent."""
    result = await db.execute(
        select(Role).where(
            Role.name == role_name,
            Role.organization_id.is_(None),
            Role.is_system_role.is_(True),
        )
    )
    role = result.scalar_one_or_none()
    if role is None:
        return None
    rows = await db.execute(
        select(Permission.code)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role.id)
    )
    return set(rows.scalars().all())


async def has_permission(
    db, *, user: User, organization_id: str, permission_code: str
) -> bool:
    """Return whether the user holds the permission within the organization."""
    if user.is_platform_admin:
        return True
    membership = (
        await db.execute(
            select(UserOrganization).where(
                UserOrganization.user_id == user.id,
                UserOrganization.organization_id == organization_id,
            )
        )
    ).scalar_one_or_none()
    if membership is None:
        return False
    if membership.is_org_admin:
        return True
    role_name = membership.role_in_org or "member"
    role_permissions = await _system_role_permissions(db, role_name)
    if role_permissions is not None:
        return permission_code in role_permissions
    fallback = DEFAULT_ROLE_PERMISSIONS.get(role_name, frozenset())
    return permission_code in fallback


async def require_permission(
    db, *, user: User, organization_id: str, permission_code: str
) -> None:
    """Raise 403 unless the user holds the permission in the organization."""
    if not await has_permission(
        db, user=user, organization_id=organization_id, permission_code=permission_code
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission '{permission_code}' is required for this operation.",
        )
