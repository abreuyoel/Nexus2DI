from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Date
from sqlalchemy.orm import relationship
from app.db.base import Base


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
