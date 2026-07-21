from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Date
from datetime import datetime, timezone
from app.db.base import Base


class AuditLog(Base):
    __tablename__ = "AUDIT_LOG"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
    user_id = Column(Integer, nullable=True)
    username = Column(String(100), nullable=True, index=True)
    rol = Column(String(50), nullable=True)
    ip_address = Column(String(100), nullable=True)
    action = Column(String(100), nullable=False, index=True)
    entity_type = Column(String(100), nullable=True, index=True)
    entity_id = Column(String(100), nullable=True)
    entity_name = Column(String(500), nullable=True)
    changes = Column(Text, nullable=True)
    status = Column(String(20), default="OK", nullable=False)


class AuditoriaCategoria(Base):
    __tablename__ = "AUDITORIA_CATEGORIAS"

    id_visita = Column(Integer, ForeignKey("VISITAS_MERCADERISTA.id_visita"), primary_key=True)
    id_categoria = Column(Integer, ForeignKey("CATEGORIAS.id_categoria"), primary_key=True)
    aplico_planograma = Column(Integer, nullable=True)
    lineamiento_marca = Column(Integer, nullable=True)
    precio_correcto = Column(Integer, nullable=True)
    limpieza_correcta = Column(Integer, nullable=True)
    participacion_correcta = Column(Integer, nullable=True)
    fifo_correcto = Column(Integer, nullable=True)
    prox_vencer = Column(Integer, nullable=True)
    prox_vencer_cantidad = Column(Integer, nullable=True)
    prox_vencer_marca = Column(String(200), nullable=True)
    prox_vencer_fecha1 = Column(String(50), nullable=True)
    prox_vencer_fecha2 = Column(String(50), nullable=True)
    competencia_actividad = Column(Integer, nullable=True)
    competencia_material_pop = Column(Integer, nullable=True)
    competencia_impulsadora = Column(Integer, nullable=True)
    pop_hablador = Column(Integer, nullable=True)
    pop_rompetrafico = Column(Integer, nullable=True)
    pop_otro = Column(String(200), nullable=True)
    promo_nuestra = Column(Integer, nullable=True)
    promo_nuestra_desc = Column(String(500), nullable=True)
    promo_competencia = Column(Integer, nullable=True)
    promo_competencia_desc = Column(String(500), nullable=True)
    exhibicion_adicional = Column(Integer, nullable=True)
    exhibicion_tipos = Column(String(500), nullable=True)
