-- Crear tabla de eventos de auditoría (sin actor_type ni service)
CREATE TABLE IF NOT EXISTS audit_events (
    event_id      uuid PRIMARY KEY,
    ts            timestamptz NOT NULL DEFAULT now(),
    actor_id      text,
    actor_role    text,
    request_id    text,
    ip            inet,
    user_agent    text,
    module        text NOT NULL,  -- p.ej. gestion_usuarios
    submodule     text,           -- p.ej. roles, permisos
    feature       text,           -- p.ej. edit, create
    object_type   text,
    object_id     text,
    operation     text NOT NULL,  -- ACCESS | REGISTER | UPDATE | ...
    before        jsonb,
    after         jsonb,
    meta          jsonb,
    permission_id integer,        -- ID del permiso bajo el cual se ejecutó la acción
    diff          jsonb           -- diff calculado entre before/after (estructura la definimos en app)
);

-- Índices útiles
CREATE INDEX IF NOT EXISTS idx_audit_ts
    ON audit_events (ts);

CREATE INDEX IF NOT EXISTS idx_audit_actor
    ON audit_events (actor_id);

CREATE INDEX IF NOT EXISTS idx_audit_operation
    ON audit_events (operation);

CREATE INDEX IF NOT EXISTS idx_audit_lookup
    ON audit_events (module, object_type, object_id);

CREATE INDEX IF NOT EXISTS idx_audit_submodule
    ON audit_events (submodule);

CREATE INDEX IF NOT EXISTS idx_audit_feature
    ON audit_events (feature);

CREATE INDEX IF NOT EXISTS idx_audit_permission_id
    ON audit_events (permission_id);

CREATE INDEX IF NOT EXISTS idx_audit_meta_source
    ON audit_events ((meta->>'source'));

CREATE INDEX IF NOT EXISTS idx_audit_meta_result
    ON audit_events ((meta->>'result'));