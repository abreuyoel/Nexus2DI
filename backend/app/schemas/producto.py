from pydantic import BaseModel
from typing import Optional


class CategoriaResponse(BaseModel):
    id: int
    nombre: Optional[str] = None

    class Config:
        from_attributes = True


class ProductoBase(BaseModel):
    nombre: str  # SKU - Requerido
    categoria: Optional[str] = None
    fabricante: Optional[str] = None
    id_fabricante: Optional[int] = None
    tipo_servicio: Optional[str] = None
    tipo_fabricante: Optional[str] = None
    cod_bar: Optional[str] = None
    inagotable: Optional[bool] = False


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    nombre: Optional[str] = None
    categoria: Optional[str] = None
    fabricante: Optional[str] = None
    id_fabricante: Optional[int] = None
    tipo_servicio: Optional[str] = None
    tipo_fabricante: Optional[str] = None
    cod_bar: Optional[str] = None
    inagotable: Optional[bool] = None


class ProductoResponse(ProductoBase):
    id: int

    class Config:
        from_attributes = True


class ProductoListResponse(BaseModel):
    total: int
    pagina: int
    items: list["ProductoResponse"]
