from sqlalchemy import Column, Integer, String, Float, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from app.db.base import Base

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

    # columna real con ñ: id_clasificacion_tamaño ; el "nombre" es 'clasificacion'
    id = Column("id_clasificacion_tamaño", Integer, primary_key=True, index=True)
    nombre = Column("clasificacion", String(255))


class Producto(Base):
    # Tabla única de productos = PRODUCTS (la BI/snowflake). Los nombres de atributo
    # se mantienen (producto_gu, cod_prod, descripcion_bi, id_producto) mapeados a las
    # columnas reales de PRODUCTS para no tocar el resto del código.
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
    # PRODUCTS también trae estas dimensiones directas (no se usan para mostrar,
    # se deriva por subcategoría para alinear con CATEGORIAS_CLIENTES):
    id_categoria = Column(Integer, nullable=True)
    id_departamento = Column(Integer, nullable=True)
    id_productora = Column(Integer, nullable=True)
    id_clasificacion_tamano = Column("id_clasificacion_tamaño", Integer, nullable=True)

    subcategoria = relationship("SubCategoria", back_populates="productos")
    marca = relationship("Marca", back_populates="productos")
    presentacion = relationship("Presentacion", back_populates="productos")
