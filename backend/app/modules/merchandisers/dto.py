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
    mercaderista_nombre: Optional[str] = None


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
    prioridad: Optional[Union[str, int]] = None
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
    total: int = 0
    page: int = 1
    per_page: int = 20
    total_pages: int = 0


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
    estado_producto: Optional[str] = "normal"
    no_existe: bool = False


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


# ═══════════════════════════════════════════════════════════════════════════════
# DTOs f354ea2 — RUTAS / PROGRAMACIÓN / PDV ACTIVOS
# ═══════════════════════════════════════════════════════════════════════════════


class RutaAsignadaItem(BaseModel):
    """Ruta asignada al mercaderista."""
    id_ruta: int
    tipo: Optional[str] = None
    nombre: Optional[str] = None


class ClienteEnPdvItem(BaseModel):
    """Cliente programado en un PDV."""
    id_cliente: int
    nombre: str
    visitado: bool = False
    id_visita: Optional[int] = None


class PdvEnRutaItem(BaseModel):
    """PDV programado en una ruta del día."""
    id_punto: str
    nombre: str
    cadena: Optional[str] = None
    direccion: Optional[str] = None
    latitud: Optional[str] = None
    longitud: Optional[str] = None
    prioridad: Optional[str] = None
    id_ruta: int
    ruta_nombre: Optional[str] = None
    clientes: List[ClienteEnPdvItem] = []


class RutaDelDiaItem(BaseModel):
    """Ruta del día con sus PDVs."""
    id_ruta: int
    tipo: Optional[str] = None
    nombre: Optional[str] = None
    pdvs: List[PdvEnRutaItem] = []
    activada: bool = False
    finalizada: bool = False


class MisRutasResponse(BaseModel):
    """Respuesta completa de rutas del mercaderista para hoy."""
    mercaderista_id: int
    dia_semana: str
    fecha: str
    rutas_fijas: List[RutaDelDiaItem] = []
    rutas_variables: List[RutaDelDiaItem] = []


class ProgramacionProducto(BaseModel):
    """Producto en el catálogo para la programación."""
    id_producto: int
    sku: Optional[str] = None
    nombre: Optional[str] = None
    fabricante: Optional[str] = None
    categoria_id: Optional[int] = None
    categoria_nombre: Optional[str] = None
    precio_base_bs: Optional[float] = None
    precio_base_ds: Optional[float] = None


class ProgramacionMercaderista(BaseModel):
    """Datos del mercaderista en la programación."""
    id: int
    nombre: str
    cedula: str


class ProgramacionResponse(BaseModel):
    """Programación completa del día: rutas + productos en una sola llamada."""
    fecha: str
    dia_semana: str
    mercaderista: ProgramacionMercaderista
    rutas_fijas: List[RutaDelDiaItem] = []
    rutas_variables: List[RutaDelDiaItem] = []
    productos: List[ProgramacionProducto] = []


class PdvActivoResponse(BaseModel):
    """PDV con trabajo pendiente hoy."""
    punto_id: str
    punto_nombre: str
    ruta_id: Optional[int] = None
    ruta_nombre: Optional[str] = None
    clientes_pendientes: List[str] = []
    clientes_listos: List[str] = []
    falta_desactivacion: bool = False
    ultima_visita_local_id: Optional[int] = None
    ultima_visita_cliente_id: Optional[int] = None
    ultima_visita_cliente_nombre: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# DTOs f354ea2 — VISITAS (historial / detalle / balances)
# ═══════════════════════════════════════════════════════════════════════════════


class VisitaHistorialItem(BaseModel):
    """Item del historial de visitas."""
    id_visita: int
    fecha: Optional[str] = None
    fecha_visita: Optional[str] = None
    estado: Optional[str] = None
    estado_data: Optional[str] = None
    observaciones: Optional[str] = None
    identificador_punto: Optional[str] = None
    identificador_punto_interes: Optional[str] = None
    pdv_nombre: Optional[str] = None
    cadena: Optional[str] = None
    region: Optional[str] = None
    cliente_nombre: Optional[str] = None
    id_cliente: Optional[int] = None
    fotos_count: int = 0
    balances_count: int = 0
    total_fotos: int = 0
    total_balances: int = 0
    fotos_rechazadas: int = 0
    fotos_aprobadas: int = 0


