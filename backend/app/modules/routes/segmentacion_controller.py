from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.clients.entities import Cliente, CategoriaCliente, ClienteRuta
from app.modules.catalogues.entities import Categoria
from app.modules.routes.entities import Ruta, RutaProgramacion
from app.modules.routes.dto import (
    CategoriaClienteCreate, CategoriaClienteResponse,
    ClienteRutaCreate, ClienteRutaUpdate, ClienteRutaResponse,
    UsuarioClienteRutaItem, RutaDisponibleItem, RutasDisponiblesClienteResponse
)

router = APIRouter(prefix="/api", tags=["Segmentación Cliente"])


# ════════════════════════════════════════════════════════════════════════════
# CATEGORIAS_CLIENTES
# ════════════════════════════════════════════════════════════════════════════

@router.get("/categorias-clientes", response_model=List[CategoriaClienteResponse])
def list_categorias_clientes(
    id_cliente: Optional[int] = Query(None),
    id_categoria: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = (
        db.query(CategoriaCliente, Categoria.nombre, Cliente.nombre)
        .join(Categoria, Categoria.id_categoria == CategoriaCliente.id_categoria)
        .join(Cliente, Cliente.id == CategoriaCliente.id_cliente)
    )
    if id_cliente is not None:
        q = q.filter(CategoriaCliente.id_cliente == id_cliente)
    if id_categoria is not None:
        q = q.filter(CategoriaCliente.id_categoria == id_categoria)
    return [
        CategoriaClienteResponse(
            id_categoria=rel.id_categoria, id_cliente=rel.id_cliente,
            categoria_nombre=cat_nom, cliente_nombre=cli_nom,
        )
        for rel, cat_nom, cli_nom in q.all()
    ]


@router.post("/categorias-clientes", response_model=CategoriaClienteResponse, status_code=201)
def create_categoria_cliente(
    data: CategoriaClienteCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    cat = db.query(Categoria).filter(Categoria.id_categoria == data.id_categoria).first()
    cli = db.query(Cliente).filter(Cliente.id == data.id_cliente).first()
    if not cat:
        raise HTTPException(404, "Categoría no existe")
    if not cli:
        raise HTTPException(404, "Cliente no existe")
    if db.query(CategoriaCliente).filter_by(id_cliente=data.id_cliente, id_categoria=data.id_categoria).first():
        raise HTTPException(409, "El cliente ya tiene esa categoría")
    db.add(CategoriaCliente(id_cliente=data.id_cliente, id_categoria=data.id_categoria))
    db.commit()
    return CategoriaClienteResponse(
        id_categoria=data.id_categoria, id_cliente=data.id_cliente,
        categoria_nombre=cat.nombre, cliente_nombre=cli.nombre,
    )


@router.delete("/categorias-clientes")
def delete_categoria_cliente(
    id_cliente: int = Query(...),
    id_categoria: int = Query(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    rel = db.query(CategoriaCliente).filter_by(id_cliente=id_cliente, id_categoria=id_categoria).first()
    if not rel:
        raise HTTPException(404, "Asignación no encontrada")
    db.delete(rel)
    db.commit()
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
def list_clientes_rutas(
    id_usuario: Optional[int] = Query(None),
    id_ruta: Optional[int] = Query(None),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = (
        db.query(ClienteRuta, Ruta.nombre, Usuario.username)
        .outerjoin(Ruta, Ruta.id == ClienteRuta.id_ruta)
        .outerjoin(Usuario, Usuario.id == ClienteRuta.id_usuario)
    )
    if id_usuario is not None:
        q = q.filter(ClienteRuta.id_usuario == id_usuario)
    if id_ruta is not None:
        q = q.filter(ClienteRuta.id_ruta == id_ruta)
    if activo is not None:
        q = q.filter(ClienteRuta.activo == activo)
    return [_to_resp(cr, rn, un) for cr, rn, un in q.order_by(ClienteRuta.id).all()]


@router.get("/clientes-rutas/{id_cliente_ruta}", response_model=ClienteRutaResponse)
def get_cliente_ruta(
    id_cliente_ruta: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    cr = db.query(ClienteRuta).filter(ClienteRuta.id == id_cliente_ruta).first()
    if not cr:
        raise HTTPException(404, "No encontrado")
    rn = db.query(Ruta.nombre).filter(Ruta.id == cr.id_ruta).scalar()
    un = db.query(Usuario.username).filter(Usuario.id == cr.id_usuario).scalar()
    return _to_resp(cr, rn, un)


@router.post("/clientes-rutas", response_model=ClienteRutaResponse, status_code=201)
def create_cliente_ruta(
    data: ClienteRutaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    usuario = db.query(Usuario).filter(Usuario.id == data.id_usuario).first()
    ruta = db.query(Ruta).filter(Ruta.id == data.id_ruta).first()
    if not usuario:
        raise HTTPException(404, "Usuario no existe")
    if not ruta:
        raise HTTPException(404, "Ruta no existe")
    if db.query(ClienteRuta).filter_by(id_usuario=data.id_usuario, id_ruta=data.id_ruta).first():
        raise HTTPException(409, "Esa ruta ya está asignada al usuario")
    cr = ClienteRuta(id_usuario=data.id_usuario, id_ruta=data.id_ruta, activo=data.activo)
    db.add(cr)
    db.commit()
    db.refresh(cr)
    return _to_resp(cr, ruta.nombre, usuario.username)


@router.put("/clientes-rutas/{id_cliente_ruta}", response_model=ClienteRutaResponse)
def update_cliente_ruta(
    id_cliente_ruta: int,
    data: ClienteRutaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    cr = db.query(ClienteRuta).filter(ClienteRuta.id == id_cliente_ruta).first()
    if not cr:
        raise HTTPException(404, "No encontrado")
    if data.id_ruta is not None and data.id_ruta != cr.id_ruta:
        if not db.query(Ruta).filter(Ruta.id == data.id_ruta).first():
            raise HTTPException(404, "Ruta no existe")
        if db.query(ClienteRuta).filter_by(id_usuario=cr.id_usuario, id_ruta=data.id_ruta).first():
            raise HTTPException(409, "Esa ruta ya está asignada al usuario")
        cr.id_ruta = data.id_ruta
    if data.activo is not None:
        cr.activo = data.activo
    db.commit()
    db.refresh(cr)
    rn = db.query(Ruta.nombre).filter(Ruta.id == cr.id_ruta).scalar()
    un = db.query(Usuario.username).filter(Usuario.id == cr.id_usuario).scalar()
    return _to_resp(cr, rn, un)


@router.delete("/clientes-rutas/{id_cliente_ruta}")
def delete_cliente_ruta(
    id_cliente_ruta: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    cr = db.query(ClienteRuta).filter(ClienteRuta.id == id_cliente_ruta).first()
    if not cr:
        raise HTTPException(404, "No encontrado")
    db.delete(cr)
    db.commit()
    return {"detail": "Asignación de ruta eliminada"}


# ── Apoyo para la UI: usuarios cliente + rutas disponibles del cliente ──
@router.get("/clientes-rutas-usuarios", response_model=List[UsuarioClienteRutaItem])
def list_usuarios_cliente(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    sub_count = (
        db.query(
            ClienteRuta.id_usuario.label("id_usuario"),
            func.count(ClienteRuta.id).label("n_rutas")
        )
        .group_by(ClienteRuta.id_usuario)
        .subquery()
    )

    rows = (
        db.query(
            Usuario.id,
            Usuario.username,
            Usuario.id_perfil,
            Cliente.nombre,
            func.coalesce(sub_count.c.n_rutas, 0)
        )
        .outerjoin(Cliente, Cliente.id == Usuario.id_perfil)
        .outerjoin(sub_count, sub_count.c.id_usuario == Usuario.id)
        .filter(Usuario.id_rol == 1, Usuario.activo == True)
        .order_by(Cliente.nombre, Usuario.username)
        .all()
    )

    return [
        UsuarioClienteRutaItem(
            id_usuario=r[0],
            username=r[1],
            id_cliente=r[2],
            cliente=r[3],
            n_rutas=r[4]
        )
        for r in rows
    ]


@router.get("/clientes-rutas-disponibles/{id_usuario}", response_model=RutasDisponiblesClienteResponse)
def rutas_disponibles_cliente(id_usuario: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    user = db.query(Usuario).filter(Usuario.id == id_usuario).first()
    if not user or not user.id_perfil:
        raise HTTPException(404, "Usuario cliente no encontrado o sin cliente asociado")
    id_cliente = user.id_perfil

    sub_cr = (
        db.query(ClienteRuta.id.label("id_cliente_ruta"), ClienteRuta.id_ruta)
        .filter(ClienteRuta.id_usuario == id_usuario)
        .subquery()
    )

    rows = (
        db.query(
            Ruta.id,
            Ruta.nombre,
            func.count(RutaProgramacion.punto_id.distinct()).label("pdvs"),
            sub_cr.c.id_cliente_ruta
        )
        .join(RutaProgramacion, RutaProgramacion.ruta_id == Ruta.id)
        .outerjoin(sub_cr, sub_cr.c.id_ruta == Ruta.id)
        .filter(RutaProgramacion.id_cliente == id_cliente, RutaProgramacion.activo == True)
        .group_by(Ruta.id, Ruta.nombre, sub_cr.c.id_cliente_ruta)
        .order_by(Ruta.nombre)
        .all()
    )

    return RutasDisponiblesClienteResponse(
        id_cliente=id_cliente,
        rutas=[
            RutaDisponibleItem(
                id_ruta=r[0],
                ruta=r[1],
                pdvs=r[2] or 0,
                asignada=r[3] is not None,
                id_cliente_ruta=r[3]
            )
            for r in rows
        ]
    )
