"""add_project_naming_rules

Revision ID: b2c3d4e5f6a7
Revises: 46aeadb1d6d7
Create Date: 2026-06-03 07:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "46aeadb1d6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "project_naming_rules",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column(
            "separator", sa.String(length=10), nullable=False, server_default="-"
        ),
        sa.Column("segments", sa.JSON(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", name="uq_project_naming_rule"),
    )
    op.create_index(
        "ix_project_naming_rules_project_id",
        "project_naming_rules",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_project_naming_rules_project_id", table_name="project_naming_rules"
    )
    op.drop_table("project_naming_rules")
