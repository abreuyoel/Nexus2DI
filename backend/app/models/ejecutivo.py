from sqlalchemy import Column, Integer, String
from app.db.base import Base


class Ejecutivo(Base):
    __tablename__ = "EJECUTIVOS"

    id = Column("id_ejecutivo", Integer, primary_key=True, index=True)
    nombre = Column("nombre_ejecutivo", String(200), nullable=False)
