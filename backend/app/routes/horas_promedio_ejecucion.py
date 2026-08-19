from sqlalchemy import select, literal_column
"""CRUD de HORAS_PROMEDIO_EJECUCION: minutos promedio de ejecución esperados
por cliente + clasificación de PDV (CAT_TIPO_NEGOCIO)."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import aliased
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from app.db.session import get_async_db
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

UsuarioCreador = aliased(Usuario, name="creador")
UsuarioModificador = aliased(Usuario, name="modificador")


def _build_stmt():
    return (
        select(
            HorasPromedioEjecucion,
            Cliente.nombre.label("cliente_nombre"),
            TipoNegocio.nombre.label("tipo_negocio_nombre"),
            UsuarioCreador.username.label("creador_username"),
            UsuarioModificador.username.label("modificador_username"),
        )
        .outerjoin(Cliente, Cliente.id == HorasPromedioEjecucion.id_cliente)
        .outerjoin(TipoNegocio, TipoNegocio.id == HorasPromedioEjecucion.id_tipo_negocio)
        .outerjoin(UsuarioCreador, UsuarioCreador.id == HorasPromedioEjecucion.id_usuario_creador)
        .outerjoin(UsuarioModificador, UsuarioModificador.id == HorasPromedioEjecucion.id_usuario_modificador)
    )


def _to_resp(row) -> HorasPromedioEjecucionResponse:
    h = row.HorasPromedioEjecucion
    return HorasPromedioEjecucionResponse(
        id=h.id, id_cliente=h.id_cliente, id_tipo_negocio=h.id_tipo_negocio,
        minutos_promedio=h.minutos_promedio,
        fecha_creado=h.fecha_creado, fecha_modificado=h.fecha_modificado,
        id_usuario_creador=h.id_usuario_creador, id_usuario_modificador=h.id_usuario_modificador,
        cliente_nombre=row.cliente_nombre, tipo_negocio_nombre=row.tipo_negocio_nombre,
        usuario_creador_username=row.creador_username, usuario_modificador_username=row.modificador_username,
    )


@router.get("", response_model=List[HorasPromedioEjecucionResponse])
async def list_horas_promedio(
    id_cliente: Optional[int] = Query(None),
    id_tipo_negocio: Optional[int] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    stmt = _build_stmt()
    if id_cliente is not None:
        stmt = stmt.filter(HorasPromedioEjecucion.id_cliente == id_cliente)
    if id_tipo_negocio is not None:
        stmt = stmt.filter(HorasPromedioEjecucion.id_tipo_negocio == id_tipo_negocio)
    stmt = stmt.order_by(HorasPromedioEjecucion.id.desc())
    rows = (await db.execute(stmt)).all()
    return [_to_resp(row) for row in rows]


@router.get("/{id_horas}", response_model=HorasPromedioEjecucionResponse)
async def get_horas_promedio(id_horas: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    row = (await db.execute(_build_stmt().filter(HorasPromedioEjecucion.id == id_horas))).first()
    if not row:
        raise HTTPException(404, "Registro no encontrado")
    return _to_resp(row)


@router.post("", response_model=HorasPromedioEjecucionResponse, status_code=201)
async def create_horas_promedio(
    data: HorasPromedioEjecucionCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    if not (await db.execute(select(Cliente).filter(Cliente.id == data.id_cliente))).scalars().first():
        raise HTTPException(404, "Cliente no existe")
    if not (await db.execute(select(TipoNegocio).filter(TipoNegocio.id == data.id_tipo_negocio))).scalars().first():
        raise HTTPException(404, "Clasificación de PDV no existe")
    h = HorasPromedioEjecucion(
        id_cliente=data.id_cliente, id_tipo_negocio=data.id_tipo_negocio,
        minutos_promedio=data.minutos_promedio, id_usuario_creador=current_user.id,
    )
    db.add(h)
    await db.flush()
    log_action(db, action="CREATE_HORAS_PROMEDIO_EJECUCION", entity_type="HorasPromedioEjecucion",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=h.id, entity_name=f"cliente={data.id_cliente} tipo_negocio={data.id_tipo_negocio}",
               changes=data.model_dump())
    await db.commit()
    return await get_horas_promedio(h.id, db, current_user)


@router.put("/{id_horas}", response_model=HorasPromedioEjecucionResponse)
async def update_horas_promedio(
    id_horas: int,
    data: HorasPromedioEjecucionUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    h = (await db.execute(select(HorasPromedioEjecucion).filter(HorasPromedioEjecucion.id == id_horas))).scalars().first()
    if not h:
        raise HTTPException(404, "Registro no encontrado")
    if data.id_cliente is not None and not (await db.execute(select(Cliente).filter(Cliente.id == data.id_cliente))).scalars().first():
        raise HTTPException(404, "Cliente no existe")
    if data.id_tipo_negocio is not None and not (await db.execute(select(TipoNegocio).filter(TipoNegocio.id == data.id_tipo_negocio))).scalars().first():
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
    await db.commit()
    return await get_horas_promedio(id_horas, db, current_user)


@router.delete("/{id_horas}")
async def delete_horas_promedio(
    id_horas: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    h = (await db.execute(select(HorasPromedioEjecucion).filter(HorasPromedioEjecucion.id == id_horas))).scalars().first()
    if not h:
        raise HTTPException(404, "Registro no encontrado")
    log_action(db, action="DELETE_HORAS_PROMEDIO_EJECUCION", entity_type="HorasPromedioEjecucion",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=h.id, entity_name=f"cliente={h.id_cliente} tipo_negocio={h.id_tipo_negocio}")
    await db.delete(h)
    await db.commit()
    return {"detail": "Registro eliminado"}
