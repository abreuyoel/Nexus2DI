from pydantic import BaseModel
from typing import Optional, List, Union


class JornadaActivaResponse(BaseModel):
    success: bool
    activa: bool
    id_jornada: Optional[int] = None
    fecha_inicio: Optional[str] = None
    visitas: int = 0


class ActivarJornadaResponse(BaseModel):
    success: bool
    id_jornada: int
    fecha_inicio: Optional[str] = None
    ya_activa: bool = False


class FinalizarJornadaResponse(BaseModel):
    success: bool
    message: str


class PdvSellerResponse(BaseModel):
    identificador: str
    nombre: Optional[str] = None
    direccion: Optional[str] = None
    ciudad: Optional[str] = None
    localidad: Optional[str] = None


class ClienteSellerResponse(BaseModel):
    id_cliente: int
    nombre: Optional[str] = None


class RegistrarVisitaSellerRequest(BaseModel):
    id_punto_interes: str
    id_cliente: int
    vendio: Union[bool, int, str]
    monto: Optional[Union[float, str]] = None
    razon_no_venta: Optional[str] = None
    latitud: Optional[Union[float, str]] = None
    longitud: Optional[Union[float, str]] = None


class RegistrarVisitaSellerResponse(BaseModel):
    success: bool
    message: str
    visitas: int


class VisitaSellerItem(BaseModel):
    fecha_hora: Optional[str] = None
    vendio: bool
    monto: Optional[float] = None
    razon_no_venta: Optional[str] = None
    pdv: Optional[str] = None
    cliente: Optional[str] = None


class VisitasHoySellerResponse(BaseModel):
    success: bool
    visitas: List[VisitaSellerItem] = []


class SolicitarPdvSellerRequest(BaseModel):
    punto_de_interes: str
    rif: str
    direccion: str
    foto_tienda: str
    foto_rif: str
    latitud: Optional[Union[float, str]] = None
    longitud: Optional[Union[float, str]] = None


class SolicitarPdvSellerResponse(BaseModel):
    success: bool
    message: str
