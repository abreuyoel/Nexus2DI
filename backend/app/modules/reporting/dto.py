from pydantic import BaseModel
from typing import List, Optional, Dict, Any


class PeriodoDto(BaseModel):
    inicio: str
    fin: str


class SummaryVisitasDto(BaseModel):
    total: int
    completadas: int
    pendientes: int
    porcentaje_completadas: float


class SummaryFotosDto(BaseModel):
    total: int
    aprobadas: int
    rechazadas: int
    pendientes: int


class ReportSummaryResponse(BaseModel):
    periodo: PeriodoDto
    visitas: SummaryVisitasDto
    fotos: SummaryFotosDto


class ChartDataResponse(BaseModel):
    labels: List[str]
    data: List[int]
    title: str


class ActivatedRouteItemResponse(BaseModel):
    ruta_id: int
    cedula: Optional[int] = None
    hora: Optional[str] = None


# Centro de Mando DTOs
class ClienteCentroMandoItem(BaseModel):
    id_cliente: int
    cliente: str


class ClienteCentroMandoResponse(BaseModel):
    success: bool
    clientes: List[ClienteCentroMandoItem] = []
    message: Optional[str] = None


class ResumenDiaKpis(BaseModel):
    total_asignados: int
    total_planificados: int
    cobertura_planificada_pct: float
    total_activos: int
    ejecucion_activa_pct: float
    pendientes: int


class ResumenDiaFiltrosAplicados(BaseModel):
    desde: str
    hasta: str
    cliente_id: Optional[int] = None
    dias_evaluados: List[str] = []


class ResumenDiaResponse(BaseModel):
    success: bool
    cliente_nombre: str
    filtros: ResumenDiaFiltrosAplicados
    kpis: ResumenDiaKpis
    message: Optional[str] = None


class DetalleMercaderistaItem(BaseModel):
    id_mercaderista: int
    nombre: str
    cedula: Optional[int] = None
    tipo_campo: Optional[str] = None
    tipo_servicio: Optional[str] = None
    planificado_hoy: bool = False
    planificados_total: int = 0
    activo_hoy: bool = False
    activos_total: int = 0
    rutas_activadas: int = 0
    n_clientes_asignados: int = 1
    ultima_activacion: Optional[str] = None
    estado_asistencia: str


class DetalleMercaderistasResponse(BaseModel):
    success: bool
    total: int
    mercaderistas: List[DetalleMercaderistaItem] = []
    message: Optional[str] = None


class PuntoFilterItem(BaseModel):
    id: str
    nombre: str


class FiltrosOpcionesResponse(BaseModel):
    success: bool
    cadenas: List[str] = []
    regiones: List[str] = []
    cuadrantes: List[str] = []
    puntos: List[PuntoFilterItem] = []
    message: Optional[str] = None


class FotoVisualizadorItem(BaseModel):
    id_foto: int
    visita_id: int
    fecha: Optional[str] = None
    blob_path: Optional[str] = None
    url: Optional[str] = None
    estado: Optional[str] = None
    tipo_nombre: Optional[str] = None
    pdv_nombre: Optional[str] = None
    cadena: Optional[str] = None
    region: Optional[str] = None
    mercaderista: Optional[str] = None


class FotosVisualizadorResponse(BaseModel):
    success: bool
    total: int
    fotos: List[FotoVisualizadorItem] = []
    message: Optional[str] = None
