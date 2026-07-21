import json
from typing import Optional, Any
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.modules.auditors.entities import AuditLog


def log_action(
    db: Session,
    *,
    action: str,
    entity_type: str,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    rol: Optional[str] = None,
    ip_address: Optional[str] = None,
    entity_id: Optional[Any] = None,
    entity_name: Optional[str] = None,
    changes: Optional[dict] = None,
    status: str = "OK",
) -> None:
    """Add an audit entry to the session. Caller must commit."""
    db.add(AuditLog(
        user_id=user_id,
        username=username,
        rol=rol,
        ip_address=ip_address,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id is not None else None,
        entity_name=entity_name,
        changes=json.dumps(changes, default=str, ensure_ascii=False) if changes else None,
        status=status,
        timestamp=datetime.now(timezone.utc),
    ))
    try:
        from app.services.realtime import notify_event
        notify_event("audit.created", {"action": action, "entity_type": entity_type, "username": username})
    except Exception:
        pass