class ProductoBalanceItem(BaseModel):
    """Producto individual en el formulario de balance."""
    sku: Optional[str] = None
    fabricante: Optional[str] = None
    categoria: Optional[str] = None
    inv_inicial: float = 0
    inv_final: float = 0
    inv_deposito: float = 0
    caras: int = 0
    precio_bs: float = 0
    precio_ds: float = 0
    fifo: Optional[str] = None  # fecha FEFO
    estado_producto: Optional[str] = "normal"
    no_existe: bool = False


class BalanceRequest(BaseModel):
    """Payload para guardar balances de una visita."""
    id_cliente: Optional[int] = None
    id_pdv: Optional[str] = None
    productos: List[ProductoBalanceItem]


class BalanceResponse(BaseModel):
    """Respuesta al guardar balances."""
    success: bool
    productos_guardados: int


class FinalizarVisitaRequest(BaseModel):
    """Payload para finalizar visita."""
    id_visita: int


class FinalizarVisitaResponse(BaseModel):
    """Respuesta al finalizar visita."""
    success: bool
    id_visita: int


class ProductoParaBalance(BaseModel):
    """Producto disponible para el formulario de balance."""
    id: int
    sku: Optional[str] = None
    nombre: Optional[str] = None
    fabricante: Optional[str] = None
    categoria: Optional[str] = None
    id_categoria: Optional[int] = None


class ProductoCatalogoItem(BaseModel):
    """Producto del catálogo completo para el formulario de balance."""
    id_producto: int
    sku: Optional[str] = None
    nombre: Optional[str] = None
    fabricante: Optional[str] = None
    categoria: Optional[str] = None
    id_categoria: Optional[int] = None
    categoria_nombre: Optional[str] = None


class CategoriaConProductos(BaseModel):
    """Categoría con sus productos para el balance."""
    id_categoria: int
    nombre: str
    productos: List[ProductoCatalogoItem] = []


class ProductosCatalogoResponse(BaseModel):
    """Respuesta del catálogo de productos para balance."""
    categorias: List[CategoriaConProductos] = []
    total_productos: int = 0


# ═══════════════════════════════════════════════════════════════════════════════
# DTOs f354ea2 — NOTIFICACIONES (rechazos / aprobaciones / visitas revisadas)
# ═══════════════════════════════════════════════════════════════════════════════


class NotificacionRechazoItem(BaseModel):
    """Foto rechazada con motivo."""
    id_foto: int
    id_visita: int
    tipo_foto: Optional[str] = None
    url: Optional[str] = None
    motivo_rechazo: Optional[str] = None
    fecha_rechazo: Optional[str] = None
    leido: bool = False
    punto_nombre: Optional[str] = None
    cliente_nombre: Optional[str] = None


class NotificacionAprobacionItem(BaseModel):
    """Foto aprobada."""
    id_foto: int
    id_visita: int
    tipo_foto: Optional[str] = None
    url: Optional[str] = None
    fecha_aprobacion: Optional[str] = None
    leido: bool = False
    punto_nombre: Optional[str] = None


class NotificacionVisitaRevisadaItem(BaseModel):
    """Visita marcada como revisada por el analista."""
    id_visita: int
    punto_nombre: Optional[str] = None
    cliente_nombre: Optional[str] = None
    fecha_revision: Optional[str] = None
    leido: bool = False


class NotificacionesResponse(BaseModel):
    """Todas las notificaciones pendientes del mercaderista."""
    rechazos: List[NotificacionRechazoItem] = []
    aprobaciones: List[NotificacionAprobacionItem] = []
    visitas_revisadas: List[NotificacionVisitaRevisadaItem] = []


# ═══════════════════════════════════════════════════════════════════════════════
# DTOs f354ea2 — VISITA DETALLE (review completo)
# ═══════════════════════════════════════════════════════════════════════════════


class FotoDetalleItem(BaseModel):
    """Foto con estado de revisión completo."""
    id_foto: int
    estado: Optional[str] = None  # pendiente, aprobado, rechazado
    fecha: Optional[str] = None
    url: Optional[str] = None
    tipo_foto: Optional[str] = None
    categoria: Optional[str] = None
    motivo_rechazo: Optional[str] = None
    latitud: Optional[float] = None
    longitud: Optional[float] = None


