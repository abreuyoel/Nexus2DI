from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from pydantic import BaseModel
from app.db.session import get_db
from app.core.dependencies import require_admin, require_analyst_or_admin, get_current_user
from app.modules.analysts.entities import Analista, AnalistaCliente
from app.modules.routes.entities import Ruta, RutaProgramacion, AnalistaRuta
from app.modules.clients.entities import Cliente
from app.modules.auth.entities import Usuario
from app.modules.analysts.dto import AnalistaCreate, AnalistaUpdate, AnalistaResponse

router = APIRouter(prefix="/api/analysts", tags=["Analistas"])


class IdListRequest(BaseModel):
    ids: List[int] = []


@router.get("/", response_model=List[AnalistaResponse])
def list_analysts(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    return db.query(Analista).order_by(Analista.nombre).all()


@router.get("/with-assignments")
def list_analysts_with_assignments(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Analistas (rol 2) + conteo de rutas y clientes asignados (para las tarjetas)."""
    analistas = db.query(Analista).filter(Analista.id_rol == 2).order_by(Analista.nombre).all()
    rutas_counts = dict(
        db.query(AnalistaRuta.id_analista, func.count(AnalistaRuta.id_ruta))
        .group_by(AnalistaRuta.id_analista).all()
    )
    cli_counts = dict(
        db.query(AnalistaCliente.id_analista, func.count(AnalistaCliente.id_cliente))
        .group_by(AnalistaCliente.id_analista).all()
    )
    return [{
        "id": a.id,
        "nombre": a.nombre,
        "rutas_count": rutas_counts.get(a.id, 0),
        "clientes_count": cli_counts.get(a.id, 0),
    } for a in analistas]


@router.get("/{analyst_id}/routes")
def get_analyst_routes(
    analyst_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    rows = (
        db.query(Ruta)
        .join(AnalistaRuta, AnalistaRuta.id_ruta == Ruta.id)
        .filter(AnalistaRuta.id_analista == analyst_id)
        .order_by(Ruta.nombre).all()
    )
    return [{"id": r.id, "nombre": r.nombre, "servicio": r.servicio, "cuadrante": r.cuadrante} for r in rows]


@router.post("/{analyst_id}/sync-routes")
def sync_analyst_routes(
    analyst_id: int,
    data: IdListRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    if not db.query(Analista).filter(Analista.id == analyst_id).first():
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    db.query(AnalistaRuta).filter(AnalistaRuta.id_analista == analyst_id).delete(synchronize_session=False)
    for rid in set(data.ids):
        db.add(AnalistaRuta(id_analista=analyst_id, id_ruta=rid))
    db.commit()
    return {"message": "Rutas del analista sincronizadas", "count": len(set(data.ids))}


@router.get("/{analyst_id}/clients")
def get_analyst_clients(
    analyst_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    rows = (
        db.query(Cliente)
        .join(AnalistaCliente, AnalistaCliente.id_cliente == Cliente.id)
        .filter(AnalistaCliente.id_analista == analyst_id)
        .order_by(Cliente.nombre).all()
    )
    return [{"id": c.id, "nombre": c.nombre} for c in rows]


@router.get("/{analyst_id}/route-clients")
def get_analyst_route_clients(
    analyst_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Clientes distintos presentes en las rutas asignadas al analista
    (opciones válidas para asignarle clientes — flujo 'dentro de la ruta')."""
    rows = (
        db.query(Cliente.id, Cliente.nombre)
        .join(RutaProgramacion, RutaProgramacion.id_cliente == Cliente.id)
        .join(AnalistaRuta, AnalistaRuta.id_ruta == RutaProgramacion.ruta_id)
        .filter(
            AnalistaRuta.id_analista == analyst_id,
            RutaProgramacion.activo == True,
            Cliente.nombre.isnot(None),
        )
        .distinct().order_by(Cliente.nombre).all()
    )
    return [{"id": cid, "nombre": cn} for cid, cn in rows]


@router.post("/{analyst_id}/sync-clients")
def sync_analyst_clients(
    analyst_id: int,
    data: IdListRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    if not db.query(Analista).filter(Analista.id == analyst_id).first():
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    db.query(AnalistaCliente).filter(AnalistaCliente.id_analista == analyst_id).delete(synchronize_session=False)
    for cid in set(data.ids):
        db.add(AnalistaCliente(id_analista=analyst_id, id_cliente=cid))
    db.commit()
    return {"message": "Clientes del analista sincronizados", "count": len(set(data.ids))}


@router.get("/{analyst_id}", response_model=AnalistaResponse)
def get_analyst(analyst_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    analyst = db.query(Analista).filter(Analista.id == analyst_id).first()
    if not analyst:
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    return analyst


@router.post("/", response_model=AnalistaResponse, status_code=status.HTTP_201_CREATED)
def create_analyst(
    data: AnalistaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    analyst = Analista(**data.model_dump())
    db.add(analyst)
    db.commit()
    db.refresh(analyst)
    return analyst


@router.put("/{analyst_id}", response_model=AnalistaResponse)
def update_analyst(
    analyst_id: int,
    data: AnalistaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    analyst = db.query(Analista).filter(Analista.id == analyst_id).first()
    if not analyst:
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    
    update_data = data.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(analyst, key, value)
    
    db.commit()
    db.refresh(analyst)
    return analyst


@router.delete("/{analyst_id}")
def delete_analyst(
    analyst_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    analyst = db.query(Analista).filter(Analista.id == analyst_id).first()
    if not analyst:
        raise HTTPException(status_code=404, detail="Analista no encontrado")
    db.delete(analyst)
    db.commit()
    return {"message": "Analista eliminado"}
