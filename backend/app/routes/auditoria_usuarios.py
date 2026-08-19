from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select
from typing import Optional, List
from datetime import datetime
import json

from app.db.session import get_db, get_async_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario

router = APIRouter(prefix="/api/auditoria-usuarios", tags=["Auditoría de Usuarios"])


@router.get("")
@router.get("/")
async def get_auditoria_usuarios(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    accion: Optional[str] = None,
    ejecutor: Optional[str] = None,
    search: Optional[str] = None,
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Consulta el historial de auditoría de creación, edición, borrado y asignación de roles de usuarios."""
    # Guard manual — sólo admin, analyst y auditor pueden ver la auditoría
    ROLES_PERMITIDOS = {"admin", "superadmin", "analyst", "auditor"}
    if current_user.rol not in ROLES_PERMITIDOS and current_user.id_rol not in (2, 7, 8):
        raise HTTPException(status_code=403, detail="Sin permiso para ver la auditoría de usuarios")

    where_clauses = ["entity_type IN ('Usuario', 'Permisos', 'User') OR action IN ('CREATE_USER', 'UPDATE_USER', 'DELETE_USER', 'UPDATE_PERMISSIONS')"]
    params = {"skip": skip, "limit": limit}

    if accion:
        where_clauses.append("action = :accion")
        params["accion"] = accion

    if ejecutor:
        where_clauses.append("username LIKE :ejecutor")
        params["ejecutor"] = f"%{ejecutor}%"

    if search:
        where_clauses.append("(username LIKE :search OR entity_name LIKE :search OR changes LIKE :search)")
        params["search"] = f"%{search}%"

    if fecha_inicio:
        where_clauses.append("timestamp >= :fecha_inicio")
        params["fecha_inicio"] = fecha_inicio

    if fecha_fin:
        where_clauses.append("timestamp <= :fecha_fin")
        params["fecha_fin"] = fecha_fin

    where_sql = " AND ".join(f"({c})" for c in where_clauses)

    count_query = text(f"SELECT COUNT(*) FROM AUDIT_LOG WHERE {where_sql}")
    total = (await db.execute(count_query, params)).scalar() or 0

    query = text(f"""
        SELECT id, user_id, username, rol, ip_address, action, entity_type, entity_id, entity_name, changes, status, timestamp
        FROM AUDIT_LOG
        WHERE {where_sql}
        ORDER BY id DESC
        OFFSET :skip ROWS FETCH NEXT :limit ROWS ONLY
    """)

    rows = (await db.execute(query, params)).fetchall()

    result = []
    for r in rows:
        changes_parsed = None
        if r.changes:
            try:
                changes_parsed = json.loads(r.changes)
            except Exception:
                changes_parsed = r.changes

        result.append({
            "id": r.id,
            "user_id": r.user_id,
            "username": r.username or "Sistema",
            "rol": r.rol or "N/A",
            "ip_address": r.ip_address,
            "action": r.action,
            "entity_type": r.entity_type,
            "entity_id": r.entity_id,
            "entity_name": r.entity_name,
            "changes": changes_parsed,
            "status": r.status,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None,
        })

    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "data": result,
    }
