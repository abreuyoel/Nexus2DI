from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, func, select, delete
from typing import List, Optional
from app.db.session import get_db, get_async_db
from app.core.dependencies import require_admin, get_current_user, require_permission, _cache_invalidate_user
from app.core.security import get_password_hash
from app.models.mercaderista import Mercaderista
from app.models.cliente import Cliente
from app.models.encuestador import Encuestador
from app.models.user import Usuario, UserPermission, ROL_MAP
from app.schemas.user import UsuarioCreate, UsuarioUpdate, UsuarioResponse, UpdatePermissionsRequest, PermissionResponse
from app.schemas.cliente import ClienteCreate, ClienteResponse
from app.services.audit_service import log_action
from app.services.realtime import notify_event
from app.services.default_permissions import seed_default_permissions, async_seed_default_permissions
from app.core.request_ip import get_client_ip

router = APIRouter(prefix="/api/users", tags=["Usuarios"])


from app.models.analista import Analista
from app.models.ejecutivo import Ejecutivo

@router.get("")
@router.get("/")
async def list_users(
    skip: int = 0,
    limit: Optional[int] = Query(None),
    search: str = Query(None, alias="q"),
    id_rol: Optional[int] = Query(None),
    rol: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('users', 'read', fallback_roles=('admin',))),
):
    q = select(
        Usuario,
        Cliente.nombre.label('cliente_nombre'),
        Analista.nombre.label('analista_nombre'),
        Mercaderista.nombre.label('mercaderista_nombre'),
        Encuestador.nombre.label('encuestador_nombre'),
        Ejecutivo.nombre.label('ejecutivo_nombre'),
    ).outerjoin(
        Cliente, (Usuario.id_perfil == Cliente.id) & (Usuario.id_rol == 1)
    ).outerjoin(
        Analista, (Usuario.id_perfil == Analista.id) & (Usuario.id_rol == 2)
    ).outerjoin(
        Mercaderista, (Usuario.id_perfil == Mercaderista.id) & (Usuario.id_rol == 5)
    ).outerjoin(
        # 12 = Encuestador, 13 = IQVIA (también puede activar jornadas propias)
        Encuestador, (Usuario.id_perfil == Encuestador.id) & (Usuario.id_rol.in_((12, 13)))
    ).outerjoin(
        Ejecutivo, (Usuario.id_perfil == Ejecutivo.id) & (Usuario.id_rol == 15)
    )

    # El cliente puro (id_rol=1) solo ve otros usuarios de su mismo cliente
    if current_user.rol == "client":
        q = q.filter(
            Usuario.id_rol == 1,
            Usuario.id_perfil == current_user.id_perfil,
        )

    if id_rol:
        q = q.filter(Usuario.id_rol == id_rol)
    elif rol:
        target_rol = rol.strip().lower()
        matching_ids = [k for k, v in ROL_MAP.items() if v.lower() == target_rol]
        if matching_ids:
            q = q.filter(Usuario.id_rol.in_(matching_ids))

    if search:
        term = f"%{search.strip().lower()}%"
        q = q.filter(
            or_(
                func.lower(Usuario.username).like(term),
                func.lower(Usuario.email).like(term),
                func.lower(Usuario.cedula).like(term),
                func.lower(Cliente.nombre).like(term),
                func.lower(Analista.nombre).like(term),
                func.lower(Mercaderista.nombre).like(term),
                func.lower(Encuestador.nombre).like(term),
                func.lower(Ejecutivo.nombre).like(term),
            )
        )

    q = q.order_by(Usuario.id.desc())
    if skip:
        q = q.offset(skip)
    if limit is not None:
        q = q.limit(min(max(1, limit), 5000))

    users = (await db.execute(q)).all()

    result = []
    for u, c_nombre, a_nombre, m_nombre, e_nombre, ej_nombre in users:
        u.perfil_nombre = c_nombre or a_nombre or m_nombre or e_nombre or ej_nombre
        result.append(u)
    return result



