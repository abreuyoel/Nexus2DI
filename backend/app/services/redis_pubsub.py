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

# Dos clientes separados, NO uno compartido -- este era el bug real
# (10/ago/2026, ~7.5h de degradación en producción: /health lento
# intermitente, reinicios periódicos, y una fuga confirmada de +30
# conexiones colgadas -- ver CLIENT LIST en el pod de Redis, todas
# cmd=publish, idle entre 48min y 4h, nunca reutilizadas).
#
# publish() envolvía la llamada en asyncio.wait_for(timeout=1.5) EXTERNO
# al cliente -- redis-py no garantiza devolver la conexión al pool
# limpiamente cuando quien cancela es un wait_for de afuera, no el socket
# mismo. Cada timeout (y con el pool sin `max_connections`, sin límite)
# dejaba una conexión abierta y huérfana. Fix: el timeout ahora vive DENTRO
# del cliente (`socket_timeout`), que sí sabe descartar/reponer una
# conexión que se cuelga, más un `max_connections` como techo duro.
#
# _listen_loop() necesita LO CONTRARIO: pubsub().listen() se queda
# bloqueado esperando mensajes indefinidamente por diseño -- aplicarle el
# mismo socket_timeout corto lo desconectaría cada ~1.5s sin mensajes.
# Por eso son dos clientes, no uno.
_client: Optional["aioredis.Redis"] = None
_listener_client: Optional["aioredis.Redis"] = None
_listener_task: Optional[asyncio.Task] = None


def _get_client() -> "aioredis.Redis":
    """Para publish() -- timeouts cortos, pool acotado."""
    global _client
    if _client is None:
        _client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_timeout=1.5,
            socket_connect_timeout=1.5,
            max_connections=20,
            health_check_interval=30,
        )
    return _client


def _get_listener_client() -> "aioredis.Redis":
    """Para el listener -- SIN socket_timeout de lectura: pubsub.listen()
    tiene que poder bloquear indefinidamente esperando el próximo mensaje,
    eso es correcto, no un cuelgue.

    health_check_interval=15: redis-py envía un PING interno cada 15s sobre
    la conexión idle, lo que evita que el NAT de Docker Desktop (o cualquier
    firewall intermedio) cierre la sesión TCP por inactividad -- de ahí el
    'Connection closed by server' que se veía al correr en local+Docker."""
    global _listener_client
    if _listener_client is None:
        _listener_client = aioredis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            password=settings.REDIS_PASSWORD or None,
            db=settings.REDIS_DB,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_keepalive=True,
            health_check_interval=15,
        )
    return _listener_client


async def publish(room: str, message: dict) -> None:
    """Best-effort: nunca bloquea ni lanza. La entrega local ya pasó antes de
    llamar a esto (ver ConnectionManager.broadcast_to_room). El timeout lo
    aplica el socket del cliente (socket_timeout=1.5 en _get_client()), no
    un asyncio.wait_for() externo -- ver comentario arriba de por qué."""
    try:
        payload = json.dumps({"origin": PROCESS_ID, "room": room, "message": message})
        await _get_client().publish(CHANNEL, payload)
    except Exception as e:
        # {e!r} no {e}: asyncio.TimeoutError (y algunas excepciones de
        # redis-py) tienen str() vacío -- "publish falló: " sin nada
        # detrás no decía CUÁL era el error real. Costó tiempo de
        # diagnóstico en producción el 10/ago/2026.
        logger.warning(f"[redis_pubsub] publish falló (se ignora, ya se entregó local): {e!r}")


async def _listen_loop(manager) -> None:
    global _listener_client
    backoff = 1
    while True:
        try:
            pubsub = _get_listener_client().pubsub()
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
            # Descartar el cliente roto para que el próximo intento cree
            # una conexión TCP nueva. Sin esto, _get_listener_client()
            # devuelve la misma instancia rota (el global ya no es None)
            # y subscribe() falla inmediatamente en cada reintento.
            if _listener_client is not None:
                try:
                    await _listener_client.aclose()
                except Exception:
                    pass
                _listener_client = None
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, 30)


def start_listener(manager) -> None:
    global _listener_task
    _listener_task = asyncio.create_task(_listen_loop(manager))


async def stop_listener() -> None:
    global _listener_task, _client, _listener_client
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
    if _listener_client is not None:
        try:
            await _listener_client.aclose()
        except Exception:
            pass
        _listener_client = None
