from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base

ROL_MAP: dict[int, str] = {
    1: "client",        # Cliente
    2: "analyst",       # Analista
    3: "coordinador_exclusivo",  # Coordinador Exclusivo
    4: "coordinador_tradex",     # Coordinador Tradex
    5: "mercaderista",  # Mercaderista
    6: "supervisor",    # Supervisor
    7: "auditor",       # Auditor
    8: "admin",         # Administrador
    9: "vendedor",      # Vendedor
    10: "atc",          # Atencion al Cliente
    11: "coordinador_general",   # Coordinador General
    12: "encuestador",  # Encuestador
    13: "cliente_encuestador", # Cliente Encuestador
    14: "auditor_campo", # Auditor de Campo
}


class Rol(Base):
    __tablename__ = "ROLES"

    id = Column("id_rol", Integer, primary_key=True)
    nombre = Column("rol", String(100), nullable=False)


class Usuario(Base):
    __tablename__ = "USUARIOS"

    id = Column("id_usuario", Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column("password_hash", String(255), nullable=False)
    email = Column(String(200), nullable=True)
    id_rol = Column(Integer, ForeignKey("ROLES.id_rol"), nullable=True)
    id_perfil = Column(Integer, nullable=True)
    activo = Column(Boolean, default=True)

    rol_obj = relationship(Rol, lazy="joined", foreign_keys=[id_rol])
    sesiones = relationship("SesionActiva", back_populates="usuario", cascade="all, delete-orphan")
    solicitudes = relationship("Solicitud", back_populates="usuario", cascade="all, delete-orphan")
    permisos = relationship("UserPermission", back_populates="usuario", cascade="all, delete-orphan", lazy="noload")

    @property
    def rol(self) -> str:
        return ROL_MAP.get(self.id_rol or 0, "client")

    @property
    def rol_nombre(self) -> str:
        return self.rol_obj.nombre if self.rol_obj else ROL_MAP.get(self.id_rol or 0, "client")

    @property
    def is_admin(self) -> bool:
        return self.id_rol == 8

    @property
    def is_analyst(self) -> bool:
        return self.id_rol == 2

    @property
    def is_supervisor(self) -> bool:
        return self.id_rol == 6

    @property
    def is_client(self) -> bool:
        return self.id_rol in (1, 3, 4, 9, 11, 12) or self.rol == "client"

    @property
    def is_atc(self) -> bool:
        return self.id_rol == 10

    @property
    def is_mercaderista(self) -> bool:
        return self.id_rol == 5

    @property
    def is_auditor_campo(self) -> bool:
        return self.id_rol == 14

    @property
    def is_vendedor(self) -> bool:
        return self.id_rol == 9

    @property
    def is_coordinador_exclusivo(self) -> bool:
        return self.id_rol == 3

    @property
    def is_coordinador_tradex(self) -> bool:
        return self.id_rol == 4

    @property
    def is_coordinador_general(self) -> bool:
        return self.id_rol == 11

    @property
    def is_coordinador(self) -> bool:
        return self.id_rol in (3, 4, 11)

    def has_permission(self, module: str, action: str) -> bool:
        if self.is_admin:
            return True
        p = next((p for p in self.permisos if p.module == module), None)
        if not p:
            return False
        if action == 'read': return p.can_read
        if action == 'write': return p.can_write
        if action == 'delete': return p.can_delete
        return False


class UserPermission(Base):
    __tablename__ = "usuario_permisos"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column("id_usuario", Integer, ForeignKey("USUARIOS.id_usuario"), nullable=False)
    module = Column(String(50), nullable=False)
    can_read = Column(Boolean, default=True)
    can_write = Column(Boolean, default=False)
    can_delete = Column(Boolean, default=False)
    can_see_all = Column(Boolean, default=False)

    usuario = relationship("Usuario", back_populates="permisos")


class SesionActiva(Base):
    __tablename__ = "SESIONES_ACTIVAS"

    id = Column("id_sesion", Integer, primary_key=True, index=True)
    user_id = Column("id_usuario", Integer, ForeignKey("USUARIOS.id_usuario"), nullable=False)
    username = Column(String(100), nullable=True)
    rol = Column(String(50), nullable=True)
    session_token = Column("session_id", String(1000), nullable=False, unique=True)
    ip_address = Column(String(100), nullable=True)
    user_agent = Column(String(500), nullable=True)
    activa = Column(Boolean, default=True)
    created_at = Column("fecha_inicio", DateTime, nullable=True)
    last_active = Column("ultimo_acceso", DateTime, nullable=True)
    fecha_cierre = Column(DateTime, nullable=True)
    motivo_cierre = Column(String(100), nullable=True)

    usuario = relationship("Usuario", back_populates="sesiones")
