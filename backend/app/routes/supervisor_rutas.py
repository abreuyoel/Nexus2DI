from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, delete as sa_delete
from typing import List
from pydantic import BaseModel
from app.db.session import get_async_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.models.user import Usuario
from app.models.supervisor import Supervisor, SupervisorRuta, SupervisorCliente
from app.models.ruta import Ruta, RutaProgramacion
from app.models.cliente import Cliente

router = APIRouter(prefix="/api/supervisores", tags=["Supervisores"])


class IdListRequest(BaseModel):
    ids: List[int] = []


class SupervisorCreate(BaseModel):
    nombre: str


class SupervisorUpdate(BaseModel):
    nombre: str


@router.post("", status_code=201)
async def create_supervisor(
    data: SupervisorCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    nombre = (data.nombre or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es requerido")
    s = Supervisor(nombre=nombre)
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return {"id": s.id, "nombre": s.nombre, "rutas_count": 0, "clientes_count": 0}


@router.put("/{supervisor_id}")
async def update_supervisor(
    supervisor_id: int,
    data: SupervisorUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    s = (await db.execute(select(Supervisor).filter(Supervisor.id == supervisor_id))).scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="Supervisor no encontrado")
    nombre = (data.nombre or "").strip()
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre es requerido")
    s.nombre = nombre
    await db.commit()
    return {"id": s.id, "nombre": s.nombre}


@router.delete("/{supervisor_id}", status_code=204)
async def delete_supervisor(
    supervisor_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    s = (await db.execute(select(Supervisor).filter(Supervisor.id == supervisor_id))).scalars().first()
    if not s:
        raise HTTPException(status_code=404, detail="Supervisor no encontrado")
    await db.execute(sa_delete(SupervisorRuta).where(SupervisorRuta.id_supervisor == supervisor_id))
    await db.execute(sa_delete(SupervisorCliente).where(SupervisorCliente.id_supervisor == supervisor_id))
    await db.delete(s)
    await db.commit()
    return None


@router.get("/with-assignments")
async def list_supervisors_with_assignments(
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    sups = (await db.execute(select(Supervisor).order_by(Supervisor.nombre))).scalars().all()
    rutas_counts = dict(
        (await db.execute(
            select(SupervisorRuta.id_supervisor, func.count(SupervisorRuta.id_ruta))
            .group_by(SupervisorRuta.id_supervisor)
        )).all()
    )
    cli_counts = dict(
        (await db.execute(
            select(SupervisorCliente.id_supervisor, func.count(SupervisorCliente.id_cliente))
            .group_by(SupervisorCliente.id_supervisor)
        )).all()
    )
    return [{
        "id": s.id,
        "nombre": s.nombre,
        "rutas_count": rutas_counts.get(s.id, 0),
        "clientes_count": cli_counts.get(s.id, 0),
    } for s in sups]


@router.get("/{supervisor_id}/routes")
async def get_supervisor_routes(
    supervisor_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Ruta)
        .join(SupervisorRuta, SupervisorRuta.id_ruta == Ruta.id)
        .filter(SupervisorRuta.id_supervisor == supervisor_id)
        .order_by(Ruta.nombre)
    )).scalars().all()
    return [{"id": r.id, "nombre": r.nombre, "servicio": r.servicio, "cuadrante": r.cuadrante} for r in rows]


@router.post("/{supervisor_id}/sync-routes")
async def sync_supervisor_routes(
    supervisor_id: int,
    data: IdListRequest,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    if not (await db.execute(select(Supervisor).filter(Supervisor.id == supervisor_id))).scalars().first():
        raise HTTPException(status_code=404, detail="Supervisor no encontrado")
    await db.execute(sa_delete(SupervisorRuta).where(SupervisorRuta.id_supervisor == supervisor_id))
    for rid in set(data.ids):
        db.add(SupervisorRuta(id_supervisor=supervisor_id, id_ruta=rid))
    await db.commit()
    return {"message": "Rutas del supervisor sincronizadas", "count": len(set(data.ids))}


@router.get("/{supervisor_id}/clients")
async def get_supervisor_clients(
    supervisor_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    rows = (await db.execute(
        select(Cliente)
        .join(SupervisorCliente, SupervisorCliente.id_cliente == Cliente.id)
        .filter(SupervisorCliente.id_supervisor == supervisor_id)
        .order_by(Cliente.nombre)
    )).scalars().all()
    return [{"id": c.id, "nombre": c.nombre} for c in rows]


@router.get("/{supervisor_id}/route-clients")
async def get_supervisor_route_clients(
    supervisor_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    """Clientes distintos presentes en las rutas asignadas al supervisor."""
    rows = (await db.execute(
        select(Cliente.id, Cliente.nombre)
        .join(RutaProgramacion, RutaProgramacion.id_cliente == Cliente.id)
        .join(SupervisorRuta, SupervisorRuta.id_ruta == RutaProgramacion.ruta_id)
        .filter(
            SupervisorRuta.id_supervisor == supervisor_id,
            RutaProgramacion.activo == True,
            Cliente.nombre.isnot(None),
        )
        .distinct().order_by(Cliente.nombre)
    )).all()
    return [{"id": cid, "nombre": cn} for cid, cn in rows]


@router.post("/{supervisor_id}/sync-clients")
async def sync_supervisor_clients(
    supervisor_id: int,
    data: IdListRequest,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    if not (await db.execute(select(Supervisor).filter(Supervisor.id == supervisor_id))).scalars().first():
        raise HTTPException(status_code=404, detail="Supervisor no encontrado")
    await db.execute(sa_delete(SupervisorCliente).where(SupervisorCliente.id_supervisor == supervisor_id))
    for cid in set(data.ids):
        db.add(SupervisorCliente(id_supervisor=supervisor_id, id_cliente=cid))
    await db.commit()
    return {"message": "Clientes del supervisor sincronizados", "count": len(set(data.ids))}


