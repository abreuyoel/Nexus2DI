from sqlalchemy import select, update
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import logging
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timezone
from app.db.session import get_db, get_async_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.dependencies import get_current_user, _cache_invalidate
from app.core.config import settings
from app.models.user import Usuario
from app.models.mercaderista import Mercaderista
from app.models.sesion import SesionActiva
from app.schemas.auth import LoginRequest, LoginMercaderistaRequest, TokenResponse, ResetPasswordRequest, ConfirmResetPasswordRequest
from app.schemas.user import UsuarioCurrentResponse
from app.services.audit_service import log_action
from app.core.limiter import limiter
from app.core.request_ip import get_client_ip

router = APIRouter(prefix="/auth", tags=["Autenticación"])
logger = logging.getLogger("app.auth")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login(data: LoginRequest, request: Request, db: AsyncSession = Depends(get_async_db)):
    ip = get_client_ip(request)
    logger.info(f"Intento de login para usuario: {data.username}")
    try:
        user = (await db.execute(select(Usuario).filter(
            Usuario.username == data.username,
            Usuario.activo == True,
        ))).scalars().first()

        if not user or not verify_password(data.password, user.password):
            logger.warning(f"Credenciales inválidas para: {data.username}")
            log_action(db, action="LOGIN_FAILED", entity_type="Auth",
                       username=data.username, ip_address=ip, status="FAILED",
                       changes={"motivo": "Credenciales inválidas"})
            await db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

        rol = user.rol
        username_display = user.username
        token_data = {"sub": str(user.id), "rol": rol}

        if user.is_mercaderista:
            merc = None
            if user.id_perfil:
                merc = (await db.execute(select(Mercaderista).filter(Mercaderista.id == user.id_perfil))).scalars().first()
            if not merc:
                try:
                    cedula_val = int(user.username)
                    merc = (await db.execute(select(Mercaderista).filter(Mercaderista.cedula == cedula_val))).scalars().first()
                except ValueError:
                    pass
            if merc:
                username_display = merc.nombre
                token_data.update({"cedula": user.username, "tipo": merc.tipo})

        token = create_access_token(token_data)

        sesion = SesionActiva(
            user_id=user.id,
            username=user.username,
            rol=rol,
            session_token=token,
            ip_address=ip,
            user_agent=request.headers.get("User-Agent"),
        )
        db.add(sesion)

        log_action(db, action="LOGIN", entity_type="Auth",
                   user_id=user.id, username=user.username, rol=rol, ip_address=ip)
        await db.commit()

        return TokenResponse(access_token=token, rol=rol, username=username_display, user_id=user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en login: {str(e)}", exc_info=True)
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/login-mercaderista", response_model=TokenResponse)
@limiter.limit("5/minute")
async def login_mercaderista(data: LoginMercaderistaRequest, request: Request, db: AsyncSession = Depends(get_async_db)):
    ip = get_client_ip(request)
    user = (await db.execute(select(Usuario).filter(
        Usuario.username == data.cedula,
        Usuario.id_rol == 5,
        Usuario.activo == True,
    ))).scalars().first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cédula o contraseña incorrecta")

    merc = None
    if user.id_perfil:
        merc = (await db.execute(select(Mercaderista).filter(Mercaderista.id == user.id_perfil))).scalars().first()
    if not merc:
        try:
            cedula_val = int(user.username)
            merc = (await db.execute(select(Mercaderista).filter(Mercaderista.cedula == cedula_val))).scalars().first()
        except ValueError:
            pass

    token = create_access_token({
        "sub": str(user.id),
        "rol": "mercaderista",
        "cedula": data.cedula,
        "tipo": merc.tipo if merc else "Mercaderista",
    })

    sesion = SesionActiva(
        user_id=user.id,
        username=user.username,
        rol="mercaderista",
        session_token=token,
        ip_address=ip,
        user_agent=request.headers.get("User-Agent"),
    )
    db.add(sesion)

    log_action(db, action="LOGIN", entity_type="Auth",
               user_id=user.id, username=user.username, rol="mercaderista", ip_address=ip)
    await db.commit()

    return TokenResponse(
        access_token=token,
        rol="mercaderista",
        username=merc.nombre if merc else user.username,
        user_id=user.id,
    )


@router.post("/logout")
async def logout(request: Request, current_user: Usuario = Depends(get_current_user), db: AsyncSession = Depends(get_async_db)):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    ip = get_client_ip(request)

    # Invalidar el cache de autenticación inmediatamente
    _cache_invalidate(token)

    await db.execute(
        update(SesionActiva)
        .where(
            SesionActiva.session_token == token,
            SesionActiva.activa == True,
        )
        .values(
            activa=False,
            fecha_cierre=datetime.now(timezone.utc),
            motivo_cierre="Logout voluntario",
        )
    )

    log_action(db, action="LOGOUT", entity_type="Auth",
               user_id=current_user.id, username=current_user.username,
               rol=current_user.rol, ip_address=ip)
    await db.commit()
    return {"message": "Sesión cerrada exitosamente"}


@router.get("/me", response_model=UsuarioCurrentResponse)
async def get_me(
    credentials: HTTPAuthorizationCredentials | None = Depends(HTTPBearer(auto_error=False)),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    from app.core.dependencies import _cache_get
    from app.models.user import UserPermission
    from fastapi.security import HTTPBearer as _HTTPBearer

    # Intentar obtener permisos del cache antes de ir a DB
    token = credentials.credentials if credentials else None
    perms = None
    if token:
        _, perms = _cache_get(token)
    if perms is None:
        try:
            perms = (await db.execute(select(UserPermission).filter(
                UserPermission.user_id == current_user.id
            ))).scalars().all()
        except Exception:
            perms = []

    nombre = None
    cedula = None
    if current_user.is_mercaderista or current_user.id_rol == 5:
        try:
            merc = None
            if current_user.id_perfil:
                merc = (await db.execute(select(Mercaderista).filter(Mercaderista.id == current_user.id_perfil))).scalars().first()
            if not merc:
                try:
                    cedula_val = int(current_user.username)
                    merc = (await db.execute(select(Mercaderista).filter(Mercaderista.cedula == cedula_val))).scalars().first()
                except ValueError:
                    pass
            if merc:
                nombre = merc.nombre
                cedula = str(merc.cedula)
        except Exception as e:
            logger.error(f"Error fetching mercaderista for {current_user.username}: {str(e)}")

    return UsuarioCurrentResponse(
        id=current_user.id,
        username=current_user.username,
        rol=current_user.rol,
        rol_nombre=current_user.rol_nombre,
        email=current_user.email,
        id_rol=current_user.id_rol,
        id_perfil=current_user.id_perfil,
        is_admin=current_user.is_admin,
        is_analyst=current_user.is_analyst,
        is_supervisor=current_user.is_supervisor,
        is_client=current_user.is_client,
        is_mercaderista=current_user.is_mercaderista,
        is_coordinador_exclusivo=current_user.is_coordinador_exclusivo,
        is_coordinador_tradex=current_user.is_coordinador_tradex,
        is_ejecutivo_cuenta=current_user.is_ejecutivo_cuenta,
        permisos=perms,
        nombre=nombre,
        cedula=cedula,
    )


@router.post("/change-password")
async def change_password(
    data: ConfirmResetPasswordRequest,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db),
):
    ip = get_client_ip(request)
    current_user.password = get_password_hash(data.new_password)
    log_action(db, action="CHANGE_PASSWORD", entity_type="Auth",
               user_id=current_user.id, username=current_user.username,
               rol=current_user.rol, ip_address=ip,
               entity_id=current_user.id, entity_name=current_user.username)
    await db.commit()
    return {"message": "Contraseña actualizada exitosamente"}
