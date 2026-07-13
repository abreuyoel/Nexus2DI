from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class Mercaderista(Base):
    __tablename__ = "MERCADERISTAS"

    id = Column("id_mercaderista", Integer, primary_key=True, index=True)
    cedula = Column(Integer, unique=True, nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    email = Column(String(200), nullable=True)
    telefono = Column(String(50), nullable=True)
    tipo = Column(String(50), nullable=False, default="Mercaderista")
    activo = Column(Boolean, default=True)

    visitas = relationship("Visita", back_populates="mercaderista")
    rutas = relationship("MercaderistaRuta", back_populates="mercaderista")

    @property
    def is_auditor(self) -> bool:
        return self.tipo == "Auditor"

    @property
    def nombre_completo(self) -> str:
        return self.nombre


class MercaderistaRuta(Base):
    __tablename__ = "MERCADERISTAS_RUTAS"

    id = Column("id_mercaderista_ruta", Integer, primary_key=True, index=True)
    mercaderista_id = Column("id_mercaderista", Integer, ForeignKey("MERCADERISTAS.id_mercaderista"), nullable=False)
    ruta_id = Column("id_ruta", Integer, ForeignKey("RUTAS_NUEVAS.id_ruta"), nullable=False)
    tipo_ruta = Column(String(50), nullable=True)

    mercaderista = relationship("Mercaderista", back_populates="rutas")
    ruta = relationship("Ruta", back_populates="mercaderistas")
