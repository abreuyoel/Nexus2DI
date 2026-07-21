"""
Resolución DINÁMICA de la membresía de los grupos de chat por cliente —
puerto 1:1 de AppWeb v1 (Astroweb: app/utils/chat_grupos_membresia.py +
chat_grupos_provision.py) a SQLAlchemy. Mismas tablas que v1 y la APK del
mercaderista (epran_backend), para que los tres clientes vean el mismo
chat.

No se guarda lista de miembros: se calcula desde las tablas operativas. Si
cambian los mercaderistas/analistas/etc. del cliente, los grupos se ajustan
solos.

Fuentes de verdad del vínculo persona ↔ cliente:
  • Mercaderistas → RUTA_PROGRAMACION (activa=1) vía MERCADERISTAS_RUTAS,
                    resolviendo el usuario por USUARIOS.username =
                    MERCADERISTAS.cedula.
  • Analistas     → RUTA_PROGRAMACION (activa=1) vía analistas_rutas (no
                    ANALISTAS_CLIENTE, desactualizada — mismo criterio que
                    el resto de Nexus2DI esta sesión), resolviendo el
                    usuario por USUARIOS.id_perfil (id_rol=2).
  • Coordinadores + administrador → USUARIOS.id_rol IN (3, 4, 8, 11)
                    (8 = admin, igual que Usuario.is_admin en
                    app/models/user.py). A diferencia de
                    mercaderistas/analistas, ven y son miembros de TODOS
                    los clientes con grupo activo, sin filtrar — mismo
                    criterio que v1 para coordinadores, extendido acá a
                    admin porque
                    app/services/visibility.py::coordinator_client_ids()
                    ya le da acceso sin filtro a todo lo demás (ver rol 8
                    ahi) y el chat se habia quedado corto.
  • Usuarios cliente → USUARIOS.id_perfil (id_rol=1) — solo en
                    tipo_grupo='operativo_cliente'.

  (El bloque de supervisores de v1 está deshabilitado porque
  USUARIOS.id_supervisor no existe y no hay una relación confiable para
  resolverlo — se porta tal cual, no es un problema introducido acá.)

Tipos de grupo:
  • 'operativo'          → solo personal epran
  • 'operativo_cliente'  → lo anterior + usuarios rol cliente del cliente
"""
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

TIPOS_VALIDOS = ("operativo", "operativo_cliente")
ROLES_COORDINADOR = (3, 4, 8, 11)  # 8 = admin (Usuario.is_admin)


def get_miembros_grupo(db: Session, id_cliente: int, tipo_grupo: str) -> list[dict]:
    """Lista de miembros de un grupo: [{'id_usuario', 'username', 'origen'}]."""
    if tipo_grupo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo_grupo inválido: {tipo_grupo}")

    bloques: list[tuple[str, dict]] = [
        ("""
            SELECT DISTINCT u.id_usuario, u.username, 'mercaderista' AS origen
            FROM MERCADERISTAS_RUTAS mr
            JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = mr.id_ruta
            JOIN MERCADERISTAS mm     ON mm.id_mercaderista = mr.id_mercaderista
            JOIN USUARIOS u           ON u.username = CAST(mm.cedula AS NVARCHAR(50))
            WHERE rp.id_cliente = :cid AND rp.activa = 1
        """, {"cid": id_cliente}),
        ("""
            SELECT DISTINCT u.id_usuario, u.username, 'analista' AS origen
            FROM analistas_rutas ar
            JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = ar.id_ruta
            JOIN USUARIOS u           ON u.id_perfil = ar.id_analista
            WHERE u.id_rol = 2 AND rp.id_cliente = :cid AND rp.activa = 1
        """, {"cid": id_cliente}),
        ("""
            SELECT DISTINCT u.id_usuario, u.username, 'coordinador' AS origen
            FROM USUARIOS u
            WHERE u.id_rol IN (3, 4, 8, 11)
        """, {}),
    ]

    if tipo_grupo == "operativo_cliente":
        bloques.append(("""
            SELECT DISTINCT u.id_usuario, u.username, 'cliente' AS origen
            FROM USUARIOS u
            WHERE u.id_rol = 1 AND u.id_perfil = :cid
        """, {"cid": id_cliente}))

    miembros: dict[int, dict] = {}
    for sql, params in bloques:
        try:
            rows = db.execute(text(sql), params).fetchall()
        except Exception:
            continue
        for row in rows:
            uid = row[0]
            if uid is None or uid in miembros:
                continue
            miembros[uid] = {"id_usuario": int(uid), "username": row[1], "origen": row[2]}

    return list(miembros.values())


def get_miembros_ids(db: Session, id_cliente: int, tipo_grupo: str) -> set[int]:
    """Conjunto de id_usuario miembros — para autorización y fan-out rápido."""
    return {m["id_usuario"] for m in get_miembros_grupo(db, id_cliente, tipo_grupo)}


def usuario_es_miembro(db: Session, id_usuario: Optional[int], id_cliente: int, tipo_grupo: str) -> bool:
    """¿El usuario pertenece al grupo? Sin bypass por rol genérico — cliente
    y analista deben resolver como miembros reales, no colarse por rol."""
    if id_usuario is None:
        return False
    return int(id_usuario) in get_miembros_ids(db, id_cliente, tipo_grupo)


