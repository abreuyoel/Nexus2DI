from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class FrecuenciaPdvClienteBase(BaseModel):
    id_cliente: int
    id_punto_interes: str
    frecuencia_semanal: float
    observaciones: Optional[str] = None
    activo: bool = True


class FrecuenciaPdvClienteCreate(FrecuenciaPdvClienteBase):
    pass


class FrecuenciaPdvClienteUpdate(BaseModel):
    id_cliente: Optional[int] = None
    id_punto_interes: Optional[str] = None
    frecuencia_semanal: Optional[float] = None
    observaciones: Optional[str] = None
    activo: Optional[bool] = None


class FrecuenciaPdvClienteResponse(FrecuenciaPdvClienteBase):
    id: int
    fecha_creacion: Optional[datetime] = None
    fecha_modificacion: Optional[datetime] = None
    id_usuario: Optional[int] = None
    cliente_nombre: Optional[str] = None
    pdv_nombre: Optional[str] = None
    usuario_username: Optional[str] = None

    class Config:
        from_attributes = True


class FrecuenciaBulkItem(BaseModel):
    id_punto_interes: str
    frecuencia_semanal: float
    observaciones: Optional[str] = None


class FrecuenciaBulkCreate(BaseModel):
    id_cliente: int
    items: List[FrecuenciaBulkItem]


class PdvDisponibleClienteResponse(BaseModel):
    id_punto_interes: str
    pdv_nombre: str
    id_frecuencia: Optional[int] = None
    frecuencia_semanal: Optional[float] = None
    observaciones: Optional[str] = None


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
