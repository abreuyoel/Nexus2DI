from sqlalchemy import select, update as sa_update
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from app.db.session import get_async_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.models.foto import NotificacionRechazoFoto
from app.schemas.foto import NotificacionRechazoResponse
from app.websockets.manager import manager

router = APIRouter(prefix="/api/notifications", tags=["Notificaciones"])


@router.get("/rejection", response_model=List[NotificacionRechazoResponse])
async def get_rejection_notifications(
    cedula: str | None = None,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    stmt = select(NotificacionRechazoFoto).filter(NotificacionRechazoFoto.leida == False)
    if cedula:
        stmt = stmt.filter(NotificacionRechazoFoto.mercaderista_cedula == cedula)
    stmt = stmt.order_by(NotificacionRechazoFoto.fecha_notificacion.desc()).limit(50)
    return (await db.execute(stmt)).scalars().all()


@router.post("/mark-read/{notif_id}")
async def mark_as_read(
    notif_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    notif = (await db.execute(select(NotificacionRechazoFoto).filter(NotificacionRechazoFoto.id == notif_id))).scalars().first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    notif.leida = True
    await db.commit()
    return {"message": "Notificación marcada como leída"}


@router.post("/mark-all-read")
async def mark_all_read(
    cedula: str | None = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(get_current_user),
):
    stmt = sa_update(NotificacionRechazoFoto).where(NotificacionRechazoFoto.leida == False).values(leida=True)
    if cedula:
        stmt = stmt.where(NotificacionRechazoFoto.mercaderista_cedula == cedula)
    result = await db.execute(stmt)
    await db.commit()
    return {"message": f"{result.rowcount} notificaciones marcadas como leídas"}


@router.websocket("/ws/{user_id}")
async def notifications_websocket(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, f"notif_{user_id}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"notif_{user_id}")
