from sqlalchemy import Column, String, Boolean, DateTime, Float, Integer, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base


class PuntoInteres(Base):
    __tablename__ = "PUNTOS_INTERES1"

    id = Column("identificador", String(100), primary_key=True, index=True)
    nombre = Column("punto_de_interes", String(300), nullable=True)
    direccion = Column("Direccion", String(500), nullable=True)
    latitud = Column(String(50), nullable=True)
    longitud = Column(String(50), nullable=True)
    departamento = Column(String(200), nullable=True)
    jerarquia_n2 = Column("jerarquia_nivel_2", String(200), nullable=True)
    jerarquia_n2_2 = Column("jerarquia_nivel_2_2", String(200), nullable=True)
    ciudad = Column(String(200), nullable=True)
    cadena = Column("clasificacion_de_canal", String(200), nullable=True)
    radio = Column(String(50), nullable=True)
    tiempo_minimo = Column("tiempo_minimo_de_visita", Integer, nullable=True)
    fecha_creado = Column(DateTime, nullable=True)
    nivel_de_alcance = Column(String(200), nullable=True)
    rif = Column(String(50), nullable=True)

    programaciones = relationship("RutaProgramacion", back_populates="punto")
    visitas = relationship("Visita", back_populates="punto")
    activaciones = relationship("Activacion", back_populates="punto")

    @property
    def region(self) -> str | None:
        return self.departamento
