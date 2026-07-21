from pydantic import BaseModel
from typing import Optional, List, Any, Dict
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


class AsignacionCategoria(BaseModel):
    id_categoria: int


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


class ExclusiveClientResponse(BaseModel):
    id_cliente: int
    cliente: str
    id_tipo_cliente: Optional[int] = None


class ClientDashboardResponse(BaseModel):
    has_dashboard: bool
    url_html: Optional[str] = None
    tipo: Optional[str] = None


class ClientSummaryResponse(BaseModel):
    recent_visits: int
    recent_photos: int
    recent_messages: int
    period: str = "Últimos 30 días"


class RegionItemResponse(BaseModel):
    region: str


class ChainItemResponse(BaseModel):
    cadena: str


class PointItemResponse(BaseModel):
    identificador: str
    punto_de_interes: str
    cadena: str
    direccion: str
    ciudad: str


class UsuarioClienteRutaItem(BaseModel):
    id_usuario: int
    username: str
    id_cliente: Optional[int] = None
    cliente: Optional[str] = None
    n_rutas: int = 0


class RutaDisponibleItem(BaseModel):
    id_ruta: int
    ruta: str
    pdvs: int = 0
    asignada: bool = False
    id_cliente_ruta: Optional[int] = None


class RutasDisponiblesClienteResponse(BaseModel):
    id_cliente: int
    rutas: List[RutaDisponibleItem]


class PdvItem(BaseModel):
    id: str
    nombre: str


class ClientDataFiltersResponse(BaseModel):
    productos: List[str]
    mercaderistas: List[str]
    pdvs: List[PdvItem]
    cadenas: List[str]
    regiones: List[str]
    categorias: List[str]
    departamentos: List[str]
    cuadrantes: List[str]
    estados: List[str]


class BalanceItemResponse(BaseModel):
    id_balance: int
    fecha_balance: Optional[str] = None
    visita_id: Optional[int] = None
    region: Optional[str] = None
    cadena: Optional[str] = None
    pdv_nombre: Optional[str] = None
    departamento: Optional[str] = None
    cuadrante: Optional[str] = None
    estado: Optional[str] = None
    mercaderista: Optional[str] = None
    producto: Optional[str] = None
    categoria: Optional[str] = None
    inv_inicial: Optional[float] = None
    inv_final: Optional[float] = None
    inv_deposito: Optional[float] = None
    caras: Optional[int] = None
    precio_bs: Optional[float] = None
    precio_ds: Optional[float] = None


class VisitaItemResponse(BaseModel):
    id_visita: int
    fecha_visita: Optional[str] = None
    mercaderista: str = ""
    punto_id: Optional[str] = None
    punto_nombre: str = ""
    departamento: str = ""
    ciudad: str = ""
    ruta: str = ""
    cadena: str = ""
    cliente_nombre: str = ""
    total_fotos: int = 0
    preview_foto: Optional[str] = None
    fotos_por_categoria: Dict[str, List[Any]] = {}


class FiltrosResponse(BaseModel):
    rutas: List[str] = []
    cadenas: List[str] = []
    puntos: List[Any] = []


class MisVisitasPaginatedResponse(BaseModel):
    success: bool = True
    fecha_inicio: str = ""
    fecha_fin: str = ""
    es_hoy: bool = False
    visitas: List[VisitaItemResponse] = []
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0
    filtros: FiltrosResponse = FiltrosResponse()
