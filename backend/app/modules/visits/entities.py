from typing import Optional
from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Float, Text, Date
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
    motivo_rechazo = Column("motivo_rechazo", String(500), nullable=True)
    revisada_por = Column("revisada_por", String(100), nullable=True)
    fecha_revision = Column("fecha_revision", DateTime, nullable=True)
    comentario = Column("comentario", Text, nullable=True)
    ultimo_rechazo_por_paso1 = Column("ultimo_rechazo_por_paso1", String(100), nullable=True)
    ultima_fecha_rechazo_paso1 = Column("ultima_fecha_rechazo_paso1", DateTime, nullable=True)

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
        from app.shared.azure_service import azure_service
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


class FotoRazonRechazo(Base):
    __tablename__ = "FOTOS_RAZONES_RECHAZOS"

    id = Column("id_foto_razon", Integer, primary_key=True, index=True)
    id_foto = Column(Integer, nullable=False, index=True)
    id_razones_rechazos = Column(Integer, nullable=False)
    rechazado_por = Column(Integer, nullable=True)
    fecha = Column(DateTime, default=datetime.now)


class RazonRechazo(Base):
    __tablename__ = "RAZONES_RECHAZOS"

    id = Column("id_razones_rechazos", Integer, primary_key=True, index=True)
    razon = Column(String(300), nullable=False)


class TipoFoto(Base):
    __tablename__ = "TIPOS_FOTOS"

    id = Column("id_tipo_foto", Integer, primary_key=True, index=True)
    nombre = Column("tipo_foto", String(200), nullable=True)


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


class PushSubscription(Base):
    __tablename__ = "PUSH_SUBSCRIPTIONS"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("USUARIOS.id_usuario"), nullable=True)
    mercaderista_cedula = Column(String(20), nullable=True)
    endpoint = Column(String(1000), nullable=False)
    p256dh = Column(String(500), nullable=False)
    auth = Column(String(200), nullable=False)
    created_at = Column(DateTime, nullable=True)


class Balance(Base):
    __tablename__ = "BALANCES_TOTALES"

    id = Column("id_balance", Integer, primary_key=True, index=True)
    id_cliente = Column("id_cliente", Integer, ForeignKey("CLIENTES.id_cliente"), nullable=True)
    fecha_balance = Column("fecha_balance", DateTime, nullable=True)
    identificador_pdv = Column("identificador_pdv", String(100), nullable=True)
    mercaderista = Column("mercaderista", String(100), nullable=True)
    producto = Column("producto", String(255), nullable=True)
    id_categoria = Column("id_categoria", Integer, nullable=True)
    categoria = Column("categoria", String(100), nullable=True)
    fabricante = Column("fabricante", String(100), nullable=True)
    inv_inicial = Column("inv_inicial", Float, nullable=True)
    inv_final = Column("inv_final", Float, nullable=True)
    inv_deposito = Column("inv_deposito", Float, nullable=True)
    caras = Column("caras", Integer, nullable=True)
    precio_bs = Column("precio_bs", Float, nullable=True)
    precio_ds = Column("precio_ds", Float, nullable=True)
    visita_id = Column("id_visita", Integer, ForeignKey("VISITAS_MERCADERISTA.id_visita"), nullable=True)
    fecha_inicio_modificacion = Column("fecha_inicio_modificacion", DateTime, nullable=True)
    fecha_modificacion = Column("fecha_modificacion", DateTime, nullable=True)

    visita = relationship("Visita", backref="balances")
