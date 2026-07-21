from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class Solicitud(Base):
    __tablename__ = "SOLICITUDES"

    id = Column("id_solicitud", Integer, primary_key=True, index=True)
    user_id = Column("id_solicitante", Integer, ForeignKey("USUARIOS.id_usuario"), nullable=True)
    tipo = Column("tipo_solicitud", String(100), nullable=False)
    descripcion = Column("datos", Text, nullable=True)
    respuesta = Column("respuesta", Text, nullable=True)
    estado = Column(String(50), default="pendiente")
    created_at = Column("fecha_solicitud", DateTime, nullable=True)

    usuario = relationship("Usuario", back_populates="solicitudes")
