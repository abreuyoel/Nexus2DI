from typing import Optional
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text
from sqlalchemy.orm import relationship
from app.db.base import Base


class Foto(Base):
    __tablename__ = "FOTOS_TOTALES"

    id = Column("id_foto", Integer, primary_key=True, index=True)
    visita_id = Column("id_visita", Integer, ForeignKey("VISITAS_MERCADERISTA.id_visita"), nullable=True)
    id_tipo_foto = Column(Integer, nullable=True)
    categoria = Column(Integer, nullable=True)
    blob_path = Column("file_path", String(500), nullable=True)
    fecha_registro = Column(DateTime, nullable=True)
    estado = Column("Estado", String(50), default="pendiente")
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    altitud = Column(Float, nullable=True)
    exif_timestamp = Column("fecha_disparo", DateTime, nullable=True)
    fabricante_camara = Column(String(200), nullable=True)
    camera_model = Column("modelo_camara", String(200), nullable=True)
    iso = Column(Integer, nullable=True)
    apertura = Column(String(50), nullable=True)
    tiempo_exposicion = Column(String(50), nullable=True)
    orientacion = Column(Integer, nullable=True)

    visita = relationship("Visita", back_populates="fotos")
    notificaciones = relationship("NotificacionRechazoFoto", back_populates="foto", cascade="all, delete-orphan")

    TIPO_GESTION_ANTES = 1
    TIPO_GESTION_DESPUES = 2
    TIPO_PRECIO = 3
    TIPO_EXHIBICION = 4
    TIPO_POP_ANTES = 8
    TIPO_POP_DESPUES = 9

    @property
    def url(self) -> Optional[str]:
        if not self.blob_path:
            return None
        from app.services.azure_service import azure_service
        return azure_service.get_sas_url(self.blob_path)


class NotificacionRechazoFoto(Base):
    __tablename__ = "NOTIFICACIONES_RECHAZO_FOTOS"

    id = Column("id_notificacion", Integer, primary_key=True, index=True)
    foto_id = Column("id_foto_original", Integer, ForeignKey("FOTOS_TOTALES.id_foto"), nullable=True)
    id_foto_rechazada = Column(Integer, nullable=True)
    id_visita = Column(Integer, nullable=True)
    id_cliente = Column(Integer, nullable=True)
    nombre_cliente = Column(String(200), nullable=True)
    punto_venta = Column(String(300), nullable=True)
    rechazado_por = Column(String(100), nullable=True)
    fecha_rechazo = Column(DateTime, nullable=True)
    fecha_notificacion = Column(DateTime, nullable=True)
    leida = Column("leido", Boolean, default=False)
    descripcion = Column(Text, nullable=True)

    foto = relationship("Foto", back_populates="notificaciones")


class PushSubscription(Base):
    __tablename__ = "PUSH_SUBSCRIPTIONS"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("USUARIOS.id_usuario"), nullable=True)
    mercaderista_cedula = Column(String(20), nullable=True)
    endpoint = Column(String(1000), nullable=False)
    p256dh = Column(String(500), nullable=False)
    auth = Column(String(200), nullable=False)
    created_at = Column(DateTime, nullable=True)
