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

class ConsultorioCreate(BaseModel):
    nombre_clinica: str
    piso_consultorio: Optional[str] = None
    direccion_especifica: Optional[str] = None
    horarios_json: Optional[str] = None
    valor_consulta_rango: str
    promedio_pacientes_semanal_rango: str

class MedicoCentroCreate(BaseModel):
    id_medico: Optional[int] = None
    id_medico_externo: Optional[str] = None
    apellido1: str
    apellido2: str
    nombre1: str
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
    consultorios: List[ConsultorioCreate] = []


class MedicoCentroSaveRequest(BaseModel):
    id_encuesta: int
    id_medico: Optional[int] = None
    medico_data: Optional[MedicoCentroCreate] = None


class MedicoEditRequest(BaseModel):
    id_medico_externo: Optional[str] = None
    apellido1: str
    apellido2: str
    nombre1: str
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
    consultorios: List[ConsultorioCreate] = []


class EncuestaObservacionRequest(BaseModel):
    observacion_supervisor: Optional[str] = None
    requiere_correccion: Optional[bool] = False