def _nombre_grupo(cliente_nombre: Optional[str], tipo_grupo: str) -> str:
    base = cliente_nombre or "Cliente"
    if tipo_grupo == "operativo":
        return f"Equipo operativo · {base}"
    return f"{base} · Equipo + Cliente"


def asegurar_grupos_cliente(db: Session, id_cliente: int, cliente_nombre: Optional[str] = None) -> int:
    """Crea los grupos faltantes de un cliente (idempotente). Devuelve
    cuántos creó."""
    if cliente_nombre is None:
        row = db.execute(text("""
            SELECT cliente FROM CLIENTES WHERE id_cliente = :cid
        """), {"cid": id_cliente}).fetchone()
        cliente_nombre = row[0] if row and row[0] else f"Cliente {id_cliente}"

    creados = 0
    for tipo in TIPOS_VALIDOS:
        existing = db.execute(text("""
            SELECT 1 FROM CHAT_GRUPOS WHERE id_cliente = :cid AND tipo_grupo = :tipo
        """), {"cid": id_cliente, "tipo": tipo}).fetchone()
        if existing:
            continue
        db.execute(text("""
            INSERT INTO CHAT_GRUPOS (id_cliente, tipo_grupo, nombre, activa, fecha_creacion)
            VALUES (:cid, :tipo, :nombre, 1, GETDATE())
        """), {"cid": id_cliente, "tipo": tipo, "nombre": _nombre_grupo(cliente_nombre, tipo)[:150]})
        creados += 1

    if creados:
        db.commit()
    return creados


def get_grupos_de_usuario(db: Session, id_usuario: Optional[int]) -> list[dict]:
    """Grupos (ya provisionados y activos) a los que pertenece un usuario.

    Devuelve: [{'id_grupo', 'id_cliente', 'tipo_grupo', 'nombre'}].
    """
    if id_usuario is None:
        return []

    u = db.execute(text("""
        SELECT id_usuario, id_perfil, id_rol FROM USUARIOS WHERE id_usuario = :uid
    """), {"uid": id_usuario}).fetchone()
    if not u:
        return []

    id_perfil, id_rol = u[1], u[2]
    id_merc = id_perfil if id_rol == 5 else None
    id_analista = id_perfil if id_rol == 2 else None
    id_cliente_user = id_perfil if id_rol == 1 else None

    clientes_operativo: set[int] = set()
    clientes_solo_cliente: set[int] = set()

    if id_merc:
        rows = db.execute(text("""
            SELECT DISTINCT rp.id_cliente
            FROM MERCADERISTAS_RUTAS mr
            JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = mr.id_ruta
            WHERE mr.id_mercaderista = :mid AND rp.activa = 1
        """), {"mid": id_merc}).fetchall()
        clientes_operativo |= {int(r[0]) for r in rows if r[0] is not None}

    if id_analista:
        rows = db.execute(text("""
            SELECT DISTINCT rp.id_cliente
            FROM analistas_rutas ar
            JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = ar.id_ruta
            WHERE ar.id_analista = :aid AND rp.activa = 1
        """), {"aid": id_analista}).fetchall()
        clientes_operativo |= {int(r[0]) for r in rows if r[0] is not None}

    # Coordinadores: operativos de TODOS los clientes con ruta activa, sin
    # filtrar por tipo — igual que "todas las activaciones" del Centro de
    # Mando. La auto-provisión de abajo crea el grupo la primera vez que
    # hace falta.
    if id_rol in ROLES_COORDINADOR:
        rows = db.execute(text("""
            SELECT DISTINCT rp.id_cliente FROM RUTA_PROGRAMACION rp WHERE rp.activa = 1
        """)).fetchall()
        clientes_operativo |= {int(r[0]) for r in rows if r[0] is not None}

    if id_cliente_user:
        clientes_solo_cliente.add(int(id_cliente_user))

    todos_los_clientes = clientes_operativo | clientes_solo_cliente
    if not todos_los_clientes:
        return []

    def _existentes() -> dict[tuple[int, str], tuple]:
        rows = db.execute(text("""
            SELECT id_grupo, id_cliente, tipo_grupo, nombre FROM CHAT_GRUPOS WHERE activa = 1
        """)).fetchall()
        return {(int(cli), tipo): (int(id_grupo), nombre) for id_grupo, cli, tipo, nombre in rows}

    existentes = _existentes()

    # Auto-provisión: SOLO para clientes que de verdad les falte alguno de
    # los 2 grupos (la gran mayoría ya los tiene, sobre todo coordinadores/
    # admin que ven TODOS los clientes — llamar asegurar_grupos_cliente() a
    # ciegas por cada uno multiplicaba las queries innecesariamente, ej. 110
    # grupos ⇒ ~220 SELECTs de más en cada carga de "mis grupos").
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

    grupos = []
    for (cli, tipo), (id_grupo, nombre) in existentes.items():
        es_miembro = (
            cli in clientes_operativo
            or (tipo == "operativo_cliente" and cli in clientes_solo_cliente)
        )
        if es_miembro:
            grupos.append({
                "id_grupo": id_grupo, "id_cliente": cli,
                "tipo_grupo": tipo, "nombre": nombre,
            })
    return grupos
