from pydantic import BaseModel
from typing import List

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
