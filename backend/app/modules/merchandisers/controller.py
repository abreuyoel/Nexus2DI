from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from datetime import date
from pydantic import BaseModel
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_admin, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.routes.entities import Ruta
from app.modules.visits.entities import Foto, Visita
from app.modules.merchandisers.dto import MercaderistaCreate, MercaderistaUpdate, MercaderistaResponse
from app.modules.visits.dto import FotoMetadatosResponse
from app.shared.photo_service import process_and_upload_photo

router = APIRouter(tags=["Mercaderistas"])


class RouteAssignment(BaseModel):
    ruta_id: int
    tipo_ruta: str = "Variable"


@router.get("/api/merchandisers", response_model=List[MercaderistaResponse])
@router.get("/api/merchandisers/", response_model=List[MercaderistaResponse])
def list_mercaderistas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return db.query(Mercaderista).filter(Mercaderista.activo == True).all()


@router.post("/api/merchandisers", response_model=MercaderistaResponse, status_code=201)
@router.post("/api/merchandisers/", response_model=MercaderistaResponse, status_code=201)
def create_mercaderista(
    data: MercaderistaCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    existing = db.query(Mercaderista).filter(Mercaderista.cedula == data.cedula).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un mercaderista con esa cédula")
    merc = Mercaderista(**data.model_dump())
    db.add(merc)
    db.commit()
    db.refresh(merc)
    return merc


@router.get("/api/merchandisers/{mercaderista_id}", response_model=MercaderistaResponse)
def get_mercaderista(
    mercaderista_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    merc = db.query(Mercaderista).filter(Mercaderista.id == mercaderista_id).first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    return merc


@router.patch("/api/merchandisers/{mercaderista_id}", response_model=MercaderistaResponse)
def update_mercaderista(
    mercaderista_id: int,
    data: MercaderistaUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    merc = db.query(Mercaderista).filter(Mercaderista.id == mercaderista_id).first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(merc, key, value)
    db.commit()
    db.refresh(merc)
    return merc


@router.delete("/api/merchandisers/{mercaderista_id}")
def delete_mercaderista(
    mercaderista_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    merc = db.query(Mercaderista).filter(Mercaderista.id == mercaderista_id).first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    db.delete(merc)
    db.commit()
    return {"message": "Mercaderista eliminado"}


@router.post("/api/merchandisers/upload-photo")
async def upload_photo(
    visita_id: int = Form(...),
    id_tipo_foto: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    file_bytes = await file.read()
    result = process_and_upload_photo(file_bytes, file.content_type or "image/jpeg")

    foto = Foto(
        visita_id=visita_id,
        id_tipo_foto=id_tipo_foto,
        blob_path=result.get("blob_path"),
        estado="pendiente",
        latitud=result.get("latitud"),
        longitud=result.get("longitud"),
        exif_timestamp=result.get("timestamp"),
        camera_model=result.get("camera_model"),
    )
    db.add(foto)
    db.commit()
    db.refresh(foto)
    return {"id": foto.id, "blob_path": foto.blob_path, "estado": foto.state if hasattr(foto, 'state') else getattr(foto, 'estado', 'pendiente')}


@router.get("/api/merchandisers/{cedula}/active-points")
def get_active_points(
    cedula: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    merc = db.query(Mercaderista).filter(Mercaderista.cedula == cedula).first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    today = date.today()
    visitas = db.query(Visita).filter(
        Visita.mercaderista_id == merc.id,
        Visita.fecha == today,
    ).all()
    return [{"visita_id": v.id, "punto_id": v.punto_id, "estado": v.estado} for v in visitas]


@router.get("/api/merchandisers/foto/{foto_id}/metadatos", response_model=FotoMetadatosResponse)
def get_foto_metadatos(
    foto_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    foto = db.query(Foto).filter(Foto.id == foto_id).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    return FotoMetadatosResponse(
        foto_id=foto.id,
        latitud=foto.latitud,
        longitud=foto.longitud,
        exif_timestamp=foto.exif_timestamp,
        camera_model=foto.camera_model,
    )


# ─── Mercaderista Rutas ──────────────────────────────────────────────────────

@router.get("/api/mercaderista-rutas")
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


@router.get("/api/mercaderista-rutas/mercaderista/{mercaderista_id}/routes")
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


@router.post("/api/mercaderista-rutas/mercaderista/{mercaderista_id}/sync-routes")
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


@router.post("/api/mercaderista-rutas/assign")
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
