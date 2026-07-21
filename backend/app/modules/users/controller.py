from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.core.dependencies import require_admin, get_current_user, require_permission
from app.core.security import get_password_hash
from app.modules.merchandisers.entities import Mercaderista
from app.modules.clients.entities import Cliente
from app.modules.analysts.entities import Analista
from app.modules.auth.entities import Usuario, UserPermission
from app.modules.users.dto import UsuarioCreate, UsuarioUpdate, UsuarioResponse, UpdatePermissionsRequest, PermissionResponse
from app.shared.audit_service import log_action
from app.shared.realtime import notify_event
from app.modules.users.service import seed_default_permissions
from app.core.request_ip import get_client_ip

router = APIRouter(tags=["Usuarios"])


@router.get("/api/users", response_model=List[UsuarioResponse])
def list_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('users', 'read', fallback_roles=('admin',))),
):
    users = db.query(
        Usuario,
        Cliente.nombre.label('cliente_nombre'),
        Analista.nombre.label('analista_nombre'),
        Mercaderista.nombre.label('mercaderista_nombre')
    ).outerjoin(
        Cliente, (Usuario.id_perfil == Cliente.id) & (Usuario.id_rol == 1)
    ).outerjoin(
        Analista, (Usuario.id_perfil == Analista.id) & (Usuario.id_rol == 2)
    ).outerjoin(
        Mercaderista, (Usuario.id_perfil == Mercaderista.id) & (Usuario.id_rol == 5)
    ).order_by(Usuario.id).offset(skip).limit(limit).all()

    result = []
    for u, c_nombre, a_nombre, m_nombre in users:
        u.perfil_nombre = c_nombre or a_nombre or m_nombre
        result.append(u)
    return result


@router.post("/api/users", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UsuarioCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('users', 'write', fallback_roles=('admin',))),
):
    existing = db.query(Usuario).filter(Usuario.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    user = Usuario(
        username=data.username,
        email=data.email,
        id_rol=data.id_rol,
        id_perfil=data.id_perfil,
        activo=data.activo,
        password=get_password_hash(data.password),
    )
    db.add(user)
    db.flush()  # get user.id before commit
    seed_default_permissions(db, user)

    log_action(db, action="CREATE_USER", entity_type="Usuario",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=user.id, entity_name=data.username,
               changes={"username": data.username, "email": data.email, "id_rol": data.id_rol})
    db.commit()
    db.refresh(user)
    notify_event("user.created", {"id": user.id, "username": user.username})
    return user


@router.delete("/api/users/{user_id}")
def delete_user(
    user_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('users', 'delete', fallback_roles=('admin',))),
):
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    username = user.username
    db.delete(user)

    log_action(db, action="DELETE_USER", entity_type="Usuario",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=user_id, entity_name=username)
    db.commit()
    notify_event("user.deleted", {"id": user_id})
    return {"message": "Usuario eliminado"}


@router.patch("/api/users/{user_id}", response_model=UsuarioResponse)
def update_user(
    user_id: int,
    data: UsuarioUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('users', 'write', fallback_roles=('admin',))),
):
    user = db.query(Usuario).filter(Usuario.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    log_action(db, action="UPDATE_USER", entity_type="Usuario",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=user_id, entity_name=user.username, changes=update_data)
    db.commit()
    db.refresh(user)
    notify_event("user.updated", {"id": user.id, "activo": user.activo})
    return user


@router.get("/api/users/analysts", response_model=List[UsuarioResponse])
def get_analysts(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    return db.query(Usuario).filter(Usuario.id_rol == 2, Usuario.activo == True).all()


@router.get("/api/users/supervisors", response_model=List[UsuarioResponse])
def get_supervisors(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    return db.query(Usuario).filter(Usuario.id_rol == 6, Usuario.activo == True).all()


@router.get("/api/users/{user_id}/permissions", response_model=List[PermissionResponse])
def get_user_permissions(
    user_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    return db.query(UserPermission).filter(UserPermission.user_id == user_id).all()


@router.post("/api/users/{user_id}/permissions")
def update_user_permissions(
    user_id: int,
    data: UpdatePermissionsRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_admin),
):
    target = db.query(Usuario).filter(Usuario.id == user_id).first()
    for p in data.permissions:
        existing = db.query(UserPermission).filter(
            UserPermission.user_id == user_id,
            UserPermission.module == p['module']
        ).first()
        if existing:
            existing.can_read = p.get('can_read', existing.can_read)
            existing.can_write = p.get('can_write', existing.can_write)
            existing.can_delete = p.get('can_delete', existing.can_delete)
            existing.can_see_all = p.get('can_see_all', existing.can_see_all)
        else:
            db.add(UserPermission(
                user_id=user_id,
                module=p['module'],
                can_read=p.get('can_read', True),
                can_write=p.get('can_write', False),
                can_delete=p.get('can_delete', False),
                can_see_all=p.get('can_see_all', False),
            ))

    log_action(db, action="UPDATE_PERMISSIONS", entity_type="Permisos",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=user_id, entity_name=target.username if target else str(user_id),
               changes={"permissions": data.permissions})
    db.commit()
    return {"message": "Permisos actualizados"}


@router.get("/api/modulos")
def list_modulos(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    rows = db.execute(text("""
        SELECT id_modulo, clave, nombre, id_padre, tipo, ruta, icono, orden
        FROM MODULOS WHERE activo = 1 ORDER BY orden, id_modulo
    """)).fetchall()
    return [{"id": r[0], "clave": r[1], "nombre": r[2], "id_padre": r[3],
             "tipo": r[4], "ruta": r[5], "icono": r[6], "orden": r[7]} for r in rows]
