from sqlalchemy import Column, Integer, String, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.db.base import Base
from app.models.rol import Rol

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
    15: "ejecutivo_cuenta", # Ejecutivo de Cuenta
}


class Usuario(Base):
    __tablename__ = "USUARIOS"

    id = Column("id_usuario", Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    password = Column("password_hash", String(255), nullable=False)
    email = Column(String(200), nullable=True)
    cedula = Column(String(50), nullable=True)
    id_rol = Column(Integer, ForeignKey("ROLES.id_rol"), nullable=True)
    id_perfil = Column(Integer, nullable=True)
    activo = Column(Boolean, default=True)

    # lazy="select" en lugar de "joined": el JOIN a ROLES ocurría en CADA
    # carga de Usuario aunque casi nunca se necesite rol_obj directamente.
    # rol_nombre ahora usa un dict local (cero queries extra).
    rol_obj = relationship(Rol, lazy="noload", foreign_keys=[id_rol])
    sesiones = relationship("SesionActiva", back_populates="usuario", cascade="all, delete-orphan", lazy="noload")
    solicitudes = relationship("Solicitud", back_populates="usuario", cascade="all, delete-orphan", lazy="noload")
    permisos = relationship("UserPermission", back_populates="usuario", cascade="all, delete-orphan", lazy="noload")

    @property
    def rol(self) -> str:
        return ROL_MAP.get(self.id_rol or 0, "client")

    @property
    def rol_nombre(self) -> str:
        # Lookup local — sin tocar DB ni rol_obj (0 queries adicionales)
        _nombres: dict[int, str] = {
            1: "Cliente",
            2: "Analista",
            3: "Coordinador Exclusivo",
            4: "Coordinador Tradex",
            5: "Mercaderista",
            6: "Supervisor",
            7: "Auditor",
            8: "Administrador",
            9: "Vendedor",
            10: "Atención al Cliente",
            11: "Coordinador General",
            12: "Encuestador",
            13: "Cliente Encuestador",
            14: "Auditor de Campo",
            15: "Ejecutivo de Cuenta",
        }
        return _nombres.get(self.id_rol or 0, ROL_MAP.get(self.id_rol or 0, "Usuario"))

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
        # 10 (Atención al Cliente) NO es cliente — es un rol propio (atc).
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

    @property
    def is_ejecutivo_cuenta(self) -> bool:
        return self.id_rol == 15


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
