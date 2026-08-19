from sqlalchemy import select
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date
from app.db.session import get_db, get_async_db
from app.core.dependencies import get_current_user, require_admin
from app.models.user import Usuario
from app.models.mercaderista import Mercaderista, MercaderistaRuta
from app.models.foto import Foto, NotificacionRechazoFoto
from app.models.visita import Visita
from app.schemas.mercaderista import MercaderistaCreate, MercaderistaUpdate, MercaderistaResponse
from app.schemas.foto import FotoResponse, FotoMetadatosResponse
from app.services.photo_service import process_and_upload_photo

router = APIRouter(prefix="/api/merchandisers", tags=["Mercaderistas"])


@router.get("", response_model=List[MercaderistaResponse])
async def list_mercaderistas(
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(get_current_user),
):
    return (await db.execute(select(Mercaderista).filter(Mercaderista.activo == True).order_by(Mercaderista.nombre.asc()))).scalars().all()


@router.post("", response_model=MercaderistaResponse, status_code=201)
async def create_mercaderista(
    data: MercaderistaCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    existing = (await db.execute(select(Mercaderista).filter(Mercaderista.cedula == data.cedula))).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un mercaderista con esa cédula")
    merc = Mercaderista(**data.model_dump())
    db.add(merc)
    await db.commit()
    await db.refresh(merc)
    return merc


@router.get("/{mercaderista_id}", response_model=MercaderistaResponse)
async def get_mercaderista(
    mercaderista_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    merc = (await db.execute(select(Mercaderista).filter(Mercaderista.id == mercaderista_id))).scalars().first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    return merc


@router.patch("/{mercaderista_id}", response_model=MercaderistaResponse)
async def update_mercaderista(
    mercaderista_id: int,
    data: MercaderistaUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    merc = (await db.execute(select(Mercaderista).filter(Mercaderista.id == mercaderista_id))).scalars().first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    for key, value in data.model_dump(exclude_none=True).items():
        setattr(merc, key, value)
    await db.commit()
    await db.refresh(merc)
    return merc


@router.delete("/{mercaderista_id}")
async def delete_mercaderista(
    mercaderista_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(require_admin),
):
    merc = (await db.execute(select(Mercaderista).filter(Mercaderista.id == mercaderista_id))).scalars().first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    db.delete(merc)
    await db.commit()
    return {"message": "Mercaderista eliminado"}


@router.post("/upload-photo")
async def upload_photo(
    visita_id: int = Form(...),
    id_tipo_foto: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
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
    await db.commit()
    await db.refresh(foto)
    return {"id": foto.id, "blob_path": foto.blob_path, "estado": foto.estado}


@router.get("/{cedula}/active-points")
async def get_active_points(
    cedula: str,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    try:
        ced_int = int(str(cedula).strip())
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    merc = (await db.execute(select(Mercaderista).filter(Mercaderista.cedula == ced_int))).scalars().first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    today = date.today()
    visitas = (await db.execute(select(Visita).filter(
        Visita.mercaderista_id == merc.id,
        Visita.fecha == today,
    ))).scalars().all()
    return [{"visita_id": v.id, "punto_id": v.punto_id, "estado": v.estado} for v in visitas]


@router.get("/foto/{foto_id}/metadatos", response_model=FotoMetadatosResponse)
async def get_foto_metadatos(
    foto_id: int,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    foto = (await db.execute(select(Foto).filter(Foto.id == foto_id))).scalars().first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    return FotoMetadatosResponse(
        foto_id=foto.id,
        latitud=foto.latitud,
        longitud=foto.longitud,
        exif_timestamp=foto.exif_timestamp,
        camera_model=foto.camera_model,
    )
