from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.models.foto import Foto, NotificacionRechazoFoto
from app.schemas.foto import FotoResponse, NotificacionRechazoResponse
from app.services.photo_service import process_and_upload_photo
from app.services.audit_service import log_action

router = APIRouter(prefix="/api/supervisor", tags=["Supervisor"])


@router.get("/rejected-photos", response_model=List[FotoResponse])
def get_rejected_photos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("supervisor", "admin", "analyst"):
        raise HTTPException(status_code=403, detail="Acceso denegado")
    return db.query(Foto).filter(Foto.estado == "Rechazada").order_by(Foto.fecha_registro.desc()).all()


@router.post("/replace-photo")
async def replace_rejected_photo(
    foto_id: int = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if current_user.rol not in ("supervisor", "admin", "mercaderista"):
        raise HTTPException(status_code=403, detail="Acceso denegado")

    foto = db.query(Foto).filter(Foto.id == foto_id).first()
    if not foto:
        raise HTTPException(status_code=404, detail="Foto no encontrada")

    file_bytes = await file.read()
    result = process_and_upload_photo(file_bytes, file.content_type or "image/jpeg")

    old_path = foto.blob_path
    foto.blob_path = result.get("blob_path")
    foto.estado = "pendiente"
    foto.latitud = result.get("latitud")
    foto.longitud = result.get("longitud")
    foto.exif_timestamp = result.get("timestamp")
    foto.camera_model = result.get("camera_model")

    log_action(db, action="REPLACE_PHOTO", entity_type="Foto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               entity_id=foto.id,
               changes={"old_path": old_path, "new_path": foto.blob_path})
    db.commit()
    return {"message": "Foto reemplazada exitosamente", "foto_id": foto.id, "blob_path": foto.blob_path}


@router.get("/notifications", response_model=List[NotificacionRechazoResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    return db.query(NotificacionRechazoFoto).filter(
        NotificacionRechazoFoto.leida == False
    ).order_by(NotificacionRechazoFoto.fecha_notificacion.desc()).limit(50).all()
