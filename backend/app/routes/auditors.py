from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
from app.db.session import get_db
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
def get_auditor_stats(
    cedula: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    merc = db.query(Mercaderista).filter(Mercaderista.cedula == cedula, Mercaderista.tipo == "Auditor").first()
    if not merc:
        raise HTTPException(status_code=404, detail="Auditor no encontrado")
    today = date.today()
    visitas_hoy = db.query(Visita).filter(
        Visita.mercaderista_id == merc.id,
        Visita.fecha == today,
    ).count()
    activaciones_hoy = db.query(Activacion).filter(
        Activacion.mercaderista_id == merc.id,
        Activacion.fecha == today,
    ).count()
    return {
        "cedula": cedula,
        "nombre": merc.nombre_completo,
        "visitas_hoy": visitas_hoy,
        "activaciones_hoy": activaciones_hoy,
    }


@router.get("/routes/{cedula}")
def get_auditor_routes(
    cedula: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    merc = db.query(Mercaderista).filter(Mercaderista.cedula == cedula).first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    mr_list = db.query(MercaderistaRuta).filter(
        MercaderistaRuta.mercaderista_id == merc.id,
        MercaderistaRuta.activo == True,
    ).all()
    rutas = [db.query(Ruta).get(mr.ruta_id) for mr in mr_list]
    return [{"id": r.id, "nombre": r.nombre, "activa": r.activa} for r in rutas if r]


@router.post("/activate-route")
def activate_route(
    ruta_id: int,
    cedula: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    today = date.today()
    existing = db.query(RutaActivada).filter(
        RutaActivada.ruta_id == ruta_id,
        RutaActivada.fecha == today,
        RutaActivada.mercaderista_cedula == cedula,
    ).first()
    if existing:
        return {"message": "Ruta ya activada"}
    activacion = RutaActivada(ruta_id=ruta_id, fecha=today, mercaderista_cedula=cedula)
    db.add(activacion)
    db.commit()
    return {"message": "Ruta activada exitosamente"}


@router.post("/deactivate-route")
def deactivate_route(
    ruta_id: int,
    cedula: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    today = date.today()
    db.query(RutaActivada).filter(
        RutaActivada.ruta_id == ruta_id,
        RutaActivada.fecha == today,
        RutaActivada.mercaderista_cedula == cedula,
    ).delete()
    db.commit()
    return {"message": "Ruta desactivada"}


@router.post("/upload-activation-photo")
async def upload_activation_photo(
    punto_id: int = Form(...),
    mercaderista_cedula: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    file_bytes = await file.read()
    result = process_and_upload_photo(file_bytes, file.content_type or "image/jpeg", prefix="activaciones")
    return {"blob_path": result["blob_path"], "url": result["url"], "message": "Foto de activación subida"}


@router.post("/save-data")
def save_auditor_data(
    data: dict,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    return {"message": "Datos guardados", "data": data}
