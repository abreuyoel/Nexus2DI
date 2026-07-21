from pydantic import BaseModel
from typing import Optional, List, Literal
from datetime import datetime

# ── MENSAJES (chat por visita y conversaciones) ───────────────────────────
class ChatMensajeCreate(BaseModel):
    visita_id: Optional[int] = None
    cliente_id: Optional[int] = None
    conversacion_id: Optional[int] = None
    mensaje: str
    sender_type: Optional[str] = "usuario"
    sender_id: Optional[int] = None
    sender_nombre: Optional[str] = None


class LectorInfo(BaseModel):
    id_usuario: int
    username: Optional[str] = None
    fecha_lectura: Optional[datetime] = None


class ChatMensajeResponse(BaseModel):
    id: int
    visita_id: Optional[int] = None
    cliente_id: Optional[int] = None
    conversacion_id: Optional[int] = None
    sender_type: Optional[str] = None
    sender_id: Optional[int] = None
    sender_nombre: Optional[str] = None
    mensaje: Optional[str] = None
    leido: Optional[bool] = None
    created_at: Optional[datetime] = None
    leido_por: List[LectorInfo] = []
    foto_adjunta: Optional[str] = None

    class Config:
        from_attributes = True


# ── CONVERSACIONES ─────────────────────────────────────────────────────────
ConversacionTipo = Literal["direct", "group_team", "group_region", "group_pdv"]


class CrearConversacionRequest(BaseModel):
    tipo: ConversacionTipo
    cliente_id: Optional[int] = None
    destinatario_id: Optional[int] = None
    region: Optional[str] = None
    punto_interes_id: Optional[str] = None
    titulo: Optional[str] = None
    primer_mensaje: Optional[str] = None


class ConversacionResponse(BaseModel):
    id: int
    cliente_id: int
    tipo: str
    titulo: Optional[str] = None
    region: Optional[str] = None
    punto_interes_id: Optional[str] = None
    visita_id: Optional[int] = None
    creado_por: int
    fecha_creacion: Optional[datetime] = None
    participantes_count: Optional[int] = None
    ultimo_mensaje: Optional[str] = None
    ultimo_mensaje_fecha: Optional[datetime] = None
    no_leidos: int = 0

    class Config:
        from_attributes = True


# ── DESTINATARIOS DISPONIBLES (para construir la UI del modal) ───────────
class RecipientUser(BaseModel):
    id_usuario: int
    nombre: str
    subtitulo: Optional[str] = None


class RegionRecipient(BaseModel):
    region: str
    mercaderistas_count: int


class PdvRecipient(BaseModel):
    identificador: str
    punto_de_interes: str
    region: Optional[str] = None
    mercaderistas_count: int


class RecipientsResponse(BaseModel):
    analistas: List[RecipientUser]
    mercaderistas: List[RecipientUser]
    regiones: List[RegionRecipient]
    pdvs: List[PdvRecipient]


# ── INBOX (lista de conversaciones + chats por visita unificados) ────────
class InboxItem(BaseModel):
    kind: Literal["visit", "conversation"]
    visita_id: Optional[int] = None
    punto_nombre: Optional[str] = None
    punto_id: Optional[str] = None
    fecha_visita: Optional[str] = None
    conversacion_id: Optional[int] = None
    tipo: Optional[str] = None
    titulo: Optional[str] = None
    last_message: Optional[str] = None
    last_message_date: Optional[str] = None
    unread_count: int = 0


class VisitSearchResult(BaseModel):
    visita_id: int
    punto_nombre: str
    punto_id: Optional[str] = None
    cadena: Optional[str] = None
    region: Optional[str] = None
    mercaderista_nombre: Optional[str] = None
    fecha_visita: Optional[str] = None
    last_message: Optional[str] = None
    last_message_date: Optional[str] = None
    unread_count: int = 0


# ── CHAT GRUPOS ────────────────────────────────────────────────────────────
class LectorGrupoInfo(BaseModel):
    id_usuario: int
    username: Optional[str] = None
    fecha_lectura: Optional[datetime] = None


class GrupoResponse(BaseModel):
    id_grupo: int
    id_cliente: int
    tipo_grupo: str
    nombre: Optional[str] = None
    no_leidos: int = 0
    ultimo_mensaje: Optional[str] = None
    ultimo_mensaje_fecha: Optional[datetime] = None

    class Config:
        from_attributes = True


class MiembroGrupoResponse(BaseModel):
    id_usuario: int
    username: Optional[str] = None
    origen: str


class MensajeGrupoResponse(BaseModel):
    id_mensaje: int
    id_grupo: int
    id_usuario: Optional[int] = None
    username: Optional[str] = None
    mensaje: str
    tipo_mensaje: str
    fecha_envio: Optional[datetime] = None
    foto_adjunta: Optional[str] = None
    es_mio: bool = False
    leido_por: List[LectorGrupoInfo] = []


class EnviarMensajeGrupoRequest(BaseModel):
    mensaje: str


class VisitaThreadRequest(BaseModel):
    visita_id: int
    tipo_grupo: str


class VisitaThreadResponse(BaseModel):
    id_grupo: int
    id_cliente: int
    tipo_grupo: str
    id_visita: int
    titulo: Optional[str] = None


class VisitaConChatResponse(BaseModel):
    id_visita: int
    fecha_visita: Optional[str] = None
    mercaderista: Optional[str] = None
    punto: Optional[str] = None
    estado: Optional[str] = None
    ultimo_mensaje: Optional[str] = None
    fecha_ultimo: Optional[datetime] = None


class MensajeGrupoVisitaResponse(BaseModel):
    id_mensaje: int
    id_cliente: int
    tipo_grupo: str
    id_visita: int
    id_usuario: Optional[int] = None
    username: Optional[str] = None
    mensaje: str
    tipo_mensaje: str
    fecha_envio: Optional[datetime] = None
    foto_adjunta: Optional[str] = None
    es_mio: bool = False
    leido_por: List[LectorGrupoInfo] = []


class InfoGrupoClienteResponse(BaseModel):
    id_grupo: int
    id_cliente: int
    tipo_grupo: str
    nombre: Optional[str] = None
