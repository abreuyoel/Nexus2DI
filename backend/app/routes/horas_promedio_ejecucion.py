"""CRUD de HORAS_PROMEDIO_EJECUCION: minutos promedio de ejecución esperados
por cliente + clasificación de PDV (CAT_TIPO_NEGOCIO)."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.models.user import Usuario
from app.models.cliente import Cliente
from app.models.catalogo import TipoNegocio
from app.models.horas_promedio_ejecucion import HorasPromedioEjecucion
from app.schemas.horas_promedio_ejecucion import (
    HorasPromedioEjecucionCreate, HorasPromedioEjecucionUpdate, HorasPromedioEjecucionResponse,
)
from app.services.audit_service import log_action
from app.core.request_ip import get_client_ip

router = APIRouter(prefix="/api/horas-promedio-ejecucion", tags=["Horas Promedio Ejecución"])


def _query_con_joins(db: Session):
    UsuarioCreador = Usuario
    from sqlalchemy.orm import aliased
    UsuarioModificador = aliased(Usuario)
    return (
        db.query(HorasPromedioEjecucion, Cliente.nombre, TipoNegocio.nombre,
                  UsuarioCreador.username, UsuarioModificador.username)
        .outerjoin(Cliente, Cliente.id == HorasPromedioEjecucion.id_cliente)
        .outerjoin(TipoNegocio, TipoNegocio.id == HorasPromedioEjecucion.id_tipo_negocio)
        .outerjoin(UsuarioCreador, UsuarioCreador.id == HorasPromedioEjecucion.id_usuario_creador)
        .outerjoin(UsuarioModificador, UsuarioModificador.id == HorasPromedioEjecucion.id_usuario_modificador)
    )


def _to_resp(h: HorasPromedioEjecucion, cliente_nombre=None, tipo_negocio_nombre=None,
             creador_username=None, modificador_username=None) -> HorasPromedioEjecucionResponse:
    return HorasPromedioEjecucionResponse(
        id=h.id, id_cliente=h.id_cliente, id_tipo_negocio=h.id_tipo_negocio,
        minutos_promedio=h.minutos_promedio,
        fecha_creado=h.fecha_creado, fecha_modificado=h.fecha_modificado,
        id_usuario_creador=h.id_usuario_creador, id_usuario_modificador=h.id_usuario_modificador,
        cliente_nombre=cliente_nombre, tipo_negocio_nombre=tipo_negocio_nombre,
        usuario_creador_username=creador_username, usuario_modificador_username=modificador_username,
    )


@router.get("", response_model=List[HorasPromedioEjecucionResponse])
def list_horas_promedio(
    id_cliente: Optional[int] = Query(None),
    id_tipo_negocio: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = _query_con_joins(db)
    if id_cliente is not None:
        q = q.filter(HorasPromedioEjecucion.id_cliente == id_cliente)
    if id_tipo_negocio is not None:
        q = q.filter(HorasPromedioEjecucion.id_tipo_negocio == id_tipo_negocio)
    return [_to_resp(h, cn, tn, cu, mu) for h, cn, tn, cu, mu in q.order_by(HorasPromedioEjecucion.id.desc()).all()]


@router.get("/{id_horas}", response_model=HorasPromedioEjecucionResponse)
def get_horas_promedio(id_horas: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    row = _query_con_joins(db).filter(HorasPromedioEjecucion.id == id_horas).first()
    if not row:
        raise HTTPException(404, "Registro no encontrado")
    h, cn, tn, cu, mu = row
    return _to_resp(h, cn, tn, cu, mu)


@router.post("", response_model=HorasPromedioEjecucionResponse, status_code=201)
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


@router.put("/{id_horas}", response_model=HorasPromedioEjecucionResponse)
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


@router.delete("/{id_horas}")
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
