from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Text, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.db.base import Base

class JornadaEncuestador(Base):
    __tablename__ = "JORNADAS_ENCUESTADOR"

    id_jornada = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, nullable=False)
    fecha_inicio = Column(DateTime, nullable=False, default=datetime.utcnow)
    fecha_fin = Column(DateTime, nullable=True)
    estado = Column(String(20), nullable=False)
    latitud = Column(Float, nullable=True)
    longitud = Column(Float, nullable=True)
    ciudad = Column(String(100), nullable=True)
    estado_geo = Column(String(100), nullable=True)
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

class Medico(Base):
    __tablename__ = "medicos"

    id_medico = Column(Integer, primary_key=True, index=True)
    id_medico_externo = Column(String(20), nullable=False)
    apellido1 = Column(String(100), nullable=False)
    apellido2 = Column(String(100), nullable=True)
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

class MedicoCentroEncuesta(Base):
    __tablename__ = "medico_centro_encuesta"

    id_medico_centro = Column(Integer, primary_key=True, index=True)
    id_encuesta = Column(Integer, nullable=False)
    id_medico = Column(Integer, nullable=False)
    piso_consultorio = Column(String(50), nullable=True)
    horarios_consulta = Column(String(255), nullable=True)
    dias_consulta = Column(String(255), nullable=True)
    direccion_especifica = Column(String, nullable=True)
    clinica2_nombre = Column(String(255), nullable=True)
    piso_consultorio2 = Column(String(50), nullable=True)
    horarios_consulta2 = Column(String(255), nullable=True)
    dias_consulta2 = Column(String(255), nullable=True)
    direccion_especifica2 = Column(String, nullable=True)
    valor_consulta_rango = Column(String(30), nullable=False)
    promedio_pacientes_semanal_rango = Column(String(30), nullable=False)
    actualizado_en = Column(DateTime, default=datetime.utcnow)
