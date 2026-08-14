from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, ForeignKey, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class Encuestador(Base):
    """Catálogo de encuestadores (rol 12/13) por cédula -- USUARIOS.id_perfil
    referencia a esta tabla cuando id_rol está en (12, 13), mismo patrón que
    Cliente/Analista/Mercaderista (ver outerjoin en routes/users.py)."""
    __tablename__ = "ENCUESTADORES"

    id = Column("id_encuestador", Integer, primary_key=True, index=True)
    cedula = Column(Integer, unique=True, nullable=False, index=True)
    nombre = Column(String(200), nullable=False)
    telefono = Column(String(50), nullable=True)
    email = Column(String(200), nullable=True)
    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

class JornadaEncuestador(Base):
    __tablename__ = "JORNADAS_ENCUESTADOR"

    id_jornada = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, nullable=False)
    fecha_inicio = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(20), nullable=False)
    # Ubicación de INICIO (donde activó la jornada)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    ciudad = Column(String(100), nullable=True)
    estado_geo = Column(String(100), nullable=True)
    # Ubicación de CIERRE (donde finalizó) -- columnas separadas porque un
    # encuestador se mueve de centro en centro durante el día; sin esto no
    # había forma de saber dónde terminó, solo dónde empezó.
    latitud_fin = Column(Float, nullable=True)
    longitud_fin = Column(Float, nullable=True)
    ciudad_fin = Column(String(100), nullable=True)
    estado_geo_fin = Column(String(100), nullable=True)
    notas = Column(String, nullable=True)

class CentroSalud(Base):
    __tablename__ = "centros_salud"

    id_centro = Column(Integer, primary_key=True, index=True)
    nombre_centro = Column(String(255), nullable=False)
    direccion_completa = Column(String, nullable=False)
    ciudad = Column(String(100), nullable=True)
    estado = Column(String(100), nullable=True)

class EncuestaCentro(Base):
    __tablename__ = "encuestas_centro"

    id_encuesta = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, nullable=False)
    id_centro = Column(Integer, nullable=False)
    fecha_verificacion = Column(Date, nullable=False)
    fuente_informacion = Column(String(255), nullable=False)
    notas_generales = Column(Text, nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow)
    id_jornada = Column(Integer, nullable=True)
    estado = Column(String(20), nullable=False)
    observacion_supervisor = Column(Text, nullable=True)
    requiere_correccion = Column(Boolean, default=False, server_default="0")

class Medico(Base):
    __tablename__ = "medicos"

    id_medico = Column(Integer, primary_key=True, index=True)
    id_medico_externo = Column(String(20), nullable=True)
    apellido1 = Column(String(100), nullable=False)
    apellido2 = Column(String(100), nullable=False)
    nombre1 = Column(String(100), nullable=False)
    nombre2 = Column(String(100), nullable=True)
    especialidad = Column(String(100), nullable=False)
    sub_especialidad = Column(String(100), nullable=True)
    universidad_graduacion = Column(String(255), nullable=True)
    nro_MPPS = Column(String(50), nullable=True)
    nro_colegiado = Column(String(50), nullable=True)
    ciudad = Column(String(100), nullable=False)
    estado = Column(String(100), nullable=False)
    telefono = Column(String(20), nullable=True)
    whatsapp = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    linkedin = Column(String(255), nullable=True)
    instagram = Column(String(255), nullable=True)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

class MedicoConsultorio(Base):
    __tablename__ = 'medico_consultorios'

    id_consultorio = Column(Integer, primary_key=True, index=True)
    id_medico = Column(Integer, ForeignKey('medicos.id_medico'), nullable=False)
    nombre_clinica = Column(String(255), nullable=False)
    piso_consultorio = Column(String(50), nullable=True)
    direccion_especifica = Column(String, nullable=True)
    horarios_json = Column(Text, nullable=True)
    valor_consulta_rango = Column(String(30), nullable=False)
    promedio_pacientes_semanal_rango = Column(String(30), nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

class MedicoCentroEncuesta(Base):
    __tablename__ = "medico_centro_encuesta"

    id_medico_centro = Column(Integer, primary_key=True, index=True)
    id_encuesta = Column(Integer, nullable=False)
    id_medico = Column(Integer, nullable=False)
    actualizado_en = Column(DateTime, default=datetime.utcnow)

class CatalogoEncuestador(Base):
    __tablename__ = "CATALOGOS_ENCUESTADOR"

    id = Column("id_catalogo", Integer, primary_key=True, index=True)
    tipo = Column(String(50), nullable=False, index=True)  # 'especialidad', 'subespecialidad', 'universidad', 'estado', 'ciudad'
    nombre = Column(String(150), nullable=False)
    creado_por = Column(String(150), nullable=True)
    creado_en = Column(DateTime, default=datetime.utcnow, nullable=True)
    modificado_en = Column(DateTime, nullable=True)

    __table_args__ = (
        UniqueConstraint('tipo', 'nombre', name='uq_tipo_nombre'),
    )

