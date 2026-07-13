"""CRUD de FRECUENCIAS_PDVS_CLIENTE: cuantas veces por semana debe visitarse
un PDV para un cliente dado."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.models.user import Usuario
from app.models.cliente import Cliente
from app.models.punto import PuntoInteres
from app.models.frecuencia_pdv_cliente import FrecuenciaPdvCliente
from app.schemas.frecuencia_pdv_cliente import (
    FrecuenciaPdvClienteCreate, FrecuenciaPdvClienteUpdate, FrecuenciaPdvClienteResponse,
    FrecuenciaBulkCreate,
)

router = APIRouter(prefix="/api/frecuencias-pdvs-cliente", tags=["Frecuencias PDVs Cliente"])


def _query_con_joins(db: Session):
    return (
        db.query(FrecuenciaPdvCliente, Cliente.nombre, PuntoInteres.nombre, Usuario.username)
        .outerjoin(Cliente, Cliente.id == FrecuenciaPdvCliente.id_cliente)
        .outerjoin(PuntoInteres, PuntoInteres.id == FrecuenciaPdvCliente.id_punto_interes)
        .outerjoin(Usuario, Usuario.id == FrecuenciaPdvCliente.id_usuario)
    )


def _to_resp(f: FrecuenciaPdvCliente, cliente_nombre=None, pdv_nombre=None, usuario_username=None) -> FrecuenciaPdvClienteResponse:
    return FrecuenciaPdvClienteResponse(
        id=f.id, id_cliente=f.id_cliente, id_punto_interes=f.id_punto_interes,
        frecuencia_semanal=float(f.frecuencia_semanal), observaciones=f.observaciones, activo=f.activo,
        fecha_creacion=f.fecha_creacion, fecha_modificacion=f.fecha_modificacion, id_usuario=f.id_usuario,
        cliente_nombre=cliente_nombre, pdv_nombre=pdv_nombre, usuario_username=usuario_username,
    )


@router.get("", response_model=List[FrecuenciaPdvClienteResponse])
def list_frecuencias(
    id_cliente: Optional[int] = Query(None),
    id_punto_interes: Optional[str] = Query(None),
    activo: Optional[bool] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = _query_con_joins(db)
    if id_cliente is not None:
        q = q.filter(FrecuenciaPdvCliente.id_cliente == id_cliente)
    if id_punto_interes is not None:
        q = q.filter(FrecuenciaPdvCliente.id_punto_interes == id_punto_interes)
    if activo is not None:
        q = q.filter(FrecuenciaPdvCliente.activo == activo)
    return [_to_resp(f, cn, pn, un) for f, cn, pn, un in q.order_by(FrecuenciaPdvCliente.id.desc()).all()]


@router.get("/pdvs-disponibles/{id_cliente}")
def pdvs_disponibles_cliente(
    id_cliente: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """PDVs unicos donde aparece el cliente en RUTA_PROGRAMACION, marcando la
    frecuencia ya asignada (si existe) para poder editarla en la carga masiva."""
    if not db.query(Cliente).filter(Cliente.id == id_cliente).first():
        raise HTTPException(404, "Cliente no existe")
    rows = db.execute(text("""
        SELECT DISTINCT rp.id_punto_interes, rp.punto_interes
        FROM RUTA_PROGRAMACION rp
        WHERE rp.id_cliente = :cid AND rp.activa = 1 AND rp.id_punto_interes IS NOT NULL
        ORDER BY rp.punto_interes
    """), {"cid": id_cliente}).fetchall()
    existentes = {
        f.id_punto_interes: f
        for f in db.query(FrecuenciaPdvCliente).filter(FrecuenciaPdvCliente.id_cliente == id_cliente).all()
    }
    resultado = []
    for pdv_id, pdv_nombre in rows:
        ex = existentes.get(pdv_id)
        resultado.append({
            "id_punto_interes": pdv_id,
            "pdv_nombre": pdv_nombre,
            "id_frecuencia": ex.id if ex else None,
            "frecuencia_semanal": float(ex.frecuencia_semanal) if ex else None,
            "observaciones": ex.observaciones if ex else None,
        })
    return resultado


@router.post("/bulk")
def bulk_upsert_frecuencias(
    data: FrecuenciaBulkCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    """Crea o actualiza (upsert) varias frecuencias de una vez para un mismo
    cliente — pensado para la carga masiva desde los PDVs de su programación."""
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


@router.get("/{id_frecuencia}", response_model=FrecuenciaPdvClienteResponse)
def get_frecuencia(id_frecuencia: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    row = _query_con_joins(db).filter(FrecuenciaPdvCliente.id == id_frecuencia).first()
    if not row:
        raise HTTPException(404, "Registro no encontrado")
    f, cn, pn, un = row
    return _to_resp(f, cn, pn, un)


@router.post("", response_model=FrecuenciaPdvClienteResponse, status_code=201)
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


@router.put("/{id_frecuencia}", response_model=FrecuenciaPdvClienteResponse)
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


@router.delete("/{id_frecuencia}")
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
