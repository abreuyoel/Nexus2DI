from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Boolean, DateTime, UniqueConstraint, func
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


# ── Dimensiones y Producto (antes models/producto.py) ───────────────────────

class Departamento(Base):
    __tablename__ = "DEPARTAMENTOS"

    id_departamento = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))

    categorias = relationship("Categoria", back_populates="departamento")


class Categoria(Base):
    __tablename__ = "CATEGORIAS"

    id_categoria = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))
    nombre_bi = Column(String(255))
    id_departamento = Column(Integer, ForeignKey("DEPARTAMENTOS.id_departamento"))

    departamento = relationship("Departamento", back_populates="categorias")
    subcategorias = relationship("SubCategoria", back_populates="categoria")


class SubCategoria(Base):
    __tablename__ = "SUBCATEGORIAS"

    id_subcategoria = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))
    nombre_bi = Column(String(255))
    id_categoria = Column(Integer, ForeignKey("CATEGORIAS.id_categoria"))

    categoria = relationship("Categoria", back_populates="subcategorias")
    productos = relationship("Producto", back_populates="subcategoria")


class Productora(Base):
    __tablename__ = "PRODUCTORAS"

    id_productora = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))

    marcas = relationship("Marca", back_populates="productora")


class Marca(Base):
    __tablename__ = "MARCAS"

    id_marca = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))
    id_productora = Column(Integer, ForeignKey("PRODUCTORAS.id_productora"))

    productora = relationship("Productora", back_populates="marcas")
    productos = relationship("Producto", back_populates="marca")


class Presentacion(Base):
    __tablename__ = "PRESENTACIONES"

    id_presentacion = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(255))
    clasificacion_tamanos = Column(String(255))

    productos = relationship("Producto", back_populates="presentacion")


class ClasificacionTamano(Base):
    __tablename__ = "CLASIFICACION_TAMANOS"

    id = Column("id_clasificacion_tamaño", Integer, primary_key=True, index=True)
    nombre = Column("clasificacion", String(255))


class Producto(Base):
    __tablename__ = "PRODUCTS"

    id_producto = Column("id_product", Integer, primary_key=True, index=True)
    producto_gu = Column("producto_gutrade", String(255))
    descripcion_bi = Column("descripcionbi", String(255))
    gramos = Column(Float)
    cod_prod = Column("cod_bar", String(100))
    inagotable = Column("inagotable", Boolean, nullable=True, default=False)
    comentario = Column(Text)

    id_subcategoria = Column(Integer, ForeignKey("SUBCATEGORIAS.id_subcategoria"))
    id_marca = Column(Integer, ForeignKey("MARCAS.id_marca"))
    id_presentacion = Column(Integer, ForeignKey("PRESENTACIONES.id_presentacion"))
    id_categoria = Column(Integer, nullable=True)
    id_departamento = Column(Integer, nullable=True)
    id_productora = Column(Integer, nullable=True)
    id_clasificacion_tamano = Column("id_clasificacion_tamaño", Integer, nullable=True)

    subcategoria = relationship("SubCategoria", back_populates="productos")
    marca = relationship("Marca", back_populates="productos")
    presentacion = relationship("Presentacion", back_populates="productos")
