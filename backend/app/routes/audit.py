import json
from sqlalchemy import select, func
from fastapi import APIRouter, Depends, Query, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import datetime
from app.db.session import get_async_db
from app.core.dependencies import require_admin, get_current_user, require_permission
from app.models.user import Usuario
from app.models.audit import AuditLog
from app.models.punto import PuntoInteres
from app.services.audit_service import log_action
from app.core.request_ip import get_client_ip

router = APIRouter(prefix="/api/audit", tags=["Auditoría"])

ENTITY_TYPES = ["Auth", "Usuario", "Foto", "PuntoInteres", "Producto", "Sesion", "Permisos"]


@router.get("/logs")
async def get_audit_logs(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    search: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('users', 'read', fallback_roles=('admin', 'analyst', 'auditor'))),
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
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.filter(
            AuditLog.entity_name.ilike(term) |
            AuditLog.entity_id.ilike(term) |
            AuditLog.changes.ilike(term)
        )
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
async def get_entity_types(_: Usuario = Depends(get_current_user)):
    return ENTITY_TYPES


@router.get("/pdvs")
async def get_pdv_audit_logs(
    action: Optional[str] = None,
    username: Optional[str] = None,
    search: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('points', 'read', fallback_roles=('admin', 'analyst', 'auditor', 'atc'))),
):
    stmt = select(AuditLog).filter(
        (AuditLog.entity_type == "PuntoInteres") | 
        (AuditLog.action.in_(["CREATE_POINT", "UPDATE_POINT", "DELETE_POINT", "RESTORE_POINT", "MERGE_DELETE_POINT"]))
    )
    if action:
        stmt = stmt.filter(AuditLog.action.ilike(f"%{action}%"))
    if username:
        stmt = stmt.filter(AuditLog.username.ilike(f"%{username}%"))
    if search:
        term = f"%{search.strip()}%"
        stmt = stmt.filter(
            AuditLog.entity_name.ilike(term) | 
            AuditLog.entity_id.ilike(term) |
            AuditLog.changes.ilike(term)
        )
    if status:
        stmt = stmt.filter(AuditLog.status == status)

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    logs = (await db.execute(stmt.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit))).scalars().all()

    items = []
    for log in logs:
        parsed_changes = None
        if log.changes:
            try:
                parsed_changes = json.loads(log.changes)
            except Exception:
                parsed_changes = log.changes

        items.append({
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
            "changes": parsed_changes,
            "status": log.status or "OK",
        })

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": items
    }


