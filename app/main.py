import os, uuid, datetime, json
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from .schemas import AuditEventIn
from .db import get_conn

AUDIT_TOKEN = os.getenv("AUDIT_TOKEN", "devtoken")

app = FastAPI(title="Audit Service", version="0.1.0")

# Configuración de CORS para permitir acceso desde cualquier origen
from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        os.getenv("FRONTEND_PRUEBAS_URL"),
        os.getenv("FRONTEND_URL"),
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
)

@app.post("/audit-events", status_code=202)
def ingest(ev: AuditEventIn, x_audit_token: str = Header(None)):
    # 1) Validar token
    if x_audit_token != AUDIT_TOKEN:
        raise HTTPException(401, "Invalid audit token")

    # 2) Generar event_id y timestamp si no vienen
    event_id = ev.event_id or str(uuid.uuid4())
    ts = ev.ts or (datetime.datetime.utcnow().isoformat() + "Z")

    # 3) Preparar submodule y feature
    submodule = ev.submodule
    feature = ev.feature
    if (not submodule or not feature) and ev.meta and isinstance(ev.meta.get("source"), str):
        src = ev.meta["source"]
        if "." in src:
            left, right = src.split(".", 1)
            submodule = submodule or left
            feature   = feature   or right

    # 4) Insertar en la base
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""
            INSERT INTO audit_events (
              event_id, ts, actor_id, actor_role, actor_type,
              request_id, ip, user_agent, service, module,
              submodule, feature,
              object_type, object_id, operation,
              before, after, meta
            ) VALUES (
              %s, %s, %s, %s, %s,
              %s, %s, %s, %s, %s,
              %s, %s,
              %s, %s, %s,
              %s::jsonb, %s::jsonb, %s::jsonb
            )
        """, (
            event_id, ts, ev.actor_id, ev.actor_role, ev.actor_type,
            ev.request_id, ev.ip, ev.user_agent, ev.service, ev.module,
            submodule, feature,
            ev.object_type, ev.object_id, ev.operation,
            json.dumps(ev.before) if ev.before else None,
            json.dumps(ev.after)  if ev.after  else None,
            json.dumps(ev.meta)   if ev.meta   else None,
        ))
        conn.commit()

    # 5) Respuesta
    return {"accepted": True, "event_id": event_id}

@app.get("/audit-events")
def list_events(
    actor_id: str | None = None,
    operation: str | None = None,
    module: str | None = None,
    service: str | None = None,
    object_type: str | None = None,
    object_id: str | None = None,
    submodule: str | None = Query(None),   
    feature: str | None = Query(None),  
    source: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    limit: int = 100,
    offset: int = 0,
):
    q = ["SELECT * FROM audit_events WHERE 1=1"]
    p = []
    def add(cond, val):
        if val is not None:
            q.append(cond); p.append(val)
    add("AND actor_id = %s", actor_id)
    add("AND operation = %s", operation)
    add("AND module = %s", module)
    add("AND service = %s", service)
    add("AND object_type = %s", object_type)
    add("AND object_id = %s", object_id)
    add("AND LOWER(submodule) = LOWER(%s)", submodule)
    add("AND LOWER(feature) = LOWER(%s)", feature) 
    add("AND meta->>'source' = %s", source)
    add("AND ts >= %s", date_from)
    add("AND ts <= %s", date_to)
    q.append("ORDER BY ts DESC LIMIT %s OFFSET %s")
    p.extend([limit, offset])

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(" ".join(q), p)
        # Nombres de columnas compatibles con psycopg2 y psycopg3
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    # Asegura que datetime/inet etc. sean serializables
    return JSONResponse(content=jsonable_encoder(rows))

@app.get("/healthz")
def healthz():
    return {"status": "ok"}