"""
Servicio de Caché sobre Redis con soporte para fallback seguro y serialización JSON.
Cualquier caída o fallo de Redis es ignorado silenciosamente para consultar directamente SQL Server.
"""
import json
import logging
from typing import Any, Optional
from app.services.redis_pubsub import _get_client

logger = logging.getLogger("app")


async def cache_get(key: str) -> Optional[Any]:
    """Obtiene un objeto serializado de Redis. Retorna None si no existe o si Redis falla."""
    try:
        r = _get_client()
        data = await r.get(key)
        if data:
            return json.loads(data)
    except Exception as e:
        logger.warning(f"[cache] Error leyendo clave '{key}': {e}")
    return None


async def cache_set(key: str, value: Any, ttl_seconds: int = 120) -> None:
    """Guarda un objeto serializable en Redis con un TTL especificable."""
    try:
        r = _get_client()
        await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)
    except Exception as e:
        logger.warning(f"[cache] Error escribiendo clave '{key}': {e}")


async def cache_invalidate_pattern(pattern: str) -> None:
    """Invalida todas las claves en Redis que coincidan con el patrón glob especificado."""
    try:
        r = _get_client()
        keys = await r.keys(pattern)
        if keys:
            await r.delete(*keys)
    except Exception as e:
        logger.warning(f"[cache] Error invalidando patrón '{pattern}': {e}")
