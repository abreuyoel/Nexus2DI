"""Pub/sub sobre Redis para que broadcast_to_room llegue también a sockets
conectados a OTROS procesos/pods, no solo al que originó el evento.

Diseño: un solo canal fijo (sin PSUBSCRIBE ni subscribe dinámico por sala) --
el nombre de sala va en el payload y cada proceso filtra localmente contra su
propio ConnectionManager.active_connections. Redis caído nunca bloquea ni
rompe nada: la entrega local (manager._local_send) ya ocurre antes de llamar
a publish(), y el listener reintenta para siempre con backoff exponencial.
"""
import asyncio
import json
import logging
import uuid
from typing import Optional

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger("app")

# Prefijo "nexus2di:" + REDIS_DB separado de epran_backend (que usa DB 0 para
# socket.io/BullMQ) para no chocar con su tráfico en la misma instancia.
CHANNEL = "nexus2di:ws:broadcast"
PROCESS_ID = uuid.uuid4().hex[:12]

_client: Optional["aioredis.Redis"] = None
_listener_task: Optional[asyncio.Task] = None


def _get_client() -> "aioredis.Redis":
    global _client
    if _client is None:
        _client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            db=settings.REDIS_DB,
            decode_responses=True,
        )
    return _client


async def publish(room: str, message: dict) -> None:
    """Best-effort: nunca bloquea ni lanza. La entrega local ya pasó antes de
    llamar a esto (ver ConnectionManager.broadcast_to_room)."""
    try:
        payload = json.dumps({"origin": PROCESS_ID, "room": room, "message": message})
        await asyncio.wait_for(_get_client().publish(CHANNEL, payload), timeout=1.5)
    except Exception as e:
        logger.warning(f"[redis_pubsub] publish falló (se ignora, ya se entregó local): {e}")


async def _listen_loop(manager) -> None:
    backoff = 1
    while True:
        try:
            pubsub = _get_client().pubsub()
            await pubsub.subscribe(CHANNEL)
            logger.info(f"[redis_pubsub] suscrito a '{CHANNEL}' (process={PROCESS_ID})")
            backoff = 1  # se pudo conectar/suscribir: resetear el backoff
            async for raw in pubsub.listen():
                if raw.get("type") != "message":
                    continue
                try:
                    data = json.loads(raw["data"])
                except (TypeError, ValueError):
                    continue
                if data.get("origin") == PROCESS_ID:
                    continue  # ya se entregó local al publicar, evita eco
                room = data.get("room")
                message = data.get("message")
                if room is None or message is None:
                    continue
                await manager._local_send(room, message)
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning(f"[redis_pubsub] listener caído, reintentando en {backoff}s: {e}")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


def start_listener(manager) -> None:
    global _listener_task
    _listener_task = asyncio.create_task(_listen_loop(manager))


async def stop_listener() -> None:
    global _listener_task, _client
    if _listener_task is not None:
        _listener_task.cancel()
        try:
            await _listener_task
        except asyncio.CancelledError:
            pass
        _listener_task = None
    if _client is not None:
        try:
            await _client.aclose()
        except Exception:
            pass
        _client = None
