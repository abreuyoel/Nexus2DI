from datetime import datetime
from typing import List, Optional, Any
from pydantic import BaseModel


class AuditorStatsResponse(BaseModel):
    cedula: str
    nombre: str
    visitas_hoy: int
    activaciones_hoy: int


class AuditorRouteResponse(BaseModel):
    id: int
    nombre: str
    activa: bool


class ActivarRutaRequest(BaseModel):
    ruta_id: int
    cedula: str


class DeactivarRutaRequest(BaseModel):
    ruta_id: int
    cedula: str


class AuditorCampoRutaResponse(BaseModel):
    id: int
    nombre: str
    total_puntos: int
    esta_activa: bool


class RutaPuntoResponse(BaseModel):
    id: str
    nombre: str
    prioridad: str
    total_clientes: int
    activado: bool


class ActivarRutaCampoRequest(BaseModel):
    id_ruta: int
    cedula: str


class NoActivarRutaCampoRequest(BaseModel):
    id_ruta: int
    cedula: str
    razon: str


class DesactivarRutaCampoRequest(BaseModel):
    id_ruta: int
    cedula: str


class PdvClienteResponse(BaseModel):
    id: int
    nombre: str
    prioridad: str


class ClienteCategoriaResponse(BaseModel):
    id: int
    nombre: str


class IniciarAuditoriaClienteRequest(BaseModel):
    cliente_id: int
    point_id: str
    cedula: str


class IniciarAuditoriaClienteResponse(BaseModel):
    success: bool
    id_visita: int


class GuardarAuditoriaCategoriaRequest(BaseModel):
    id_visita: int
    id_categoria: int
    aplico_planograma: Optional[Any] = None
    lineamiento_marca: Optional[Any] = None
    precio_correcto: Optional[Any] = None
    limpieza_correcta: Optional[Any] = None
    participacion_correcta: Optional[Any] = None
    fifo_correcto: Optional[Any] = None
    prox_vencer: Optional[Any] = None
    prox_vencer_cantidad: Optional[Any] = None
    prox_vencer_marca: Optional[str] = None
    prox_vencer_fecha1: Optional[str] = None
    prox_vencer_fecha2: Optional[str] = None
    competencia_actividad: Optional[Any] = None
    competencia_material_pop: Optional[Any] = None
    competencia_impulsadora: Optional[Any] = None
    pop_hablador: Optional[Any] = None
    pop_rompetrafico: Optional[Any] = None
    pop_otro: Optional[str] = None
    promo_nuestra: Optional[Any] = None
    promo_nuestra_desc: Optional[str] = None
    promo_competencia: Optional[Any] = None
    promo_competencia_desc: Optional[str] = None
    exhibicion_adicional: Optional[Any] = None
    exhibicion_tipos: Optional[str] = None


class FinalizarAuditoriaClienteRequest(BaseModel):
    id_visita: int


class AuditLogItemResponse(BaseModel):
    id: int
    timestamp: datetime
    user_id: Optional[int] = None
    username: Optional[str] = None
    rol: Optional[str] = None
    ip_address: Optional[str] = None
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    entity_name: Optional[str] = None
    changes: Optional[str] = None
    status: str


class AuditLogsPaginatedResponse(BaseModel):
    total: int
    offset: int
    limit: int
    items: List[AuditLogItemResponse]
