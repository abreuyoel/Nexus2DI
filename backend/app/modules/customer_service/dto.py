from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class SolicitudBase(BaseModel):
    tipo: str
    descripcion: Optional[str] = None


class SolicitudCreate(SolicitudBase):
    pass


class SolicitudUpdate(BaseModel):
    estado: Optional[str] = None
    respuesta: Optional[str] = None


class SolicitudResponse(SolicitudBase):
    id: int
    user_id: Optional[int] = None
    estado: str
    respuesta: Optional[str] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AprobarSolicitudRequest(BaseModel):
    completar: Optional[Dict[str, Any]] = None
