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
from sqlalchemy import text

from app.db.session import get_db
from app.core.dependencies import require_admin
from app.models.user import Usuario
from app.services.chat_grupos_membresia import (
    get_miembros_grupo, asegurar_grupos_cliente, TIPOS_POR_CLIENTE,
)

router = APIRouter(prefix="/api/admin/chat-grupos", tags=["Admin - Grupos de Chat"])


@router.get("")
def listar_grupos(db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    rows = db.execute(text("""
        SELECT g.id_grupo, g.id_cliente, g.tipo_grupo, g.nombre, g.activa,
               c.cliente AS cliente_nombre,
               (SELECT COUNT(*) FROM CHAT_GRUPO_MIEMBROS_EXTRA x WHERE x.id_grupo = g.id_grupo) AS extra_count
        FROM CHAT_GRUPOS g
        LEFT JOIN CLIENTES c ON c.id_cliente = g.id_cliente AND g.id_cliente <> 0
        ORDER BY g.tipo_grupo = 'encuestador' DESC, c.cliente, g.tipo_grupo
    """)).fetchall()
    return [{
        "id_grupo": r[0], "id_cliente": r[1], "tipo_grupo": r[2], "nombre": r[3],
        "activa": bool(r[4]), "cliente_nombre": r[5] or ("IQVIA / Encuestadores" if r[1] == 0 else None),
        "extra_count": r[6],
    } for r in rows]


@router.get("/clientes")
def listar_clientes_sin_o_con_grupo(q: str = "", db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Para el selector "crear grupos para este cliente" -- todos los
    clientes, marcando cuáles ya tienen sus 2 grupos (operativo/operativo_cliente)."""
    like = f"%{q}%"
    rows = db.execute(text("""
        SELECT c.id_cliente, c.cliente,
               (SELECT COUNT(*) FROM CHAT_GRUPOS g WHERE g.id_cliente = c.id_cliente) AS grupos_existentes
        FROM CLIENTES c
        WHERE (:q = '' OR c.cliente LIKE :like)
        ORDER BY c.cliente
    """), {"q": q, "like": like}).fetchall()
    return [{
        "id_cliente": r[0], "cliente": r[1],
        "grupos_completos": (r[2] or 0) >= len(TIPOS_POR_CLIENTE),
    } for r in rows]


@router.post("/asegurar/{id_cliente}")
def asegurar_grupos(id_cliente: int, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Fuerza la creación temprana de los grupos operativo/operativo_cliente
    de un cliente -- normalmente se crean solos la primera vez que alguien
    con ruta a ese cliente abre el chat; esto es para no esperar a que pase."""
    creados = asegurar_grupos_cliente(db, id_cliente)
    return {"success": True, "creados": creados}


@router.get("/{id_grupo}/miembros")
def miembros_del_grupo(id_grupo: int, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    info = db.execute(text("SELECT id_cliente, tipo_grupo FROM CHAT_GRUPOS WHERE id_grupo = :id"), {"id": id_grupo}).fetchone()
    if not info:
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    return get_miembros_grupo(db, info[0], info[1])


@router.get("/usuarios")
def buscar_usuarios(q: str = Query(""), db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    """Picker de usuarios para agregar como miembro extra -- busca por
    username o por el nombre real si tiene perfil (cliente/analista/
    mercaderista/encuestador), igual que el listado de Usuarios."""
    like = f"%{q}%"
    rows = db.execute(text("""
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
    """), {"q": q, "like": like}).fetchall()
    return [{
        "id_usuario": r[0], "username": r[1], "id_rol": r[2], "rol_nombre": r[3], "nombre_real": r[4],
    } for r in rows]


@router.post("/{id_grupo}/miembros-extra")
def agregar_miembro_extra(id_grupo: int, body: dict, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    id_usuario = body.get("id_usuario")
    if not id_usuario:
        raise HTTPException(status_code=400, detail="Falta id_usuario")
    if not db.execute(text("SELECT 1 FROM CHAT_GRUPOS WHERE id_grupo = :id"), {"id": id_grupo}).fetchone():
        raise HTTPException(status_code=404, detail="Grupo no encontrado")
    if not db.execute(text("SELECT 1 FROM USUARIOS WHERE id_usuario = :id"), {"id": id_usuario}).fetchone():
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    db.execute(text("""
        IF NOT EXISTS (SELECT 1 FROM CHAT_GRUPO_MIEMBROS_EXTRA WHERE id_grupo = :g AND id_usuario = :u)
        INSERT INTO CHAT_GRUPO_MIEMBROS_EXTRA (id_grupo, id_usuario, agregado_en) VALUES (:g, :u, :ahora)
    """), {"g": id_grupo, "u": id_usuario, "ahora": datetime.now()})
    db.commit()
    return {"success": True}


@router.delete("/{id_grupo}/miembros-extra/{id_usuario}")
def quitar_miembro_extra(id_grupo: int, id_usuario: int, db: Session = Depends(get_db), _: Usuario = Depends(require_admin)):
    db.execute(text("""
        DELETE FROM CHAT_GRUPO_MIEMBROS_EXTRA WHERE id_grupo = :g AND id_usuario = :u
    """), {"g": id_grupo, "u": id_usuario})
    db.commit()
    return {"success": True}
