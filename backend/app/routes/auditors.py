from sqlalchemy import select, func, delete as sa_delete
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date
from app.db.session import get_async_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.models.mercaderista import Mercaderista, MercaderistaRuta
from app.models.visita import Visita
from app.models.ruta import Ruta, RutaActivada
from app.models.activacion import Activacion
from app.models.foto import Foto
from app.services.photo_service import process_and_upload_photo

router = APIRouter(prefix="/api/auditor", tags=["Auditor"])


@router.get("/stats/{cedula}")
async def get_auditor_stats(
    cedula: str,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    try:
        ced_int = int(str(cedula).strip())
    except (ValueError, TypeError):
        raise HTTPException(status_code=404, detail="Auditor no encontrado")
    merc = (await db.execute(select(Mercaderista).filter(Mercaderista.cedula == ced_int, Mercaderista.tipo == "Auditor"))).scalars().first()
    if not merc:
        raise HTTPException(status_code=404, detail="Auditor no encontrado")
    today = date.today()
    visitas_hoy = (await db.execute(
        select(func.count(Visita.id)).filter(
            Visita.mercaderista_id == merc.id,
            Visita.fecha == today,
        )
    )).scalar() or 0
    activaciones_hoy = (await db.execute(
        select(func.count(Activacion.id)).filter(
            Activacion.mercaderista_id == merc.id,
            Activacion.fecha == today,
        )
    )).scalar() or 0
    return {
        "cedula": cedula,
        "nombre": merc.nombre_completo,
        "visitas_hoy": visitas_hoy,
        "activaciones_hoy": activaciones_hoy,
    }


@router.get("/routes/{cedula}")
async def get_auditor_routes(
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
    mr_list = (await db.execute(
        select(MercaderistaRuta).filter(
            MercaderistaRuta.mercaderista_id == merc.id,
            MercaderistaRuta.activo == True,
        )
    )).scalars().all()
    rutas = []
    for mr in mr_list:
        r = (await db.execute(select(Ruta).filter(Ruta.id == mr.ruta_id))).scalars().first()
        if r:
            rutas.append(r)
    return [{"id": r.id, "nombre": r.nombre, "activa": r.activa} for r in rutas if r]


@router.post("/activate-route")
async def activate_route(
    ruta_id: int,
    cedula: str,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    today = date.today()
    existing = (await db.execute(
        select(RutaActivada).filter(
            RutaActivada.ruta_id == ruta_id,
            RutaActivada.fecha == today,
            RutaActivada.mercaderista_cedula == cedula,
        )
    )).scalars().first()
    if existing:
        return {"message": "Ruta ya activada"}
    activacion = RutaActivada(ruta_id=ruta_id, fecha=today, mercaderista_cedula=cedula)
    db.add(activacion)
    await db.commit()
    return {"message": "Ruta activada exitosamente"}


@router.post("/deactivate-route")
async def deactivate_route(
    ruta_id: int,
    cedula: str,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    today = date.today()
    await db.execute(
        sa_delete(RutaActivada).where(
            RutaActivada.ruta_id == ruta_id,
            RutaActivada.fecha == today,
            RutaActivada.mercaderista_cedula == cedula,
        )
    )
    await db.commit()
    return {"message": "Ruta desactivada"}


@router.post("/upload-activation-photo")
async def upload_activation_photo(
    punto_id: int = Form(...),
    mercaderista_cedula: str = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    file_bytes = await file.read()
    result = process_and_upload_photo(file_bytes, file.content_type or "image/jpeg", prefix="activaciones")
    return {"blob_path": result["blob_path"], "url": result["url"], "message": "Foto de activación subida"}


@router.post("/save-data")
async def save_auditor_data(
    data: dict,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    return {"message": "Datos guardados", "data": data}