@router.post("")
@router.post("/")
async def create_user(
    data: UsuarioCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('users', 'write', fallback_roles=('admin',))),
):
    existing = (await db.execute(select(Usuario).filter(Usuario.username == data.username))).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")

    id_perfil = data.id_perfil
    # Si es rol encuestador (12) y se envió cédula sin id_perfil, buscar o crear perfil en ENCUESTADORES
    if data.id_rol in (12, 13) and not id_perfil and data.cedula:
        try:
            cedula_int = int(str(data.cedula).strip())
            enc = (await db.execute(select(Encuestador).filter(Encuestador.cedula == cedula_int))).scalars().first()
            if not enc:
                enc = Encuestador(cedula=cedula_int, nombre=data.username, activo=data.activo if data.activo is not None else True)
                db.add(enc)
                await db.flush()
            id_perfil = enc.id
        except Exception:
            pass

    user = Usuario(
        username=data.username,
        email=data.email,
        cedula=str(data.cedula) if data.cedula else None,
        id_rol=data.id_rol,
        id_perfil=id_perfil,
        activo=data.activo,
        password=get_password_hash(data.password),
    )
    db.add(user)
    await db.flush()  # get user.id before commit
    await async_seed_default_permissions(db, user)

    log_action(db, action="CREATE_USER", entity_type="Usuario",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=user.id, entity_name=data.username,
               changes={
                   "old": None,
                   "new": {
                       "username": data.username,
                       "email": data.email,
                       "cedula": data.cedula,
                       "id_rol": data.id_rol,
                       "id_perfil": id_perfil,
                       "activo": data.activo
                   }
               })
    await db.commit()
    await db.refresh(user)
    notify_event("user.created", {"id": user.id, "username": user.username})
    return user