class BalanceDetalleItem(BaseModel):
    """Balance individual en detalle de visita."""
    id_balance: int
    producto: Optional[str] = None
    categoria: Optional[str] = None
    fabricante: Optional[str] = None
    inv_inicial: Optional[float] = None
    inv_final: Optional[float] = None
    inv_deposito: Optional[float] = None
    caras: Optional[int] = None
    precio_bs: Optional[float] = None
    precio_ds: Optional[float] = None
    fefo: Optional[str] = None
    estado_producto: Optional[str] = None
    no_existe: bool = False


class VisitaDetalleResponse(BaseModel):
    """Detalle completo de una visita (fotos + balances + metadata)."""
    id_visita: int
    fecha: Optional[str] = None
    estado: Optional[str] = None
    estado_data: Optional[str] = None
    punto_nombre: Optional[str] = None
    cadena: Optional[str] = None
    direccion: Optional[str] = None
    cliente_nombre: Optional[str] = None
    revisada_por: Optional[str] = None
    fecha_revision: Optional[str] = None
    fotos: List[FotoDetalleItem] = []
    balances: List[BalanceDetalleItem] = []
    punto: Optional[dict] = None
    punto_activado: bool = False
    es_ultimo_cliente: bool = False


# ═══════════════════════════════════════════════════════════════════════════════
# DTOs f354ea2 — PDV (activación / desactivación / cierre)
# ═══════════════════════════════════════════════════════════════════════════════


class ActivarPdvRequest(BaseModel):
    """Payload para activar un PDV."""
    id_punto: str
    id_ruta: Optional[int] = None


class ActivarPdvResponse(BaseModel):
    """Respuesta al activar PDV."""
    success: bool
    id_activacion: Optional[int] = None
    ya_activado: bool = False


class ActivarRutaRequest(BaseModel):
    """Payload para activar una ruta completa."""
    id_ruta: int


class ActivarRutaResponse(BaseModel):
    """Respuesta al activar una ruta."""
    success: bool
    id_activacion: Optional[int] = None
    ya_activado: bool = False


class FinalizarRutaRequest(BaseModel):
    """Payload para finalizar una ruta."""
    id_ruta: int


class FinalizarRutaResponse(BaseModel):
    """Respuesta al finalizar una ruta."""
    success: bool
    mensaje: Optional[str] = None


class DesactivarPdvRequest(BaseModel):
    """Payload para desactivar un PDV."""
    id_punto: str


class DesactivarPdvResponse(BaseModel):
    """Respuesta al desactivar PDV."""
    success: bool
    mensaje: Optional[str] = None


class ValidarCierrePdvResponse(BaseModel):
    """Resultado de validación de cierre de PDV."""
    puede_cerrar: bool
    total_clientes: int
    clientes_visitados: int
    clientes_pendientes: List[str] = []
    mensaje: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# DTOs f354ea2 — CHAT DE VISITA
# ═══════════════════════════════════════════════════════════════════════════════


class ChatMensajePortalResponse(BaseModel):
    """Mensaje de chat de visita (portal mercaderista)."""
    id_mensaje: int
    id_visita: Optional[int] = None
    sender_nombre: Optional[str] = None
    mensaje: Optional[str] = None
    tipo_mensaje: Optional[str] = None
    fecha_envio: Optional[str] = None
    foto_adjunta: Optional[str] = None


class EnviarMensajeRequest(BaseModel):
    """Payload para enviar mensaje."""
    visita_id: int
    mensaje: str
    sender_nombre: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# DTOs f354ea2 — AUDITORÍA DE TIEMPO / REABRIR VISITA
# ═══════════════════════════════════════════════════════════════════════════════


class AuditoriaTiempoRequest(BaseModel):
    """Payload para registrar una auditoría de tiempo/temporizador."""
    id_visita: Optional[int] = None
    identificador_punto_interes: Optional[str] = None
    evento: str
    detalle: Optional[str] = None
    tiempo_restante_segundos: int


class ReabrirVisitaRequest(BaseModel):
    """Payload para reabrir una visita finalizada."""
    motivo: str


class AuditoriaTiempoResponse(BaseModel):
    """Respuesta al registrar auditoría de tiempo."""
    success: bool
    id_auditoria_tiempo: int
