-- =========================================
-- Audit schema
-- =========================================

CREATE TABLE IF NOT EXISTS audit_events (
    event_id         UUID PRIMARY KEY,
    ts               TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_id         TEXT NOT NULL,
    actor_name       TEXT NOT NULL,
    actor_role       TEXT NOT NULL,
    permission_id    BIGINT,
    permission_description TEXT,
    operation        TEXT NOT NULL CHECK (operation IN ('CREATE','UPDATE','DELETE','READ','LOGIN','LOGOUT')),
    object_id        TEXT,
    ip               INET,
    user_agent       TEXT,
    diff             JSONB NOT NULL DEFAULT '{"changed": {}, "removed": {}}'
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_audit_events_ts             ON audit_events (ts DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_actor_id       ON audit_events (actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_permission_id  ON audit_events (permission_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_operation      ON audit_events (operation);
CREATE INDEX IF NOT EXISTS idx_audit_events_object_id      ON audit_events (object_id);
CREATE INDEX IF NOT EXISTS idx_audit_events_diff_gin       ON audit_events USING GIN (diff);