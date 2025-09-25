from __future__ import annotations

import os
import uuid
import json
from datetime import datetime, timezone
from typing import List, Dict, Any

from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder

try:
    from zoneinfo import ZoneInfo
except Exception:
    ZoneInfo = None

from .schemas import AuditEventIn
from .db import get_conn

AUDIT_TOKEN = os.getenv("AUDIT_TOKEN", "devtoken")
DEFAULT_TZ = os.getenv("AUDIT_LIST_TZ", "America/Bogota")  # Zona horaria por defecto para listados

app = FastAPI(title="Audit Service", version="2.0.0")


# Helpers
def _ensure_dt_utc(dt: datetime | None) -> datetime:
    """Si viene None, ahora en UTC. Si viene naive, asumir UTC; si trae tz, convertir a UTC."""
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_tz(dt: datetime, tz_name: str | None) -> datetime:
    """Convierte un datetime aware (UTC) a tz de salida; si falla, deja UTC."""
    if tz_name and ZoneInfo:
        try:
            return dt.astimezone(ZoneInfo(tz_name))
        except Exception:
            pass
    return dt


@app.post("/audit-events", status_code=202)
def ingest_v2(event: AuditEventIn, x_audit_token: str = Header(None)):
    # 1) Token
    if x_audit_token != AUDIT_TOKEN:
        raise HTTPException(401, "Invalid audit token")

    # 2) ID y timestamp
    event_id = event.event_id or str(uuid.uuid4())
    ts_utc = _ensure_dt_utc(event.ts)

    # 3) Normalizar operation
    operation = (event.operation or "").upper()
    if not operation:
        raise HTTPException(400, "operation es requerido")

    diff_json = json.dumps(event.diff.model_dump() if event.diff else {"created": {}, "changed": {}, "removed": {}})
    with get_conn() as conn, conn.cursor() as cur:
        # comprobar si existe la columna permission_description en audit_events
        cur.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_name = 'audit_events' AND column_name = 'permission_description'
            LIMIT 1
            """
        )
        has_perm_desc = cur.fetchone() is not None

        # columnas comunes
        cols = [
            "event_id", "ts",
            "actor_id", "actor_name", "actor_role",
            "ip", "user_agent",
            "object_id", "operation",
            "permission_id", "diff"
        ]
        vals = ["%s"] * len(cols)

        params: List[Any] = [
            event_id,
            ts_utc,
            event.actor_id,
            event.actor_name,
            event.actor_role,
            event.ip,
            event.user_agent,
            event.object_id,
            operation,
            event.permission_id,
            diff_json,
        ]

        if has_perm_desc:
            # insertar permission_description justo después de permission_id 
            insert_pos = cols.index("permission_id") + 1
            cols.insert(insert_pos, "permission_description")
            vals.insert(insert_pos, "%s")
            params.insert(insert_pos, event.permission_description)

        sql = f"INSERT INTO audit_events ({', '.join(cols)}) VALUES ({', '.join(vals)})"
        cur.execute(sql, params)
        conn.commit()

    return {"accepted": True, "event_id": event_id}


@app.get("/audit-events")
def list_events_v2(
    actor_id: str | None = Query(None),
    actor_name: str | None = Query(None),
    operation: str | None = Query(None),
    object_id: str | None = Query(None),
    permission_id: int | None = Query(None),
    date_from: str | None = Query(None, description="ISO8601 (p.ej. 2025-09-01T00:00:00Z)"),
    date_to: str | None = Query(None, description="ISO8601"),
    tz: str | None = Query(DEFAULT_TZ, description="Zona horaria de salida (p.ej. America/Bogota)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    # 1) Query dinámica
    q: List[str] = ["SELECT * FROM audit_events WHERE 1=1"]
    p: List[Any] = []

    def add(cond: str, val: Any):
        if val is not None:
            q.append(cond)
            p.append(val)

    add("AND actor_id = %s", actor_id)
    add("AND actor_name ILIKE %s", f"%{actor_name}%" if actor_name else None)
    add("AND operation = %s", operation.upper() if operation else None)
    add("AND object_id = %s", object_id)
    add("AND permission_id = %s", permission_id)
    add("AND ts >= %s", date_from)
    add("AND ts <= %s", date_to)

    q.append("ORDER BY ts DESC LIMIT %s OFFSET %s")
    p.extend([limit, offset])

    # 2) Ejecutar
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(" ".join(q), p)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    # 3) Conversión de zona horaria para salida
    out: List[Dict[str, Any]] = []
    for r in rows:
        ts: datetime | None = r.get("ts")
        if isinstance(ts, datetime):
            ts_loc = _to_tz(ts, tz)
            r["ts"] = ts_loc.isoformat()
        # asegurar que diff siempre tenga las 3 claves (created/changed/removed) para claridad en la API
        if "diff" in r and r["diff"] is not None:
            try:
                d = r["diff"]
                # Normalizar forma mínima
                d.setdefault("created", {})
                d.setdefault("changed", {})
                d.setdefault("removed", {})
                r["diff"] = d
            except Exception:
                pass
        out.append(r)

    return JSONResponse(content=jsonable_encoder(out))


@app.get("/healthz")
def healthz():
    return {"status": "ok"}