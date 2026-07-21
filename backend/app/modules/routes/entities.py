from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from app.db.base import Base


class Ruta(Base):
    __tablename__ = "RUTAS_NUEVAS"

    id = Column("id_ruta", Integer, primary_key=True, index=True)
    nombre = Column("ruta", String(200), nullable=True, index=True)
    servicio = Column(String(200), nullable=True)
    coordinador_1 = Column(String(200), nullable=True)
    coordinador_2 = Column(String(200), nullable=True)
    supervisor = Column(String(200), nullable=True)
    cuadrante = Column(String(200), nullable=True)
    id_cliente_exclusivo = Column(Integer, ForeignKey("CLIENTES.id_cliente"), nullable=True)

    programaciones = relationship("RutaProgramacion", back_populates="ruta", cascade="all, delete-orphan")
    mercaderistas = relationship("MercaderistaRuta", back_populates="ruta")
    cambios_futuros = relationship("RutaCambioFuturo", back_populates="ruta", cascade="all, delete-orphan")
    activaciones_ruta = relationship("RutaActivada", back_populates="ruta")
    analistas = relationship("AnalistaRuta", back_populates="ruta")
    cliente_exclusivo = relationship("Cliente", foreign_keys=[id_cliente_exclusivo])

    @property
    def activa(self) -> bool:
        return True


class AnalistaRuta(Base):
    __tablename__ = "analistas_rutas"

    id_analista = Column(Integer, primary_key=True)
    id_ruta = Column(Integer, ForeignKey("RUTAS_NUEVAS.id_ruta"), primary_key=True)

    ruta = relationship("Ruta", back_populates="analistas")


class RutaProgramacion(Base):
    __tablename__ = "RUTA_PROGRAMACION"

    id = Column("id_programacion", Integer, primary_key=True, index=True)
    ruta_id = Column("id_ruta", Integer, ForeignKey("RUTAS_NUEVAS.id_ruta"), nullable=False)
    punto_id = Column("id_punto_interes", String(100), ForeignKey("PUNTOS_INTERES1.identificador"), nullable=True)
    dia = Column(String(20), nullable=True)
    activo = Column("activa", Boolean, default=True)
    id_cliente = Column(Integer, ForeignKey("CLIENTES.id_cliente"), nullable=True)
    prioridad = Column(String(50), nullable=True)
    punto_interes_nombre = Column("punto_interes", String(300), nullable=True)

    ruta = relationship("Ruta", back_populates="programaciones")
    punto = relationship("PuntoInteres", back_populates="programaciones")
    cliente = relationship("Cliente")


class RutaCambioFuturo(Base):
    __tablename__ = "RUTA_PROGRAMACION_CAMBIOS_FUTUROS"

    id = Column("id_cambio_futuro", Integer, primary_key=True, index=True)
    id_programacion = Column(Integer, nullable=True)
    ruta_id = Column("id_ruta", ForeignKey("RUTAS_NUEVAS.id_ruta"), nullable=False)
    ruta_nombre = Column(String(200), nullable=True)
    id_punto_interes = Column(String(100), nullable=True)
    punto_interes_nombre = Column(String(300), nullable=True)
    id_cliente = Column(Integer, nullable=True)
    cliente_nombre = Column(String(200), nullable=True)
    dia = Column(String(20), nullable=True)
    prioridad = Column(String(50), nullable=True)
    activa = Column(Boolean, nullable=True)
    tipo_cambio = Column(String(50), default="modificacion", nullable=False)
    fecha_ejecucion = Column("fecha_ejecucion", Date, nullable=True)
    fecha_creacion = Column("fecha_creacion", DateTime, nullable=True)
    creado_por = Column(String(200), nullable=True)
    estado = Column(String(20), default="PENDIENTE")
    fecha_ejecutado = Column(DateTime, nullable=True)
    ejecutado_por = Column(String(200), nullable=True)
    observaciones = Column(String(500), nullable=True)

    ruta = relationship("Ruta", back_populates="cambios_futuros")


class RutaActivada(Base):
    __tablename__ = "RUTAS_ACTIVADAS"

    id = Column(Integer, primary_key=True, index=True)
    ruta_id = Column("id_ruta", Integer, ForeignKey("RUTAS_NUEVAS.id_ruta"), nullable=False)
    mercaderista_id = Column("id_mercaderista", Integer, ForeignKey("MERCADERISTAS.id_mercaderista"), nullable=True)
    fecha_hora_activacion = Column(DateTime, nullable=True)
    estado = Column(String(50), nullable=True)
    tipo_activacion = Column(String(50), nullable=True)
    motivo_no_activacion = Column(String(500), nullable=True)

    ruta = relationship("Ruta", back_populates="activaciones_ruta")


class PuntoInteres(Base):
    __tablename__ = "PUNTOS_INTERES1"

    id = Column("identificador", String(100), primary_key=True, index=True)
    nombre = Column("punto_de_interes", String(300), nullable=True, index=True)
    direccion = Column("Direccion", String(500), nullable=True)
    latitud = Column(String(50), nullable=True)
    longitud = Column(String(50), nullable=True)
    departamento = Column(String(200), nullable=True, index=True)
    jerarquia_n2 = Column("jerarquia_nivel_2", String(200), nullable=True, index=True)
    jerarquia_n2_2 = Column("jerarquia_nivel_2_2", String(200), nullable=True)
    ciudad = Column(String(200), nullable=True, index=True)
    cadena = Column("clasificacion_de_canal", String(200), nullable=True, index=True)
    radio = Column(String(50), nullable=True)
    tiempo_minimo = Column("tiempo_minimo_de_visita", Integer, nullable=True)
    fecha_creado = Column(DateTime, nullable=True)
    nivel_de_alcance = Column(String(200), nullable=True)
    rif = Column(String(50), nullable=True)

    programaciones = relationship("RutaProgramacion", back_populates="punto")
    visitas = relationship("Visita", back_populates="punto")
    activaciones = relationship("Activacion", back_populates="punto")

    @property
    def region(self) -> str | None:
        return self.departamento
