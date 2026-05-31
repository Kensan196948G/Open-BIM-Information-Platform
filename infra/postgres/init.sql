-- PostgreSQL initialization for Open BIM Platform
-- Extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";  -- for full-text search

-- Audit log trigger function (append-only enforcement)
CREATE OR REPLACE FUNCTION prevent_audit_log_modification()
RETURNS TRIGGER AS $$
BEGIN
  RAISE EXCEPTION 'audit_logs are immutable — DELETE and UPDATE are forbidden';
END;
$$ LANGUAGE plpgsql;

-- Note: the trigger binding is applied in the Alembic migration that creates
-- the audit_logs table, so the function is available before tables exist here.
-- The migration will run:
--   CREATE TRIGGER audit_logs_no_modify
--   BEFORE UPDATE OR DELETE ON audit_logs
--   FOR EACH ROW EXECUTE FUNCTION prevent_audit_log_modification();
