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
  • 'operativo_cliente'  → lo anterior + usuarios rol cliente
  • 'encuestador'        → equipo de encuestadores (id_rol=12) + IQVIA
                            (id_rol=13). Es UN solo grupo global, no por
                            cliente -- no existe un "cliente" real para
                            encuestas médicas. CHAT_GRUPOS.id_cliente es
                            NOT NULL y está compartida con AppWeb v1/APK
                            (no se puede tocar el esquema), así que este
                            tipo usa ID_CLIENTE_ENCUESTADORES como sentinel
                            reservado en vez de NULL.
"""
from typing import Optional
from sqlalchemy import text
from sqlalchemy.orm import Session

TIPOS_VALIDOS = ("operativo", "operativo_cliente", "encuestador")
# Subconjunto usado para aprovisionar POR CLIENTE (asegurar_grupos_cliente) --
# 'encuestador' es el único grupo global (id_cliente=0), NO se crea uno por
# cada cliente. Si se itera TIPOS_VALIDOS completo ahí, se crea un grupo
# "encuestador" bogus por cada cliente real la primera vez que un
# coordinador/admin (que ven TODOS los clientes) abre el chat.
TIPOS_POR_CLIENTE = ("operativo", "operativo_cliente")
ROLES_COORDINADOR = (3, 4, 8, 11)  # 8 = admin (Usuario.is_admin)
ROLES_ENCUESTADOR = (12, 13)  # 12 = Encuestador, 13 = IQVIA
# 0 nunca es un id_cliente real (IDENTITY arranca en 1) -- reservado para
# el único grupo 'encuestador'.
ID_CLIENTE_ENCUESTADORES = 0
NOMBRE_GRUPO_ENCUESTADORES = "Equipo Encuestadores · IQVIA"


def _miembros_extra(db: Session, id_cliente: int, tipo_grupo: str) -> list[dict]:
    """Miembros agregados a mano desde el CRUD de admin (CHAT_GRUPO_MIEMBROS_EXTRA)
    -- gente que no encaja en ningún bloque dinámico de abajo (ni ruta, ni rol,
    ni cliente) pero igual necesita participar en ESTE grupo puntual."""
    rows = db.execute(text("""
        SELECT u.id_usuario, u.username
        FROM CHAT_GRUPO_MIEMBROS_EXTRA x
        JOIN CHAT_GRUPOS g ON g.id_grupo = x.id_grupo
        JOIN USUARIOS u ON u.id_usuario = x.id_usuario
        WHERE g.id_cliente = :cid AND g.tipo_grupo = :tipo AND u.activo = 1
    """), {"cid": id_cliente, "tipo": tipo_grupo}).fetchall()
    return [{"id_usuario": int(r[0]), "username": r[1], "nombre": None, "origen": "agregado"} for r in rows]


def get_miembros_grupo(db: Session, id_cliente: int, tipo_grupo: str) -> list[dict]:
    """Lista de miembros de un grupo: [{'id_usuario', 'username', 'nombre', 'origen'}]."""
    if tipo_grupo not in TIPOS_VALIDOS:
        raise ValueError(f"tipo_grupo inválido: {tipo_grupo}")

    miembros: dict[int, dict] = {}

    if tipo_grupo == "encuestador":
        # LEFT JOIN a ENCUESTADORES para el nombre real (id_rol=12/13 usan
        # id_perfil -> ENCUESTADORES.id_encuestador) -- IQVIA sin fila propia
        # ahí (username ya es legible, ej. "pparaqueimo") cae a nombre=None.
        rows = db.execute(text("""
            SELECT u.id_usuario, u.username, e.nombre
            FROM USUARIOS u
            LEFT JOIN ENCUESTADORES e ON e.id_encuestador = u.id_perfil AND u.id_rol IN (12, 13)
            WHERE u.id_rol IN (12, 13) AND u.activo = 1
        """)).fetchall()
        for r in rows:
            miembros[int(r[0])] = {"id_usuario": int(r[0]), "username": r[1], "nombre": r[2], "origen": "encuestador"}
        # Los administradores también ven este grupo (ver es_miembro() en
        # get_grupos_de_usuario) -- listarlos también como miembros acá para
        # que "Miembros del Grupo" sea consistente con quién puede entrar.
        admins = db.execute(text("SELECT id_usuario, username FROM USUARIOS WHERE id_rol = 8 AND activo = 1")).fetchall()
        for r in admins:
            if int(r[0]) not in miembros:
                miembros[int(r[0])] = {"id_usuario": int(r[0]), "username": r[1], "nombre": None, "origen": "admin"}
    else:
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

        for sql, params in bloques:
            try:
                rows = db.execute(text(sql), params).fetchall()
            except Exception:
                continue
            for row in rows:
                uid = row[0]
                if uid is None or uid in miembros:
                    continue
                miembros[int(uid)] = {"id_usuario": int(uid), "username": row[1], "nombre": None, "origen": row[2]}

    for m in _miembros_extra(db, id_cliente, tipo_grupo):
        miembros.setdefault(m["id_usuario"], m)

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
    for tipo in TIPOS_POR_CLIENTE:
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


def asegurar_grupo_encuestadores(db: Session) -> Optional[int]:
    """Crea (idempotente) el único grupo 'encuestador' global. Devuelve su id_grupo."""
    row = db.execute(text("""
        SELECT id_grupo FROM CHAT_GRUPOS WHERE id_cliente = :cid AND tipo_grupo = 'encuestador'
    """), {"cid": ID_CLIENTE_ENCUESTADORES}).fetchone()
    if row:
        return int(row[0])
    row = db.execute(text("""
        INSERT INTO CHAT_GRUPOS (id_cliente, tipo_grupo, nombre, activa, fecha_creacion)
        OUTPUT INSERTED.id_grupo
        VALUES (:cid, 'encuestador', :nombre, 1, GETDATE())
    """), {"cid": ID_CLIENTE_ENCUESTADORES, "nombre": NOMBRE_GRUPO_ENCUESTADORES}).fetchone()
    db.commit()
    return int(row[0]) if row else None


def _grupos_extra_de_usuario(db: Session, id_usuario: int) -> list[dict]:
    """Grupos a los que un usuario entra por asignación manual (CRUD de admin),
    no por rol/ruta/cliente -- ej. alguien que necesita participar en un
    grupo puntual sin encajar en ningún bloque dinámico."""
    rows = db.execute(text("""
        SELECT g.id_grupo, g.id_cliente, g.tipo_grupo, g.nombre
        FROM CHAT_GRUPO_MIEMBROS_EXTRA x
        JOIN CHAT_GRUPOS g ON g.id_grupo = x.id_grupo AND g.activa = 1
        WHERE x.id_usuario = :uid
    """), {"uid": id_usuario}).fetchall()
    return [{"id_grupo": int(r[0]), "id_cliente": int(r[1]), "tipo_grupo": r[2], "nombre": r[3]} for r in rows]


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
    extra = _grupos_extra_de_usuario(db, id_usuario)

    # Encuestador (12) / IQVIA (13): completamente aparte del sistema por
    # cliente -- un solo grupo global, sin rutas/clientes de por medio.
    if id_rol in ROLES_ENCUESTADOR:
        id_grupo_enc = asegurar_grupo_encuestadores(db)
        grupos_enc = [{
            "id_grupo": id_grupo_enc, "id_cliente": ID_CLIENTE_ENCUESTADORES,
            "tipo_grupo": "encuestador", "nombre": NOMBRE_GRUPO_ENCUESTADORES,
        }] if id_grupo_enc else []
        vistos = {g["id_grupo"] for g in grupos_enc}
        return grupos_enc + [g for g in extra if g["id_grupo"] not in vistos]

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
        if any((cli, tipo) not in existentes for tipo in TIPOS_POR_CLIENTE)
    ]
    if faltantes:
        for cli in faltantes:
            try:
                asegurar_grupos_cliente(db, cli)
            except Exception:
                pass
        existentes = _existentes()

    # Coordinadores, analistas y mercaderistas pertenecen a AMBOS tipos
    # de grupo (operativo y operativo_cliente) para sus clientes —
    # consistente con get_miembros_grupo() que los lista en ambos.
    # Solo los usuarios rol cliente (id_rol=1) son exclusivos de
    # operativo_cliente y no aparecen en operativo.
    is_coordinador = id_rol in ROLES_COORDINADOR
    es_personal_epran = id_rol in ROLES_COORDINADOR or id_rol in (2, 5)  # admin/coord + analista + mercaderista

    grupos = []
    for (cli, tipo), (id_grupo, nombre) in existentes.items():
        es_miembro = (
            (tipo == "operativo" and cli in clientes_operativo)
            or (tipo == "operativo_cliente" and (
                cli in clientes_solo_cliente
                or (es_personal_epran and cli in clientes_operativo)
            ))
            # El administrador también ve el grupo global de encuestadores
            # (consistente con get_miembros_grupo(), que ya lo lista ahí).
            or (tipo == "encuestador" and id_rol == 8)
        )
        if es_miembro:
            grupos.append({
                "id_grupo": id_grupo, "id_cliente": cli,
                "tipo_grupo": tipo, "nombre": nombre,
            })

    vistos = {g["id_grupo"] for g in grupos}
    grupos += [g for g in extra if g["id_grupo"] not in vistos]
    return grupos
