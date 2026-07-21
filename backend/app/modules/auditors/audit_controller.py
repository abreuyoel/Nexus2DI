from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional
from datetime import datetime
from app.db.session import get_db
from app.core.dependencies import require_admin
from app.modules.auth.entities import Usuario
from app.modules.auditors.entities import AuditLog

router = APIRouter(prefix="/api/audit", tags=["Auditoría"])

ENTITY_TYPES = ["Auth", "Usuario", "Foto", "PuntoInteres", "Producto", "Sesion", "Permisos"]


@router.get("/logs")
def get_audit_logs(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if username:
        q = q.filter(AuditLog.username.ilike(f"%{username}%"))
    if from_date:
        q = q.filter(AuditLog.timestamp >= from_date)
    if to_date:
        q = q.filter(AuditLog.timestamp <= to_date)
    if status:
        q = q.filter(AuditLog.status == status)

    total = q.count()
    logs = q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "user_id": log.user_id,
                "username": log.username,
                "rol": log.rol,
                "ip_address": log.ip_address,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "entity_name": log.entity_name,
                "changes": log.changes,
                "status": log.status,
            }
            for log in logs
        ],
    }


@router.get("/entity-types")
def get_entity_types(_: Usuario = Depends(require_admin)):
    return ENTITY_TYPES
