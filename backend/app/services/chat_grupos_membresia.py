"""
Resolución DINÁMICA de la membresía de los grupos de chat por cliente mediante SQLAlchemy ORM.
"""
from typing import Optional, List, Dict, Set
from sqlalchemy.orm import Session
from sqlalchemy import cast, String, func

from app.modules.auth.entities import Usuario
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.routes.entities import RutaProgramacion, AnalistaRuta
from app.modules.clients.entities import Cliente
from app.modules.chat.entities import ChatGrupo

TIPOS_VALIDOS = ("operativo", "operativo_cliente")
ROLES_COORDINADOR = (3, 4, 8, 11)


def get_miembros_grupo(db: Session, id_cliente: int, tipo_grupo: str) -> List[Dict]:
    """Lista de miembros de un grupo usando SQLAlchemy ORM."""
    if tipo_grupo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo_grupo inválido: {tipo_grupo}")

    miembros: Dict[int, Dict] = {}

    # 1. Mercaderistas
    try:
        merc_rows = (
            db.query(Usuario.id, Usuario.username)
            .distinct()
            .join(Mercaderista, cast(Mercaderista.cedula, String) == Usuario.username)
            .join(MercaderistaRuta, MercaderistaRuta.mercaderista_id == Mercaderista.id)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
            .filter(
                RutaProgramacion.id_cliente == id_cliente,
                func.coalesce(RutaProgramacion.activa, True) == True
            )
            .all()
        )
        for uid, username in merc_rows:
            if uid and uid not in miembros:
                miembros[uid] = {"id_usuario": int(uid), "username": username, "origen": "mercaderista"}
    except Exception:
        pass

    # 2. Analistas
    try:
        anal_rows = (
            db.query(Usuario.id, Usuario.username)
            .distinct()
            .join(AnalistaRuta, AnalistaRuta.id_analista == Usuario.id_perfil)
            .join(RutaProgramacion, RutaProgramacion.ruta_id == AnalistaRuta.id_ruta)
            .filter(
                Usuario.id_rol == 2,
                RutaProgramacion.id_cliente == id_cliente,
                func.coalesce(RutaProgramacion.activa, True) == True
            )
            .all()
        )
        for uid, username in anal_rows:
            if uid and uid not in miembros:
                miembros[uid] = {"id_usuario": int(uid), "username": username, "origen": "analista"}
    except Exception:
        pass

    # 3. Coordinadores & Admins
    try:
        coord_rows = (
            db.query(Usuario.id, Usuario.username)
            .filter(Usuario.id_rol.in_(ROLES_COORDINADOR))
            .all()
        )
        for uid, username in coord_rows:
            if uid and uid not in miembros:
                miembros[uid] = {"id_usuario": int(uid), "username": username, "origen": "coordinador"}
    except Exception:
        pass

    # 4. Usuarios Cliente (si tipo es 'operativo_cliente')
    if tipo_grupo == "operativo_cliente":
        try:
            cli_rows = (
                db.query(Usuario.id, Usuario.username)
                .filter(Usuario.id_rol == 1, Usuario.id_perfil == id_cliente)
                .all()
            )
            for uid, username in cli_rows:
                if uid and uid not in miembros:
                    miembros[uid] = {"id_usuario": int(uid), "username": username, "origen": "cliente"}
        except Exception:
            pass

    return list(miembros.values())


def get_miembros_ids(db: Session, id_cliente: int, tipo_grupo: str) -> Set[int]:
    return {m["id_usuario"] for m in get_miembros_grupo(db, id_cliente, tipo_grupo)}


def usuario_es_miembro(db: Session, id_usuario: Optional[int], id_cliente: int, tipo_grupo: str) -> bool:
    if id_usuario is None:
        return False
    return int(id_usuario) in get_miembros_ids(db, id_cliente, tipo_grupo)


def _nombre_grupo(cliente_nombre: Optional[str], tipo_grupo: str) -> str:
    base = cliente_nombre or "Cliente"
    if tipo_grupo == "operativo":
        return f"Equipo operativo · {base}"
    return f"{base} · Equipo + Cliente"


def asegurar_grupos_cliente(db: Session, id_cliente: int, cliente_nombre: Optional[str] = None) -> int:
    if cliente_nombre is None:
        cli = db.query(Cliente.cliente).filter(Cliente.id == id_cliente).first()
        cliente_nombre = cli.cliente if cli and cli.cliente else f"Cliente {id_cliente}"

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
            fecha_creacion=func.now()
        )
        db.add(nuevo_grupo)
        creados += 1

    if creados:
        db.commit()
    return creados


def get_grupos_de_usuario(db: Session, id_usuario: Optional[int]) -> List[Dict]:
    if id_usuario is None:
        return []

    u = db.query(Usuario.id, Usuario.id_perfil, Usuario.id_rol).filter(Usuario.id == id_usuario).first()
    if not u:
        return []

    _, id_perfil, id_rol = u
    id_merc = id_perfil if id_rol == 5 else None
    id_analista = id_perfil if id_rol == 2 else None
    id_cliente_user = id_perfil if id_rol == 1 else None

    clientes_operativo: Set[int] = set()
    clientes_solo_cliente: Set[int] = set()

    if id_merc:
        rows = (
            db.query(RutaProgramacion.id_cliente)
            .distinct()
            .join(MercaderistaRuta, MercaderistaRuta.ruta_id == RutaProgramacion.ruta_id)
            .filter(
                MercaderistaRuta.mercaderista_id == id_merc,
                func.coalesce(RutaProgramacion.activa, True) == True
            )
            .all()
        )
        clientes_operativo |= {int(r[0]) for r in rows if r[0] is not None}

    if id_analista:
        rows = (
            db.query(RutaProgramacion.id_cliente)
            .distinct()
            .join(AnalistaRuta, AnalistaRuta.id_ruta == RutaProgramacion.ruta_id)
            .filter(
                AnalistaRuta.id_analista == id_analista,
                func.coalesce(RutaProgramacion.activa, True) == True
            )
            .all()
        )
        clientes_operativo |= {int(r[0]) for r in rows if r[0] is not None}

    if id_rol in ROLES_COORDINADOR:
        rows = (
            db.query(RutaProgramacion.id_cliente)
            .distinct()
            .filter(func.coalesce(RutaProgramacion.activa, True) == True)
            .all()
        )
        clientes_operativo |= {int(r[0]) for r in rows if r[0] is not None}

    if id_cliente_user:
        clientes_solo_cliente.add(int(id_cliente_user))

    todos_los_clientes = clientes_operativo | clientes_solo_cliente
    if not todos_los_clientes:
        return []

    def _existentes() -> Dict[tuple[int, str], tuple]:
        rows = db.query(ChatGrupo.id, ChatGrupo.cliente_id, ChatGrupo.tipo_grupo, ChatGrupo.nombre)\
                 .filter(ChatGrupo.activa == True).all()
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
