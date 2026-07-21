from datetime import date, timedelta, datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario
from app.modules.visits.entities import Balance, Visita
from app.modules.routes.entities import PuntoInteres, RutaProgramacion, Ruta, AnalistaRuta
from app.modules.analysts.entities import AnalistaCliente
from app.modules.clients.dto import ClientDataFiltersResponse, PdvItem, BalanceItemResponse

router = APIRouter(prefix="/api/client-data", tags=["Client Data"])


@router.get("/filters", response_model=ClientDataFiltersResponse)
def get_client_data_filters(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from app.shared.visibility import coordinator_client_ids
    visible_ids = coordinator_client_ids(db, current_user) if current_user.is_client else None

    if visible_ids is not None and not visible_ids:
        return ClientDataFiltersResponse(
            productos=[], mercaderistas=[], pdvs=[], cadenas=[], regiones=[],
            categorias=[], departamentos=[], cuadrantes=[], estados=[]
        )

    base_filter = []
    if visible_ids is not None:
        base_filter.append(Balance.id_cliente.in_(visible_ids))

    if current_user.is_analyst and current_user.id_perfil:
        analista_id = int(current_user.id_perfil)
        sub_rp = (
            db.query(RutaProgramacion.punto_id)
            .join(AnalistaRuta, RutaProgramacion.ruta_id == AnalistaRuta.id_ruta)
            .filter(RutaProgramacion.activo == True, AnalistaRuta.id_analista == analista_id)
            .subquery()
        )
        base_filter.append(Balance.identificador_pdv.in_(sub_rp))

    if current_user.rol == "client":
        from app.shared.visibility import client_route_ids
        route_ids = client_route_ids(db, current_user)
        if route_ids is not None:
            sub_cr = (
                db.query(RutaProgramacion.punto_id)
                .filter(RutaProgramacion.activo == True, RutaProgramacion.ruta_id.in_(route_ids))
                .subquery()
            )
            base_filter.append(Balance.identificador_pdv.in_(sub_cr))

    # Productos
    productos = [
        r[0] for r in db.query(Balance.producto)
        .distinct()
        .filter(*base_filter, Balance.producto.isnot(None))
        .all() if r[0]
    ]

    # Mercaderistas
    mercaderistas = [
        r[0] for r in db.query(Balance.mercaderista)
        .distinct()
        .filter(*base_filter, Balance.mercaderista.isnot(None))
        .all() if r[0]
    ]

    # Categorias
    categorias = [
        r[0] for r in db.query(Balance.categoria)
        .distinct()
        .filter(*base_filter, Balance.categoria.isnot(None))
        .all() if r[0]
    ]

    # PDVs
    pdvs_rows = (
        db.query(PuntoInteres.id, PuntoInteres.nombre)
        .distinct()
        .join(Balance, Balance.identificador_pdv == PuntoInteres.id)
        .filter(*base_filter)
        .all()
    )
    pdvs = [PdvItem(id=r[0], nombre=r[1] or "") for r in pdvs_rows]

    # Cadenas
    cadenas = [
        r[0] for r in db.query(PuntoInteres.cadena)
        .distinct()
        .join(Balance, Balance.identificador_pdv == PuntoInteres.id)
        .filter(*base_filter, PuntoInteres.cadena.isnot(None))
        .all() if r[0]
    ]

    # Regiones
    regiones = [
        r[0] for r in db.query(PuntoInteres.departamento)
        .distinct()
        .join(Balance, Balance.identificador_pdv == PuntoInteres.id)
        .filter(*base_filter, PuntoInteres.departamento.isnot(None))
        .all() if r[0]
    ]

    # Departamentos
    departamentos = [
        r[0] for r in db.query(PuntoInteres.departamento)
        .distinct()
        .join(Balance, Balance.identificador_pdv == PuntoInteres.id)
        .filter(*base_filter, PuntoInteres.departamento.isnot(None))
        .all() if r[0]
    ]

    # Cuadrantes
    sub_cuad = (
        db.query(
            RutaProgramacion.punto_id.label("id_punto_interes"),
            func.min(Ruta.cuadrante).label("cuadrante")
        )
        .join(Ruta, RutaProgramacion.ruta_id == Ruta.id)
        .filter(RutaProgramacion.activo == True, Ruta.cuadrante.isnot(None))
        .group_by(RutaProgramacion.punto_id)
        .subquery()
    )

    cuadrantes_rows = (
        db.query(sub_cuad.c.cuadrante)
        .distinct()
        .join(PuntoInteres, sub_cuad.c.id_punto_interes == PuntoInteres.id)
        .join(Balance, Balance.identificador_pdv == PuntoInteres.id)
        .filter(*base_filter, sub_cuad.c.cuadrante.isnot(None))
        .all()
    )
    cuadrantes = [r[0] for r in cuadrantes_rows if r[0]]

    # Estados
    estados_rows = (
        db.query(Visita.estado)
        .distinct()
        .join(Balance, Balance.visita_id == Visita.id)
        .filter(*base_filter, Visita.estado.isnot(None))
        .all()
    )
    estados = [r[0] for r in estados_rows if r[0]]

    return ClientDataFiltersResponse(
        productos=sorted(set(productos)),
        mercaderistas=sorted(set(mercaderistas)),
        pdvs=pdvs,
        cadenas=sorted(set(cadenas)),
        regiones=sorted(set(regiones)),
        categorias=sorted(set(categorias)),
        departamentos=sorted(set(departamentos)),
        cuadrantes=sorted(set(cuadrantes)),
        estados=sorted(set(estados))
    )


@router.get("/balances", response_model=List[BalanceItemResponse])
def get_client_balances(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    producto: Optional[str] = None,
    cadena: Optional[str] = None,
    region: Optional[str] = None,
    pdv: Optional[str] = None,
    mercaderista: Optional[str] = None,
    visita_id: Optional[int] = None,
    categoria: Optional[str] = None,
    departamento: Optional[str] = None,
    cuadrante: Optional[str] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from app.shared.visibility import coordinator_client_ids
    visible_ids = coordinator_client_ids(db, current_user) if current_user.is_client else None

    if not fecha_inicio and not fecha_fin:
        fecha_fin = date.today()
        fecha_inicio = fecha_fin - timedelta(days=30)

    sub_cuad = (
        db.query(
            RutaProgramacion.punto_id.label("id_punto_interes"),
            func.min(Ruta.cuadrante).label("cuadrante")
        )
        .join(Ruta, RutaProgramacion.ruta_id == Ruta.id)
        .filter(RutaProgramacion.activo == True, Ruta.cuadrante.isnot(None))
        .group_by(RutaProgramacion.punto_id)
        .subquery()
    )

    query = (
        db.query(
            Balance.id,
            Balance.fecha_balance,
            Balance.visita_id,
            PuntoInteres.departamento.label("region"),
            PuntoInteres.cadena.label("cadena"),
            PuntoInteres.nombre.label("pdv_nombre"),
            PuntoInteres.departamento.label("departamento"),
            sub_cuad.c.cuadrante.label("cuadrante"),
            Visita.estado.label("estado"),
            Balance.mercaderista,
            Balance.producto,
            Balance.categoria,
            Balance.inv_inicial,
            Balance.inv_final,
            Balance.inv_deposito,
            Balance.caras,
            Balance.precio_bs,
            Balance.precio_ds
        )
        .outerjoin(PuntoInteres, Balance.identificador_pdv == PuntoInteres.id)
        .outerjoin(sub_cuad, sub_cuad.c.id_punto_interes == PuntoInteres.id)
        .outerjoin(Visita, Balance.visita_id == Visita.id)
    )

    if visible_ids is not None:
        if not visible_ids:
            return []
        query = query.filter(Balance.id_cliente.in_(visible_ids))

    if current_user.is_analyst and current_user.id_perfil:
        analista_id = int(current_user.id_perfil)
        sub_rp = (
            db.query(RutaProgramacion.punto_id)
            .join(AnalistaRuta, RutaProgramacion.ruta_id == AnalistaRuta.id_ruta)
            .filter(RutaProgramacion.activo == True, AnalistaRuta.id_analista == analista_id)
            .subquery()
        )
        query = query.filter(Balance.identificador_pdv.in_(sub_rp))

    if current_user.rol == "client":
        from app.shared.visibility import client_route_ids
        route_ids = client_route_ids(db, current_user)
        if route_ids is not None:
            sub_cr = (
                db.query(RutaProgramacion.punto_id)
                .filter(RutaProgramacion.activo == True, RutaProgramacion.ruta_id.in_(route_ids))
                .subquery()
            )
            query = query.filter(Balance.identificador_pdv.in_(sub_cr))

    if fecha_inicio:
        query = query.filter(Balance.fecha_balance >= datetime.combine(fecha_inicio, datetime.min.time()))
    if fecha_fin:
        next_day = fecha_fin + timedelta(days=1)
        query = query.filter(Balance.fecha_balance < datetime.combine(next_day, datetime.min.time()))
    if producto:
        query = query.filter(Balance.producto == producto)
    if cadena:
        query = query.filter(PuntoInteres.cadena == cadena)
    if region:
        query = query.filter(PuntoInteres.departamento == region)
    if pdv:
        query = query.filter(Balance.identificador_pdv == pdv)
    if mercaderista:
        query = query.filter(Balance.mercaderista == mercaderista)
    if visita_id:
        query = query.filter(Balance.visita_id == visita_id)
    if categoria:
        query = query.filter(Balance.categoria == categoria)
    if departamento:
        query = query.filter(PuntoInteres.departamento == departamento)
    if cuadrante:
        query = query.filter(sub_cuad.c.cuadrante == cuadrante)

    if estado:
        query = query.filter(Visita.estado == estado)
    elif current_user.is_client:
        query = query.filter(Visita.estado == 'Revisado')

    rows = query.order_by(Balance.fecha_balance.desc()).all()

    return [
        BalanceItemResponse(
            id_balance=r[0],
            fecha_balance=str(r[1]) if r[1] else None,
            visita_id=r[2],
            region=r[3],
            cadena=r[4],
            pdv_nombre=r[5],
            departamento=r[6],
            cuadrante=r[7],
            estado=r[8],
            mercaderista=r[9],
            producto=r[10],
            categoria=r[11],
            inv_inicial=r[12],
            inv_final=r[13],
            inv_deposito=r[14],
            caras=r[15],
            precio_bs=r[16],
            precio_ds=r[17]
        )
        for r in rows
    ]