@router.delete("/{user_id}")
async def delete_user(
    user_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('users', 'delete', fallback_roles=('admin',))),
):
    user = (await db.execute(select(Usuario).filter(Usuario.id == user_id))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    username = user.username
    old_values = {
        "username": user.username,
        "email": user.email,
        "id_rol": user.id_rol,
        "id_perfil": user.id_perfil,
        "activo": user.activo
    }
    
    # Delete child records referencing user.id to avoid FK constraint violations
    await db.execute(delete(UserPermission).where(UserPermission.user_id == user_id))
    from app.models.sesion import SesionActiva
    await db.execute(delete(SesionActiva).where(SesionActiva.user_id == user_id))

    await db.delete(user)

    log_action(db, action="DELETE_USER", entity_type="Usuario",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=user_id, entity_name=username,
               changes={"old": old_values, "new": None})
    await db.commit()
    notify_event("user.deleted", {"id": user_id})
    return {"message": "Usuario eliminado"}


@router.patch("/{user_id}", response_model=UsuarioResponse)
async def update_user(
    user_id: int,
    data: UsuarioUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('users', 'write', fallback_roles=('admin',))),
):
    user = (await db.execute(select(Usuario).filter(Usuario.id == user_id))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    old_values = {
        "username": user.username,
        "email": user.email,
        "id_rol": user.id_rol,
        "id_perfil": user.id_perfil,
        "activo": user.activo
    }
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(user, key, value)

    new_values = {
        "username": user.username,
        "email": user.email,
        "id_rol": user.id_rol,
        "id_perfil": user.id_perfil,
        "activo": user.activo
    }

    log_action(db, action="UPDATE_USER", entity_type="Usuario",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=user_id, entity_name=user.username,
               changes={"old": old_values, "new": new_values, "modified_fields": list(update_data.keys())})
    await db.commit()
    await db.refresh(user)
    # Invalidar cache si el usuario fue desactivado o cambió rol
    if "activo" in update_data or "id_rol" in update_data:
        _cache_invalidate_user(user_id)
    notify_event("user.updated", {"id": user.id, "activo": user.activo})
    return user


@router.get("/analysts", response_model=List[UsuarioResponse])
async def get_analysts(db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    return (await db.execute(select(Usuario).filter(Usuario.id_rol == 2, Usuario.activo == True))).scalars().all()


@router.get("/supervisors", response_model=List[UsuarioResponse])
async def get_supervisors(db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    return (await db.execute(select(Usuario).filter(Usuario.id_rol == 6, Usuario.activo == True))).scalars().all()


@router.get("/clients-list", response_model=List[ClienteResponse])
async def list_clients(db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('users', 'read', fallback_roles=('admin',)))):
    return (await db.execute(select(Cliente).filter(Cliente.activo == True))).scalars().all()


@router.post("/clients", response_model=ClienteResponse, status_code=201)
async def add_client(
    data: ClienteCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('users', 'write', fallback_roles=('admin',))),
):
    client = Cliente(**data.model_dump())
    db.add(client)
    await db.commit()
    await db.refresh(client)
    notify_event("client.created", {"id": getattr(client, "id_cliente", None)})
    return client


@router.get("/{user_id}/permissions", response_model=List[PermissionResponse])
async def get_user_permissions(
    user_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    return (await db.execute(select(UserPermission).filter(UserPermission.user_id == user_id))).scalars().all()


@router.post("/{user_id}/permissions")
async def update_user_permissions(
    user_id: int,
    data: UpdatePermissionsRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_admin),
):
    target = (await db.execute(select(Usuario).filter(Usuario.id == user_id))).scalars().first()
    
    # 0. Obtener permisos anteriores
    old_perms_list = (await db.execute(select(UserPermission).filter(UserPermission.user_id == user_id))).scalars().all()
    old_permissions = [
        {
            "module": p.module,
            "can_read": p.can_read,
            "can_write": p.can_write,
            "can_delete": p.can_delete,
            "can_see_all": p.can_see_all
        }
        for p in old_perms_list
    ]

    # 1. Obtener los módulos enviados desde el frontend (los que no son 'inherit')
    sent_modules = [p['module'] for p in data.permissions]
    
    # 2. Borrar los permisos existentes que ya no están en la lista (ahora son 'inherit')
    if sent_modules:
        await db.execute(delete(UserPermission).where(
            UserPermission.user_id == user_id,
            UserPermission.module.notin_(sent_modules)
        ))
    else:
        await db.execute(delete(UserPermission).where(UserPermission.user_id == user_id))

    # 3. Actualizar o insertar los enviados
    for p in data.permissions:
        existing = (await db.execute(select(UserPermission).filter(
            UserPermission.user_id == user_id,
            UserPermission.module == p['module']
        ))).scalars().first()
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
               changes={
                   "old": old_permissions,
                   "new": data.permissions,
                   "permissions": data.permissions
               })
    await db.commit()
    # Invalidar cache del usuario: sus permisos han cambiado
    _cache_invalidate_user(user_id)
    return {"message": "Permisos actualizados"}



# =============================================================================
# ENDPOINT SLIM — para selectores y dropdowns (sin JOINs, payload mínimo)
# =============================================================================

_ROL_NOMBRES: dict[int, str] = {
    1: "Cliente", 2: "Analista", 3: "Coordinador Exclusivo",
    4: "Coordinador Tradex", 5: "Mercaderista", 6: "Supervisor",
    7: "Auditor", 8: "Administrador", 9: "Vendedor", 10: "Atención al Cliente",
    11: "Coordinador General", 12: "Encuestador", 13: "Cliente Encuestador",
    14: "Auditor de Campo", 15: "Ejecutivo de Cuenta",
}

