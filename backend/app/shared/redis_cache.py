"""
Redis caching layer for expensive endpoint results.
Gracefully degrades if Redis is unavailable — falls back to normal execution.
"""
import json
import hashlib
from typing import Any, Callable, Optional

import redis as _redis
from app.core.config import settings

_client: Optional[_redis.Redis] = None
"""Lazy-init'ed Redis client — None means either not connected or unavailable."""

_cache_enabled: bool = True


def enable_cache(state: bool = True) -> None:
    global _cache_enabled
    _cache_enabled = state


def _get_connection() -> Optional[_redis.Redis]:
    """Return the shared Redis client, creating it on first call.
    Returns None if Redis is unreachable (callers must handle gracefully).
    """
    global _client
    if _client is not None:
        return _client
    if not _cache_enabled:
        return None
    try:
        _client = _redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=0,
            decode_responses=True,
            socket_connect_timeout=1.5,
            socket_timeout=2.0,
            retry_on_timeout=False,
            health_check_interval=30,
        )
        _client.ping()
        print(f"[redis_cache] Connected to {settings.REDIS_HOST}:{settings.REDIS_PORT}", flush=True)
    except Exception as exc:
        print(f"[redis_cache] Redis unavailable ({exc}) — caching disabled", flush=True)
        _client = None
    return _client


def make_cache_key(prefix: str, *args, **kwargs) -> str:
    """Deterministic cache key from prefix + positional + keyword arguments."""
    h = hashlib.md5()
    for a in args:
        h.update(str(a).encode("utf-8"))
    for k, v in sorted(kwargs.items()):
        h.update(str(k).encode("utf-8"))
        h.update(str(v).encode("utf-8"))
    return f"centro_mando:{prefix}:{h.hexdigest()}"


def _serialize(obj: Any) -> str:
    """JSON-serialise *obj*, falling back to ``str()`` for non-serialisable types."""
    return json.dumps(obj, default=str, ensure_ascii=False)


def _deserialize(raw: str) -> Any:
    """JSON-deserialise *raw* back into a Python object."""
    return json.loads(raw)


def get_cached_or_compute(key: str, ttl_seconds: int, compute: Callable[[], Any]) -> Any:
    """Try to fetch *key* from Redis; on miss call *compute*, store and return.
    Returns the Python object (already deserialised).
    """
    client = _get_connection()
    if client:
        try:
            raw = client.get(key)
            if raw is not None:
                return _deserialize(raw)
        except Exception:
            pass  # cache miss → fall through to compute

    result = compute()

    if client:
        try:
            client.setex(key, ttl_seconds, _serialize(result))
        except Exception:
            pass  # non-blocking — best-effort caching

    return result


def check_cache(key: str) -> Any:
    """Return cached value for *key* or ``_MISS`` sentinel if not found.
    Never raises — returns ``_MISS`` on any Redis error.
    """
    client = _get_connection()
    if client:
        try:
            raw = client.get(key)
            if raw is not None:
                return _deserialize(raw)
        except Exception:
            pass
    return _MISS


def set_cache(key: str, ttl_seconds: int, value: Any) -> None:
    """Store *value* under *key* in Redis with *ttl_seconds*. Best-effort."""
    client = _get_connection()
    if client:
        try:
            client.setex(key, ttl_seconds, _serialize(value))
        except Exception:
            pass


# Sentinel object — DO NOT compare with ``is``, use ``type(x) is type(_MISS)``
class _MISS:
    pass


_MISS = _MISS()


def invalidate_key(pattern: str) -> None:
    """Delete all keys matching *pattern* (e.g. ``centro_mando:resumen_dia:*``)."""
    client = _get_connection()
    if client:
        try:
            for k in client.scan_iter(match=pattern, count=100):
                client.delete(k)
        except Exception:
            pass


def invalidate_all() -> None:
    """Delete ALL centro_mando cache keys."""
    invalidate_key("centro_mando:*")
