from sqlalchemy import Column, Integer, DateTime, ForeignKey, func
from app.db.base import Base


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
