"""add requirement item due_date/milestone_name columns

Revision ID: 7f8a9b0c1d2e
Revises: 6f7a8b9c0d1e
Create Date: 2026-09-06
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "7f8a9b0c1d2e"
down_revision: Union[str, None] = "6f7a8b9c0d1e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "requirement_items",
        sa.Column("due_date", sa.String(length=20), nullable=True),
    )
    op.add_column(
        "requirement_items",
        sa.Column("milestone_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("requirement_items", "milestone_name")
    op.drop_column("requirement_items", "due_date")
