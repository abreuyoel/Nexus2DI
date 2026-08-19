from sqlalchemy import select, func
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from app.db.session import get_async_db
from app.core.dependencies import require_admin
from app.models.user import Usuario
from app.models.audit import AuditLog

router = APIRouter(prefix="/api/audit", tags=["Auditoría"])

ENTITY_TYPES = ["Auth", "Usuario", "Foto", "PuntoInteres", "Producto", "Sesion", "Permisos"]


@router.get("/logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    stmt = select(AuditLog)
    if entity_type:
        stmt = stmt.filter(AuditLog.entity_type == entity_type)
    if action:
        stmt = stmt.filter(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        stmt = stmt.filter(AuditLog.user_id == user_id)
    if username:
        stmt = stmt.filter(AuditLog.username.ilike(f"%{username}%"))
    if from_date:
        stmt = stmt.filter(AuditLog.timestamp >= from_date)
    if to_date:
        stmt = stmt.filter(AuditLog.timestamp <= to_date)
    if status:
        stmt = stmt.filter(AuditLog.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    logs = (await db.execute(stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit))).scalars().all()

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
async def get_entity_types(_: Usuario = Depends(require_admin)):
    return ENTITY_TYPES

