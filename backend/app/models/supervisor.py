from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.base import Base


class Supervisor(Base):
    __tablename__ = "SUPERVISORES"

    id = Column("id_supervisor", Integer, primary_key=True, index=True)
    nombre = Column("nombre_supervisor", String(200), nullable=False)


class SupervisorRuta(Base):
    __tablename__ = "SUPERVISORES_RUTAS"

    id_supervisor = Column(Integer, ForeignKey("SUPERVISORES.id_supervisor"), primary_key=True)
    id_ruta = Column(Integer, ForeignKey("RUTAS_NUEVAS.id_ruta"), primary_key=True)


class SupervisorCliente(Base):
    __tablename__ = "SUPERVISORES_CLIENTES"

    id_supervisor = Column(Integer, ForeignKey("SUPERVISORES.id_supervisor"), primary_key=True)
    id_cliente = Column(Integer, ForeignKey("CLIENTES.id_cliente"), primary_key=True)
