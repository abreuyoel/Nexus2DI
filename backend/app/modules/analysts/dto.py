from pydantic import BaseModel
from typing import Optional


class AnalistaBase(BaseModel):
    nombre: str
    id_rol: Optional[int] = 2


class AnalistaCreate(AnalistaBase):
    pass


class AnalistaUpdate(BaseModel):
    nombre: Optional[str] = None
    id_rol: Optional[int] = None


class AnalistaResponse(AnalistaBase):
    id: int

    class Config:
        from_attributes = True
