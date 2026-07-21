from datetime import datetime, timezone, timedelta
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.core.security import decode_token
from app.modules.auth.entities import Usuario, UserPermission, SesionActiva

bearer_scheme = HTTPBearer()

_LAST_ACTIVE_INTERVAL = timedelta(minutes=5)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> Usuario:
    token = credentials.credentials
    payload = decode_token(token)
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")

    session = db.query(SesionActiva).filter(
        SesionActiva.session_token == token,
        SesionActiva.activa == True,
    ).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión expirada o terminada. Inicia sesión nuevamente.",
        )

    # Update last_active at most every 5 min to reduce DB writes
    now = datetime.now(timezone.utc)
    last = session.last_active
    if last is None or (now - (last if last.tzinfo else last.replace(tzinfo=timezone.utc))) > _LAST_ACTIVE_INTERVAL:
        try:
            session.last_active = now
            db.commit()
        except Exception:
            db.rollback()

    user = db.query(Usuario).filter(Usuario.id == int(user_id)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuario no encontrado")
    return user


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


def require_permission(clave: str, action: str = "read", fallback_roles: tuple = ("admin", "analyst")):
    """Dependencia de permiso por módulo (tabla usuario_permisos, module=clave).
    - Admin: siempre.
    - Si el usuario TIENE permisos configurados: manda el permiso (read/write/delete de la clave).
    - Si NO tiene permisos: se cae a los roles indicados (no rompe usuarios sin configurar)."""
    def _checker(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)) -> Usuario:
        if current_user.rol == "admin":
            return current_user
        perms = db.query(UserPermission).filter(UserPermission.user_id == current_user.id).all()
        if perms:
            p = next((x for x in perms if x.module == clave), None)
            ok = bool(p and (p.can_write if action == "write" else p.can_delete if action == "delete" else p.can_read))
            if not ok:
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Sin permiso: {clave} ({action})")
            return current_user
        if current_user.rol in fallback_roles:
            return current_user
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    return _checker
