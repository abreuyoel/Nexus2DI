from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ClienteRutaBase(BaseModel):
    id_usuario: int
    id_ruta: int


class ClienteRutaCreate(ClienteRutaBase):
    activo: bool = True


class ClienteRutaUpdate(BaseModel):
    id_ruta: Optional[int] = None
    activo: Optional[bool] = None


class ClienteRutaResponse(BaseModel):
    id_cliente_ruta: int
    id_usuario: int
    id_ruta: int
    activo: bool
    fecha_creacion: Optional[datetime] = None
    ruta_nombre: Optional[str] = None
    usuario_username: Optional[str] = None

    class Config:
        from_attributes = True
