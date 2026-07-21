from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario
from app.modules.visits.entities import NotificacionRechazoFoto, Foto, Visita
from app.modules.merchandisers.entities import Mercaderista
from app.modules.visits.dto import NotificacionRechazoResponse
from app.websockets.manager import manager
from app.websockets.guard import ws_guard

router = APIRouter(prefix="/api/notifications", tags=["Notificaciones"])


@router.get("/rejection", response_model=List[NotificacionRechazoResponse])
def get_rejection_notifications(
    cedula: Optional[str] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = db.query(NotificacionRechazoFoto)
    if cedula:
        try:
            ced_int = int(cedula.strip())
            query = (
                query.join(Foto, NotificacionRechazoFoto.foto_id == Foto.id)
                .join(Visita, Foto.visita_id == Visita.id)
                .join(Mercaderista, Visita.mercaderista_id == Mercaderista.id)
                .filter(Mercaderista.cedula == ced_int)
            )
        except ValueError:
            pass

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
    cedula: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    query = db.query(NotificacionRechazoFoto).filter(NotificacionRechazoFoto.leida == False)
    if cedula:
        try:
            ced_int = int(cedula.strip())
            sub_foto_ids = (
                db.query(Foto.id)
                .join(Visita, Foto.visita_id == Visita.id)
                .join(Mercaderista, Visita.mercaderista_id == Mercaderista.id)
                .filter(Mercaderista.cedula == ced_int)
                .subquery()
            )
            query = query.filter(NotificacionRechazoFoto.foto_id.in_(sub_foto_ids))
        except ValueError:
            pass

    updated = query.update({"leida": True}, synchronize_session=False)
    db.commit()
    return {"message": f"{updated} notificaciones marcadas como leídas"}


@router.websocket("/ws/{user_id}")
async def notifications_websocket(websocket: WebSocket, user_id: str):
    await manager.connect_guarded(websocket, f"notif_{user_id}", require_auth=False)
    try:
        while True:
            await websocket.receive_text()
            if not ws_guard.check_rate_limit(websocket):
                await websocket.send_json({"error": "Rate limit exceeded. Please slow down."})
    except WebSocketDisconnect:
        manager.disconnect(websocket, f"notif_{user_id}")
    except Exception:
        manager.disconnect(websocket, f"notif_{user_id}")
