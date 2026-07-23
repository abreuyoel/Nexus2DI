"""
chat_grupos_membresia.py — Reglas de membresía y grupos dinámicos por cliente (SQLAlchemy ORM).

Grupos por cliente:
  - 'operativo'           : Equipo interno (Analista, Mercaderistas, Coordinador).
                            Excluye usuarios con rol Cliente (id_rol=1).
  - 'operativo_cliente'   : Equipo interno + Rol Cliente (id_rol=1).

Auto-provisionamiento:
  Al solicitar los grupos de un cliente, si no existen en CHAT_GRUPOS, se
  crean automáticamente los 2 tipos de grupo para ese cliente.
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import func, String
from sqlalchemy.orm import Session

from app.modules.auth.entities import Usuario
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.routes.entities import RutaProgramacion, AnalistaRuta
from app.modules.clients.entities import Cliente
from app.modules.chat.entities import ChatGrupo

TIPOS_VALIDOS = ("operativo", "operativo_cliente")
ROLES_COORDINADOR = (3, 4, 8, 11)


def get_miembros_grupo(db: Session, id_cliente: int, tipo_grupo: str) -> list[dict]:
    """Retorna la lista de miembros actuales de un grupo de cliente usando consultas ORM.

    Devuelve dicts: [{'id_usuario', 'username', 'origen'}]
    """
    if tipo_grupo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo_grupo inválido: {tipo_grupo}")

    miembros: dict[int, dict] = {}

    # 1. Bloque Mercaderistas asignaciones activas
    try:
        rows_merc = (
            db.query(Usuario.id, Usuario.username)
            .join(Mercaderista, func.cast(Mercaderista.cedula, String) == Usuario.username)
            .join(MercaderistaRuta, MercaderistaRuta.mercaderista_id == Mercaderista.id)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
            .filter(RutaProgramacion.id_cliente == id_cliente, RutaProgramacion.activo == True)
            .distinct()
            .all()
        )
        for uid, uname in rows_merc:
            if uid is not None and uid not in miembros:
                miembros[uid] = {"id_usuario": int(uid), "username": uname, "origen": "mercaderista"}
    except Exception:
        pass

    # 2. Bloque Analistas asignados a rutas activas del cliente
    try:
        rows_analista = (
            db.query(Usuario.id, Usuario.username)
            .join(AnalistaRuta, Usuario.id_perfil == AnalistaRuta.id_analista)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == AnalistaRuta.id_ruta)
            .filter(Usuario.id_rol == 2, RutaProgramacion.id_cliente == id_cliente, RutaProgramacion.activo == True)
            .distinct()
            .all()
        )
        for uid, uname in rows_analista:
            if uid is not None and uid not in miembros:
                miembros[uid] = {"id_usuario": int(uid), "username": uname, "origen": "analista"}
    except Exception:
        pass

    # 3. Bloque Coordinadores y Administradores
    try:
        rows_coord = (
            db.query(Usuario.id, Usuario.username)
            .filter(Usuario.id_rol.in_(ROLES_COORDINADOR))
            .distinct()
            .all()
        )
        for uid, uname in rows_coord:
            if uid is not None and uid not in miembros:
                miembros[uid] = {"id_usuario": int(uid), "username": uname, "origen": "coordinador"}
    except Exception:
        pass

    # 4. Bloque Cliente (solo si el grupo incluye cliente)
    if tipo_grupo == "operativo_cliente":
        try:
            rows_cliente = (
                db.query(Usuario.id, Usuario.username)
                .filter(Usuario.id_rol == 1, Usuario.id_perfil == id_cliente)
                .distinct()
                .all()
            )
            for uid, uname in rows_cliente:
                if uid is not None and uid not in miembros:
                    miembros[uid] = {"id_usuario": int(uid), "username": uname, "origen": "cliente"}
        except Exception:
            pass

    return list(miembros.values())


def get_miembros_ids(db: Session, id_cliente: int, tipo_grupo: str) -> set[int]:
    """Conjunto de id_usuario miembros — para autorización y fan-out rápido."""
    return {m["id_usuario"] for m in get_miembros_grupo(db, id_cliente, tipo_grupo)}


def usuario_es_miembro(db: Session, id_usuario: Optional[int], id_cliente: int, tipo_grupo: str) -> bool:
    """¿El usuario pertenece al grupo?"""
    if id_usuario is None:
        return False
    return int(id_usuario) in get_miembros_ids(db, id_cliente, tipo_grupo)


def _nombre_grupo(cliente_nombre: Optional[str], tipo_grupo: str) -> str:
    base = cliente_nombre or "Cliente"
    if tipo_grupo == "operativo":
        return f"Equipo operativo · {base}"
    return f"{base} · Equipo + Cliente"


def asegurar_grupos_cliente(db: Session, id_cliente: int, cliente_nombre: Optional[str] = None) -> int:
    """Crea los grupos faltantes de un cliente (idempotente) con consultas ORM. Devuelve cuántos creó."""
    if cliente_nombre is None:
        cliente_obj = db.query(Cliente).filter(Cliente.id == id_cliente).first()
        cliente_nombre = cliente_obj.nombre if (cliente_obj and cliente_obj.nombre) else f"Cliente {id_cliente}"

    creados = 0
    for tipo in TIPOS_VALIDOS:
        existing = db.query(ChatGrupo).filter(
            ChatGrupo.cliente_id == id_cliente,
            ChatGrupo.tipo_grupo == tipo
        ).first()
        if existing:
            continue
        nuevo_grupo = ChatGrupo(
            cliente_id=id_cliente,
            tipo_grupo=tipo,
            nombre=_nombre_grupo(cliente_nombre, tipo)[:150],
            activa=True,
            fecha_creacion=datetime.now()
        )
        db.add(nuevo_grupo)
        creados += 1

    if creados:
        db.commit()
    return creados


def get_grupos_de_usuario(db: Session, id_usuario: Optional[int]) -> list[dict]:
    """Grupos (ya provisionados y activos) a los que pertenece un usuario mediante ORM.
    Devuelve: [{'id_grupo', 'id_cliente', 'tipo_grupo', 'nombre'}].
    """
    if id_usuario is None:
        return []

    u = db.query(Usuario.id, Usuario.id_perfil, Usuario.id_rol).filter(Usuario.id == id_usuario).first()
    if not u:
        return []

    id_perfil, id_rol = u.id_perfil, u.id_rol
    id_merc = id_perfil if id_rol == 5 else None
    id_analista = id_perfil if id_rol == 2 else None
    id_cliente_user = id_perfil if id_rol == 1 else None

    clientes_operativo: set[int] = set()
    clientes_solo_cliente: set[int] = set()

    if id_merc:
        rows_merc = (
            db.query(RutaProgramacion.id_cliente)
            .join(MercaderistaRuta, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
            .filter(MercaderistaRuta.mercaderista_id == id_merc, RutaProgramacion.activo == True)
            .distinct()
            .all()
        )
        clientes_operativo |= {int(r[0]) for r in rows_merc if r[0] is not None}

    if id_analista:
        rows_analista = (
            db.query(RutaProgramacion.id_cliente)
            .join(AnalistaRuta, RutaProgramacion.ruta_id == AnalistaRuta.id_ruta)
            .filter(AnalistaRuta.id_analista == id_analista, RutaProgramacion.activo == True)
            .distinct()
            .all()
        )
        clientes_operativo |= {int(r[0]) for r in rows_analista if r[0] is not None}

    if id_rol in ROLES_COORDINADOR:
        rows_coord = (
            db.query(RutaProgramacion.id_cliente)
            .filter(RutaProgramacion.activo == True)
            .distinct()
            .all()
        )
        clientes_operativo |= {int(r[0]) for r in rows_coord if r[0] is not None}

    if id_cliente_user:
        clientes_solo_cliente.add(int(id_cliente_user))

    todos_los_clientes = clientes_operativo | clientes_solo_cliente
    if not todos_los_clientes:
        return []

    def _existentes() -> dict[tuple[int, str], tuple]:
        rows = db.query(ChatGrupo.id, ChatGrupo.cliente_id, ChatGrupo.tipo_grupo, ChatGrupo.nombre).filter(ChatGrupo.activa == True).all()
        return {(int(cli), tipo): (int(id_grupo), nombre) for id_grupo, cli, tipo, nombre in rows}

    existentes = _existentes()

    faltantes = [
        cli for cli in todos_los_clientes
        if any((cli, tipo) not in existentes for tipo in TIPOS_VALIDOS)
    ]
    if faltantes:
        for cli in faltantes:
            try:
                asegurar_grupos_cliente(db, cli)
            except Exception:
                pass
        existentes = _existentes()

    es_personal_epran = id_rol in ROLES_COORDINADOR or id_rol in (2, 5)

    grupos = []
    for (cli, tipo), (id_grupo, nombre) in existentes.items():
        es_miembro = (
            (tipo == "operativo" and cli in clientes_operativo)
            or (tipo == "operativo_cliente" and (
                cli in clientes_solo_cliente
                or (es_personal_epran and cli in clientes_operativo)
            ))
        )
        if es_miembro:
            grupos.append({
                "id_grupo": id_grupo, "id_cliente": cli,
                "tipo_grupo": tipo, "nombre": nombre,
            })
    return grupos
