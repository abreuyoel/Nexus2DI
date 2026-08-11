from sqlalchemy import Column, Integer, String, DateTime
from app.db.base import Base
from datetime import datetime

class AuditoriaTiempo(Base):
    __tablename__ = "MERC_AUDITORIA_TIEMPO"

    id = Column("id_auditoria_tiempo", Integer, primary_key=True, index=True)
    id_visita = Column("id_visita", Integer, nullable=True)
    identificador_punto_interes = Column("identificador_punto_interes", String(50), nullable=True)
    id_mercaderista = Column("id_mercaderista", Integer, nullable=False)
    evento = Column("evento", String(50), nullable=False)
    detalle = Column("detalle", String(500), nullable=True)
    tiempo_restante_segundos = Column("tiempo_restante_segundos", Integer, nullable=False)
    fecha_registro = Column("fecha_registro", DateTime, default=datetime.utcnow)
