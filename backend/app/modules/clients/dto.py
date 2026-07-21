from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


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


class CategoriaClienteBase(BaseModel):
    id_categoria: int
    id_cliente: int


class CategoriaClienteCreate(CategoriaClienteBase):
    pass


class CategoriaClienteResponse(CategoriaClienteBase):
    categoria_nombre: str
    cliente_nombre: str

    class Config:
        from_attributes = True


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
