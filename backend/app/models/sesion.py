from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class SesionActiva(Base):
    __tablename__ = "SESIONES_ACTIVAS"

    id = Column("id_sesion", Integer, primary_key=True, index=True)
    user_id = Column("id_usuario", Integer, ForeignKey("USUARIOS.id_usuario"), nullable=False)
    username = Column(String(100), nullable=True)
    rol = Column(String(50), nullable=True)
    session_token = Column("session_id", String(1000), nullable=False, unique=True)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(String(500), nullable=True)
    activa = Column(Boolean, default=True)
    created_at = Column("fecha_inicio", DateTime, nullable=True)
    last_active = Column("ultimo_acceso", DateTime, nullable=True)
    fecha_cierre = Column(DateTime, nullable=True)
    motivo_cierre = Column(String(100), nullable=True)

    usuario = relationship("Usuario", back_populates="sesiones")
