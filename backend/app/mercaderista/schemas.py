"""
Schemas Pydantic para el Portal Mercaderista.
Todos los modelos de request/response centralizados aquí.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════════════════════════
# AUTH / PERFIL
# ═══════════════════════════════════════════════════════════════════════════════

class MercaderistaProfile(BaseModel):
    """Perfil del mercaderista autenticado."""
    id: int
    nombre: str
    cedula: str
    email: Optional[str] = None
    telefono: Optional[str] = None
    rutas: List[RutaAsignada] = []

    class Config:
        from_attributes = True


class RutaAsignada(BaseModel):
    """Ruta asignada al mercaderista."""
    id_ruta: int
    tipo: Optional[str] = None
    nombre: Optional[str] = None

    class Config:
        from_attributes = True


# ═══════════════════════════════════════════════════════════════════════════════
# RUTAS
# ═══════════════════════════════════════════════════════════════════════════════

class ClienteEnPdv(BaseModel):
    """Cliente programado en un PDV."""
    id_cliente: int
    nombre: str
    visitado: bool = False
    id_visita: Optional[int] = None


class PdvEnRuta(BaseModel):
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
    clientes: List[ClienteEnPdv] = []


class RutaDelDia(BaseModel):
    """Ruta del día con sus PDVs."""
    id_ruta: int
    tipo: Optional[str] = None
    nombre: Optional[str] = None
    pdvs: List[PdvEnRuta] = []
    activada: bool = False
    finalizada: bool = False


class MisRutasResponse(BaseModel):
    """Respuesta completa de rutas del mercaderista para hoy."""
    mercaderista_id: int
    dia_semana: str
    fecha: str
    rutas_fijas: List[RutaDelDia] = []
    rutas_variables: List[RutaDelDia] = []


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
    """Programación completa del día: rutas + productos en una sola llamada.
    Equivale a getProgramacion() de la APK."""
    fecha: str
    dia_semana: str
    mercaderista: ProgramacionMercaderista
    rutas_fijas: List[RutaDelDia] = []
    rutas_variables: List[RutaDelDia] = []
    productos: List[ProgramacionProducto] = []


# ═══════════════════════════════════════════════════════════════════════════════
# PDV ACTIVOS
# ═══════════════════════════════════════════════════════════════════════════════

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
# VISITAS
# ═══════════════════════════════════════════════════════════════════════════════

class IniciarVisitaRequest(BaseModel):
    """Payload para iniciar una visita."""
    id_punto: str
    id_cliente: int


class IniciarVisitaResponse(BaseModel):
    """Respuesta al iniciar visita."""
    id_visita: int
    nueva: bool


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


class FotoEnVisita(BaseModel):
    """Foto dentro de una visita."""
    id_foto: int
    estado: Optional[str] = None
    fecha: Optional[str] = None
    url: Optional[str] = None


class TipoFotoGrupo(BaseModel):
    """Grupo de fotos por tipo."""
    codigo: str
    label: str
    solo_camara: bool
    fotos: List[FotoEnVisita] = []


class FotosVisitaResponse(BaseModel):
    """Respuesta de fotos agrupadas por tipo."""
    visita_id: int
    tipos: List[TipoFotoGrupo] = []


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
    """Payload para guardar balances."""
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


# ═══════════════════════════════════════════════════════════════════════════════
# PRODUCTOS (Catálogo para Balance)
# ═══════════════════════════════════════════════════════════════════════════════

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
# NOTIFICACIONES (Rechazos, Aprobaciones, Visitas Revisadas)
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
# VISITA DETALLE (Review completo)
# ═══════════════════════════════════════════════════════════════════════════════

class FotoDetalleItem(BaseModel):
    """Foto con estado de revisión completo."""
    id_foto: int
    estado: Optional[str] = None           # pendiente, aprobado, rechazado
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
# PDV (Activación / Desactivación)
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
# CHAT
# ═══════════════════════════════════════════════════════════════════════════════

class ChatInboxItem(BaseModel):
    """Conversación en la bandeja de chat."""
    id_visita: int
    fecha_visita: Optional[str] = None
    estado: Optional[str] = None
    pdv_nombre: Optional[str] = None
    cliente_nombre: Optional[str] = None
    total_msgs: int = 0
    ultimo_mensaje: Optional[str] = None
    ultimo_timestamp: Optional[str] = None


class ChatMensajeResponse(BaseModel):
    """Mensaje de chat."""
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
# CHAT GRUPOS (Equipo Operativo / Equipo + Cliente)
# ═══════════════════════════════════════════════════════════════════════════════

class GrupoChatItem(BaseModel):
    """Grupo de chat al que pertenece el mercaderista."""
    id_grupo: int
    id_cliente: int
    tipo_grupo: str
    nombre: Optional[str] = None
    no_leidos: int = 0
    ultimo_mensaje: Optional[str] = None
    ultimo_mensaje_fecha: Optional[str] = None


class MiembroGrupoItem(BaseModel):
    """Miembro de un grupo de chat."""
    id_usuario: int
    username: Optional[str] = None
    nombre: Optional[str] = None
    origen: str


class MensajeGrupoItem(BaseModel):
    """Mensaje en el chat general del grupo."""
    id_mensaje: int
    id_grupo: int
    id_usuario: Optional[int] = None
    username: Optional[str] = None
    mensaje: str
    tipo_mensaje: str
    fecha_envio: Optional[str] = None
    foto_adjunta: Optional[str] = None
    es_mio: bool = False


class EnviarMensajeGrupoRequest(BaseModel):
    """Payload para enviar mensaje al grupo."""
    mensaje: str


class VisitaGrupoChatItem(BaseModel):
    """Visita activa con hilo de chat en el grupo."""
    id_visita: int
    fecha_visita: Optional[str] = None
    mercaderista: Optional[str] = None
    punto: Optional[str] = None
    estado: Optional[str] = None
    ultimo_mensaje: Optional[str] = None
    fecha_ultimo: Optional[str] = None


class MensajeGrupoVisitaItem(BaseModel):
    """Mensaje en el sub-hilo de visita del grupo."""
    id_mensaje: int
    id_cliente: int
    tipo_grupo: str
    id_visita: int
    id_usuario: Optional[int] = None
    username: Optional[str] = None
    mensaje: str
    tipo_mensaje: str
    fecha_envio: Optional[str] = None
    foto_adjunta: Optional[str] = None
    es_mio: bool = False


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
