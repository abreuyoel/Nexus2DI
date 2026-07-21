from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.websockets.manager import manager
from app.websockets.guard import ws_guard
from app.shared.realtime import EVENTS_ROOM

router = APIRouter(prefix="/api", tags=["Realtime"])


@router.websocket("/ws/events")
async def ws_events(websocket: WebSocket):
    """Canal de solo lectura: el cliente se conecta y recibe eventos de dominio
    (visitas, fotos, usuarios, etc.) difundidos por `notify_event`."""
    await manager.connect_guarded(websocket, EVENTS_ROOM, require_auth=False)
    try:
        while True:
            await websocket.receive_text()
            if not ws_guard.check_rate_limit(websocket):
                await websocket.send_json({"error": "Rate limit exceeded. Please slow down."})
    except WebSocketDisconnect:
        manager.disconnect(websocket, EVENTS_ROOM)
    except Exception:
        manager.disconnect(websocket, EVENTS_ROOM)
