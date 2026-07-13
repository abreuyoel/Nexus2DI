from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Date, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class Activacion(Base):
    __tablename__ = "ACTIVACIONES"

    id = Column(Integer, primary_key=True, index=True)
    punto_id = Column("identificador_punto_interes", String(100), ForeignKey("PUNTOS_INTERES1.identificador"), nullable=True)
    mercaderista_id = Column("id_mercaderista", Integer, ForeignKey("MERCADERISTAS.id_mercaderista"), nullable=True)
    mercaderista_cedula = Column(String(20), nullable=True)
    producto_id = Column("ID_PRODUCT", Integer, ForeignKey("PRODUCTS.id_product"), nullable=True)
    fecha = Column(Date, nullable=True)
    foto_antes_id = Column("id_foto_antes", Integer, ForeignKey("FOTOS_TOTALES.id_foto"), nullable=True)
    foto_despues_id = Column("id_foto_despues", Integer, ForeignKey("FOTOS_TOTALES.id_foto"), nullable=True)
    estado = Column(String(50), default="activa")
    observaciones = Column(Text, nullable=True)
    ruta_id = Column("id_ruta", Integer, ForeignKey("RUTAS_NUEVAS.id_ruta"), nullable=True)
    created_at = Column(DateTime, nullable=True)

    punto = relationship("PuntoInteres", back_populates="activaciones")
    producto = relationship("Producto")
