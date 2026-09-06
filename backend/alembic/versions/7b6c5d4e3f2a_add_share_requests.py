"""Add share_requests table and share_request.manage permission (Issue #55).

External-share request workflow: a member requests a time-limited share
link for a container; a reviewer (or higher) approves/rejects it. This
migration is purely additive:
  - creates a new ``share_requests`` table (no existing table touched)
  - idempotently inserts the ``share_request.manage`` permission and grants
    it to the ``reviewer``/``org_admin`` system roles, following the same
    pattern as ``9a8b7c6d5e4f_add_rbac_seed_roles``.

Revision ID: 7b6c5d4e3f2a
Revises: 7f8a9b0c1d2e
Create Date: 2026-09-06
"""

import uuid
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7b6c5d4e3f2a"
down_revision: Union[str, None] = "7f8a9b0c1d2e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

PERMISSION_CODE = "share_request.manage"
PERMISSION_CATEGORY = "share_request"
PERMISSION_DESCRIPTION = "外部共有申請の承認・却下・失効"

# Granted to the same roles that already hold container.approve/return, i.e.
# reviewer and org_admin (member can still *create* requests via the
# pre-existing container.read permission — no new grant needed there).
GRANTED_ROLES = ("reviewer", "org_admin")


def _uuid(seed: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_OID, seed))


def upgrade() -> None:
    # Note: the ENUM type is created automatically as part of op.create_table
    # below (matching the pattern used for workflowstatus/approvalresult in
    # 46aeadb1d6d7_initial_schema.py) — do NOT also pre-create it via a
    # standalone `CREATE TYPE` statement, since embedding a plain sa.Enum
    # column in create_table already emits the CREATE TYPE DDL and a second,
    # manual one raises DuplicateObjectError on Postgres.
    op.create_table(
        "share_requests",
        sa.Column("container_id", sa.String(length=36), nullable=False),
        sa.Column("requested_by_user_id", sa.String(length=36), nullable=False),
        sa.Column("approved_by_user_id", sa.String(length=36), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "approved",
                "rejected",
                "revoked",
                "expired",
                name="sharerequeststatus",
            ),
            nullable=False,
        ),
        sa.Column("token", sa.String(length=64), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["container_id"], ["information_containers.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["approved_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        op.f("ix_share_requests_container_id"),
        "share_requests",
        ["container_id"],
        unique=False,
    )

    # ─── Seed permission + role grants (additive, idempotent) ─────────────
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
                roles_table.c.name.in_(GRANTED_ROLES),
            )
        )
    }
    for name in GRANTED_ROLES:
        role_id = existing_roles.get(name) or _uuid(f"system-role:{name}")
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
    role_ids = [_uuid(f"system-role:{name}") for name in GRANTED_ROLES]
    permission_id = _uuid(f"permission:{PERMISSION_CODE}")
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
            "DELETE FROM permissions WHERE id = :pid "
            "AND id NOT IN (SELECT permission_id FROM role_permissions)"
        ),
        {"pid": permission_id},
    )

    op.drop_index(op.f("ix_share_requests_container_id"), table_name="share_requests")
    op.drop_table("share_requests")
    op.execute("DROP TYPE IF EXISTS sharerequeststatus;")
