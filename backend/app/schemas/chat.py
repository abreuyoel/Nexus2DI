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


# ── CONVERSACIONES (grupos de mercaderistas ad-hoc, sin equivalente en v1) ──
ConversacionTipo = Literal["group_region", "group_pdv"]


class CrearConversacionRequest(BaseModel):
    tipo: ConversacionTipo
    cliente_id: Optional[int] = None  # Coordinador exclusivo lo pasa; cliente normal usa su id_perfil
    # 'group_region': region; 'group_pdv': punto_interes_id
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
    visita_id: Optional[int] = None
    creado_por: int
    fecha_creacion: Optional[datetime] = None
    # Helpers que llenamos manualmente
    participantes_count: Optional[int] = None
    ultimo_mensaje: Optional[str] = None
    ultimo_mensaje_fecha: Optional[datetime] = None
    no_leidos: int = 0

    class Config:
        from_attributes = True


# ── DESTINATARIOS DISPONIBLES (para construir la UI del modal de grupos
# region/pdv — el chat de equipo/visita ya no se "crea", se auto-provisiona
# vía app/routes/chat_grupos.py) ──────────────────────────────────────────
class RegionRecipient(BaseModel):
    region: str
    mercaderistas_count: int


class PdvRecipient(BaseModel):
    identificador: str
    punto_de_interes: str
    region: Optional[str] = None
    mercaderistas_count: int


class RecipientsResponse(BaseModel):
    regiones: List[RegionRecipient]
    pdvs: List[PdvRecipient]


# ── INBOX (lista de conversaciones + chats por visita unificados) ────────
class InboxItem(BaseModel):
    kind: Literal["visit", "conversation"]
    # Visit chat legacy (kind='visit', tab "Cliente") — el chat de equipo y
    # su sub-hilo por visita viven en chat_grupos, no en este inbox.
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
