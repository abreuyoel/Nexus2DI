"""
CRUD de administración para CHAT_GRUPOS -- ver, forzar la creación de los
grupos de un cliente, y asignar "miembros extra" (gente que no encaja en
ningún bloque dinámico de chat_grupos_membresia.py pero necesita participar
en un grupo puntual, ej. alguien que da soporte a un equipo sin tener ruta
ni rol de cliente ahí).

No reemplaza la membresía dinámica -- la complementa. Ver
app/services/chat_grupos_membresia.py para el diseño completo.
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

from app.db.session import get_db
from app.core.dependencies import require_admin
from app.modules.auth.entities import Usuario, Rol
from app.modules.chat.entities import ChatGrupo, ChatGrupoMiembroExtra
from app.modules.clients.entities import Cliente
from app.modules.analysts.entities import Analista
from app.modules.merchandisers.entities import Mercaderista
from app.modules.surveyors.entities import Encuestador
from app.services.chat_grupos_membresia import (
    get_miembros_grupo, asegurar_grupos_cliente, TIPOS_POR_CLIENTE,
    ROLES_ENCUESTADOR, ID_CLIENTE_ENCUESTADORES,
)

router = APIRouter(prefix="/api/admin/chat-grupos", tags=["Admin - Grupos de Chat"])


@router.get("")
def listar_grupos(db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    extra_count = (
        db.query(func.count(ChatGrupoMiembroExtra.usuario_id))
        .filter(ChatGrupoMiembroExtra.grupo_id == ChatGrupo.id)
        .correlate(ChatGrupo)
        .scalar_subquery()
    )
    rows = (
        db.query(ChatGrupo, Cliente.nombre, extra_count)
        .outerjoin(Cliente, and_(
            Cliente.id == ChatGrupo.cliente_id,
            ChatGrupo.cliente_id != ID_CLIENTE_ENCUESTADORES,
        ))
        .order_by(
            (ChatGrupo.tipo_grupo == "encuestador").desc(),
            Cliente.nombre,
            ChatGrupo.tipo_grupo,
        )
        .all()
    )
    return [{
        "id_grupo": int(g.id),
        "id_cliente": g.cliente_id,
        "tipo_grupo": g.tipo_grupo,
        "nombre": g.nombre,
        "activa": bool(g.activa),
        "cliente_nombre": cliente_nombre or (
            "IQVIA / Encuestadores" if g.cliente_id == ID_CLIENTE_ENCUESTADORES else None
        ),
        "extra_count": extra_count,
    } for g, cliente_nombre, extra_count in rows]


@router.get("/clientes")
def listar_clientes_sin_o_con_grupo(q: str = "", db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Para el selector "crear grupos para este cliente" -- todos los
    clientes, marcando cuáles ya tienen sus 2 grupos (operativo/operativo_cliente)."""
    grupos_count = (
        db.query(func.count(ChatGrupo.id))
        .filter(ChatGrupo.cliente_id == Cliente.id)
        .correlate(Cliente)
        .scalar_subquery()
    )
    query = db.query(Cliente.id, Cliente.nombre, grupos_count).order_by(Cliente.nombre)
    if q:
        query = query.filter(Cliente.nombre.like(f"%{q}%"))
    rows = query.all()
    return [{
        "id_cliente": int(cid),
        "cliente": nombre,
        "grupos_completos": (grupos_existentes or 0) >= len(TIPOS_POR_CLIENTE),
    } for cid, nombre, grupos_existentes in rows]


@router.post("/asegurar/{id_cliente}")
def asegurar_grupos(id_cliente: int, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Fuerza la creación temprana de los grupos operativo/operativo_cliente
    de un cliente -- normalmente se crean solos la primera vez que alguien
    con ruta a ese cliente abre el chat; esto es para no esperar a que pase."""
    creados = asegurar_grupos_cliente(db, id_cliente)
    return {"success": True, "creados": creados}


@router.get("/{id_grupo}/miembros")
def miembros_del_grupo(id_grupo: int, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    grupo = (
        db.query(ChatGrupo.id, ChatGrupo.cliente_id, ChatGrupo.tipo_grupo)
        .filter(ChatGrupo.id == id_grupo)
        .first()
    )
    if not grupo:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return get_miembros_grupo(db, grupo.cliente_id, grupo.tipo_grupo)


@router.get("/usuarios")
def buscar_usuarios(q: str = Query(""), db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Picker de usuarios para agregar como miembro extra -- busca por
    username o por el nombre real si tiene perfil (cliente/analista/
    mercaderista/encuestador), igual que el listado de Usuarios."""
    nombre_real = func.coalesce(
        Cliente.nombre, Analista.nombre, Mercaderista.nombre, Encuestador.nombre,
    )
    query = (
        db.query(Usuario.id, Usuario.username, Usuario.id_rol, Rol.nombre, nombre_real)
        .outerjoin(Rol, Rol.id == Usuario.id_rol)
        .outerjoin(Cliente, and_(Cliente.id == Usuario.id_perfil, Usuario.id_rol == 1))
        .outerjoin(Analista, and_(Analista.id == Usuario.id_perfil, Usuario.id_rol == 2))
        .outerjoin(Mercaderista, and_(Mercaderista.id == Usuario.id_perfil, Usuario.id_rol == 5))
        .outerjoin(Encuestador, and_(Encuestador.id == Usuario.id_perfil, Usuario.id_rol.in_(ROLES_ENCUESTADOR)))
        .filter(Usuario.activo == True)
        .order_by(Usuario.username)
    )
    if q:
        like = f"%{q}%"
        query = query.filter(or_(
            Usuario.username.like(like), Encuestador.nombre.like(like),
            Analista.nombre.like(like), Mercaderista.nombre.like(like),
            Cliente.nombre.like(like),
        ))
    rows = query.all()
    return [{
        "id_usuario": int(r[0]),
        "username": r[1],
        "id_rol": r[2],
        "rol_nombre": r[3],
        "nombre_real": r[4],
    } for r in rows]


@router.post("/{id_grupo}/miembros-extra")
def agregar_miembro_extra(id_grupo: int, body: dict, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    id_usuario = body.get("id_usuario")
    if not id_usuario:
        raise HTTPException(status_code=400, detail="Falta id_usuario")
    if not db.query(ChatGrupo.id).filter(ChatGrupo.id == id_grupo).first():
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not db.query(Usuario.id).filter(Usuario.id == id_usuario).first():
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    existing = db.query(ChatGrupoMiembroExtra).filter(
        ChatGrupoMiembroExtra.grupo_id == id_grupo,
        ChatGrupoMiembroExtra.usuario_id == id_usuario,
    ).first()
    if not existing:
        db.add(ChatGrupoMiembroExtra(
            grupo_id=id_grupo,
            usuario_id=id_usuario,
            agregado_en=datetime.now(),
        ))
        db.commit()
    return {"success": True}


@router.delete("/{id_grupo}/miembros-extra/{id_usuario}")
def quitar_miembro_extra(id_grupo: int, id_usuario: int, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    db.query(ChatGrupoMiembroExtra).filter(
        ChatGrupoMiembroExtra.grupo_id == id_grupo,
        ChatGrupoMiembroExtra.usuario_id == id_usuario,
    ).delete()
    db.commit()
    return {"success": True}
