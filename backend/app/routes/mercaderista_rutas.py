from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.models.user import Usuario
from app.models.mercaderista import Mercaderista, MercaderistaRuta
from app.models.ruta import Ruta

router = APIRouter(prefix="/api/mercaderista-rutas", tags=["Mercaderista Rutas"])


class RouteAssignment(BaseModel):
    ruta_id: int
    tipo_ruta: str = "Variable"


from sqlalchemy import func

@router.get("/")
def list_mercaderistas_con_rutas(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    counts_subq = (
        db.query(
            MercaderistaRuta.mercaderista_id.label("mercaderista_id"),
            func.count(MercaderistaRuta.id).label("rutas_count"),
        )
        .group_by(MercaderistaRuta.mercaderista_id)
        .subquery()
    )

    mercs = (
        db.query(Mercaderista, counts_subq.c.rutas_count)
        .outerjoin(counts_subq, Mercaderista.id == counts_subq.c.mercaderista_id)
        .filter(Mercaderista.activo == True)
        .order_by(Mercaderista.nombre)
        .all()
    )

    result = []
    for m, rutas_count in mercs:
        result.append({
            "id": m.id,
            "cedula": m.cedula,
            "nombre": m.nombre_completo,
            "email": m.email,
            "telefono": m.telefono,
            "tipo": m.tipo,
            "activo": m.activo,
            "rutas_count": rutas_count or 0,
        })
    return result


@router.get("/mercaderista/{mercaderista_id}/routes")
def get_mercaderista_routes(
    mercaderista_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    mr_list = db.query(MercaderistaRuta).filter(
        MercaderistaRuta.mercaderista_id == mercaderista_id
    ).all()
    result = []
    for mr in mr_list:
        ruta = db.query(Ruta).filter(Ruta.id == mr.ruta_id).first()
        if ruta:
            result.append({
                "id": ruta.id,
                "nombre": ruta.nombre,
                "servicio": ruta.servicio,
                "activa": ruta.activa,
                "tipo_ruta": mr.tipo_ruta or "Variable",
            })
    return result


@router.post("/mercaderista/{mercaderista_id}/sync-routes")
def sync_routes(
    mercaderista_id: int,
    assignments: List[RouteAssignment],
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    merc = db.query(Mercaderista).filter(Mercaderista.id == mercaderista_id).first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")

    db.query(MercaderistaRuta).filter(
        MercaderistaRuta.mercaderista_id == mercaderista_id
    ).delete(synchronize_session=False)

    for a in assignments:
        ruta = db.query(Ruta).filter(Ruta.id == a.ruta_id).first()
        if ruta:
            mr = MercaderistaRuta(
                mercaderista_id=mercaderista_id,
                ruta_id=a.ruta_id,
                tipo_ruta=a.tipo_ruta,
            )
            db.add(mr)

    db.commit()
    return {"message": "Rutas sincronizadas correctamente"}


@router.post("/assign")
def assign_route_to_mercaderista(
    mercaderista_id: int,
    ruta_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    merc = db.query(Mercaderista).filter(Mercaderista.id == mercaderista_id).first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    ruta = db.query(Ruta).filter(Ruta.id == ruta_id).first()
    if not ruta:
        raise HTTPException(status_code=404, detail="Ruta no encontrada")
    existing = db.query(MercaderistaRuta).filter(
        MercaderistaRuta.mercaderista_id == mercaderista_id,
        MercaderistaRuta.ruta_id == ruta_id,
    ).first()
    if existing:
        return {"message": "Asignación ya existe"}
    mr = MercaderistaRuta(mercaderista_id=mercaderista_id, ruta_id=ruta_id)
    db.add(mr)
    db.commit()
    return {"message": "Ruta asignada exitosamente"}
