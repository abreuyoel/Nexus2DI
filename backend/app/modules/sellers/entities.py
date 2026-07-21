from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Numeric
from sqlalchemy.orm import relationship
from app.db.base import Base


class VendedorJornada(Base):
    __tablename__ = "VENDEDOR_JORNADAS"

    id = Column("id_jornada", Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("USUARIOS.id_usuario"), nullable=False)
    fecha_inicio = Column(DateTime, nullable=False)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(50), nullable=False, default="En Progreso")

    usuario = relationship("Usuario")
    visitas = relationship("VendedorVisita", back_populates="jornada", cascade="all, delete-orphan")


class VendedorVisita(Base):
    __tablename__ = "VENDEDOR_VISITAS"

    id = Column("id_visita_vendedor", Integer, primary_key=True, index=True)
    id_jornada = Column(Integer, ForeignKey("VENDEDOR_JORNADAS.id_jornada"), nullable=False)
    id_usuario = Column(Integer, ForeignKey("USUARIOS.id_usuario"), nullable=False)
    id_punto_interes = Column(String(100), ForeignKey("PUNTOS_INTERES1.identificador"), nullable=False)
    id_cliente = Column(Integer, ForeignKey("CLIENTES.id_cliente"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False)
    vendio = Column(Boolean, nullable=False, default=False)
    monto = Column(Numeric(12, 2), nullable=True)
    razon_no_venta = Column(String(500), nullable=True)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)

    jornada = relationship("VendedorJornada", back_populates="visitas")
    usuario = relationship("Usuario")
    punto = relationship("PuntoInteres")
    cliente = relationship("Cliente")
