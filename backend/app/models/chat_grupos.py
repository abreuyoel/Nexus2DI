from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean
from app.db.base import Base


class ChatGrupo(Base):
    """Grupo de chat por cliente (CHAT_GRUPOS de v1) — mismo modelo que ya
    usan AppWeb v1 (Astroweb) y la APK del mercaderista (epran_backend), no
    se comparte nada con CHAT_CONVERSACIONES (modelo propio de v2, reservado
    para group_region/group_pdv sin equivalente en v1).

    tipo_grupo:
      - 'operativo'          → solo personal epran (mercaderistas, analistas,
                                coordinadores)
      - 'operativo_cliente'  → lo anterior + usuarios rol cliente

    Membresía 100% dinámica (ver app/services/chat_grupos_membresia.py) —
    no hay tabla de miembros, se calcula en cada consulta desde
    RUTA_PROGRAMACION/analistas_rutas/USUARIOS.
    """
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
    sender_id = Column("id_usuario", Integer, nullable=True)  # NULL = mensaje de sistema
    sender_nombre = Column("username", String(150), nullable=True)
    mensaje = Column(Text, nullable=False)
    tipo_mensaje = Column(String(20), nullable=False, default="usuario")  # 'usuario' | 'sistema'
    created_at = Column("fecha_envio", DateTime, nullable=True)
    foto_adjunta = Column(String(500), nullable=True)


class ChatGrupoLectura(Base):
    """Puntero de lectura por (grupo, usuario) — solo para el badge de
    no-leídos de 'mis-grupos'. Los recibos granulares "leído por" están en
    ChatGrupoMensajeLectura, tabla separada."""
    __tablename__ = "CHAT_GRUPO_LECTURAS"

    grupo_id = Column("id_grupo", Integer, ForeignKey("CHAT_GRUPOS.id_grupo"), primary_key=True)
    usuario_id = Column("id_usuario", Integer, primary_key=True)
    last_read_id_mensaje = Column(Integer, nullable=False, default=0)
    fecha_actualizacion = Column(DateTime, nullable=True)


class ChatGrupoMensajeLectura(Base):
    """Recibo de lectura por mensaje y usuario, estilo WhatsApp, para el
    chat general del grupo (CHAT_GRUPO_MENSAJES)."""
    __tablename__ = "CHAT_GRUPO_MENSAJE_LECTURAS"

    mensaje_id = Column("id_mensaje", Integer, ForeignKey("CHAT_GRUPO_MENSAJES.id_mensaje"), primary_key=True)
    usuario_id = Column("id_usuario", Integer, primary_key=True)
    username = Column(String(150), nullable=True)
    fecha_lectura = Column(DateTime, nullable=True)


class ChatMensajeGrupoVisita(Base):
    """Sub-hilo de chat de una visita puntual dentro de un grupo (solo
    equipo / equipo+cliente) — CHAT_MENSAJES_GRUPO_VISITA de v1. Compartida
    con la APK del mercaderista (epran_backend/mssql-chat.repository.ts) —
    NO tocar el esquema sin coordinar con ese lado.

    Sin tabla de registro aparte: la existencia del sub-hilo se infiere por
    presencia de mensajes con (id_cliente, tipo_grupo, id_visita) iguales.
    """
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
    """Recibo de lectura por mensaje y usuario para el sub-hilo de visita
    (CHAT_MENSAJES_GRUPO_VISITA)."""
    __tablename__ = "CHAT_GRUPO_VISITA_LECTURAS"

    id = Column("id_lectura", Integer, primary_key=True, index=True)
    mensaje_id = Column("id_mensaje", Integer, ForeignKey("CHAT_MENSAJES_GRUPO_VISITA.id_mensaje"), nullable=False, index=True)
    usuario_id = Column("id_usuario", Integer, nullable=False, index=True)
    username = Column(String(150), nullable=True)
    fecha_lectura = Column(DateTime, nullable=True)
