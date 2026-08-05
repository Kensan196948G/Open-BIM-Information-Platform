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

-- The trigger binding is applied by Alembic migration
-- 1f2e3d4c5b6a_add_audit_logs_trigger (alembic upgrade head).
