from sqlalchemy import Column, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, func
from app.db.base import Base


class SkuCompetencia(Base):
    """Por cliente: qué SKU propio (PRODUCTS.id_product) se enfrenta contra
    qué SKU(s) de la competencia. Sirve para que el cliente acote qué
    productos deben cargar los mercaderistas en vez de toda la categoría."""
    __tablename__ = "SKU_COMPETENCIA"

    id = Column("id_sku_competencia", Integer, primary_key=True, index=True)
    id_cliente = Column(Integer, ForeignKey("CLIENTES.id_cliente"), nullable=False)
    id_producto_cliente = Column(Integer, ForeignKey("PRODUCTS.id_product"), nullable=False)
    id_producto_competencia = Column(Integer, ForeignKey("PRODUCTS.id_product"), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("id_cliente", "id_producto_cliente", "id_producto_competencia", name="UQ_SkuCompetencia"),
    )
