import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario as User
from app.modules.customer_service.entities import Solicitud
from app.modules.routes.entities import PuntoInteres
from app.modules.clients.entities import Cliente
from app.modules.sellers.entities import VendedorJornada, VendedorVisita
from app.modules.sellers.dto import (
    JornadaActivaResponse, ActivarJornadaResponse, FinalizarJornadaResponse,
    PdvSellerResponse, ClienteSellerResponse, RegistrarVisitaSellerRequest,
    RegistrarVisitaSellerResponse, VisitasHoySellerResponse, VisitaSellerItem,
    SolicitarPdvSellerRequest, SolicitarPdvSellerResponse
)

router = APIRouter(prefix="/api/vendedor", tags=["Vendedor"])


def check_rol_vendedor(current_user: User):
    if current_user.id_rol != 9 and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso denegado. Solo para Vendedores.")


def _jornada_activa(db: Session, id_usuario: int) -> Optional[VendedorJornada]:
    return (
        db.query(VendedorJornada)
        .filter(VendedorJornada.id_usuario == id_usuario, VendedorJornada.estado == 'En Progreso')
        .order_by(VendedorJornada.id.desc())
        .first()
    )


def _contar_visitas(db: Session, id_jornada: int) -> int:
    return db.query(VendedorVisita).filter(VendedorVisita.id_jornada == id_jornada).count()


