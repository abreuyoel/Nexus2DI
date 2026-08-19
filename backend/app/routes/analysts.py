from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, delete as sa_delete
from typing import List
from pydantic import BaseModel
from app.db.session import get_async_db
from app.core.dependencies import require_admin, require_analyst_or_admin, get_current_user
from app.models.analista import Analista, AnalistaCliente
from app.models.ruta import Ruta, RutaProgramacion, AnalistaRuta
from app.models.cliente import Cliente
from app.models.user import Usuario
from app.schemas.analista import AnalistaCreate, AnalistaUpdate, AnalistaResponse

router = APIRouter(prefix="/api/analysts", tags=["Analistas"])


class IdListRequest(BaseModel):
    ids: List[int] = []


@router.get("", response_model=List[AnalistaResponse])
async def list_analysts(
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    return (await db.execute(select(Analista).order_by(Analista.nombre))).scalars().all()


@router.get("/with-assignments")
async def list_analysts_with_assignments(
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    """Analistas (rol 2) + conteo de rutas y clientes asignados (para las tarjetas).
    Los supervisores (rol 6) se gestionan aparte en /api/supervisores."""
    analistas = (await db.execute(select(Analista).filter(Analista.id_rol == 2).order_by(Analista.nombre))).scalars().all()
    rutas_counts = dict(
        (await db.execute(
            select(AnalistaRuta.id_analista, func.count(AnalistaRuta.id_ruta))
            .group_by(AnalistaRuta.id_analista)
        )).all()
    )
    cli_counts = dict(
        (await db.execute(
            select(AnalistaCliente.id_analista, func.count(AnalistaCliente.id_cliente))
            .group_by(AnalistaCliente.id_analista)
        )).all()
    )
    return [{
        "id": a.id,
        "nombre": a.nombre,
        "rutas_count": rutas_counts.get(a.id, 0),
        "clientes_count": cli_counts.get(a.id, 0),
    } for a in analistas]


@router.get("/{analyst_id}/routes")
async def get_analyst_routes(
    analyst_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Ruta)
        .join(AnalistaRuta, AnalistaRuta.id_ruta == Ruta.id)
        .filter(AnalistaRuta.id_analista == analyst_id)
        .order_by(Ruta.nombre)
    )).scalars().all()
    return [{"id": r.id, "nombre": r.nombre, "servicio": r.servicio, "cuadrante": r.cuadrante} for r in rows]


@router.post("/{analyst_id}/sync-routes")
async def sync_analyst_routes(
    analyst_id: int,
    data: IdListRequest,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    if not (await db.execute(select(Analista).filter(Analista.id == analyst_id))).scalars().first():
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    await db.execute(sa_delete(AnalistaRuta).where(AnalistaRuta.id_analista == analyst_id))
    for rid in set(data.ids):
        db.add(AnalistaRuta(id_analista=analyst_id, id_ruta=rid))
    await db.commit()
    return {"message": "Rutas del analista sincronizadas", "count": len(set(data.ids))}


@router.get("/{analyst_id}/clients")
async def get_analyst_clients(
    analyst_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Cliente)
        .join(AnalistaCliente, AnalistaCliente.id_cliente == Cliente.id)
        .filter(AnalistaCliente.id_analista == analyst_id)
        .order_by(Cliente.nombre)
    )).scalars().all()
    return [{"id": c.id, "nombre": c.nombre} for c in rows]


@router.get("/{analyst_id}/route-clients")
async def get_analyst_route_clients(
    analyst_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    """Clientes distintos presentes en las rutas asignadas al analista
    (opciones válidas para asignarle clientes — flujo 'dentro de la ruta')."""
    rows = (await db.execute(
        select(Cliente.id, Cliente.nombre)
        .join(RutaProgramacion, RutaProgramacion.id_cliente == Cliente.id)
        .join(AnalistaRuta, AnalistaRuta.id_ruta == RutaProgramacion.ruta_id)
        .filter(
            AnalistaRuta.id_analista == analyst_id,
            RutaProgramacion.activo == True,
            Cliente.nombre.isnot(None),
        )
        .distinct().order_by(Cliente.nombre)
    )).all()
    return [{"id": cid, "nombre": cn} for cid, cn in rows]


@router.post("/{analyst_id}/sync-clients")
async def sync_analyst_clients(
    analyst_id: int,
    data: IdListRequest,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    if not (await db.execute(select(Analista).filter(Analista.id == analyst_id))).scalars().first():
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    await db.execute(sa_delete(AnalistaCliente).where(AnalistaCliente.id_analista == analyst_id))
    for cid in set(data.ids):
        db.add(AnalistaCliente(id_analista=analyst_id, id_cliente=cid))
    await db.commit()
    return {"message": "Clientes del analista sincronizados", "count": len(set(data.ids))}

@router.get("/{analyst_id}", response_model=AnalistaResponse)
async def get_analyst(analyst_id: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    analyst = (await db.execute(select(Analista).filter(Analista.id == analyst_id))).scalars().first()
    if not analyst:
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    return analyst

@router.post("", response_model=AnalistaResponse, status_code=status.HTTP_201_CREATED)
async def create_analyst(
    data: AnalistaCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    analyst = Analista(**data.model_dump())
    db.add(analyst)
    await db.commit()
    await db.refresh(analyst)
    return analyst

@router.put("/{analyst_id}", response_model=AnalistaResponse)
async def update_analyst(
    analyst_id: int,
    data: AnalistaUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    analyst = (await db.execute(select(Analista).filter(Analista.id == analyst_id))).scalars().first()
    if not analyst:
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(analyst, key, value)
    
    await db.commit()
    await db.refresh(analyst)
    return analyst

@router.delete("/{analyst_id}")
async def delete_analyst(
    analyst_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    analyst = (await db.execute(select(Analista).filter(Analista.id == analyst_id))).scalars().first()
    if not analyst:
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    await db.delete(analyst)
    await db.commit()
    return {"message": "Analista eliminado"}

