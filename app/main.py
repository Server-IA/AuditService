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
from dotenv import load_dotenv

load_dotenv()

AUDIT_TOKEN = os.getenv("AUDIT_TOKEN")
if not AUDIT_TOKEN:
    raise RuntimeError("AUDIT_TOKEN no está definido en el entorno")

DEFAULT_TZ = os.getenv("AUDIT_LIST_TZ", "America/Bogota")

app = FastAPI(title="Audit Service", version="2.0.0")


# Helpers
def _ensure_dt_utc(dt: datetime | None) -> datetime:
    if dt is None:
        return datetime.now(timezone.utc)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _to_tz(dt: datetime, tz_name: str | None) -> datetime:
    if tz_name and ZoneInfo:
        try:
            return dt.astimezone(ZoneInfo(tz_name))
        except Exception:
            pass
    return dt


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
def ingest_v2(event: AuditEventIn, x_audit_token: str = Header(None)):
    if x_audit_token != AUDIT_TOKEN:
        raise HTTPException(401, "Invalid audit token")

    event_id = event.event_id or str(uuid.uuid4())
    ts_utc = _ensure_dt_utc(event.ts)

    operation = (event.operation or "").upper()
    if not operation:
        raise HTTPException(400, "operation es requerido")

    try:
        diff_obj = event.diff.model_dump() if event.diff else {"created": {}, "changed": {}, "removed": {}}
    except Exception:
        diff_obj = getattr(event, "diff", {"created": {}, "changed": {}, "removed": {}}) or {"created": {}, "changed": {}, "removed": {}}

    diff_obj.setdefault("created", {})
    diff_obj.setdefault("changed", {})
    diff_obj.setdefault("removed", {})

    diff_json = json.dumps(diff_obj, default=str)

    try:
        meta_obj = event.meta if getattr(event, "meta", None) is not None else {}
    except Exception:
        meta_obj = {}
    if not isinstance(meta_obj, dict):
        meta_obj = {}
    meta_json = json.dumps(meta_obj, default=str)

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'audit_events'
              AND column_name = 'meta'
            """
        )
        cols_on_table = {row[0] for row in cur.fetchall()}
        has_meta = "meta" in cols_on_table

        cols = [
            "event_id", "ts",
            "actor_id", "actor_name", "actor_role",
            "ip", "user_agent",
            "object_id", "operation",
            "permission_id", "module", "submodule", "diff"
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
            getattr(event, "module", None),
            getattr(event, "submodule", None),
            diff_json,
        ]

        if has_meta:
            cols.append("meta")
            vals.append("%s")
            params.append(meta_json)

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
    module: str | None = Query(None),
    submodule: str | None = Query(None),
    date_from: str | None = Query(None, description="ISO8601 (p.ej. 2025-09-01T00:00:00Z)"),
    date_to: str | None = Query(None, description="ISO8601"),
    tz: str | None = Query(DEFAULT_TZ, description="Zona horaria de salida (p.ej. America/Bogota)"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
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
    add("AND module = %s", module)
    add("AND submodule = %s", submodule)
    add("AND ts >= %s", date_from)
    add("AND ts <= %s", date_to)

    q.append("ORDER BY ts DESC LIMIT %s OFFSET %s")
    p.extend([limit, offset])

    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(" ".join(q), p)
        cols = [d[0] for d in cur.description]
        rows = [dict(zip(cols, r)) for r in cur.fetchall()]

    out: List[Dict[str, Any]] = []
    for r in rows:
        ts: datetime | None = r.get("ts")
        if isinstance(ts, datetime):
            ts_loc = _to_tz(ts, tz)
            r["ts"] = ts_loc.isoformat()

        if "diff" in r and r["diff"] is not None:
            try:
                d = r["diff"]
                if isinstance(d, str):
                    d = json.loads(d)
                d.setdefault("created", {})
                d.setdefault("changed", {})
                d.setdefault("removed", {})
                r["diff"] = d
            except Exception:
                pass

        if "meta" in r:
            try:
                m = r["meta"]
                if m is None:
                    r["meta"] = {}
                elif isinstance(m, str):
                    r["meta"] = json.loads(m)
                elif isinstance(m, dict):
                    r["meta"] = m
                else:
                    r["meta"] = {}
            except Exception:
                r["meta"] = {}

        out.append(r)

    return JSONResponse(content=jsonable_encoder(out))


@app.get("/healthz")
def healthz():
    return {"status": "ok"}