@router.get("/slim")
async def list_users_slim(
    limit: int = Query(300, ge=1, le=500),
    search: str = Query(None, alias="q"),
    rol: str = Query(None),
    id_rol: int = Query(None),
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    """Lista ligera de usuarios para selectores y dropdowns.
    Sin JOINs a tablas de perfil — devuelve solo id, username, id_rol, rol_nombre.
    Hasta 10x más rápido que GET /api/users para este caso de uso."""
    effective_limit = min(max(1, limit), 500)

    q = select(
        Usuario.id,
        Usuario.username,
        Usuario.id_rol,
        Usuario.activo,
        Usuario.email,
    ).filter(Usuario.activo == True)

    if id_rol:
        q = q.filter(Usuario.id_rol == id_rol)
    elif rol:
        target = rol.strip().lower()
        matching_ids = [k for k, v in ROL_MAP.items() if v.lower() == target]
        if matching_ids:
            q = q.filter(Usuario.id_rol.in_(matching_ids))

    if search:
        term = f"%{search.strip().lower()}%"
        q = q.filter(
            or_(
                func.lower(Usuario.username).like(term),
                func.lower(Usuario.email).like(term),
            )
        )

    rows = (await db.execute(q.order_by(Usuario.username).limit(effective_limit))).all()
    return [
        {
            "id": r.id,
            "username": r.username,
            "id_rol": r.id_rol,
            "rol_nombre": _ROL_NOMBRES.get(r.id_rol or 0, ROL_MAP.get(r.id_rol or 0, "Usuario")),
            "activo": r.activo,
        }
        for r in rows
    ]


# =============================================================================
# ENDPOINTS DE GESTIÓN DE ENCUESTADORES
# =============================================================================

from pydantic import BaseModel
from typing import Optional

class EncuestadorCreate(BaseModel):
    nombre: str
    cedula: int
    telefono: Optional[str] = None
    email: Optional[str] = None
    activo: bool = True
    username: Optional[str] = None
    password: Optional[str] = None

class EncuestadorUpdate(BaseModel):
    nombre: Optional[str] = None
    cedula: Optional[int] = None
    telefono: Optional[str] = None
    email: Optional[str] = None
    activo: Optional[bool] = None
    username: Optional[str] = None
    password: Optional[str] = None

@router.get("/encuestadores")
async def get_encuestadores_list(db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('users', 'read', fallback_roles=('admin', 'supervisor')))):
    encuestadores = (await db.execute(select(Encuestador).order_by(Encuestador.nombre))).scalars().all()
    users_enc = (await db.execute(select(Usuario).filter(Usuario.id_rol.in_((12, 13)), Usuario.id_perfil.isnot(None)))).scalars().all()
    user_map = {u.id_perfil: u for u in users_enc}

    return [{
        "id": e.id,
        "id_encuestador": e.id,
        "cedula": e.cedula,
        "nombre": e.nombre,
        "telefono": getattr(e, "telefono", None),
        "email": getattr(e, "email", None) or (user_map[e.id].email if e.id in user_map else None),
        "activo": e.activo,
        "creado_en": e.creado_en.isoformat() if e.creado_en else None,
        "id_usuario": user_map[e.id].id if e.id in user_map else None,
        "username": user_map[e.id].username if e.id in user_map else None,
        "usuario_activo": user_map[e.id].activo if e.id in user_map else None
    } for e in encuestadores]

@router.post("/encuestadores", status_code=201)
async def create_encuestador_item(
    data: EncuestadorCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('users', 'write', fallback_roles=('admin', 'supervisor')))
):
    existente = (await db.execute(select(Encuestador).filter(Encuestador.cedula == data.cedula))).scalars().first()
    if existente:
        raise HTTPException(status_code=400, detail=f"Ya existe un encuestador con la cédula {data.cedula}")

    enc = Encuestador(
        nombre=data.nombre.strip(),
        cedula=data.cedula,
        telefono=data.telefono.strip() if data.telefono else None,
        email=data.email.strip() if data.email else None,
        activo=data.activo
    )
    db.add(enc)
    await db.flush()

    if data.username and data.password:
        user_existente = (await db.execute(select(Usuario).filter(Usuario.username == data.username.strip()))).scalars().first()
        if user_existente:
            raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
        nuevo_user = Usuario(
            username=data.username.strip(),
            password=get_password_hash(data.password.strip()),
            email=data.email.strip() if data.email else None,
            cedula=str(data.cedula),
            id_rol=12,
            id_perfil=enc.id,
            activo=data.activo
        )
        db.add(nuevo_user)
        await db.flush()
        await async_seed_default_permissions(db, nuevo_user)

    await db.commit()
    await db.refresh(enc)
    return {
        "id": enc.id,
        "id_encuestador": enc.id,
        "cedula": enc.cedula,
        "nombre": enc.nombre,
        "telefono": enc.telefono,
        "email": enc.email,
        "activo": enc.activo
    }

