from pydantic import BaseModel
from typing import Optional, List


class UsuarioBase(BaseModel):
    username: str
    email: Optional[str] = None
    id_rol: Optional[int] = None
    id_perfil: Optional[int] = None
    activo: Optional[bool] = True


class UsuarioCreate(UsuarioBase):
    password: str


class UsuarioUpdate(BaseModel):
    email: Optional[str] = None
    id_rol: Optional[int] = None
    id_perfil: Optional[int] = None
    activo: Optional[bool] = None


class PermissionResponse(BaseModel):
    id: int
    module: str
    can_read: bool
    can_write: bool
    can_delete: bool
    can_see_all: bool

    class Config:
        from_attributes = True


class UpdatePermissionsRequest(BaseModel):
    permissions: List[dict]


class UsuarioResponse(UsuarioBase):
    id: int
    rol: Optional[str] = None
    rol_nombre: Optional[str] = None
    perfil_nombre: Optional[str] = None
    permisos: List[PermissionResponse] = []

    class Config:
        from_attributes = True


class UsuarioCurrentResponse(BaseModel):
    id: int
    username: str
    rol: str
    rol_nombre: Optional[str] = None
    email: Optional[str] = None
    id_rol: Optional[int] = None
    id_perfil: Optional[int] = None
    is_admin: bool
    is_analyst: bool
    is_supervisor: bool
    is_client: bool
    is_mercaderista: bool
    is_coordinador_exclusivo: bool
    is_coordinador_tradex: bool
    permisos: List[PermissionResponse] = []

    class Config:
        from_attributes = True
