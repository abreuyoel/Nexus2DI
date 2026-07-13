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
