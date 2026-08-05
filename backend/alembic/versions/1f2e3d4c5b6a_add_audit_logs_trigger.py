"""add audit_logs immutable trigger

Revision ID: 1f2e3d4c5b6a
Revises: b2c3d4e5f6a7
Create Date: 2026-08-05
"""

from typing import Sequence, Union

from alembic import op

revision: str = "1f2e3d4c5b6a"
down_revision: Union[str, None] = "b2c3d4e5f6a7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

FUNCTION_SQL = """
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'audit_logs are immutable — DELETE and UPDATE are forbidden';
END;
$$ LANGUAGE plpgsql;
"""

DROP_TRIGGER_IF_EXISTS_SQL = """
DO $$
BEGIN
  IF EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'audit_logs_no_modify') THEN
    DROP TRIGGER audit_logs_no_modify ON audit_logs;
  END IF;
END $$;
"""

TRIGGER_SQL = """
CREATE TRIGGER audit_logs_no_modify
BEFORE UPDATE OR DELETE ON audit_logs
FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
"""


def upgrade() -> None:
    op.execute(FUNCTION_SQL)
    op.execute(DROP_TRIGGER_IF_EXISTS_SQL)
    op.execute(TRIGGER_SQL)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS audit_logs_no_modify ON audit_logs;")
