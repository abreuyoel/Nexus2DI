from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import relationship
from app.db.base import Base


class TipoNegocio(Base):
    """Catálogo: Tipo de Negocio (antes 'Jerarquía N2')."""
    __tablename__ = "CAT_TIPO_NEGOCIO"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creado = Column(DateTime, server_default=func.now())


class SubtipoNegocio(Base):
    """Catálogo: Subtipo de Negocio (antes 'Jerarquía N2_2')."""
    __tablename__ = "CAT_SUBTIPO_NEGOCIO"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creado = Column(DateTime, server_default=func.now())


class Alcance(Base):
    """Catálogo: Alcance (antes 'Nivel de Alcance')."""
    __tablename__ = "CAT_ALCANCE"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creado = Column(DateTime, server_default=func.now())


class CanalVenta(Base):
    """Catálogo: Canal de Venta (antes 'Clasificación de Canal')."""
    __tablename__ = "CAT_CANAL_VENTA"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creado = Column(DateTime, server_default=func.now())


class Cuadrante(Base):
    """Catálogo: Cuadrante / Región de ruta (usado en RUTAS_NUEVAS.cuadrante)."""
    __tablename__ = "CUADRANTES"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creado = Column(DateTime, server_default=func.now())


class Servicio(Base):
    """Catálogo: Servicio de ruta (usado en RUTAS_NUEVAS.servicio)."""
    __tablename__ = "SERVICIOS"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creado = Column(DateTime, server_default=func.now())


class DepartamentoGeo(Base):
    __tablename__ = "CAT_DEPARTAMENTOS"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creado = Column(DateTime, server_default=func.now())

    ciudades = relationship("Ciudad", back_populates="departamento_geo", cascade="all, delete-orphan")


class Ciudad(Base):
    __tablename__ = "CAT_CIUDADES"
    __table_args__ = (UniqueConstraint("departamento_id", "nombre", name="uq_ciudad_departamento"),)

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False, index=True)
    departamento_id = Column(Integer, ForeignKey("CAT_DEPARTAMENTOS.id"), nullable=False, index=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creado = Column(DateTime, server_default=func.now())

    departamento_geo = relationship("DepartamentoGeo", back_populates="ciudades")

class Estado(Base):
    """Catálogo: Estados Geográficos"""
    __tablename__ = "CAT_ESTADOS"

    id = Column(Integer, primary_key=True, autoincrement=True)
    nombre = Column(String(200), nullable=False, unique=True, index=True)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creado = Column(DateTime, server_default=func.now())
