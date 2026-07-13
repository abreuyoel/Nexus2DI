from pydantic import BaseModel
from typing import Optional


class PuntoBase(BaseModel):
    id: Optional[str] = None
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    cadena: Optional[str] = None
    activo: bool = True


class PuntoResponse(PuntoBase):
    region: Optional[str] = None

    class Config:
        from_attributes = True
