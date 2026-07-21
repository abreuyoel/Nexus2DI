from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websockets.manager import manager
from app.shared.realtime import EVENTS_ROOM

router = APIRouter(prefix="/api", tags=["Realtime"])


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    """Canal de solo lectura: el cliente se conecta y recibe eventos de dominio
    (visitas, fotos, usuarios, etc.) difundidos por `notify_event`."""
    await manager.connect(websocket, EVENTS_ROOM)
    try:
        while True:
            # No esperamos mensajes del cliente; receive mantiene viva la conexión.
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket, EVENTS_ROOM)
    except Exception:
        manager.disconnect(websocket, EVENTS_ROOM)
