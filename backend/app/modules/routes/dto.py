from pydantic import BaseModel
from typing import Optional, List
from datetime import date, datetime
from app.modules.clients.dto import ClienteResponse


class PuntoBase(BaseModel):
    id: Optional[str] = None
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    cadena: Optional[str] = None
    activo: bool = True


class PuntoResponse(PuntoBase):
    region: Optional[str] = None

    class Config:
        from_attributes = True


class RutaBase(BaseModel):
    nombre: Optional[str] = None
    servicio: Optional[str] = None
    id_analista: Optional[int] = None
    coordinador_1: Optional[str] = None
    coordinador_2: Optional[str] = None
    supervisor: Optional[str] = None
    cuadrante: Optional[str] = None


class RutaCreate(RutaBase):
    tipo: str
    id_cliente_exclusivo: Optional[int] = None


class RutaUpdate(BaseModel):
    nombre: Optional[str] = None
    servicio: Optional[str] = None
    id_analista: Optional[int] = None
    coordinador_1: Optional[str] = None
    coordinador_2: Optional[str] = None
    cuadrante: Optional[str] = None
    id_cliente_exclusivo: Optional[int] = None


class RutaResponse(RutaBase):
    id: int
    activa: bool = True
    id_cliente_exclusivo: Optional[int] = None
    puntos_count: int = 0
    region: Optional[str] = None
    clientes: List[str] = []
    cliente_exclusivo_nombre: Optional[str] = None

    class Config:
        from_attributes = True


class RutaProgramacionBase(BaseModel):
    ruta_id: int
    punto_id: Optional[str] = None
    dia: Optional[str] = None
    activo: bool = True
    id_cliente: Optional[int] = None
    prioridad: Optional[str] = None


class RutaProgramacionCreate(RutaProgramacionBase):
    pass


class RutaProgramacionResponse(RutaProgramacionBase):
    id: int
    punto: Optional[PuntoResponse] = None
    cliente: Optional[ClienteResponse] = None

    class Config:
        from_attributes = True


class CambioFuturoResponse(BaseModel):
    id: int
    ruta_id: int
    id_programacion: Optional[int] = None
    punto_interes_nombre: Optional[str] = None
    cliente_nombre: Optional[str] = None
    dia: Optional[str] = None
    prioridad: Optional[str] = None
    tipo_cambio: Optional[str] = None
    fecha_ejecucion: Optional[date] = None
    estado: Optional[str] = None
    observaciones: Optional[str] = None
    creado_por: Optional[str] = None

    class Config:
        from_attributes = True


class AddPointToRouteRequest(BaseModel):
    punto_id: str
    client_id: int
    dia: str
    priority: str


class UpdatePointsRequest(BaseModel):
    puntos: List[dict]


class BulkInsert(BaseModel):
    point_id: str
    client_id: int
    dia: str
    prioridad: str


class BulkUpdate(BaseModel):
    programacion_id: int
    dia: str
    prioridad: str


class BulkDelete(BaseModel):
    programacion_id: int


class BulkApplyRequest(BaseModel):
    inserts: List[BulkInsert] = []
    updates: List[BulkUpdate] = []
    deletes: List[BulkDelete] = []


class ScheduleChangeRequest(BaseModel):
    id_programacion: Optional[int] = None
    id_punto_interes: Optional[str] = None
    punto_interes_nombre: Optional[str] = None
    id_cliente: Optional[int] = None
    cliente_nombre: Optional[str] = None
    dia: Optional[str] = None
    prioridad: Optional[str] = None
    tipo_cambio: str = "modificacion"
    fecha_ejecucion: date
    observaciones: Optional[str] = None


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


class UsuarioClienteRutaItem(BaseModel):
    id_usuario: int
    username: str
    id_cliente: Optional[int] = None
    cliente: Optional[str] = None
    n_rutas: int = 0


class RutaDisponibleItem(BaseModel):
    id_ruta: int
    ruta: Optional[str] = None
    pdvs: int = 0
    asignada: bool = False
    id_cliente_ruta: Optional[int] = None


class RutasDisponiblesClienteResponse(BaseModel):
    id_cliente: int
    rutas: List[RutaDisponibleItem] = []
