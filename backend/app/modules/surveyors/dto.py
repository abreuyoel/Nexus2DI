from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date


class JornadaActivarRequest(BaseModel):
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    ciudad: Optional[str] = None
    estado_geo: Optional[str] = None


class CentroSaludCreate(BaseModel):
    nombre_centro: str
    direccion_completa: str
    ciudad: Optional[str] = None
    estado: Optional[str] = None


class EncuestaCentroCreate(BaseModel):
    id_centro: int
    fuente_informacion: Optional[str] = "Visita presencial"
    notas_generales: Optional[str] = None


class MedicoCentroCreate(BaseModel):
    id_medico: Optional[int] = None
    id_medico_externo: Optional[str] = None
    apellido1: Optional[str] = None
    apellido2: Optional[str] = None
    nombre1: Optional[str] = None
    nombre2: Optional[str] = None
    especialidad: Optional[str] = None
    sub_especialidad: Optional[str] = None
    universidad_graduacion: Optional[str] = None
    nro_MPPS: Optional[str] = None
    nro_colegiado: Optional[str] = None
    ciudad: Optional[str] = None
    estado: Optional[str] = None
    telefono: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    linkedin: Optional[str] = None
    instagram: Optional[str] = None
    
    piso_consultorio: Optional[str] = None
    horarios_consulta: Optional[str] = None
    dias_consulta: Optional[str] = None
    direccion_especifica: Optional[str] = None
    clinica2_nombre: Optional[str] = None
    piso_consultorio2: Optional[str] = None
    horarios_consulta2: Optional[str] = None
    dias_consulta2: Optional[str] = None
    direccion_especifica2: Optional[str] = None
    valor_consulta_rango: str
    promedio_pacientes_semanal_rango: str
