-- Crear tabla de eventos de auditoría
CREATE TABLE IF NOT EXISTS audit_events (
    event_id    uuid PRIMARY KEY,
    ts          timestamptz NOT NULL DEFAULT now(),
    actor_id    text,
    actor_role  text,
    actor_type  text,          -- user | service
    request_id  text,
    ip          inet,
    user_agent  text,
    service     text NOT NULL, -- users | machinery | payroll | ...
    module      text NOT NULL, -- gestion_usuarios | nomina | ...
    object_type text,
    object_id   text,
    operation   text NOT NULL, -- ACCESS | REGISTER | UPDATE | ...
    before      jsonb,
    after       jsonb,
    meta        jsonb
);

-- Índices para mejorar consultas comunes
CREATE INDEX IF NOT EXISTS idx_audit_ts
    ON audit_events (ts);

CREATE INDEX IF NOT EXISTS idx_audit_actor
    ON audit_events (actor_id);

CREATE INDEX IF NOT EXISTS idx_audit_operation
    ON audit_events (operation);

CREATE INDEX IF NOT EXISTS idx_audit_lookup
    ON audit_events (module, object_type, object_id);