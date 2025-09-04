from pydantic import BaseModel
from typing import Optional, Dict, Any

class AuditEventIn(BaseModel):
    event_id: Optional[str] = None
    ts: Optional[str] = None
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    actor_type: Optional[str] = None  # user|service
    request_id: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None
    service: str
    module: str
    object_type: Optional[str] = None
    object_id: Optional[str] = None
    operation: str
    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None