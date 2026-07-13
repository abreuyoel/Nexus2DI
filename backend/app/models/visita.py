from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.db.base import Base


class Visita(Base):
    __tablename__ = "VISITAS_MERCADERISTA"

    id = Column("id_visita", Integer, primary_key=True, index=True)
    mercaderista_id = Column("id_mercaderista", Integer, ForeignKey("MERCADERISTAS.id_mercaderista"), nullable=True)
    punto_id = Column("identificador_punto_interes", String(100), ForeignKey("PUNTOS_INTERES1.identificador"), nullable=True)
    id_cliente = Column(Integer, ForeignKey("CLIENTES.id_cliente"), nullable=True)
    fecha = Column("fecha_visita", Date, nullable=True)
    estado = Column(String(50), default="Pendiente")
    tipo_visita = Column(String(50), nullable=True)
    estado_data = Column(String(50), nullable=True)
    revisada_por = Column(String(200), nullable=True)
    fecha_revision = Column(DateTime, nullable=True)

    mercaderista = relationship("Mercaderista", back_populates="visitas")
    punto = relationship("PuntoInteres", back_populates="visitas")
    cliente = relationship("Cliente")
    fotos = relationship("Foto", back_populates="visita")
    mensajes_chat = relationship("ChatMensaje", back_populates="visita")
