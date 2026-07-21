from fastapi import APIRouter, Depends, HTTPException, status, Request
import logging
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.db.session import get_db
from app.core.security import verify_password, create_access_token, get_password_hash
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.modules.auth.entities import Usuario, SesionActiva
from app.modules.merchandisers.entities import Mercaderista
from app.modules.auth.dto import LoginRequest, LoginMercaderistaRequest, TokenResponse, ResetPasswordRequest, ConfirmResetPasswordRequest
from app.modules.users.dto import UsuarioCurrentResponse
from app.shared.audit_service import log_action
from app.core.limiter import limiter
from app.core.request_ip import get_client_ip

router = APIRouter(prefix="/auth", tags=["Autenticación"])
logger = logging.getLogger("app.auth")


@router.post("/login", response_model=TokenResponse)
@limiter.limit("5/minute")
def login(data: LoginRequest, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    logger.info(f"Intento de login para usuario: {data.username}")
    try:
        user = db.query(Usuario).filter(
            Usuario.username == data.username,
            Usuario.activo == True,
        ).first()

        if not user or not verify_password(data.password, user.password):
            logger.warning(f"Credenciales inválidas para: {data.username}")
            log_action(db, action="LOGIN_FAILED", entity_type="Auth",
                       username=data.username, ip_address=ip, status="FAILED",
                       changes={"motivo": "Credenciales inválidas"})
            db.commit()
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciales inválidas")

        rol = user.rol
        username_display = user.username
        token_data = {"sub": str(user.id), "rol": rol}

        if user.is_mercaderista and user.id_perfil:
            merc = db.query(Mercaderista).filter(Mercaderista.id == user.id_perfil).first()
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
        db.commit()

        return TokenResponse(access_token=token, rol=rol, username=username_display, user_id=user.id)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error inesperado en login: {str(e)}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error interno: {str(e)}")


@router.post("/login-mercaderista", response_model=TokenResponse)
@limiter.limit("5/minute")
def login_mercaderista(data: LoginMercaderistaRequest, request: Request, db: Session = Depends(get_db)):
    ip = get_client_ip(request)
    user = db.query(Usuario).filter(
        Usuario.username == data.cedula,
        Usuario.id_rol == 5,
        Usuario.activo == True,
    ).first()
    if not user or not verify_password(data.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Cédula o contraseña incorrecta")

    merc = db.query(Mercaderista).filter(Mercaderista.id == user.id_perfil).first() if user.id_perfil else None

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
    db.commit()

    return TokenResponse(
        access_token=token,
        rol="mercaderista",
        username=merc.nombre if merc else user.username,
        user_id=user.id,
    )


@router.post("/logout")
def logout(request: Request, current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    token = request.headers.get("Authorization", "").removeprefix("Bearer ").strip()
    ip = get_client_ip(request)

    db.query(SesionActiva).filter(
        SesionActiva.session_token == token,
        SesionActiva.activa == True,
    ).update({
        "activa": False,
        "fecha_cierre": datetime.now(timezone.utc),
        "motivo_cierre": "Logout voluntario",
    })

    log_action(db, action="LOGOUT", entity_type="Auth",
               user_id=current_user.id, username=current_user.username,
               rol=current_user.rol, ip_address=ip)
    db.commit()
    return {"message": "Sesión cerrada exitosamente"}


@router.get("/me", response_model=UsuarioCurrentResponse)
def get_me(current_user: Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.modules.auth.entities import UserPermission
    try:
        permisos = db.query(UserPermission).filter(UserPermission.user_id == current_user.id).all()
    except Exception:
        permisos = []

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
        permisos=permisos,
    )


@router.post("/change-password")
def change_password(
    data: ConfirmResetPasswordRequest,
    request: Request,
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    ip = get_client_ip(request)
    current_user.password = get_password_hash(data.new_password)
    log_action(db, action="CHANGE_PASSWORD", entity_type="Auth",
               user_id=current_user.id, username=current_user.username,
               rol=current_user.rol, ip_address=ip,
               entity_id=current_user.id, entity_name=current_user.username)
    db.commit()
    return {"message": "Contraseña actualizada exitosamente"}
