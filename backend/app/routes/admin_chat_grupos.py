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
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

from app.db.session import get_db, get_async_db
from app.core.dependencies import require_admin
from app.models.user import Usuario
from app.services.chat_grupos_membresia import (
    async_get_miembros_grupo, async_asegurar_grupos_cliente, TIPOS_POR_CLIENTE,
)
from app.services.cache_service import cache_get, cache_set, cache_invalidate_pattern

router = APIRouter(prefix="/api/admin/chat-grupos", tags=["Admin - Grupos de Chat"])


@router.get("")
@router.get("/")
async def listar_grupos(
    q: str = "",
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin)
):
    cache_key = f"nexus2di:cache:admin_chat_grupos:{q.strip()}:{page}:{limit}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    q_str = q.strip()
    like = f"%{q_str}%"
    prefix = f"{q_str}%"

    count_sql = """
        SELECT COUNT(*)
        FROM CHAT_GRUPOS g
        LEFT JOIN CLIENTES c ON c.id_cliente = g.id_cliente AND g.id_cliente <> 0
        WHERE (:q = '' OR g.nombre LIKE :like OR c.cliente LIKE :like OR g.tipo_grupo LIKE :like)
    """
    total = (await db.execute(text(count_sql), {"q": q_str, "like": like})).scalar() or 0

    offset = (page - 1) * limit
    rows_sql = """
        SELECT g.id_grupo, g.id_cliente, g.tipo_grupo, g.nombre, g.activa,
               c.cliente AS cliente_nombre,
               (SELECT COUNT(*) FROM CHAT_GRUPO_MIEMBROS_EXTRA x WHERE x.id_grupo = g.id_grupo) AS extra_count
        FROM CHAT_GRUPOS g
        LEFT JOIN CLIENTES c ON c.id_cliente = g.id_cliente AND g.id_cliente <> 0
        WHERE (:q = '' OR g.nombre LIKE :like OR c.cliente LIKE :like OR g.tipo_grupo LIKE :like)
        ORDER BY
            CASE
                WHEN :q <> '' AND (c.cliente LIKE :prefix OR g.nombre LIKE :prefix) THEN 1
                WHEN :q <> '' AND (c.cliente LIKE :like OR g.nombre LIKE :like) THEN 2
                WHEN g.tipo_grupo = 'encuestador' THEN 3
                ELSE 4
            END,
            c.cliente, g.tipo_grupo
        OFFSET :offset ROWS FETCH NEXT :limit ROWS ONLY
    """
    rows = (await db.execute(text(rows_sql), {"q": q_str, "like": like, "prefix": prefix, "offset": offset, "limit": limit})).fetchall()

    cids = list({r[1] for r in rows if r[1] != 0})
    merc_counts = {}
    anal_counts = {}
    cli_counts = {}

    if cids:
        cids_csv = ",".join(str(int(c)) for c in cids)
        try:
            merc_rows = (await db.execute(text(f"""
                SELECT rp.id_cliente, COUNT(DISTINCT u.id_usuario)
                FROM MERCADERISTAS_RUTAS mr
                JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = mr.id_ruta
                JOIN MERCADERISTAS mm     ON mm.id_mercaderista = mr.id_mercaderista
                JOIN USUARIOS u           ON u.username = CAST(mm.cedula AS NVARCHAR(50))
                WHERE rp.id_cliente IN ({cids_csv}) AND rp.activa = 1 AND u.activo = 1
                GROUP BY rp.id_cliente
            """))).fetchall()
            merc_counts = {r[0]: r[1] for r in merc_rows}
        except Exception:
            pass

        try:
            anal_rows = (await db.execute(text(f"""
                SELECT rp.id_cliente, COUNT(DISTINCT u.id_usuario)
                FROM analistas_rutas ar
                JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = ar.id_ruta
                JOIN USUARIOS u           ON u.id_perfil = ar.id_analista
                WHERE u.id_rol = 2 AND rp.id_cliente IN ({cids_csv}) AND rp.activa = 1 AND u.activo = 1
                GROUP BY rp.id_cliente
            """))).fetchall()
            anal_counts = {r[0]: r[1] for r in anal_rows}
        except Exception:
            pass

        try:
            cli_rows = (await db.execute(text(f"""
                SELECT u.id_perfil, COUNT(DISTINCT u.id_usuario)
                FROM USUARIOS u
                WHERE u.id_rol = 1 AND u.id_perfil IN ({cids_csv}) AND u.activo = 1
                GROUP BY u.id_perfil
            """))).fetchall()
            cli_counts = {r[0]: r[1] for r in cli_rows}
        except Exception:
            pass

    coord_count = (await db.execute(text(
        "SELECT COUNT(*) FROM USUARIOS WHERE id_rol IN (3, 4, 8, 11) AND activo = 1"
    ))).scalar() or 0

    items = []
    for r in rows:
        id_grupo, id_cliente, tipo_grupo, nombre, activa, cliente_nombre, extra_count = r
        if tipo_grupo == 'encuestador':
            m_count = (await db.execute(text(
                "SELECT COUNT(*) FROM USUARIOS WHERE id_rol IN (12, 13, 8) AND activo = 1"
            ))).scalar() or 0
            m_count += extra_count
        else:
            m_cnt = merc_counts.get(id_cliente, 0)
            a_cnt = anal_counts.get(id_cliente, 0)
            c_cnt = cli_counts.get(id_cliente, 0) if tipo_grupo == 'operativo_cliente' else 0
            m_count = m_cnt + a_cnt + c_cnt + coord_count + extra_count

        items.append({
            "id_grupo": id_grupo,
            "id_cliente": id_cliente,
            "tipo_grupo": tipo_grupo,
            "nombre": nombre,
            "activa": bool(activa),
            "cliente_nombre": cliente_nombre or ("IQVIA / Encuestadores" if id_cliente == 0 else None),
            "extra_count": extra_count,
            "miembros_count": m_count,
        })

    res = {
        "total": total,
        "page": page,
        "limit": limit,
        "items": items,
    }
    await cache_set(cache_key, res, ttl_seconds=180)
    return res


