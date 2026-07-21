from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base


class ChatMensaje(Base):
    __tablename__ = "CHAT_MENSAJES_CLIENTE"

    id = Column("id_mensaje", Integer, primary_key=True, index=True)
    visita_id = Column("id_visita", Integer, ForeignKey("VISITAS_MERCADERISTA.id_visita"), nullable=True)
    cliente_id = Column("id_cliente", Integer, ForeignKey("CLIENTES.id_cliente"), nullable=True)
    conversacion_id = Column("id_conversacion", Integer, ForeignKey("CHAT_CONVERSACIONES.id_conversacion"), nullable=True)
    sender_id = Column("id_usuario", Integer, nullable=True)
    sender_nombre = Column("username", String(255), nullable=True)
    mensaje = Column(Text, nullable=True)
    sender_type = Column("tipo_mensaje", String(50), nullable=True)
    leido = Column("visto", Boolean, default=False)
    created_at = Column("fecha_envio", DateTime, nullable=True)
    metadata_json = Column("metadata", String(1000), nullable=True)

    visita = relationship("Visita", back_populates="mensajes_chat")
    conversacion = relationship("ChatConversacion", back_populates="mensajes")


class ChatConversacion(Base):
    """Conversación independiente de visitas (chats directos y grupos).

    tipo:
      - 'direct'        → 1:1 entre cliente y un staff (analista/mercaderista)
      - 'group_team'    → todo el equipo del cliente (analistas, mercs, supervisores, coords + usuarios del cliente)
      - 'group_region'  → grupo de mercaderistas de una región específica (+ creador)
      - 'group_pdv'     → grupo de mercaderistas de un PDV específico (+ creador)
    """
    __tablename__ = "CHAT_CONVERSACIONES"

    id = Column("id_conversacion", Integer, primary_key=True, index=True)
    cliente_id = Column("id_cliente", Integer, ForeignKey("CLIENTES.id_cliente"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False, index=True)
    titulo = Column(String(200), nullable=True)
    region = Column(String(100), nullable=True)
    punto_interes_id = Column("id_punto_interes", String(50), nullable=True)
    creado_por = Column(Integer, ForeignKey("USUARIOS.id_usuario"), nullable=False)
    fecha_creacion = Column(DateTime, nullable=True)

    mensajes = relationship("ChatMensaje", back_populates="conversacion",
                            cascade="all, delete-orphan", lazy="noload")
    participantes = relationship("ChatParticipante", back_populates="conversacion",
                                 cascade="all, delete-orphan", lazy="noload")


class ChatParticipante(Base):
    __tablename__ = "CHAT_PARTICIPANTES"

    conversacion_id = Column("id_conversacion", Integer, ForeignKey("CHAT_CONVERSACIONES.id_conversacion"), primary_key=True)
    usuario_id = Column("id_usuario", Integer, ForeignKey("USUARIOS.id_usuario"), primary_key=True)
    fecha_union = Column(DateTime, nullable=True)

    conversacion = relationship("ChatConversacion", back_populates="participantes")
