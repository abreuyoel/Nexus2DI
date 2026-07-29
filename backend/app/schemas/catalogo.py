from pydantic import BaseModel, Field
from typing import Optional


class CatalogoBase(BaseModel):
    nombre: str = Field(..., min_length=1, max_length=200)
    activo: bool = True


class CatalogoCreate(CatalogoBase):
    pass


class CatalogoUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    activo: Optional[bool] = None


class CatalogoResponse(CatalogoBase):
    id: int

    class Config:
        from_attributes = True


# Servicio — extiende con prefijo (sigla usada en el correlativo de rutas)
class ServicioCreate(CatalogoBase):
    prefijo: str = Field(..., min_length=1, max_length=10)


class ServicioUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    prefijo: Optional[str] = Field(None, min_length=1, max_length=10)
    activo: Optional[bool] = None


class ServicioResponse(CatalogoBase):
    id: int
    prefijo: Optional[str] = None

    class Config:
        from_attributes = True


# Ciudad — extiende con departamento_id
class CiudadCreate(CatalogoBase):
    departamento_id: int


class CiudadUpdate(BaseModel):
    nombre: Optional[str] = Field(None, min_length=1, max_length=200)
    departamento_id: Optional[int] = None
    activo: Optional[bool] = None


class CiudadResponse(CatalogoBase):
    id: int
    departamento_id: int
    departamento_nombre: Optional[str] = None

    class Config:
        from_attributes = True