@router.get("/clientes")
async def listar_clientes_sin_o_con_grupo(q: str = "", db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_admin)):
    like = f"%{q}%"
    rows = (await db.execute(text("""
        SELECT c.id_cliente, c.cliente,
               (SELECT COUNT(*) FROM CHAT_GRUPOS g WHERE g.id_cliente = c.id_cliente) AS grupos_existentes
        FROM CLIENTES c
        WHERE (:q = '' OR c.cliente LIKE :like)
        ORDER BY c.cliente
    """), {"q": q, "like": like})).fetchall()
    return [{
        "id_cliente": r[0], "cliente": r[1],
        "grupos_completos": (r[2] or 0) >= len(TIPOS_POR_CLIENTE),
    } for r in rows]


@router.post("/asegurar/{id_cliente}")
async def asegurar_grupos(id_cliente: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_admin)):
    creados = await async_asegurar_grupos_cliente(db, id_cliente)
    await cache_invalidate_pattern("nexus2di:cache:*")
    return {"success": True, "creados": creados}


@router.get("/{id_grupo}/miembros")
async def miembros_del_grupo(id_grupo: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_admin)):
    cache_key = f"nexus2di:cache:miembros_grupo:{id_grupo}"
    cached = await cache_get(cache_key)
    if cached:
        return cached

    info = (await db.execute(text("SELECT id_cliente, tipo_grupo FROM CHAT_GRUPOS WHERE id_grupo = :id"), {"id": id_grupo})).fetchone()
    if not info:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    res = await async_get_miembros_grupo(db, info[0], info[1])
    await cache_set(cache_key, res, ttl_seconds=180)
    return res


@router.get("/usuarios")
async def buscar_usuarios(q: str = Query(""), db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_admin)):
    like = f"%{q}%"
    rows = (await db.execute(text("""
        SELECT u.id_usuario, u.username, u.id_rol, r.rol,
               COALESCE(cl.cliente, an.nombre_analista, me.nombre, en.nombre) AS nombre_real
        FROM USUARIOS u
        LEFT JOIN ROLES r ON r.id_rol = u.id_rol
        LEFT JOIN CLIENTES cl ON cl.id_cliente = u.id_perfil AND u.id_rol = 1
        LEFT JOIN ANALISTAS an ON an.id_analista = u.id_perfil AND u.id_rol = 2
        LEFT JOIN MERCADERISTAS me ON me.id_mercaderista = u.id_perfil AND u.id_rol = 5
        LEFT JOIN ENCUESTADORES en ON en.id_encuestador = u.id_perfil AND u.id_rol IN (12, 13)
        WHERE u.activo = 1
          AND (:q = '' OR u.username LIKE :like OR en.nombre LIKE :like OR an.nombre_analista LIKE :like OR me.nombre LIKE :like OR cl.cliente LIKE :like)
        ORDER BY u.username
    """), {"q": q, "like": like})).fetchall()
    return [{
        "id_usuario": r[0], "username": r[1], "id_rol": r[2], "rol_nombre": r[3], "nombre_real": r[4],
    } for r in rows]


@router.post("/{id_grupo}/miembros-extra")
async def agregar_miembro_extra(id_grupo: int, body: dict, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_admin)):
    id_usuario = body.get("id_usuario")
    if not id_usuario:
        raise HTTPException(status_code=400, detail="Falta id_usuario")
    if not (await db.execute(text("SELECT 1 FROM CHAT_GRUPOS WHERE id_grupo = :id"), {"id": id_grupo})).fetchone():
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not (await db.execute(text("SELECT 1 FROM USUARIOS WHERE id_usuario = :id"), {"id": id_usuario})).fetchone():
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    await db.execute(text("""
        IF NOT EXISTS (SELECT 1 FROM CHAT_GRUPO_MIEMBROS_EXTRA WHERE id_grupo = :g AND id_usuario = :u)
        INSERT INTO CHAT_GRUPO_MIEMBROS_EXTRA (id_grupo, id_usuario, agregado_en) VALUES (:g, :u, :ahora)
    """), {"g": id_grupo, "u": id_usuario, "ahora": datetime.now()})
    await db.commit()
    await cache_invalidate_pattern("nexus2di:cache:*")
    return {"success": True}


@router.delete("/{id_grupo}/miembros-extra/{id_usuario}")
async def quitar_miembro_extra(id_grupo: int, id_usuario: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_admin)):
    await db.execute(text("""
        DELETE FROM CHAT_GRUPO_MIEMBROS_EXTRA WHERE id_grupo = :g AND id_usuario = :u
    """), {"g": id_grupo, "u": id_usuario})
    await db.commit()
    await cache_invalidate_pattern("nexus2di:cache:*")
    return {"success": True}
