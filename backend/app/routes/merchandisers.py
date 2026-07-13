from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import Usuario
from app.models.mercaderista import Mercaderista, MercaderistaRuta
from app.models.foto import Foto, NotificacionRechazoFoto
from app.models.visita import Visita
from app.schemas.mercaderista import MercaderistaCreate, MercaderistaUpdate, MercaderistaResponse
from app.schemas.foto import FotoResponse, FotoMetadatosResponse
from app.services.photo_service import process_and_upload_photo

router = APIRouter(prefix="/api/merchandisers", tags=["Mercaderistas"])


@router.get("/", response_model=List[MercaderistaResponse])
def list_mercaderistas(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return db.query(Mercaderista).filter(Mercaderista.activo == True).all()


@router.post("/", response_model=MercaderistaResponse, status_code=201)
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


@router.get("/{mercaderista_id}", response_model=MercaderistaResponse)
def get_mercaderista(
    mercaderista_id: int,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    merc = db.query(Mercaderista).filter(Mercaderista.id == mercaderista_id).first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    return merc


@router.patch("/{mercaderista_id}", response_model=MercaderistaResponse)
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


@router.delete("/{mercaderista_id}")
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


@router.post("/upload-photo")
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
    return {"id": foto.id, "blob_path": foto.blob_path, "estado": foto.estado}


@router.get("/{cedula}/active-points")
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


@router.get("/foto/{foto_id}/metadatos", response_model=FotoMetadatosResponse)
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
