from sqlalchemy import Column, Integer, String
from app.db.base import Base


class Rol(Base):
    __tablename__ = "ROLES"

    id = Column("id_rol", Integer, primary_key=True)
    nombre = Column("rol", String(100), nullable=False)
