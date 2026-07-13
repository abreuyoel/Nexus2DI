"""Difusión de eventos de dominio en tiempo real a los clientes conectados a /api/ws/events.

`notify_event` es seguro de llamar desde endpoints síncronos: encola la difusión en el
event loop del servidor (capturado en el lifespan) sin bloquear la petición.
"""
import asyncio
import logging
from typing import Optional

from app.websockets.manager import manager

logger = logging.getLogger("app")

EVENTS_ROOM = "events"
_loop: Optional[asyncio.AbstractEventLoop] = None


def set_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def notify_event(tipo: str, data: Optional[dict] = None) -> None:
    """Difunde {tipo, data} a todos los clientes del canal de eventos. No lanza si falla."""
    msg = {"tipo": tipo, "data": data or {}}
    try:
        loop = _loop
        if loop is None or not loop.is_running():
            return
        asyncio.run_coroutine_threadsafe(manager.broadcast_to_room(EVENTS_ROOM, msg), loop)
    except Exception as e:  # nunca romper la operación principal por un fallo de WS
        logger.warning(f"notify_event '{tipo}' falló: {e}")
