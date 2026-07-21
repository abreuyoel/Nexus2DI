from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario
from app.modules.visits.entities import NotificacionRechazoFoto
from app.modules.visits.dto import NotificacionRechazoResponse
from app.websockets.manager import manager

router = APIRouter(prefix="/api/notifications", tags=["Notificaciones"])


@router.get("/rejection", response_model=List[NotificacionRechazoResponse])
def get_rejection_notifications(
    cedula: str | None = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = db.query(NotificacionRechazoFoto)
    if cedula:
        query = query.filter(NotificacionRechazoFoto.mercaderista_cedula == cedula)
    return query.filter(NotificacionRechazoFoto.leida == False).order_by(
        NotificacionRechazoFoto.fecha_notificacion.desc()
    ).limit(50).all()


@router.post("/mark-read/{notif_id}")
def mark_as_read(
    notif_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    notif = db.query(NotificacionRechazoFoto).filter(NotificacionRechazoFoto.id == notif_id).first()
    if not notif:
        raise HTTPException(status_code=404, detail="Notificación no encontrada")
    notif.leida = True
    db.commit()
    return {"message": "Notificación marcada como leída"}


@router.post("/mark-all-read")
def mark_all_read(
    cedula: str | None = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    query = db.query(NotificacionRechazoFoto).filter(NotificacionRechazoFoto.leida == False)
    if cedula:
        query = query.filter(NotificacionRechazoFoto.mercaderista_cedula == cedula)
    updated = query.update({"leida": True})
    db.commit()
    return {"message": f"{updated} notificaciones marcadas como leídas"}


@router.websocket("/ws/{user_id}")
async def notifications_websocket(websocket: WebSocket, user_id: str):
    await manager.connect(websocket, f"notif_{user_id}")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"notif_{user_id}")
