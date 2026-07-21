from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.modules.merchandisers.dto import MercaderistaResponse
from app.modules.clients.dto import ClienteResponse
from app.modules.routes.dto import PuntoResponse


class VisitaBase(BaseModel):
    mercaderista_id: Optional[int] = None
    punto_id: Optional[str] = None
    ruta_id: Optional[int] = None
    id_cliente: Optional[int] = None
    fecha: Optional[date] = None
    estado: Optional[str] = "Pendiente"
    tipo_visita: Optional[str] = None


class VisitaCreate(VisitaBase):
    pass


class VisitaUpdate(BaseModel):
    estado: Optional[str] = None
    tipo_visita: Optional[str] = None


class VisitaResponse(VisitaBase):
    id: int
    punto: Optional[PuntoResponse] = None
    mercaderista: Optional[MercaderistaResponse] = None
    cliente: Optional[ClienteResponse] = None

    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    id: int
    id_cliente: Optional[int] = None
    fecha_balance: Optional[date] = None
    identificador_pdv: Optional[str] = None
    mercaderista: Optional[str] = None
    producto: Optional[str] = None
    categoria: Optional[str] = None
    fabricante: Optional[str] = None
    inv_inicial: Optional[float] = None
    inv_final: Optional[float] = None
    inv_deposito: Optional[float] = None
    caras: Optional[int] = None
    precio_bs: Optional[float] = None
    precio_ds: Optional[float] = None
    visita_id: Optional[int] = None

    class Config:
        from_attributes = True


class UpdateBalanceItem(BaseModel):
    id_balance: int
    inv_inicial: Optional[float] = None
    inv_final: Optional[float] = None
    inv_deposito: Optional[float] = None
    caras: Optional[int] = None
    precio_bs: Optional[float] = None
    precio_ds: Optional[float] = None


class UpdateBalancesRequest(BaseModel):
    visita_id: int
    balances: List[UpdateBalanceItem]


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
    razones: Optional[List[str]] = None
    razones_ids: Optional[List[int]] = None
    rechazado_por: Optional[int] = None
    rechazado_por_nombre: Optional[str] = None
    motivo_rechazo: Optional[str] = None
    revisada_por: Optional[str] = None
    fecha_revision: Optional[datetime] = None
    comentario: Optional[str] = None
    ultimo_rechazo_por: Optional[str] = None
    ultima_fecha_rechazo: Optional[datetime] = None
    mercaderista_nombre: Optional[str] = None
    mercaderista_cedula: Optional[str] = None
    fecha_visita: Optional[datetime] = None

    class Config:
        from_attributes = True


class ApprovePhotosRequest(BaseModel):
    foto_ids: List[int]


class RejectPhotoRequest(BaseModel):
    foto_id: int
    motivo: Optional[str] = None
    razones_ids: Optional[List[int]] = None


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


class VisitaPaginatedResponse(BaseModel):
    items: List[VisitaResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class RejectedPhotosPaginatedResponse(BaseModel):
    items: List[FotoResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class FotoMetadatosResponse(BaseModel):
    foto_id: int
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    exif_timestamp: Optional[datetime] = None
    camera_model: Optional[str] = None
