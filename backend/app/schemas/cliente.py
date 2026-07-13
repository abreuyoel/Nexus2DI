from pydantic import BaseModel
from typing import Optional


class ClienteBase(BaseModel):
    nombre: Optional[str] = None
    activo: bool = True


class ClienteCreate(ClienteBase):
    pass


class ClienteUpdate(BaseModel):
    nombre: Optional[str] = None
    activo: Optional[bool] = None


class ClienteResponse(ClienteBase):
    id: int

    class Config:
        from_attributes = True


class PuntoInteresBase(BaseModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    departamento: Optional[str] = None
    ciudad: Optional[str] = None
    cadena: Optional[str] = None
    jerarquia_n2: Optional[str] = None
    jerarquia_n2_2: Optional[str] = None
    nivel_de_alcance: Optional[str] = None
    latitud: Optional[str] = None
    longitud: Optional[str] = None
    rif: Optional[str] = None
    radio: Optional[str] = None


class PuntoInteresCreate(PuntoInteresBase):
    id: str


class PuntoInteresUpdate(BaseModel):
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    departamento: Optional[str] = None
    ciudad: Optional[str] = None
    cadena: Optional[str] = None
    jerarquia_n2: Optional[str] = None
    jerarquia_n2_2: Optional[str] = None
    nivel_de_alcance: Optional[str] = None
    latitud: Optional[str] = None
    longitud: Optional[str] = None
    rif: Optional[str] = None
    radio: Optional[str] = None


class PuntoInteresResponse(PuntoInteresBase):
    id: str
    fecha_creado: Optional[str] = None

    class Config:
        from_attributes = True
