from pydantic import BaseModel, field_validator
from typing import List, Optional, Union, Dict, Any
from datetime import datetime


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


# Portal DTOs
class MiPerfilRutaItem(BaseModel):
    id_ruta: int
    tipo: Optional[str] = None


class MiPerfilResponse(BaseModel):
    id: int
    nombre: str
    cedula: Union[str, int]
    email: Optional[str] = None
    telefono: Optional[str] = None
    rutas: List[MiPerfilRutaItem] = []


class RutaItemResponse(BaseModel):
    id_ruta: int
    tipo: Optional[str] = None
    nombre: Optional[str] = None


class PdvPuntoItem(BaseModel):
    id_punto: str
    nombre: Optional[str] = None
    id_cliente: Optional[int] = None
    cliente: Optional[str] = None
    id_ruta: Optional[int] = None
    cadena: Optional[str] = None
    region: Optional[str] = None
    direccion: Optional[str] = None
    tipo_ruta: Optional[str] = None
    prioridad: Optional[int] = None
    tiene_coords: bool = False
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    visita_id: Optional[int] = None
    visitado: bool = False
    estado: Optional[str] = None
    estado_data: Optional[str] = None


class MiRutaResponse(BaseModel):
    dia: str
    fecha: str
    rutas: List[RutaItemResponse] = []
    pdvs: List[PdvPuntoItem] = []


class MiVisitaResponse(BaseModel):
    id_visita: int
    fecha: Optional[str] = None
    estado: Optional[str] = None
    estado_data: Optional[str] = None
    pdv_nombre: Optional[str] = None
    cadena: Optional[str] = None
    region: Optional[str] = None
    cliente: Optional[str] = None
    id_cliente: Optional[int] = None
    observaciones: Optional[str] = None
    fotos_count: int = 0
    balances_count: int = 0


class IniciarVisitaRequest(BaseModel):
    id_punto: str
    id_cliente: int


class IniciarVisitaResponse(BaseModel):
    id_visita: int
    nueva: bool


class FotoItemResponse(BaseModel):
    id_foto: int
    estado: Optional[str] = None
    fecha: Optional[str] = None
    url: Optional[str] = None


class FotoTipoGroupResponse(BaseModel):
    codigo: str
    label: str
    solo_camara: bool
    fotos: List[FotoItemResponse] = []


class FotosVisitaResponse(BaseModel):
    visita_id: int
    tipos: List[FotoTipoGroupResponse] = []


class ProductoClienteResponse(BaseModel):
    id: int
    sku: Optional[str] = None
    fabricante: Optional[str] = None
    categoria: Optional[str] = None


class BalanceItemCreate(BaseModel):
    sku: Optional[str] = ""
    fabricante: Optional[str] = ""
    categoria: Optional[str] = ""
    inv_inicial: Optional[int] = 0
    inv_final: Optional[int] = 0
    inv_deposito: Optional[int] = 0
    caras: Optional[int] = 0
    precio_bs: Optional[float] = 0.0
    precio_ds: Optional[float] = 0.0
    fifo: Optional[str] = None


class GuardarBalancesRequest(BaseModel):
    visita_id: int
    id_cliente: Optional[int] = None
    productos: List[BalanceItemCreate]


class ChatInboxItemResponse(BaseModel):
    id_visita: int
    fecha: Optional[str] = None
    estado: Optional[str] = None
    pdv_nombre: Optional[str] = None
    cliente: Optional[str] = None
    total_msgs: int = 0
    ultimo_msg: Optional[str] = None
    ultimo_at: Optional[str] = None
    no_leidos: int = 0