@router.post("/pdvs/{audit_id}/restore")
async def restore_pdv_from_audit(
    audit_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('points', 'write', fallback_roles=('admin', 'analyst'))),
):
    log_entry = (await db.execute(select(AuditLog).filter(AuditLog.id == audit_id))).scalars().first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Registro de auditoría no encontrado")

    if not log_entry.changes:
        raise HTTPException(status_code=400, detail="El registro de auditoría no contiene datos para restablecer")

    try:
        changes = json.loads(log_entry.changes) if isinstance(log_entry.changes, str) else log_entry.changes
    except Exception:
        raise HTTPException(status_code=400, detail="No se pudo interpretar el historial de cambios")

    before_data = changes.get("before") or changes.get("old") or changes
    if not before_data or not isinstance(before_data, dict):
        raise HTTPException(status_code=400, detail="El registro no contiene datos anteriores válidos para restaurar")

    catalog_key = before_data.get("catalog")
    if catalog_key or "CATALOG" in log_entry.action:
        from app.routes.catalogos import _resolve_generic, CATALOG_USAGE
        cat_name = catalog_key or "tipo-negocio"
        cat_item_id = int(log_entry.entity_id or before_data.get("id"))
        cat_item_name = before_data.get("nombre")
        affected_pdv_ids = before_data.get("affected_pdv_ids") or []

        Model = _resolve_generic(cat_name)
        cat_item = (await db.execute(select(Model).filter(Model.id == cat_item_id))).scalars().first()
        if not cat_item:
            cat_item = Model(id=cat_item_id, nombre=cat_item_name, activo=True)
            db.add(cat_item)
        else:
            cat_item.activo = True
            if cat_item_name:
                cat_item.nombre = cat_item_name

        reassigned_count = 0
        if affected_pdv_ids and cat_name in CATALOG_USAGE:
            usage_model, usage_column, _ = CATALOG_USAGE[cat_name]
            if usage_model is PuntoInteres and cat_item_name:
                from sqlalchemy import update
                stmt = (
                    update(PuntoInteres)
                    .where(PuntoInteres.id.in_(affected_pdv_ids))
                    .values({usage_column: cat_item_name})
                )
                await db.execute(stmt)
                reassigned_count = len(affected_pdv_ids)

        log_entry.status = "RESTORED"
        log_action(db, action="RESTORE_CATALOG_ITEM", entity_type="PuntoInteres",
                   user_id=current_user.id, username=current_user.username, rol=current_user.rol,
                   ip_address=get_client_ip(request),
                   entity_id=str(cat_item_id), entity_name=cat_item_name or str(cat_item_id),
                   changes={"restored_from_log_id": audit_id, "data": before_data, "reassigned_pdvs_count": reassigned_count})
        await db.commit()
        msg = f"Ítem de catálogo '{cat_item_name}' restablecido exitosamente"
        if reassigned_count > 0:
            msg += f" y reasignado automáticamente a {reassigned_count} PDV(s)"
        return {"message": msg}

    point_id = log_entry.entity_id or before_data.get("id")
    if not point_id:
        raise HTTPException(status_code=400, detail="El código de PDV no fue especificado")

    punto = (await db.execute(select(PuntoInteres).filter(PuntoInteres.id == point_id))).scalars().first()

    if not punto:
        # Recrear el PDV eliminado
        from datetime import datetime
        punto = PuntoInteres(
            id=point_id,
            nombre=before_data.get("nombre"),
            direccion=before_data.get("direccion"),
            latitud=before_data.get("latitud"),
            longitud=before_data.get("longitud"),
            departamento=before_data.get("departamento"),
            jerarquia_n2=before_data.get("jerarquia_n2"),
            jerarquia_n2_2=before_data.get("jerarquia_n2_2"),
            ciudad=before_data.get("ciudad"),
            localidad=before_data.get("localidad"),
            cadena=before_data.get("cadena"),
            radio=before_data.get("radio"),
            tiempo_minimo=before_data.get("tiempo_minimo", 15),
            fecha_creado=datetime.now(),
            nivel_de_alcance=before_data.get("nivel_de_alcance"),
            rif=before_data.get("rif"),
        )
        db.add(punto)
    else:
        # Revertir propiedades del PDV a los valores originales (before)
        for key in ["nombre", "direccion", "latitud", "longitud", "departamento", 
                    "jerarquia_n2", "jerarquia_n2_2", "ciudad", "localidad", "cadena", 
                    "radio", "tiempo_minimo", "nivel_de_alcance", "rif"]:
            if key in before_data:
                setattr(punto, key, before_data[key])

    log_entry.status = "RESTORED"
    log_action(db, action="RESTORE_POINT", entity_type="PuntoInteres",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=point_id, entity_name=before_data.get("nombre", point_id),
               changes={"restored_from_log_id": audit_id, "data": before_data})

    await db.commit()
    return {"message": f"Punto de venta '{point_id}' restablecido exitosamente"}


@router.post("/pdvs/{audit_id}/approve")
async def approve_pdv_audit(
    audit_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('points', 'write', fallback_roles=('admin', 'analyst'))),
):
    log_entry = (await db.execute(select(AuditLog).filter(AuditLog.id == audit_id))).scalars().first()
    if not log_entry:
        raise HTTPException(status_code=404, detail="Registro no encontrado")
    log_entry.status = "APPROVED"
    await db.commit()
    return {"message": "Estado actualizado a APROBADO"}
