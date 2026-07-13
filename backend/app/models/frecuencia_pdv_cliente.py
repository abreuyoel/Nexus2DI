from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, func
from app.db.base import Base


class FrecuenciaPdvCliente(Base):
    """Cuantas veces por semana debe visitarse un PDV para un cliente dado
    (5 = 5 veces/semana, 1 = 1 vez/semana, 0.5 = 2 veces/mes, 0.25 = 1 vez/mes, etc.)."""
    __tablename__ = "FRECUENCIAS_PDVS_CLIENTE"

    id = Column("id_frecuencia_pdv_cliente", Integer, primary_key=True, index=True)
    id_cliente = Column(Integer, ForeignKey("CLIENTES.id_cliente"), nullable=False)
    id_punto_interes = Column(String(50), ForeignKey("PUNTOS_INTERES1.identificador"), nullable=False)
    frecuencia_semanal = Column(Numeric(5, 2), nullable=False)
    observaciones = Column(String(500), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_modificacion = Column(DateTime, nullable=True)
    id_usuario = Column(Integer, ForeignKey("USUARIOS.id_usuario"), nullable=True)
