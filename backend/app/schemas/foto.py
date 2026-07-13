from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class FotoResponse(BaseModel):
    id: int
    visita_id: Optional[int] = None
    id_tipo_foto: Optional[int] = None
    blob_path: Optional[str] = None
    url: Optional[str] = None
    estado: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    exif_timestamp: Optional[datetime] = None
    camera_model: Optional[str] = None
    fecha_registro: Optional[datetime] = None
    razones: Optional[List[str]] = None      # nombres de razones de rechazo
    razones_ids: Optional[List[int]] = None  # ids de razones de rechazo
    rechazado_por: Optional[int] = None       # id_usuario que rechazó
    rechazado_por_nombre: Optional[str] = None

    class Config:
        from_attributes = True


class ApprovePhotosRequest(BaseModel):
    foto_ids: List[int]


class RejectPhotoRequest(BaseModel):
    foto_id: int
    motivo: Optional[str] = None
    razones_ids: Optional[List[int]] = None  # varias razones por foto


class RejectReason(BaseModel):
    id: int
    razon: str


class SavePhotoDecisionsRequest(BaseModel):
    decisions: List[dict]


class NotificacionRechazoResponse(BaseModel):
    id: int
    foto_id: Optional[int] = None
    leida: Optional[bool] = None
    descripcion: Optional[str] = None
    fecha_notificacion: Optional[datetime] = None

    class Config:
        from_attributes = True


class FotoMetadatosResponse(BaseModel):
    foto_id: int
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    exif_timestamp: Optional[datetime] = None
    camera_model: Optional[str] = None
