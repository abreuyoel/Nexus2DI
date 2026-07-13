from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class HorasPromedioEjecucionBase(BaseModel):
    id_cliente: int
    id_tipo_negocio: int
    minutos_promedio: int


class HorasPromedioEjecucionCreate(HorasPromedioEjecucionBase):
    pass


class HorasPromedioEjecucionUpdate(BaseModel):
    id_cliente: Optional[int] = None
    id_tipo_negocio: Optional[int] = None
    minutos_promedio: Optional[int] = None


class HorasPromedioEjecucionResponse(HorasPromedioEjecucionBase):
    id: int
    fecha_creado: Optional[datetime] = None
    fecha_modificado: Optional[datetime] = None
    id_usuario_creador: Optional[int] = None
    id_usuario_modificador: Optional[int] = None
    cliente_nombre: Optional[str] = None
    tipo_negocio_nombre: Optional[str] = None
    usuario_creador_username: Optional[str] = None
    usuario_modificador_username: Optional[str] = None

    class Config:
        from_attributes = True
