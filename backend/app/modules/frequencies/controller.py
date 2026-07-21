from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session, aliased

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.clients.entities import Cliente
from app.modules.catalogues.entities import TipoNegocio
from app.modules.routes.entities import PuntoInteres, RutaProgramacion
from app.modules.frequencies.entities import FrecuenciaPdvCliente, HorasPromedioEjecucion
from app.modules.frequencies.dto import (
    FrecuenciaPdvClienteCreate, FrecuenciaPdvClienteUpdate, FrecuenciaPdvClienteResponse,
    FrecuenciaBulkCreate, PdvDisponibleClienteResponse,
    HorasPromedioEjecucionCreate, HorasPromedioEjecucionUpdate, HorasPromedioEjecucionResponse
)
from app.shared.audit_service import log_action
from app.core.request_ip import get_client_ip

router = APIRouter(tags=["Frecuencias e Horas Promedio"])


# ════════════════════════════════════════════════════════════════════════════
# 1. Frecuencias PDVs Cliente (antes routes/frecuencias_pdvs_cliente.py)
# ════════════════════════════════════════════════════════════════════════════

def _query_con_joins_frecuencias(db: Session):
    return (
        db.query(FrecuenciaPdvCliente, Cliente.nombre, PuntoInteres.nombre, Usuario.username)
        .outerjoin(Cliente, Cliente.id == FrecuenciaPdvCliente.id_cliente)
        .outerjoin(PuntoInteres, PuntoInteres.id == FrecuenciaPdvCliente.id_punto_interes)
        .outerjoin(Usuario, Usuario.id == FrecuenciaPdvCliente.id_usuario)
    )


def _to_resp_frecuencia(f: FrecuenciaPdvCliente, cliente_nombre=None, pdv_nombre=None, usuario_username=None) -> FrecuenciaPdvClienteResponse:
    return FrecuenciaPdvClienteResponse(
        id=f.id, id_cliente=f.id_cliente, id_punto_interes=f.id_punto_interes,
        frecuencia_semanal=float(f.frecuencia_semanal), observaciones=f.observaciones, activo=f.activo,
        fecha_creacion=f.fecha_creacion, fecha_modificacion=f.fecha_modificacion, id_usuario=f.id_usuario,
        cliente_nombre=cliente_nombre, pdv_nombre=pdv_nombre, usuario_username=usuario_username,
    )


