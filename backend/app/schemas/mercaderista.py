from pydantic import BaseModel, field_validator
from typing import Optional, Union


class MercaderistaBase(BaseModel):
    cedula: Optional[Union[str, int]] = None
    nombre: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    tipo: Optional[str] = "Mercaderista"
    activo: bool = True

    @field_validator("cedula", mode="before")
    @classmethod
    def coerce_cedula_to_string(cls, v):
        if v is None:
            return None
        return str(v)


class MercaderistaCreate(MercaderistaBase):
    pass


class MercaderistaUpdate(BaseModel):
    nombre: Optional[str] = None
    email: Optional[str] = None
    telefono: Optional[str] = None
    tipo: Optional[str] = None
    activo: Optional[bool] = None


class MercaderistaResponse(MercaderistaBase):
    id: int
    nombre_completo: Optional[str] = None
    is_auditor: Optional[bool] = None

    class Config:
        from_attributes = True


class VerifyMercaderistaRequest(BaseModel):
    cedula: str
    password: str


class MercaderistaRutaResponse(BaseModel):
    id: int
    mercaderista_id: int
    ruta_id: int
    activo: bool

    class Config:
        from_attributes = True
