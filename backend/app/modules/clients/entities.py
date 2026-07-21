from sqlalchemy import Column, Integer, String, Boolean, ForeignKey, DateTime, func
from app.db.base import Base
from sqlalchemy.orm import relationship


class Cliente(Base):
    __tablename__ = "CLIENTES"

    id = Column("id_cliente", Integer, primary_key=True, index=True)
    nombre = Column("cliente", String(200), nullable=False)


class CategoriaCliente(Base):
    __tablename__ = "CATEGORIAS_CLIENTES"

    id_categoria = Column(Integer, ForeignKey("CATEGORIAS.id_categoria"), primary_key=True)
    id_cliente = Column(Integer, ForeignKey("CLIENTES.id_cliente"), primary_key=True)


class ClienteRuta(Base):
    """Rutas visibles para un USUARIO con rol Cliente (visibilidad segmentada).

    Un usuario cliente solo ve las rutas asignadas aquí; el id_cliente para
    filtrar la programación se deriva de USUARIOS.id_perfil."""
    __tablename__ = "CLIENTES_RUTAS"

    id = Column("id_cliente_ruta", Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("USUARIOS.id_usuario"), nullable=False)
    id_ruta = Column(Integer, ForeignKey("RUTAS_NUEVAS.id_ruta"), nullable=False)
    activo = Column(Boolean, nullable=False, default=True)
    fecha_creacion = Column(DateTime, server_default=func.now())