@router.get("/api/frecuencias-pdvs-cliente", response_model=List[FrecuenciaPdvClienteResponse])
def list_frecuencias(
    id_cliente: Optional[int] = Query(None),
    id_punto_interes: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = _query_con_joins_frecuencias(db)
    if id_cliente is not None:
        q = q.filter(FrecuenciaPdvCliente.id_cliente == id_cliente)
    if id_punto_interes is not None:
        q = q.filter(FrecuenciaPdvCliente.id_punto_interes == id_punto_interes)
    if activo is not None:
        q = q.filter(FrecuenciaPdvCliente.activo == activo)
    return [_to_resp_frecuencia(f, cn, pn, un) for f, cn, pn, un in q.order_by(FrecuenciaPdvCliente.id.desc()).all()]


@router.get("/api/frecuencias-pdvs-cliente/pdvs-disponibles/{id_cliente}", response_model=List[PdvDisponibleClienteResponse])
def pdvs_disponibles_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    if not db.query(Cliente).filter(Cliente.id == id_cliente).first():
        raise HTTPException(404, "Cliente no existe")
    
    rows = (
        db.query(
            RutaProgramacion.punto_id,
            RutaProgramacion.punto_interes_nombre
        )
        .distinct()
        .filter(
            RutaProgramacion.id_cliente == id_cliente,
            RutaProgramacion.activo == True,
            RutaProgramacion.punto_id.isnot(None)
        )
        .order_by(RutaProgramacion.punto_interes_nombre)
        .all()
    )

    existentes = {
        f.id_punto_interes: f
        for f in db.query(FrecuenciaPdvCliente).filter(FrecuenciaPdvCliente.id_cliente == id_cliente).all()
    }
    resultado = []
    for pdv_id, pdv_nombre in rows:
        ex = existentes.get(pdv_id)
        resultado.append(PdvDisponibleClienteResponse(
            id_punto_interes=pdv_id,
            pdv_nombre=pdv_nombre or "",
            id_frecuencia=ex.id if ex else None,
            frecuencia_semanal=float(ex.frecuencia_semanal) if ex else None,
            observaciones=ex.observaciones if ex else None,
        ))
    return resultado


@router.post("/api/frecuencias-pdvs-cliente/bulk")
def bulk_upsert_frecuencias(
    data: FrecuenciaBulkCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    if not db.query(Cliente).filter(Cliente.id == data.id_cliente).first():
        raise HTTPException(404, "Cliente no existe")
    creados = 0
    actualizados = 0
    for item in data.items:
        existente = db.query(FrecuenciaPdvCliente).filter_by(
            id_cliente=data.id_cliente, id_punto_interes=item.id_punto_interes
        ).first()
        if existente:
            existente.frecuencia_semanal = item.frecuencia_semanal
            existente.observaciones = item.observaciones
            existente.activo = True
            existente.id_usuario = current_user.id
            existente.fecha_modificacion = datetime.utcnow()
            actualizados += 1
        else:
            db.add(FrecuenciaPdvCliente(
                id_cliente=data.id_cliente, id_punto_interes=item.id_punto_interes,
                frecuencia_semanal=item.frecuencia_semanal, observaciones=item.observaciones,
                activo=True, id_usuario=current_user.id,
            ))
            creados += 1
    db.commit()
    return {"creados": creados, "actualizados": actualizados}


@router.get("/api/frecuencias-pdvs-cliente/{id_frecuencia}", response_model=FrecuenciaPdvClienteResponse)
def get_frecuencia(id_frecuencia: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    row = _query_con_joins_frecuencias(db).filter(FrecuenciaPdvCliente.id == id_frecuencia).first()
    if not row:
        raise HTTPException(404, "Registro no encontrado")
    f, cn, pn, un = row
    return _to_resp_frecuencia(f, cn, pn, un)


@router.post("/api/frecuencias-pdvs-cliente", response_model=FrecuenciaPdvClienteResponse, status_code=201)
def create_frecuencia(
    data: FrecuenciaPdvClienteCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    if not db.query(Cliente).filter(Cliente.id == data.id_cliente).first():
        raise HTTPException(404, "Cliente no existe")
    if not db.query(PuntoInteres).filter(PuntoInteres.id == data.id_punto_interes).first():
        raise HTTPException(404, "PDV no existe")
    f = FrecuenciaPdvCliente(
        id_cliente=data.id_cliente, id_punto_interes=data.id_punto_interes,
        frecuencia_semanal=data.frecuencia_semanal, observaciones=data.observaciones,
        activo=data.activo, id_usuario=current_user.id,
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return get_frecuencia(f.id, db, current_user)


@router.put("/api/frecuencias-pdvs-cliente/{id_frecuencia}", response_model=FrecuenciaPdvClienteResponse)
def update_frecuencia(
    id_frecuencia: int,
    data: FrecuenciaPdvClienteUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    f = db.query(FrecuenciaPdvCliente).filter(FrecuenciaPdvCliente.id == id_frecuencia).first()
    if not f:
        raise HTTPException(404, "Registro no encontrado")
    if data.id_cliente is not None and not db.query(Cliente).filter(Cliente.id == data.id_cliente).first():
        raise HTTPException(404, "Cliente no existe")
    if data.id_punto_interes is not None and not db.query(PuntoInteres).filter(PuntoInteres.id == data.id_punto_interes).first():
        raise HTTPException(404, "PDV no existe")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(f, k, v)
    f.id_usuario = current_user.id
    f.fecha_modificacion = datetime.utcnow()
    db.commit()
    return get_frecuencia(id_frecuencia, db, current_user)


@router.delete("/api/frecuencias-pdvs-cliente/{id_frecuencia}")
def delete_frecuencia(
    id_frecuencia: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    f = db.query(FrecuenciaPdvCliente).filter(FrecuenciaPdvCliente.id == id_frecuencia).first()
    if not f:
        raise HTTPException(404, "Registro no encontrado")
    db.delete(f)
    db.commit()
    return {"detail": "Registro eliminado"}


# ════════════════════════════════════════════════════════════════════════════
# 2. Horas Promedio Ejecución (antes routes/horas_promedio_ejecucion.py)
# ════════════════════════════════════════════════════════════════════════════

def _query_con_joins_horas(db: Session):
    UsuarioCreador = Usuario
    UsuarioModificador = aliased(Usuario)
    return (
        db.query(HorasPromedioEjecucion, Cliente.nombre, TipoNegocio.nombre,
                  UsuarioCreador.username, UsuarioModificador.username)
        .outerjoin(Cliente, Cliente.id == HorasPromedioEjecucion.id_cliente)
        .outerjoin(TipoNegocio, TipoNegocio.id == HorasPromedioEjecucion.id_tipo_negocio)
        .outerjoin(UsuarioCreador, UsuarioCreador.id == HorasPromedioEjecucion.id_usuario_creador)
        .outerjoin(UsuarioModificador, UsuarioModificador.id == HorasPromedioEjecucion.id_usuario_modificador)
    )


def _to_resp_horas(h: HorasPromedioEjecucion, cliente_nombre=None, tipo_negocio_nombre=None,
              creador_username=None, modificador_username=None) -> HorasPromedioEjecucionResponse:
    return HorasPromedioEjecucionResponse(
        id=h.id, id_cliente=h.id_cliente, id_tipo_negocio=h.id_tipo_negocio,
        minutos_promedio=h.minutos_promedio,
        fecha_creado=h.fecha_creado, fecha_modificado=h.fecha_modificado,
        id_usuario_creador=h.id_usuario_creador, id_usuario_modificador=h.id_usuario_modificador,
        cliente_nombre=cliente_nombre, tipo_negocio_nombre=tipo_negocio_nombre,
        usuario_creador_username=creador_username, usuario_modificador_username=modificador_username,
    )


@router.get("/api/horas-promedio-ejecucion", response_model=List[HorasPromedioEjecucionResponse])
def list_horas_promedio(
    id_cliente: Optional[int] = Query(None),
    id_tipo_negocio: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = _query_con_joins_horas(db)
    if id_cliente is not None:
        q = q.filter(HorasPromedioEjecucion.id_cliente == id_cliente)
    if id_tipo_negocio is not None:
        q = q.filter(HorasPromedioEjecucion.id_tipo_negocio == id_tipo_negocio)
    return [_to_resp_horas(h, cn, tn, cu, mu) for h, cn, tn, cu, mu in q.order_by(HorasPromedioEjecucion.id.desc()).all()]


@router.get("/api/horas-promedio-ejecucion/{id_horas}", response_model=HorasPromedioEjecucionResponse)
def get_horas_promedio(id_horas: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    row = _query_con_joins_horas(db).filter(HorasPromedioEjecucion.id == id_horas).first()
    if not row:
        raise HTTPException(404, "Registro no encontrado")
    h, cn, tn, cu, mu = row
    return _to_resp_horas(h, cn, tn, cu, mu)


@router.post("/api/horas-promedio-ejecucion", response_model=HorasPromedioEjecucionResponse, status_code=201)
def create_horas_promedio(
    data: HorasPromedioEjecucionCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    if not db.query(Cliente).filter(Cliente.id == data.id_cliente).first():
        raise HTTPException(404, "Cliente no existe")
    if not db.query(TipoNegocio).filter(TipoNegocio.id == data.id_tipo_negocio).first():
        raise HTTPException(404, "Clasificación de PDV no existe")
    h = HorasPromedioEjecucion(
        id_cliente=data.id_cliente, id_tipo_negocio=data.id_tipo_negocio,
        minutos_promedio=data.minutos_promedio, id_usuario_creador=current_user.id,
    )
    db.add(h)
    db.flush()
    log_action(db, action="CREATE_HORAS_PROMEDIO_EJECUCION", entity_type="HorasPromedioEjecucion",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=h.id, entity_name=f"cliente={data.id_cliente} tipo_negocio={data.id_tipo_negocio}",
               changes=data.model_dump())
    db.commit()
    return get_horas_promedio(h.id, db, current_user)


@router.put("/api/horas-promedio-ejecucion/{id_horas}", response_model=HorasPromedioEjecucionResponse)
def update_horas_promedio(
    id_horas: int,
    data: HorasPromedioEjecucionUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    h = db.query(HorasPromedioEjecucion).filter(HorasPromedioEjecucion.id == id_horas).first()
    if not h:
        raise HTTPException(404, "Registro no encontrado")
    if data.id_cliente is not None and not db.query(Cliente).filter(Cliente.id == data.id_cliente).first():
        raise HTTPException(404, "Cliente no existe")
    if data.id_tipo_negocio is not None and not db.query(TipoNegocio).filter(TipoNegocio.id == data.id_tipo_negocio).first():
        raise HTTPException(404, "Clasificación de PDV no existe")
    changes = data.model_dump(exclude_unset=True)
    for k, v in changes.items():
        setattr(h, k, v)
    h.id_usuario_modificador = current_user.id
    h.fecha_modificado = datetime.utcnow()
    log_action(db, action="UPDATE_HORAS_PROMEDIO_EJECUCION", entity_type="HorasPromedioEjecucion",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=h.id, entity_name=f"cliente={h.id_cliente} tipo_negocio={h.id_tipo_negocio}",
               changes=changes)
    db.commit()
    return get_horas_promedio(id_horas, db, current_user)


@router.delete("/api/horas-promedio-ejecucion/{id_horas}")
def delete_horas_promedio(
    id_horas: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    h = db.query(HorasPromedioEjecucion).filter(HorasPromedioEjecucion.id == id_horas).first()
    if not h:
        raise HTTPException(404, "Registro no encontrado")
    log_action(db, action="DELETE_HORAS_PROMEDIO_EJECUCION", entity_type="HorasPromedioEjecucion",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=h.id, entity_name=f"cliente={h.id_cliente} tipo_negocio={h.id_tipo_negocio}")
    db.delete(h)
    db.commit()
    return {"detail": "Registro eliminado"}
