from sqlalchemy import select, delete
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.db.session import get_db, get_async_db
from app.core.dependencies import require_admin
from app.models.user import Usuario
from app.models.sesion import SesionActiva
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/admin/sessions", tags=["Admin - Sesiones"])


@router.get("/active")
async def get_active_sessions(
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    sessions = (await db.execute(
        select(SesionActiva)
        .filter(SesionActiva.activa == True)
        .order_by(SesionActiva.created_at.desc())
    )).scalars().all()
    return [
        {
            "id": s.id,
            "user_id": s.user_id,
            "username": s.username,
            "rol": s.rol,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "created_at": s.created_at,
            "last_active": s.last_active,
        }
        for s in sessions
    ]


@router.post("/kill/{session_id}")
async def kill_session(
    session_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_admin),
):
    session = (await db.execute(select(SesionActiva).filter(SesionActiva.id == session_id))).scalars().first()
    if not session:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")
    if not session.activa:
        raise HTTPException(status_code=400, detail="La sesión ya está inactiva")

    session.activa = False
    session.fecha_cierre = datetime.now(timezone.utc)
    session.motivo_cierre = f"Terminada por admin: {current_user.username}"

    log_action(db, action="KILL_SESSION", entity_type="Sesion",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               entity_id=session_id, entity_name=session.username,
               changes={"target_user": session.username, "target_rol": session.rol, "ip": session.ip_address})
    await db.commit()
    return {"message": f"Sesión {session_id} terminada"}


@router.post("/kill-user/{user_id}")
async def kill_user_sessions(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_admin),
):
    target = (await db.execute(select(Usuario).filter(Usuario.id == user_id))).scalars().first()
    target_name = target.username if target else str(user_id)
    now = datetime.now(timezone.utc)

    sessions = (await db.execute(
        select(SesionActiva).filter(
            SesionActiva.user_id == user_id, SesionActiva.activa == True
        )
    )).scalars().all()
    for s in sessions:
        s.activa = False
        s.fecha_cierre = now
        s.motivo_cierre = f"Todas las sesiones terminadas por admin: {current_user.username}"

    log_action(db, action="KILL_ALL_SESSIONS", entity_type="Sesion",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               entity_id=user_id, entity_name=target_name,
               changes={"sessions_killed": len(sessions)})
    await db.commit()
    return {"message": f"{len(sessions)} sesiones terminadas para {target_name}"}


@router.get("/history/{user_id}")
async def get_session_history(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    sessions = (await db.execute(
        select(SesionActiva)
        .filter(SesionActiva.user_id == user_id)
        .order_by(SesionActiva.created_at.desc())
        .limit(50)
    )).scalars().all()
    return [
        {
            "id": s.id,
            "activa": s.activa,
            "ip_address": s.ip_address,
            "user_agent": s.user_agent,
            "created_at": s.created_at,
            "last_active": s.last_active,
            "fecha_cierre": s.fecha_cierre,
            "motivo_cierre": s.motivo_cierre,
        }
        for s in sessions
    ]


@router.post("/cleanup")
async def cleanup_sessions(
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_admin),
):
    res = await db.execute(delete(SesionActiva).where(SesionActiva.activa == False))
    deleted = res.rowcount
    log_action(db, action="CLEANUP_SESSIONS", entity_type="Sesion",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               changes={"deleted": deleted})
    await db.commit()
    return {"message": f"Se eliminaron {deleted} sesiones inactivas"}


# Backwards-compat aliases
@router.post("/invalidate")
async def invalidate_session(session_id: int, db: AsyncSession = Depends(get_async_db), current_user: Usuario = Depends(require_admin)):
    return kill_session(session_id, db, current_user)


@router.post("/invalidate-user/{user_id}")
async def invalidate_user_sessions(user_id: int, db: AsyncSession = Depends(get_async_db), current_user: Usuario = Depends(require_admin)):
    return kill_user_sessions(user_id, db, current_user)