@router.put("/encuestadores/{id_encuestador}")
async def update_encuestador_item(
    id_encuestador: int,
    data: EncuestadorUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('users', 'write', fallback_roles=('admin', 'supervisor')))
):
    enc = (await db.execute(select(Encuestador).filter(Encuestador.id == id_encuestador))).scalars().first()
    if not enc:
        raise HTTPException(status_code=404, detail="Encuestador no encontrado")

    if data.nombre is not None:
        enc.nombre = data.nombre.strip()
    if data.cedula is not None:
        enc.cedula = data.cedula
    if data.telefono is not None:
        enc.telefono = data.telefono.strip() if data.telefono else None
    if data.email is not None:
        enc.email = data.email.strip() if data.email else None
    if data.activo is not None:
        enc.activo = data.activo

    user = (await db.execute(select(Usuario).filter(Usuario.id_rol.in_((12, 13)), Usuario.id_perfil == enc.id))).scalars().first()
    if user:
        if data.activo is not None:
            user.activo = data.activo
        if data.email is not None:
            user.email = data.email.strip() if data.email else None
        if data.cedula is not None:
            user.cedula = str(data.cedula)
        if data.username and data.username.strip() and data.username.strip() != user.username:
            user_existente = (await db.execute(select(Usuario).filter(Usuario.username == data.username.strip(), Usuario.id != user.id))).scalars().first()
            if user_existente:
                raise HTTPException(status_code=400, detail="El nombre de usuario ya está en uso")
            user.username = data.username.strip()
        if data.password and data.password.strip():
            user.password = get_password_hash(data.password.strip())
    elif data.username and data.username.strip():
        user_existente = (await db.execute(select(Usuario).filter(Usuario.username == data.username.strip()))).scalars().first()
        if user_existente:
            raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
        nuevo_user = Usuario(
            username=data.username.strip(),
            password=get_password_hash(data.password.strip() if data.password else "123456"),
            email=data.email.strip() if data.email else None,
            cedula=str(enc.cedula),
            id_rol=12,
            id_perfil=enc.id,
            activo=enc.activo
        )
        db.add(nuevo_user)
        await db.flush()
        await async_seed_default_permissions(db, nuevo_user)

    await db.commit()
    return {"message": "Encuestador actualizado", "id": enc.id}

@router.delete("/encuestadores/{id_encuestador}")
async def delete_encuestador_item(
    id_encuestador: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_permission('users', 'delete', fallback_roles=('admin', 'supervisor')))
):
    enc = (await db.execute(select(Encuestador).filter(Encuestador.id == id_encuestador))).scalars().first()
    if not enc:
        raise HTTPException(status_code=404, detail="Encuestador no encontrado")

    user = (await db.execute(select(Usuario).filter(Usuario.id_rol.in_((12, 13)), Usuario.id_perfil == enc.id))).scalars().first()
    if user:
        await db.execute(delete(UserPermission).where(UserPermission.user_id == user.id))
        from app.models.sesion import SesionActiva
        await db.execute(delete(SesionActiva).where(SesionActiva.user_id == user.id))
        await db.delete(user)

    await db.delete(enc)
    await db.commit()
    return {"message": "Encuestador eliminado"}
