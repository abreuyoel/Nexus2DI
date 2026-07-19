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

    class Config:
        from_attributes = True


# ── CONVERSACIONES ─────────────────────────────────────────────────────────
ConversacionTipo = Literal["direct", "group_team", "group_region", "group_pdv"]


class CrearConversacionRequest(BaseModel):
    tipo: ConversacionTipo
    cliente_id: Optional[int] = None  # Coordinador exclusivo lo pasa; cliente normal usa su id_perfil
    # 'direct': destinatario (un solo id_usuario)
    destinatario_id: Optional[int] = None
    # 'group_region': region; 'group_pdv': punto_interes_id; 'group_team': nada extra
    region: Optional[str] = None
    punto_interes_id: Optional[str] = None
    titulo: Optional[str] = None  # opcional, si no se autogenera
    primer_mensaje: Optional[str] = None  # opcional: arranca con un primer mensaje


class ConversacionResponse(BaseModel):
    id: int
    cliente_id: int
    tipo: str
    titulo: Optional[str] = None
    region: Optional[str] = None
    punto_interes_id: Optional[str] = None
    creado_por: int
    fecha_creacion: Optional[datetime] = None
    # Helpers que llenamos manualmente
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
    subtitulo: Optional[str] = None  # rol, cédula, etc.


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
    # Visit chat
    visita_id: Optional[int] = None
    punto_nombre: Optional[str] = None
    punto_id: Optional[str] = None
    fecha_visita: Optional[str] = None
    # Conversation
    conversacion_id: Optional[int] = None
    tipo: Optional[str] = None
    titulo: Optional[str] = None
    # Comunes
    last_message: Optional[str] = None
    last_message_date: Optional[str] = None
    unread_count: int = 0
