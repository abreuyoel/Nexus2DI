from sqlalchemy import Column, Integer, DateTime
from datetime import datetime
from app.db.base import Base


class FotoRazonRechazo(Base):
    """Tabla puente: una foto puede tener N razones de rechazo (RAZONES_RECHAZOS)."""
    __tablename__ = "FOTOS_RAZONES_RECHAZOS"

    id = Column("id_foto_razon", Integer, primary_key=True, index=True)
    id_foto = Column(Integer, nullable=False, index=True)
    id_razones_rechazos = Column(Integer, nullable=False)
    rechazado_por = Column(Integer, nullable=True)
    fecha = Column(DateTime, default=datetime.now)
