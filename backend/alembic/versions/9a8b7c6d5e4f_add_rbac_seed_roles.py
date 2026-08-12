"""Seed default permissions and system roles for endpoint-level RBAC.

Revision ID: 9a8b7c6d5e4f
Revises: 3c4d5e6f7a8b
Create Date: 2026-08-12

System roles (organization_id IS NULL) are matched to
``user_organizations.role_in_org`` by name. Permissions are idempotently
inserted so custom roles can reuse the same codes.
"""

import uuid
from datetime import UTC, datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9a8b7c6d5e4f"
down_revision: Union[str, None] = "3c4d5e6f7a8b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSIONS: dict[str, tuple[str, str]] = {
    "container.read": ("container", "情報コンテナの閲覧"),
    "container.create": ("container", "情報コンテナの作成"),
    "container.update": ("container", "WIPコンテナの更新"),
    "container.submit": ("container", "Sharedへ提出"),
    "container.approve": ("container", "Publishedへ承認・公開"),
    "container.return": ("container", "WIPへ差戻し"),
    "container.revise": ("container", "改訂の開始"),
    "container.archive": ("container", "保管"),
    "file.upload": ("file", "ファイルのアップロード"),
    "file.delete": ("file", "WIPファイルの削除"),
    "workflow.start": ("workflow", "承認ワークフローの開始"),
    "workflow.act": ("workflow", "承認・却下・差戻しの実行"),
    "project.create": ("project", "プロジェクトの作成"),
    "project.update": ("project", "プロジェクトの更新"),
    "naming_rule.manage": ("naming_rule", "命名規則の管理"),
    "requirements.read": ("requirements", "要求文書の閲覧"),
    "requirements.manage": ("requirements", "要求文書の管理"),
}

MEMBER = {
    "container.read",
    "container.create",
    "container.update",
    "container.submit",
    "container.revise",
    "file.upload",
    "file.delete",
    "workflow.start",
    "requirements.read",
    "requirements.manage",
}
REVIEWER = MEMBER | {
    "container.approve",
    "container.return",
    "container.archive",
    "workflow.act",
}
ORG_ADMIN = REVIEWER | {"project.create", "project.update", "naming_rule.manage"}

ROLES: dict[str, set[str]] = {
    "member": MEMBER,
    "reviewer": REVIEWER,
    "org_admin": ORG_ADMIN,
}


def _uuid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_OID, seed))


def upgrade() -> None:
    conn = op.get_bind()
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.String),
        sa.column("code", sa.String),
        sa.column("category", sa.String),
        sa.column("description", sa.Text),
    )
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.String),
        sa.column("organization_id", sa.String),
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("is_system_role", sa.Boolean),
        sa.column("created_at", sa.DateTime(timezone=True)),
        sa.column("updated_at", sa.DateTime(timezone=True)),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("id", sa.String),
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
    )

    for code, (category, description) in PERMISSIONS.items():
        conn.execute(
            sa.dialects.postgresql.insert(permissions_table)
            .values(
                id=_uuid(f"permission:{code}"),
                code=code,
                category=category,
                description=description,
            )
            .on_conflict_do_nothing(index_elements=["code"])
        )

    existing_roles = {
        row.name: row.id
        for row in conn.execute(
            sa.select(roles_table.c.name, roles_table.c.id).where(
                roles_table.c.organization_id.is_(None),
                roles_table.c.is_system_role.is_(True),
            )
        )
    }
    for name in ROLES:
        role_id = existing_roles.get(name) or _uuid(f"system-role:{name}")
        if name not in existing_roles:
            now = datetime.now(UTC)
            conn.execute(
                sa.dialects.postgresql.insert(roles_table).values(
                    id=role_id,
                    organization_id=None,
                    name=name,
                    description=f"システム既定ロール: {name}",
                    is_system_role=True,
                    created_at=now,
                    updated_at=now,
                )
            )
        for code in ROLES[name]:
            conn.execute(
                sa.dialects.postgresql.insert(role_permissions_table)
                .values(
                    id=_uuid(f"rp:{name}:{code}"),
                    role_id=role_id,
                    permission_id=_uuid(f"permission:{code}"),
                )
                .on_conflict_do_nothing(
                    index_elements=["role_id", "permission_id"]
                )
            )


def downgrade() -> None:
    conn = op.get_bind()
    role_ids = [_uuid(f"system-role:{name}") for name in ROLES]
    permission_ids = [_uuid(f"permission:{code}") for code in PERMISSIONS]
    role_placeholders = ",".join(f":rid{i}" for i in range(len(role_ids)))
    role_params = {f"rid{i}": rid for i, rid in enumerate(role_ids)}
    conn.execute(
        sa.text(
            f"DELETE FROM role_permissions WHERE role_id IN ({role_placeholders})"
        ),
        role_params,
    )
    conn.execute(sa.text(f"DELETE FROM roles WHERE id IN ({role_placeholders})"), role_params)
    permission_placeholders = ",".join(
        f":pid{i}" for i in range(len(permission_ids))
    )
    permission_params = {
        f"pid{i}": pid for i, pid in enumerate(permission_ids)
    }
    conn.execute(
        sa.text(
            f"DELETE FROM permissions WHERE id IN ({permission_placeholders}) "
            "AND id NOT IN (SELECT permission_id FROM role_permissions)"
        ),
        permission_params,
    )
