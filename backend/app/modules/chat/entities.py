from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base


class ChatMensaje(Base):
    __tablename__ = "CHAT_MENSAJES_CLIENTE"

    id = Column("id_mensaje", Integer, primary_key=True, index=True)
    visita_id = Column("id_visita", Integer, ForeignKey("VISITAS_MERCADERISTA.id_visita"), nullable=True)
    cliente_id = Column("id_cliente", Integer, ForeignKey("CLIENTES.id_cliente"), nullable=True)
    conversacion_id = Column("id_conversacion", Integer, ForeignKey("CHAT_CONVERSACIONES.id_conversacion"), nullable=True)
    sender_id = Column("id_usuario", Integer, ForeignKey("USUARIOS.id_usuario"), nullable=True)
    sender_nombre = Column("username", String(255), nullable=True)
    mensaje = Column(Text, nullable=True)
    sender_type = Column("tipo_mensaje", String(50), nullable=True)
    leido = Column("visto", Boolean, default=False)
    created_at = Column("fecha_envio", DateTime, nullable=True)
    metadata_json = Column("metadata", String(1000), nullable=True)
    foto_adjunta = Column(String(500), nullable=True)

    visita = relationship("Visita", back_populates="mensajes_chat")
    conversacion = relationship("ChatConversacion", back_populates="mensajes")
    cliente = relationship("Cliente")
    sender = relationship("Usuario", foreign_keys=[sender_id])


class ChatConversacion(Base):
    """Conversación independiente de visitas (chats directos y grupos)."""
    __tablename__ = "CHAT_CONVERSACIONES"

    id = Column("id_conversacion", Integer, primary_key=True, index=True)
    cliente_id = Column("id_cliente", Integer, ForeignKey("CLIENTES.id_cliente"), nullable=False, index=True)
    tipo = Column(String(20), nullable=False, index=True)
    titulo = Column(String(200), nullable=True)
    region = Column(String(100), nullable=True)
    punto_interes_id = Column("id_punto_interes", String(50), nullable=True)
    visita_id = Column("id_visita", Integer, ForeignKey("VISITAS_MERCADERISTA.id_visita"), nullable=True, index=True)
    creado_por = Column(Integer, ForeignKey("USUARIOS.id_usuario"), nullable=False)
    fecha_creacion = Column(DateTime, nullable=True)

    mensajes = relationship("ChatMensaje", back_populates="conversacion",
                            cascade="all, delete-orphan", lazy="noload")
    participantes = relationship("ChatParticipante", back_populates="conversacion",
                                 cascade="all, delete-orphan", lazy="noload")
    cliente = relationship("Cliente")
    creador = relationship("Usuario", foreign_keys=[creado_por])


class ChatParticipante(Base):
    __tablename__ = "CHAT_PARTICIPANTES"

    conversacion_id = Column("id_conversacion", Integer, ForeignKey("CHAT_CONVERSACIONES.id_conversacion"), primary_key=True)
    usuario_id = Column("id_usuario", Integer, ForeignKey("USUARIOS.id_usuario"), primary_key=True)
    fecha_union = Column(DateTime, nullable=True)

    conversacion = relationship("ChatConversacion", back_populates="participantes")
    usuario = relationship("Usuario", foreign_keys=[usuario_id])


class ChatMensajeLectura(Base):
    """Recibo de lectura por mensaje y usuario (estilo WhatsApp)."""
    __tablename__ = "CHAT_MENSAJE_LECTURAS"

    id = Column("id_lectura", Integer, primary_key=True, index=True)
    mensaje_id = Column("id_mensaje", Integer, ForeignKey("CHAT_MENSAJES_CLIENTE.id_mensaje"), nullable=False, index=True)
    usuario_id = Column("id_usuario", Integer, nullable=False, index=True)
    username = Column(String(150), nullable=True)
    fecha_lectura = Column(DateTime, nullable=True)


