from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base


class Analista(Base):
    __tablename__ = "ANALISTAS"

    id = Column("id_analista", Integer, primary_key=True, index=True)
    nombre = Column("nombre_analista", String(200), nullable=False)
    id_rol = Column(Integer, ForeignKey("ROLES.id_rol"), nullable=True)


class AnalistaCliente(Base):
    __tablename__ = "ANALISTAS_CLIENTE"

    id_analista = Column(Integer, ForeignKey("ANALISTAS.id_analista"), primary_key=True)
    id_cliente = Column(Integer, ForeignKey("CLIENTES.id_cliente"), primary_key=True)
