from typing import Optional, Dict, Any, Union
from pydantic import BaseModel, ConfigDict

class AuditEventIn(BaseModel):
    event_id: Optional[str] = None
    ts: Optional[str] = None

    actor_id: Optional[str] = None
    actor_role: Optional[str] = None

    request_id: Optional[str] = None
    ip: Optional[str] = None
    user_agent: Optional[str] = None

    module: str
    object_type: Optional[str] = None
    object_id: Optional[str] = None
    operation: str

    before: Optional[Dict[str, Any]] = None
    after: Optional[Dict[str, Any]] = None
    meta: Optional[Dict[str, Any]] = None

    submodule: Optional[str] = None
    feature: Optional[str] = None

    permission_id: Optional[Union[int, str]] = None
    diff: Optional[Dict[str, Any]] = None  

    model_config = ConfigDict(extra="ignore")