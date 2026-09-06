"""Add reports.read permission for reviewer/org_admin (Issue #51 reports API).

Revision ID: 6f7a8b9c0d1e
Revises: 5e4d3c2b1a09
Create Date: 2026-09-06

Additive-only: inserts a new permission code and links it to the existing
``reviewer`` / ``org_admin`` system roles so the audit & compliance reports
endpoints (GET /projects/{id}/reports/*) are enabled for already-seeded
production databases without waiting on an app-side fallback matrix.
``member`` is intentionally excluded — reports are reviewer+ only. Idempotent
via ON CONFLICT DO NOTHING so it is safe to re-run.
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "6f7a8b9c0d1e"
down_revision: Union[str, None] = "5e4d3c2b1a09"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PERMISSION_CODE = "reports.read"
PERMISSION_CATEGORY = "reports"
PERMISSION_DESCRIPTION = "監査・コンプライアンスレポートの閲覧"

ROLES_TO_GRANT = ["reviewer", "org_admin"]


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
        sa.column("is_system_role", sa.Boolean),
    )
    role_permissions_table = sa.table(
        "role_permissions",
        sa.column("id", sa.String),
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
    )

    conn.execute(
        sa.dialects.postgresql.insert(permissions_table)
        .values(
            id=_uuid(f"permission:{PERMISSION_CODE}"),
            code=PERMISSION_CODE,
            category=PERMISSION_CATEGORY,
            description=PERMISSION_DESCRIPTION,
        )
        .on_conflict_do_nothing(index_elements=["code"])
    )

    existing_roles = {
        row.name: row.id
        for row in conn.execute(
            sa.select(roles_table.c.name, roles_table.c.id).where(
                roles_table.c.organization_id.is_(None),
                roles_table.c.is_system_role.is_(True),
                roles_table.c.name.in_(ROLES_TO_GRANT),
            )
        )
    }
    for name in ROLES_TO_GRANT:
        # 9a8b7c6d5e4f (this migration's prerequisite) always creates the
        # member/reviewer/org_admin system roles, so this should always be
        # populated — but skip defensively rather than fail if it is not.
        role_id = existing_roles.get(name)
        if role_id is None:
            continue
        conn.execute(
            sa.dialects.postgresql.insert(role_permissions_table)
            .values(
                id=_uuid(f"rp:{name}:{PERMISSION_CODE}"),
                role_id=role_id,
                permission_id=_uuid(f"permission:{PERMISSION_CODE}"),
            )
            .on_conflict_do_nothing(index_elements=["role_id", "permission_id"])
        )


def downgrade() -> None:
    conn = op.get_bind()
    permission_id = _uuid(f"permission:{PERMISSION_CODE}")
    role_ids = [_uuid(f"system-role:{name}") for name in ROLES_TO_GRANT]
    role_placeholders = ",".join(f":rid{i}" for i in range(len(role_ids)))
    role_params = {f"rid{i}": rid for i, rid in enumerate(role_ids)}
    conn.execute(
        sa.text(
            "DELETE FROM role_permissions WHERE permission_id = :pid "
            f"AND role_id IN ({role_placeholders})"
        ),
        {"pid": permission_id, **role_params},
    )
    conn.execute(
        sa.text(
            "DELETE FROM permissions WHERE id = :pid AND id NOT IN "
            "(SELECT permission_id FROM role_permissions)"
        ),
        {"pid": permission_id},
    )
