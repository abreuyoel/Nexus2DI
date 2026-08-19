"""
Dependencias centrales de autenticación y autorización.

Optimización: Cache de autenticación en memoria (TTL 60s).
- Cache HIT  → 0 queries a DB para auth (solo la query del endpoint de negocio)
- Cache MISS → 1 query JOIN (SesionActiva + Usuario) → resultado queda en cache
- last_active → se escribe en background thread, no bloquea el response

Invalidación:
  - logout                    → _cache_invalidate(token)
  - update_user / deactivate  → _cache_invalidate_user(user_id)
  - update_permissions        → _cache_invalidate_user(user_id)
"""
import threading
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import get_db, get_async_db
from app.core.security import decode_token
from app.models.user import Usuario, UserPermission

# auto_error=False: si falta el header Authorization, HTTPBearer NO lanza 403
# automáticamente; lo manejamos abajo devolviendo 401 para que el frontend
# (interceptor de auth) redirija a /login de forma consistente.
bearer_scheme = HTTPBearer(auto_error=False)

_LAST_ACTIVE_INTERVAL = timedelta(minutes=5)

# ─────────────────────────────────────────────────────────────────────────────
# Cache de autenticación en memoria
# Clave: session_token (el Bearer JWT)
# Valor: (usuario: Usuario, perms: list[UserPermission], timestamp: float)
# TTL: 60 segundos — máximo delay en propagación de cambios de permisos/estado
# ─────────────────────────────────────────────────────────────────────────────
_auth_cache: dict[str, tuple] = {}
_auth_cache_lock = threading.Lock()
AUTH_CACHE_TTL = 60  # segundos


def _cache_get(token: str) -> tuple[Optional["Usuario"], Optional[list]]:
    """Devuelve (usuario, perms) si hay un entry válido en cache, o (None, None)."""
    with _auth_cache_lock:
        entry = _auth_cache.get(token)
        if entry and (time.monotonic() - entry[2]) < AUTH_CACHE_TTL:
            return entry[0], entry[1]
    return None, None


def _cache_set(token: str, usuario: "Usuario", perms: list) -> None:
    """Guarda (usuario, perms) en cache con timestamp actual."""
    with _auth_cache_lock:
        _auth_cache[token] = (usuario, perms, time.monotonic())


def _cache_invalidate(token: str) -> None:
    """Elimina una sesión específica del cache. Llamar en logout."""
    with _auth_cache_lock:
        _auth_cache.pop(token, None)


def _cache_invalidate_user(user_id: int) -> None:
    """Elimina todas las sesiones de un usuario del cache.
    Llamar al desactivar usuario o cambiar sus permisos."""
    with _auth_cache_lock:
        to_del = [k for k, (u, _p, _t) in _auth_cache.items() if u.id == user_id]
        for k in to_del:
            del _auth_cache[k]


def _cache_cleanup() -> None:
    """Elimina entries expirados. Se puede llamar periódicamente si hace falta."""
    now = time.monotonic()
    with _auth_cache_lock:
        expired = [k for k, (_u, _p, ts) in _auth_cache.items()
                   if (now - ts) >= AUTH_CACHE_TTL]
        for k in expired:
            del _auth_cache[k]


def get_cache_stats() -> dict:
    """Estadísticas del cache para el endpoint de diagnóstico."""
    with _auth_cache_lock:
        now = time.monotonic()
        active = sum(1 for _, (_u, _p, ts) in _auth_cache.items()
                     if (now - ts) < AUTH_CACHE_TTL)
        return {"total_entries": len(_auth_cache), "active_entries": active}


