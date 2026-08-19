"""CRUD de las relaciones de segmentación por cliente:
   - CATEGORIAS_CLIENTES  (qué categorías tiene un cliente)
   - CLIENTES_RUTAS       (qué rutas ve un usuario con rol Cliente)

Nota: CATEGORIAS_CLIENTES también se gestiona, anidado, desde clients.py
(/api/clients/{id}/categorias). Estos endpoints son la versión standalone.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.session import get_db, get_async_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.models.user import Usuario
from app.models.cliente import Cliente, CategoriaCliente, ClienteRuta
from app.models.producto import Categoria
from app.models.ruta import Ruta
from app.schemas.cliente_categoria import CategoriaClienteCreate, CategoriaClienteResponse
from app.schemas.cliente_ruta import ClienteRutaCreate, ClienteRutaUpdate, ClienteRutaResponse

router = APIRouter(prefix="/api", tags=["Segmentación Cliente"])


# ════════════════════════════════════════════════════════════════════════════
# CATEGORIAS_CLIENTES
# ════════════════════════════════════════════════════════════════════════════

@router.get("/categorias-clientes", response_model=List[CategoriaClienteResponse])
async def list_categorias_clientes(
    id_cliente: Optional[int] = Query(None),
    id_categoria: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    stmt = (
        select(CategoriaCliente, Categoria.nombre.label("cat_nom"), Cliente.nombre.label("cli_nom"))
        .join(Categoria, Categoria.id_categoria == CategoriaCliente.id_categoria)
        .join(Cliente, Cliente.id == CategoriaCliente.id_cliente)
    )
    if id_cliente is not None:
        stmt = stmt.filter(CategoriaCliente.id_cliente == id_cliente)
    if id_categoria is not None:
        stmt = stmt.filter(CategoriaCliente.id_categoria == id_categoria)
    rows = (await db.execute(stmt)).all()
    return [
        CategoriaClienteResponse(
            id_categoria=row.CategoriaCliente.id_categoria, id_cliente=row.CategoriaCliente.id_cliente,
            categoria_nombre=row.cat_nom, cliente_nombre=row.cli_nom,
        )
        for row in rows
    ]


@router.post("/categorias-clientes", response_model=CategoriaClienteResponse, status_code=201)
async def create_categoria_cliente(
    data: CategoriaClienteCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    cat = (await db.execute(select(Categoria).filter(Categoria.id_categoria == data.id_categoria))).scalars().first()
    cli = (await db.execute(select(Cliente).filter(Cliente.id == data.id_cliente))).scalars().first()
    if not cat:
        raise HTTPException(404, "Categoría no existe")
    if not cli:
        raise HTTPException(404, "Cliente no existe")
    if (await db.execute(select(CategoriaCliente).filter_by(id_cliente=data.id_cliente, id_categoria=data.id_categoria))).scalars().first():
        raise HTTPException(409, "El cliente ya tiene esa categoría")
    db.add(CategoriaCliente(id_cliente=data.id_cliente, id_categoria=data.id_categoria))
    await db.commit()
    return CategoriaClienteResponse(
        id_categoria=data.id_categoria, id_cliente=data.id_cliente,
        categoria_nombre=cat.nombre, cliente_nombre=cli.nombre,
    )


@router.delete("/categorias-clientes")
async def delete_categoria_cliente(
    id_cliente: int = Query(...),
    id_categoria: int = Query(...),
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    rel = (await db.execute(select(CategoriaCliente).filter_by(id_cliente=id_cliente, id_categoria=id_categoria))).scalars().first()
    if not rel:
        raise HTTPException(404, "Asignación no encontrada")
    await db.delete(rel)
    await db.commit()
    return {"detail": "Categoría desasignada del cliente"}


# ════════════════════════════════════════════════════════════════════════════
# CLIENTES_RUTAS
# ════════════════════════════════════════════════════════════════════════════

def _to_resp(cr: ClienteRuta, ruta_nombre=None, username=None) -> ClienteRutaResponse:
    return ClienteRutaResponse(
        id_cliente_ruta=cr.id, id_usuario=cr.id_usuario, id_ruta=cr.id_ruta,
        activo=cr.activo, fecha_creacion=cr.fecha_creacion,
        ruta_nombre=ruta_nombre, usuario_username=username,
    )


@router.get("/clientes-rutas", response_model=List[ClienteRutaResponse])
async def list_clientes_rutas(
    id_usuario: Optional[int] = Query(None),
    id_ruta: Optional[int] = Query(None),
    activo: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    stmt = (
        select(ClienteRuta, Ruta.nombre.label("ruta_nombre"), Usuario.username.label("username"))
        .outerjoin(Ruta, Ruta.id == ClienteRuta.id_ruta)
        .outerjoin(Usuario, Usuario.id == ClienteRuta.id_usuario)
    )
    if id_usuario is not None:
        stmt = stmt.filter(ClienteRuta.id_usuario == id_usuario)
    if id_ruta is not None:
        stmt = stmt.filter(ClienteRuta.id_ruta == id_ruta)
    if activo is not None:
        stmt = stmt.filter(ClienteRuta.activo == activo)
    rows = (await db.execute(stmt.order_by(ClienteRuta.id))).all()
    return [_to_resp(row.ClienteRuta, row.ruta_nombre, row.username) for row in rows]


@router.get("/clientes-rutas/{id_cliente_ruta}", response_model=ClienteRutaResponse)
async def get_cliente_ruta(
    id_cliente_ruta: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    cr = (await db.execute(select(ClienteRuta).filter(ClienteRuta.id == id_cliente_ruta))).scalars().first()
    if not cr:
        raise HTTPException(404, "No encontrado")
    rn = (await db.execute(select(Ruta.nombre).filter(Ruta.id == cr.id_ruta))).scalar()
    un = (await db.execute(select(Usuario.username).filter(Usuario.id == cr.id_usuario))).scalar()
    return _to_resp(cr, rn, un)


@router.post("/clientes-rutas", response_model=ClienteRutaResponse, status_code=201)
async def create_cliente_ruta(
    data: ClienteRutaCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    usuario = (await db.execute(select(Usuario).filter(Usuario.id == data.id_usuario))).scalars().first()
    ruta = (await db.execute(select(Ruta).filter(Ruta.id == data.id_ruta))).scalars().first()
    if not usuario:
        raise HTTPException(404, "Usuario no existe")
    if not ruta:
        raise HTTPException(404, "Ruta no existe")
    if (await db.execute(select(ClienteRuta).filter_by(id_usuario=data.id_usuario, id_ruta=data.id_ruta))).scalars().first():
        raise HTTPException(409, "Esa ruta ya está asignada al usuario")
    cr = ClienteRuta(id_usuario=data.id_usuario, id_ruta=data.id_ruta, activo=data.activo)
    db.add(cr)
    await db.commit()
    await db.refresh(cr)
    return _to_resp(cr, ruta.nombre, usuario.username)


@router.put("/clientes-rutas/{id_cliente_ruta}", response_model=ClienteRutaResponse)
async def update_cliente_ruta(
    id_cliente_ruta: int,
    data: ClienteRutaUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    cr = (await db.execute(select(ClienteRuta).filter(ClienteRuta.id == id_cliente_ruta))).scalars().first()
    if not cr:
        raise HTTPException(404, "No encontrado")
    if data.id_ruta is not None and data.id_ruta != cr.id_ruta:
        if not (await db.execute(select(Ruta).filter(Ruta.id == data.id_ruta))).scalars().first():
            raise HTTPException(404, "Ruta no existe")
        if (await db.execute(select(ClienteRuta).filter_by(id_usuario=cr.id_usuario, id_ruta=data.id_ruta))).scalars().first():
            raise HTTPException(409, "Esa ruta ya está asignada al usuario")
        cr.id_ruta = data.id_ruta
    if data.activo is not None:
        cr.activo = data.activo
    await db.commit()
    await db.refresh(cr)
    rn = (await db.execute(select(Ruta.nombre).filter(Ruta.id == cr.id_ruta))).scalar()
    un = (await db.execute(select(Usuario.username).filter(Usuario.id == cr.id_usuario))).scalar()
    return _to_resp(cr, rn, un)


@router.delete("/clientes-rutas/{id_cliente_ruta}")
async def delete_cliente_ruta(
    id_cliente_ruta: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    cr = (await db.execute(select(ClienteRuta).filter(ClienteRuta.id == id_cliente_ruta))).scalars().first()
    if not cr:
        raise HTTPException(404, "No encontrado")
    await db.delete(cr)
    await db.commit()
    return {"detail": "Asignación de ruta eliminada"}


# ── Apoyo para la UI: usuarios cliente + rutas disponibles del cliente ──
@router.get("/clientes-rutas-usuarios")
async def list_usuarios_cliente(db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    """Usuarios con rol Cliente (id_rol=1) a los que se les puede asignar rutas.
    id_perfil = id_cliente (relación con CLIENTES)."""
    rows = (await db.execute(text("""
        SELECT u.id_usuario, u.username, u.id_perfil AS id_cliente, c.cliente,
               (SELECT COUNT(DISTINCT rp.id_ruta) FROM RUTA_PROGRAMACION rp
                WHERE rp.id_cliente = u.id_perfil AND rp.activa = 1) AS n_rutas
        FROM USUARIOS u
        LEFT JOIN CLIENTES c ON c.id_cliente = u.id_perfil
        WHERE u.id_rol = 1 AND u.activo = 1
        ORDER BY c.cliente, u.username
    """))).fetchall()
    return [{"id_usuario": r[0], "username": r[1], "id_cliente": r[2],
             "cliente": r[3], "n_rutas": r[4] or 0} for r in rows]


@router.get("/clientes-rutas-disponibles/{id_usuario}")
async def rutas_disponibles_cliente(id_usuario: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    """Rutas donde aparece el cliente del usuario (según RUTA_PROGRAMACION),
    marcando cuáles ya están asignadas en CLIENTES_RUTAS."""
    u = (await db.execute(text("SELECT id_perfil FROM USUARIOS WHERE id_usuario = :u"), {"u": id_usuario})).fetchone()
    if not u or not u[0]:
        raise HTTPException(404, "Usuario cliente no encontrado o sin cliente asociado")
    id_cliente = u[0]
    rows = (await db.execute(text("""
        SELECT rn.id_ruta, rn.ruta,
               COUNT(DISTINCT rp.id_punto_interes) AS pdvs,
               (SELECT TOP 1 cr.id_cliente_ruta FROM CLIENTES_RUTAS cr
                WHERE cr.id_usuario = :u AND cr.id_ruta = rn.id_ruta) AS id_cliente_ruta
        FROM RUTA_PROGRAMACION rp
        JOIN RUTAS_NUEVAS rn ON rn.id_ruta = rp.id_ruta
        WHERE rp.id_cliente = :cid AND rp.activa = 1
        GROUP BY rn.id_ruta, rn.ruta
        ORDER BY rn.ruta
    """), {"u": id_usuario, "cid": id_cliente})).fetchall()
    return {
        "id_cliente": id_cliente,
        "rutas": [{"id_ruta": r[0], "ruta": r[1], "pdvs": r[2] or 0,
                   "asignada": r[3] is not None, "id_cliente_ruta": r[3]} for r in rows],
    }
