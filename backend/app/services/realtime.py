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


# ═══════════════════════════════════════════════════════════════════════════════
# Helpers semánticos — wrappers alrededor de notify_event para cada tipo de
# evento de dominio que la APK / frontend esperan por WebSocket.
# ═══════════════════════════════════════════════════════════════════════════════

def notify_ai_alert(id_foto: int, id_visita: int, estado: str, motivo: Optional[str] = None) -> None:
    """AI aprueba o rechaza una foto automáticamente."""
    notify_event("ai_alert", {
        "id_foto": id_foto,
        "id_visita": id_visita,
        "estado": estado,
        "motivo": motivo,
    })


def notify_foto_status(id_foto: int, id_visita: int, estado: str, motivo: Optional[str] = None,
                        tipo_foto: Optional[str] = None) -> None:
    """Analista aprueba/rechaza manualmente una foto."""
    notify_event("foto_status", {
        "id_foto": id_foto,
        "id_visita": id_visita,
        "estado": estado,
        "motivo": motivo,
        "tipo_foto": tipo_foto,
    })


def notify_visita_revisada(id_visita: int) -> None:
    """Analista marca una visita como 'Revisado'."""
    notify_event("visita_revisada", {
        "id_visita": id_visita,
    })


def notify_programacion_updated() -> None:
    """Backend actualizó la programación del día — los clientes deben refrescar."""
    notify_event("programacion_updated", {})


def notify_productos_updated() -> None:
    """Backend actualizó el catálogo de productos — los clientes deben refrescar."""
    notify_event("productos_updated", {})


def notify_grupo_lectura(id_grupo: int, id_usuario: int, username: str) -> None:
    """Alguien leyó los mensajes del chat general de un grupo."""
    notify_event("grupo_lectura", {
        "id_grupo": id_grupo,
        "id_usuario": id_usuario,
        "username": username,
    })


def notify_grupo_visita_lectura(id_grupo: int, id_visita: int, id_usuario: int,
                                  username: str) -> None:
    """Alguien leyó los mensajes del hilo de visita dentro de un grupo."""
    notify_event("grupo_visita_lectura", {
        "id_grupo": id_grupo,
        "id_visita": id_visita,
        "id_usuario": id_usuario,
        "username": username,
    })
