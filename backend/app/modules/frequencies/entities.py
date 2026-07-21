from sqlalchemy import Column, Integer, String, Numeric, Boolean, DateTime, ForeignKey, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class FrecuenciaPdvCliente(Base):
    """Cuantas veces por semana debe visitarse un PDV para un cliente dado
    (5 = 5 veces/semana, 1 = 1 vez/semana, 0.5 = 2 veces/mes, 0.25 = 1 vez/mes, etc.)."""
    __tablename__ = "FRECUENCIAS_PDVS_CLIENTE"

    id = Column("id_frecuencia_pdv_cliente", Integer, primary_key=True, index=True)
    id_cliente = Column(Integer, ForeignKey("CLIENTES.id_cliente"), nullable=False)
    id_punto_interes = Column(String(100), ForeignKey("PUNTOS_INTERES1.identificador"), nullable=False)
    frecuencia_semanal = Column(Numeric(5, 2), nullable=False)
    observaciones = Column(String(500), nullable=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
    fecha_modificacion = Column(DateTime, nullable=True)
    id_usuario = Column(Integer, ForeignKey("USUARIOS.id_usuario"), nullable=True)

    cliente = relationship("Cliente")
    punto = relationship("PuntoInteres")
    usuario = relationship("Usuario")


class HorasPromedioEjecucion(Base):
    """Minutos promedio de ejecución esperados para un cliente según la
    clasificación de PDV (CAT_TIPO_NEGOCIO, equivalente a
    PUNTOS_INTERES1.jerarquia_nivel_2_2)."""
    __tablename__ = "HORAS_PROMEDIO_EJECUCION"

    id = Column("id_horas_promedio_ejecucion", Integer, primary_key=True, index=True)
    id_cliente = Column(Integer, ForeignKey("CLIENTES.id_cliente"), nullable=False)
    id_tipo_negocio = Column(Integer, ForeignKey("CAT_TIPO_NEGOCIO.id"), nullable=False)
    minutos_promedio = Column(Integer, nullable=False)
    fecha_creado = Column(DateTime, server_default=func.now())
    fecha_modificado = Column(DateTime, nullable=True)
    id_usuario_creador = Column(Integer, ForeignKey("USUARIOS.id_usuario"), nullable=True)
    id_usuario_modificador = Column(Integer, ForeignKey("USUARIOS.id_usuario"), nullable=True)

    cliente = relationship("Cliente")
    tipo_negocio = relationship("TipoNegocio")
    usuario_creador = relationship("Usuario", foreign_keys=[id_usuario_creador])
    usuario_modificador = relationship("Usuario", foreign_keys=[id_usuario_modificador])
