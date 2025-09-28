from __future__ import annotations

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field, ConfigDict, field_validator, model_validator


class AuditDiff(BaseModel):
    """
    Nuevo diff v2 extendido que incluye:
      - created: objetos totalmente nuevos (sin "from")
      - changed: campos modificados { field: {"from": X, "to": Y}, ... }
      - removed: campos eliminados { field: <valor_anterior>, ... }

    Se fuerza que los tres sean diccionarios y por defecto vacíos.
    """
    created: Dict[str, Any] = Field(default_factory=dict)
    changed: Dict[str, Any] = Field(default_factory=dict)
    removed: Dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="after")
    def _validate_shapes(self) -> "AuditDiff":
        if not isinstance(self.created, dict):
            raise ValueError("diff.created debe ser un objeto (dict).")
        if not isinstance(self.changed, dict):
            raise ValueError("diff.changed debe ser un objeto (dict).")
        if not isinstance(self.removed, dict):
            raise ValueError("diff.removed debe ser un objeto (dict).")
        return self


class AuditEventIn(BaseModel):
    """
    Evento de entrada para ingest v2.
    - permission_description: texto opcional con la descripción del permiso (se puede poblar en el emisor).
    - diff: AuditDiff (ahora con created/changed/removed).
    - meta: objeto libre para pasar metadatos (p.ej. result, username_hint, razón).
    """
    # IDs / tiempo
    event_id: Optional[str] = Field(default=None)
    ts: Optional[datetime] = Field(
        default=None,
        description="Timestamp del evento. Si llega naive, se asume UTC.",
    )

    # Actor
    actor_id: str
    actor_name: str
    actor_role: str

    # Contexto
    ip: Optional[str] = None
    user_agent: Optional[str] = None

    # Objeto afectado
    object_id: Optional[str] = None

    # Operación & permiso
    operation: str
    permission_id: Optional[int] = None
    # permission_description: Optional[str] = None

    # Diff
    diff: AuditDiff = Field(default_factory=AuditDiff)

    # Meta (libre, opcional). Útil para result/hint u otros datos no normalizados.
    meta: Optional[Dict[str, Any]] = Field(default_factory=dict)

    model_config = ConfigDict(extra="forbid")

    # --- Normalizaciones/validaciones ---

    @field_validator("ts", mode="before")
    @classmethod
    def _parse_ts(cls, v):
        # mantener compatibilidad con strings ISO y datetime; asumir UTC si es naive
        if v is None:
            return None
        if isinstance(v, datetime):
            return v.replace(tzinfo=timezone.utc) if v.tzinfo is None else v
        dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)

    @field_validator("operation")
    @classmethod
    def _upper_operation(cls, v: str) -> str:
        if not v:
            raise ValueError("operation es requerido.")
        return str(v).upper()

    @model_validator(mode="after")
    def _required_actor_fields(self) -> "AuditEventIn":
        # Campos actor obligatorios no vacíos
        for f in ("actor_id", "actor_name", "actor_role"):
            if not getattr(self, f, None):
                raise ValueError(f"{f} es requerido.")
        # Asegurar diff tiene la forma correcta (AuditDiff ya valida, esto es redundante pero seguro)
        if not isinstance(self.diff, AuditDiff):
            raise ValueError("diff inválido.")
        # meta debe ser dict si viene
        if self.meta is None:
            self.meta = {}
        elif not isinstance(self.meta, dict):
            raise ValueError("meta debe ser un objeto (dict).")
        return self