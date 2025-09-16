import os, uuid, datetime, json
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from .schemas import AuditEventIn
from .db import get_conn

AUDIT_TOKEN = os.getenv("AUDIT_TOKEN", "devtoken")

app = FastAPI(title="Audit Service", version="0.1.0")

@app.post("/audit-events", status_code=202)
def ingest(ev: AuditEventIn, x_audit_token: str = Header(None)):
    # 1) Validar token
    if x_audit_token != AUDIT_TOKEN:
        raise HTTPException(401, "Invalid audit token")

    # 2) Generar event_id y timestamp 
    event_id = ev.event_id or str(uuid.uuid4())
    ts = ev.ts or (datetime.datetime.utcnow().isoformat() + "Z")

    # 3) Preparar submodule & feature
    submodule = ev.submodule
    feature = ev.feature
    if (not submodule or not feature) and ev.meta and isinstance(ev.meta.get("source"), str):
        src = ev.meta["source"]
        if "." in src:
            left, right = src.split(".", 1)
            submodule = submodule or left
            feature   = feature   or right

    # 4) Normalizar permission_id 
    perm_id_value = None
    if ev.permission_id is not None:
        if isinstance(ev.permission_id, int):
            perm_id_value = ev.permission_id
        elif isinstance(ev.permission_id, str) and ev.permission_id.isdigit():
            perm_id_value = int(ev.permission_id)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO audit_events (
                event_id, ts, actor_id, actor_role,
                request_id, ip, user_agent,
                module, submodule, feature,
                object_type, object_id, operation,
                before, after, meta,
                permission_id, diff
                ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s, %s, %s,
                %s::jsonb, %s::jsonb, %s::jsonb,
                %s, %s::jsonb
            )
        """, (
            event_id, ts, ev.actor_id, ev.actor_role,
            ev.request_id, ev.ip, ev.user_agent,
            ev.module, submodule, feature,
            ev.object_type, ev.object_id, ev.operation,
            json.dumps(ev.before) if ev.before is not None else None,
            json.dumps(ev.after)  if ev.after  is not None else None,
            json.dumps(ev.meta)   if ev.meta   is not None else None,
            perm_id_value,
            json.dumps(ev.diff) if ev.diff is not None else None,
        ))
        conn.commit()

    # 6) Respuesta
    return {"accepted": True, "event_id": event_id}

@app.get("/audit-events")
def list_events(
    actor_id: str | None = None,
    operation: str | None = None,
    module: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    submodule: str | None = Query(None),
    feature: str | None = Query(None),
    source: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    permission_id: int | None = Query(None),
    limit: int = 100,
    offset: int = 0,
):
    q = ["SELECT * FROM audit_events WHERE 1=1"]
    p: list = []

    def add(cond, val):
        if val is not None:
            q.append(cond); p.append(val)

    add("AND actor_id = %s", actor_id)
    add("AND operation = %s", operation)
    add("AND module = %s", module)
    add("AND object_type = %s", object_type)
    add("AND object_id = %s", object_id)
    add("AND LOWER(submodule) = LOWER(%s)", submodule)
    add("AND LOWER(feature) = LOWER(%s)", feature)
    add("AND meta->>'source' = %s", source)
    add("AND ts >= %s", date_from)
    add("AND ts <= %s", date_to)
    add("AND permission_id = %s", permission_id)

    q.append("ORDER BY ts DESC LIMIT %s OFFSET %s")
    p.extend([limit, offset])

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(" ".join(q), p)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    return JSONResponse(content=jsonable_encoder(rows))

@app.get("/healthz")
def healthz():
    return {"status": "ok"}