class ChatGrupo(Base):
    """Grupo de chat por cliente (CHAT_GRUPOS de v1)."""
    __tablename__ = "CHAT_GRUPOS"

    id = Column("id_grupo", Integer, primary_key=True, index=True)
    cliente_id = Column("id_cliente", Integer, nullable=False, index=True)
    tipo_grupo = Column(String(20), nullable=False)
    nombre = Column(String(150), nullable=True)
    activa = Column(Boolean, nullable=False, default=True)
    fecha_creacion = Column(DateTime, nullable=True)


class ChatGrupoMensaje(Base):
    """Mensajes del chat general de un grupo (CHAT_GRUPO_MENSAJES de v1)."""
    __tablename__ = "CHAT_GRUPO_MENSAJES"

    id = Column("id_mensaje", Integer, primary_key=True, index=True)
    grupo_id = Column("id_grupo", Integer, ForeignKey("CHAT_GRUPOS.id_grupo"), nullable=False, index=True)
    sender_id = Column("id_usuario", Integer, nullable=True)
    sender_nombre = Column("username", String(150), nullable=True)
    mensaje = Column(Text, nullable=False)
    tipo_mensaje = Column(String(20), nullable=False, default="usuario")
    created_at = Column("fecha_envio", DateTime, nullable=True)
    foto_adjunta = Column(String(500), nullable=True)


class ChatGrupoLectura(Base):
    """Puntero de lectura por (grupo, usuario)."""
    __tablename__ = "CHAT_GRUPO_LECTURAS"

    grupo_id = Column("id_grupo", Integer, ForeignKey("CHAT_GRUPOS.id_grupo"), primary_key=True)
    usuario_id = Column("id_usuario", Integer, primary_key=True)
    last_read_id_mensaje = Column(Integer, nullable=False, default=0)
    fecha_actualizacion = Column(DateTime, nullable=True)


class ChatGrupoMensajeLectura(Base):
    """Recibo de lectura por mensaje y usuario para CHAT_GRUPO_MENSAJES."""
    __tablename__ = "CHAT_GRUPO_MENSAJE_LECTURAS"

    mensaje_id = Column("id_mensaje", Integer, ForeignKey("CHAT_GRUPO_MENSAJES.id_mensaje"), primary_key=True)
    usuario_id = Column("id_usuario", Integer, primary_key=True)
    username = Column(String(150), nullable=True)
    fecha_lectura = Column(DateTime, nullable=True)


class ChatMensajeGrupoVisita(Base):
    """Sub-hilo de chat de una visita puntual dentro de un grupo."""
    __tablename__ = "CHAT_MENSAJES_GRUPO_VISITA"

    id = Column("id_mensaje", Integer, primary_key=True, index=True)
    cliente_id = Column("id_cliente", Integer, nullable=False, index=True)
    tipo_grupo = Column(String(20), nullable=False)
    visita_id = Column("id_visita", Integer, nullable=False, index=True)
    sender_id = Column("id_usuario", Integer, nullable=True)
    sender_nombre = Column("username", String(150), nullable=True)
    mensaje = Column(Text, nullable=False)
    tipo_mensaje = Column(String(20), nullable=False, default="usuario")
    created_at = Column("fecha_envio", DateTime, nullable=True)
    foto_adjunta = Column(String(500), nullable=True)


class ChatGrupoVisitaLectura(Base):
    """Recibo de lectura por mensaje y usuario para CHAT_MENSAJES_GRUPO_VISITA."""
    __tablename__ = "CHAT_GRUPO_VISITA_LECTURAS"

    id = Column("id_lectura", Integer, primary_key=True, index=True)
    mensaje_id = Column("id_mensaje", Integer, ForeignKey("CHAT_MENSAJES_GRUPO_VISITA.id_mensaje"), nullable=False, index=True)
    usuario_id = Column("id_usuario", Integer, nullable=False, index=True)
    username = Column(String(150), nullable=True)
    fecha_lectura = Column(DateTime, nullable=True)