@router.get("/jornada-activa", response_model=JornadaActivaResponse)
def jornada_activa(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    j = _jornada_activa(db, current_user.id)
    if not j:
        return JornadaActivaResponse(success=True, activa=False, visitas=0)
    return JornadaActivaResponse(
        success=True,
        activa=True,
        id_jornada=j.id,
        fecha_inicio=j.fecha_inicio.isoformat() if j.fecha_inicio else None,
        visitas=_contar_visitas(db, j.id),
    )


@router.post("/activar-jornada", response_model=ActivarJornadaResponse)
def activar_jornada(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    j = _jornada_activa(db, current_user.id)
    if j:
        return ActivarJornadaResponse(
            success=True,
            id_jornada=j.id,
            fecha_inicio=j.fecha_inicio.isoformat() if j.fecha_inicio else None,
            ya_activa=True
        )
    nueva_jornada = VendedorJornada(
        id_usuario=current_user.id,
        fecha_inicio=datetime.now(),
        estado='En Progreso'
    )
    db.add(nueva_jornada)
    db.commit()
    db.refresh(nueva_jornada)
    return ActivarJornadaResponse(
        success=True,
        id_jornada=nueva_jornada.id,
        fecha_inicio=nueva_jornada.fecha_inicio.isoformat() if nueva_jornada.fecha_inicio else None
    )


@router.post("/finalizar-jornada", response_model=FinalizarJornadaResponse)
def finalizar_jornada(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    jornadas = (
        db.query(VendedorJornada)
        .filter(VendedorJornada.id_usuario == current_user.id, VendedorJornada.estado == 'En Progreso')
        .all()
    )
    now = datetime.now()
    for j in jornadas:
        j.estado = 'Finalizada'
        j.fecha_fin = now
    db.commit()
    return FinalizarJornadaResponse(success=True, message="Jornada finalizada")


@router.get("/pdvs", response_model=List[PdvSellerResponse])
def get_pdvs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    rows = (
        db.query(PuntoInteres.id, PuntoInteres.nombre, PuntoInteres.direccion, PuntoInteres.ciudad)
        .order_by(PuntoInteres.nombre)
        .all()
    )
    return [
        PdvSellerResponse(
            identificador=r[0],
            nombre=r[1],
            direccion=r[2],
            ciudad=r[3],
            localidad=None
        )
        for r in rows
    ]


@router.get("/clientes", response_model=List[ClienteSellerResponse])
def get_clientes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    rows = db.query(Cliente.id, Cliente.nombre).order_by(Cliente.nombre).all()
    return [ClienteSellerResponse(id_cliente=r[0], nombre=r[1]) for r in rows]


@router.post("/registrar-visita", response_model=RegistrarVisitaSellerResponse)
def registrar_visita(payload: RegistrarVisitaSellerRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    id_punto_interes = payload.id_punto_interes
    id_cliente = payload.id_cliente
    vendio = payload.vendio
    if not id_punto_interes or not id_cliente or vendio is None:
        raise HTTPException(status_code=400, detail="Datos incompletos")

    vendio_bool = bool(vendio) if isinstance(vendio, bool) else str(vendio).lower() in ("true", "1")
    monto = None
    razon = None
    if vendio_bool:
        try:
            monto = float(payload.monto) if payload.monto is not None else 0.0
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="El monto es requerido y debe ser numérico")
        if monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor que cero")
    else:
        razon = (payload.razon_no_venta or "").strip()
        if not razon:
            raise HTTPException(status_code=400, detail="La razón de no venta es requerida")

    j = _jornada_activa(db, current_user.id)
    if not j:
        raise HTTPException(status_code=400, detail="No tienes una jornada activa. Activa tu ruta primero.")

    lat = payload.latitud
    lon = payload.longitud
    try:
        lat = float(lat) if lat not in (None, "") else None
        lon = float(lon) if lon not in (None, "") else None
    except (TypeError, ValueError):
        lat, lon = None, None

    nueva_visita = VendedorVisita(
        id_jornada=j.id,
        id_usuario=current_user.id,
        id_punto_interes=str(id_punto_interes),
        id_cliente=id_cliente,
        fecha_hora=datetime.now(),
        vendio=vendio_bool,
        monto=monto,
        razon_no_venta=razon,
        latitud=lat,
        longitud=lon
    )
    db.add(nueva_visita)
    db.commit()
    return RegistrarVisitaSellerResponse(
        success=True,
        message="Visita registrada",
        visitas=_contar_visitas(db, j.id)
    )


@router.get("/visitas-hoy", response_model=VisitasHoySellerResponse)
def visitas_hoy(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    j = _jornada_activa(db, current_user.id)
    if not j:
        return VisitasHoySellerResponse(success=True, visitas=[])

    rows = (
        db.query(
            VendedorVisita.fecha_hora,
            VendedorVisita.vendio,
            VendedorVisita.monto,
            VendedorVisita.razon_no_venta,
            PuntoInteres.nombre,
            Cliente.nombre
        )
        .outerjoin(PuntoInteres, PuntoInteres.id == VendedorVisita.id_punto_interes)
        .outerjoin(Cliente, Cliente.id == VendedorVisita.id_cliente)
        .filter(VendedorVisita.id_jornada == j.id)
        .order_by(VendedorVisita.id.desc())
        .all()
    )

    return VisitasHoySellerResponse(
        success=True,
        visitas=[
            VisitaSellerItem(
                fecha_hora=r[0].isoformat() if r[0] else None,
                vendio=bool(r[1]),
                monto=float(r[2]) if r[2] is not None else None,
                razon_no_venta=r[3],
                pdv=r[4],
                cliente=r[5]
            )
            for r in rows
        ]
    )


@router.post("/solicitar-pdv", response_model=SolicitarPdvSellerResponse)
def solicitar_pdv(payload: SolicitarPdvSellerRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    nombre = payload.punto_de_interes.strip()
    rif = payload.rif.strip()
    direccion = payload.direccion.strip()
    foto_tienda = payload.foto_tienda
    foto_rif = payload.foto_rif

    faltan = []
    if not nombre: faltan.append("nombre del PDV")
    if not rif: faltan.append("RIF")
    if not direccion: faltan.append("dirección")
    if not foto_tienda: faltan.append("foto de la tienda")
    if not foto_rif: faltan.append("foto del RIF")
    if faltan:
        raise HTTPException(status_code=400, detail="Faltan datos: " + ", ".join(faltan))

    lat = payload.latitud
    lon = payload.longitud
    try:
        lat = float(lat) if lat not in (None, "") else None
        lon = float(lon) if lon not in (None, "") else None
    except (TypeError, ValueError):
        lat, lon = None, None

    datos = {
        "punto_de_interes": nombre, "rif": rif, "direccion": direccion,
        "latitud": lat, "longitud": lon, "foto_tienda": foto_tienda, "foto_rif": foto_rif,
    }
    solicitud = Solicitud(
        user_id=current_user.id, tipo="creacion_pdv",
        descripcion=json.dumps(datos), estado="pendiente", created_at=datetime.now(),
    )
    db.add(solicitud)
    db.commit()
    return SolicitarPdvSellerResponse(
        success=True,
        message="Solicitud de creación de PDV enviada. Espera la aprobación de Atención al Cliente."
    )