# ─────────────────────────────────────────────────────────────────────────────
# Dependencia principal — get_current_user
# ─────────────────────────────────────────────────────────────────────────────

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_async_db),
) -> Usuario:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No autenticado: falta el token de acceso",
        )
    token = credentials.credentials

    # ── Cache HIT → retornar sin ir a DB ──────────────────────────────────
    cached_user, _ = _cache_get(token)
    if cached_user is not None:
        return cached_user

    # ── Cache MISS → validar JWT y buscar sesión en DB ────────────────────
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    from app.models.sesion import SesionActiva
    from sqlalchemy.orm import joinedload

    stmt_session = (
        select(SesionActiva)
        .options(joinedload(SesionActiva.usuario))
        .filter(SesionActiva.session_token == token, SesionActiva.activa == True)
    )
    result_session = await db.execute(stmt_session)
    session = result_session.scalars().first()

    if not session or not session.usuario:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada o terminada. Inicia sesión nuevamente.",
        )

    usuario = session.usuario

    # Cargar permisos del usuario junto con la sesión (un solo round-trip adicional
    # en el cache MISS, pero el resultado queda en cache los próximos 60s)
    stmt_perms = select(UserPermission).filter(UserPermission.user_id == usuario.id)
    result_perms = await db.execute(stmt_perms)
    perms = result_perms.scalars().all()

    # expunge: usuario/perms quedan en _auth_cache (memoria del proceso) mucho
    # más allá del ciclo de vida de esta sesión de request -- sin esto,
    # cualquier commit posterior en ESTA MISMA sesión (de cualquier endpoint,
    # no solo este) expira sus atributos (expire_on_commit=True, default de
    # SQLAlchemy), y el próximo request que reutilice el cache y toque un
    # atributo todavía no accedido (ej. current_user.id_rol en
    # require_permission) revienta con DetachedInstanceError. Confirmado en
    # producción 2026-08-19 -- tumbaba /api/cargas-powerbi/summary, pero
    # afecta a cualquier endpoint detrás de require_permission según qué
    # atributo toque primero.
    db.expunge(usuario)
    for p in perms:
        db.expunge(p)

    # Guardar en cache para los siguientes requests
    _cache_set(token, usuario, perms)

    # ── Actualizar last_active en background (no bloquea el response) ─────
    now = datetime.now(timezone.utc)
    last = session.last_active
    needs_update = (
        last is None or
        (now - (last if last.tzinfo else last.replace(tzinfo=timezone.utc))) > _LAST_ACTIVE_INTERVAL
    )
    if needs_update:
        session_id = session.id

        def _update_last_active():
            from app.db.session import SessionLocal
            _db = SessionLocal()
            try:
                from app.models.sesion import SesionActiva as _SesionActiva
                _s = _db.query(_SesionActiva).filter(
                    _SesionActiva.id == session_id
                ).first()
                if _s:
                    _s.last_active = datetime.now(timezone.utc)
                    _db.commit()
            except Exception:
                _db.rollback()
            finally:
                _db.close()

        threading.Thread(target=_update_last_active, daemon=True).start()

    return usuario


# ─────────────────────────────────────────────────────────────────────────────
# require_permission — usa el cache de permisos sin ir a DB
# ─────────────────────────────────────────────────────────────────────────────

def require_permission(clave: str, action: str = "read", fallback_roles: tuple = ("admin", "analyst")):
    """Dependencia de permiso por módulo (tabla usuario_permisos, module=clave).
    - Admin (id_rol=8): acceso total sin restricciones.
    - Permisos cargados desde cache (0 queries extra en cache HIT).
    - Si no tiene la fila: usa los fallback_roles."""
    async def _checker(
        credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
        current_user: Usuario = Depends(get_current_user),
        db: AsyncSession = Depends(get_async_db),
    ) -> Usuario:
        if current_user.id_rol == 8 or current_user.is_admin or current_user.rol in ("admin", "superadmin"):
            return current_user

        # Obtener permisos desde cache (si hay HIT no va a DB)
        token = credentials.credentials if credentials else None
        perms = None
        if token:
            _, perms = _cache_get(token)

        # Fallback: cargar permisos desde DB si no están en cache
        if perms is None:
            stmt_perms = select(UserPermission).filter(UserPermission.user_id == current_user.id)
            result_perms = await db.execute(stmt_perms)
            perms = result_perms.scalars().all()

        if perms:
            p = next((x for x in perms if x.module == clave), None)
            if p:
                ok = bool(
                    p.can_write if action == "write"
                    else p.can_delete if action == "delete"
                    else p.can_read
                )
                if not ok:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Sin permiso: {clave} ({action})"
                    )
                return current_user
            if current_user.rol in fallback_roles or current_user.id_rol in (2, 7):
                return current_user
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Sin permiso: {clave} ({action})"
            )

        if current_user.rol in fallback_roles or current_user.id_rol in (2, 7):
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    return _checker


# ─────────────────────────────────────────────────────────────────────────────
# Helpers de roles (sin cambios de interfaz)
# ─────────────────────────────────────────────────────────────────────────────

def require_roles(*roles: str):
    def _checker(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        if current_user.rol not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Roles permitidos: {', '.join(roles)}",
            )
        return current_user
    return _checker


def require_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.rol != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Se requiere rol admin")
    return current_user


def require_analyst_or_admin(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    if current_user.rol not in ("admin", "analyst"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return current_user
