"""add requirement item status/notes columns

Revision ID: 3c4d5e6f7a8b
Revises: 2a3b4c5d6e7f
Create Date: 2026-08-05
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "3c4d5e6f7a8b"
down_revision: Union[str, None] = "2a3b4c5d6e7f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE itemstatus AS ENUM ('met', 'partial', 'not_met');")
    op.add_column(
        "requirement_items",
        sa.Column(
            "status",
            sa.Enum("met", "partial", "not_met", name="itemstatus", create_type=False),
            server_default="not_met",
            nullable=False,
        ),
    )
    op.add_column(
        "requirement_items",
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("requirement_items", "notes")
    op.drop_column("requirement_items", "status")
    op.execute("DROP TYPE IF EXISTS itemstatus;")
