from pydantic import BaseModel
from typing import Optional

class CategoriaBase(BaseModel):
    nombre: str
    nombre_bi: Optional[str] = None
    id_departamento: Optional[int] = None

class CategoriaCreate(CategoriaBase):
    pass

class CategoriaUpdate(CategoriaBase):
    pass

class CategoriaResponse(CategoriaBase):
    id_categoria: int

    class Config:
        from_attributes = True


class SubCategoriaBase(BaseModel):
    nombre: str
    nombre_bi: Optional[str] = None
    id_categoria: Optional[int] = None

class SubCategoriaCreate(SubCategoriaBase):
    pass

class SubCategoriaUpdate(SubCategoriaBase):
    pass

class SubCategoriaResponse(SubCategoriaBase):
    id_subcategoria: int

    class Config:
        from_attributes = True


# ── Catálogo simple (dropdowns: marcas, productoras, presentaciones, departamentos)
class CatalogoSimple(BaseModel):
    id: int
    nombre: Optional[str] = None
    id_productora: Optional[int] = None  # solo aplica a marcas

    class Config:
        from_attributes = True


# ── Productos (snowflake: tabla PRODUCTOS)
class ProductoBase(BaseModel):
    producto_gu: str
    cod_prod: Optional[str] = None
    descripcion_bi: Optional[str] = None
    gramos: Optional[float] = None
    inagotable: Optional[bool] = False
    comentario: Optional[str] = None
    id_subcategoria: Optional[int] = None
    id_marca: Optional[int] = None
    id_presentacion: Optional[int] = None
    id_clasificacion_tamano: Optional[int] = None


class ProductoCreate(ProductoBase):
    pass


class ProductoUpdate(BaseModel):
    producto_gu: Optional[str] = None
    cod_prod: Optional[str] = None
    descripcion_bi: Optional[str] = None
    gramos: Optional[float] = None
    inagotable: Optional[bool] = None
    comentario: Optional[str] = None
    id_subcategoria: Optional[int] = None
    id_marca: Optional[int] = None
    id_presentacion: Optional[int] = None
    id_clasificacion_tamano: Optional[int] = None


class ProductoResponse(BaseModel):
    id: int
    producto_gu: Optional[str] = None
    cod_prod: Optional[str] = None
    descripcion_bi: Optional[str] = None
    gramos: Optional[float] = None
    inagotable: Optional[bool] = None
    comentario: Optional[str] = None
    id_subcategoria: Optional[int] = None
    subcategoria: Optional[str] = None
    id_categoria: Optional[int] = None
    categoria: Optional[str] = None
    id_marca: Optional[int] = None
    marca: Optional[str] = None
    fabricante: Optional[str] = None        # = productora
    id_presentacion: Optional[int] = None
    presentacion: Optional[str] = None
    id_departamento: Optional[int] = None
    departamento: Optional[str] = None
    id_clasificacion_tamano: Optional[int] = None
    tamano: Optional[str] = None


class ProductoListResponse(BaseModel):
    total: int
    pagina: int
    items: list[ProductoResponse]


# ── ABM de catálogos (departamentos, marcas, presentaciones) ──
class DepartamentoCreate(BaseModel):
    nombre: str

class DepartamentoUpdate(BaseModel):
    nombre: Optional[str] = None

class MarcaCreate(BaseModel):
    nombre: str
    id_productora: Optional[int] = None

class MarcaUpdate(BaseModel):
    nombre: Optional[str] = None
    id_productora: Optional[int] = None

class PresentacionCreate(BaseModel):
    nombre: str
    clasificacion_tamanos: Optional[str] = None

class PresentacionUpdate(BaseModel):
    nombre: Optional[str] = None
    clasificacion_tamanos: Optional[str] = None

class TamanoCreate(BaseModel):
    nombre: str

class TamanoUpdate(BaseModel):
    nombre: Optional[str] = None
