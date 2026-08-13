from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel

from app.db.session import get_db
from app.core.dependencies import require_permission
from app.modules.auth.entities import Usuario as User
from app.modules.surveyors.entities import (
    JornadaEncuestador,
    CentroSalud,
    EncuestaCentro,
    Medico,
    MedicoCentroEncuesta,
    MedicoConsultorio,
    Encuestador
)


router = APIRouter(prefix="/api/supervisor-encuestadores", tags=["Supervisor de Encuestadores"])

# --- SCHEMAS ---

class JornadaRequest(BaseModel):
    id_usuario: int
    fecha_inicio: datetime
    fecha_fin: Optional[datetime] = None
    estado: str
    latitud: Optional[float] = None
    longitud: Optional[float] = None
    ciudad: Optional[str] = None
    estado_geo: Optional[str] = None
    notas: Optional[str] = None

class EncuestaRequest(BaseModel):
    id_usuario: int
    id_centro: int
    id_jornada: Optional[int] = None
    fecha_verificacion: date
    fuente_informacion: str
    notas_generales: Optional[str] = None
    estado: str
    observacion_supervisor: Optional[str] = None
    requiere_correccion: Optional[bool] = False

class ConsultorioEdit(BaseModel):
    nombre_clinica: str
    piso_consultorio: Optional[str] = None
    direccion_especifica: Optional[str] = None
    horarios_json: Optional[str] = None
    valor_consulta_rango: str
    promedio_pacientes_semanal_rango: str

class MedicoEditRequest(BaseModel):
    id_medico_externo: str
    apellido1: str
    apellido2: Optional[str] = None
    nombre1: str
    nombre2: Optional[str] = None
    especialidad: str
    sub_especialidad: Optional[str] = None
    universidad_graduacion: Optional[str] = None
    nro_MPPS: Optional[str] = None
    nro_colegiado: Optional[str] = None
    ciudad: str
    estado: str
    telefono: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    linkedin: Optional[str] = None
    instagram: Optional[str] = None
    consultorios: List[ConsultorioEdit] = []

class MedicoCentroSaveRequest(BaseModel):
    id_encuesta: int
    id_medico: Optional[int] = None  # Si ya existe
    medico_data: Optional[MedicoEditRequest] = None  # Si se crea de cero

# --- ENDPOINTS ---

@router.get("/encuestadores")
def get_encuestadores(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    # Trae usuarios con rol admin (8), supervisor (10), analista (11), encuestador (12) o cliente_encuestador (13)
    encuestadores = db.query(User).filter(User.id_rol.in_((8, 10, 11, 12, 13))).order_by(User.username).all()
    result = []
    for u in encuestadores:
        # Buscar perfil de Encuestador si existe por cédula/username o id_perfil
        nombre_real = u.username
        perf = None
        if u.id_perfil:
            perf = db.query(Encuestador).filter(Encuestador.id == u.id_perfil).first()
        if not perf:
            try:
                ced = int(u.username)
                perf = db.query(Encuestador).filter(Encuestador.cedula == ced).first()
            except ValueError:
                pass
        if perf:
            nombre_real = perf.nombre

        result.append({
            "id": u.id,
            "username": u.username,
            "nombre": nombre_real,
            "rol": u.rol,
            "activo": u.activo
        })
    return result


# --- JORNADAS ---

@router.get("/jornadas")
def list_jornadas(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    # Subquery to count surveys per journey in one go
    encuestas_count_sub = db.query(
        EncuestaCentro.id_jornada,
        func.count(EncuestaCentro.id_encuesta).label("encuestas_count")
    ).group_by(EncuestaCentro.id_jornada).subquery()

    query = db.query(
        JornadaEncuestador,
        User.username,
        func.coalesce(encuestas_count_sub.c.encuestas_count, 0).label("encuestas_count")
    ).outerjoin(
        User, User.id == JornadaEncuestador.id_usuario
    ).outerjoin(
        encuestas_count_sub, encuestas_count_sub.c.id_jornada == JornadaEncuestador.id_jornada
    )

    if user_id:
        query = query.filter(JornadaEncuestador.id_usuario == user_id)
    jornadas = query.order_by(desc(JornadaEncuestador.id_jornada)).all()

    result = []
    for j, username, encuestas_count in jornadas:
        result.append({
            "id_jornada": j.id_jornada,
            "id_usuario": j.id_usuario,
            "username": username or "Desconocido",
            "fecha_inicio": j.fecha_inicio.isoformat() if j.fecha_inicio else None,
            "fecha_fin": j.fecha_fin.isoformat() if j.fecha_fin else None,
            "estado": j.estado,
            "latitud": j.latitud,
            "longitud": j.longitud,
            "ciudad": j.ciudad,
            "estado_geo": j.estado_geo,
            "notas": j.notas,
            "encuestas_count": encuestas_count
        })
    return result

@router.get("/jornadas/{id_jornada}/detalle")
def get_jornada_detalle(
    id_jornada: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    jornada = db.query(JornadaEncuestador).filter(JornadaEncuestador.id_jornada == id_jornada).first()
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    u = db.query(User).filter(User.id == jornada.id_usuario).first()

    # Obtener encuestas realizadas en esta jornada
    encuestas = db.query(EncuestaCentro).filter(EncuestaCentro.id_jornada == id_jornada).all()
    encuestas_list = []
    
    for e in encuestas:
        centro = db.query(CentroSalud).filter(CentroSalud.id_centro == e.id_centro).first()
        
        # Obtener médicos registrados en esta encuesta
        medicos_rel = db.query(MedicoCentroEncuesta).filter(MedicoCentroEncuesta.id_encuesta == e.id_encuesta).all()
        medicos_list = []
        for mr in medicos_rel:
            m = db.query(Medico).filter(Medico.id_medico == mr.id_medico).first()
            if m:
                consultorios = db.query(MedicoConsultorio).filter(MedicoConsultorio.id_medico == m.id_medico).all()
                medicos_list.append({
                    "id_medico": m.id_medico,
                    "id_medico_externo": m.id_medico_externo,
                    "apellido1": m.apellido1,
                    "apellido2": m.apellido2,
                    "nombre1": m.nombre1,
                    "nombre2": m.nombre2,
                    "nombre": f"{m.apellido1} {m.apellido2 or ''}, {m.nombre1} {m.nombre2 or ''}".strip(),
                    "especialidad": m.especialidad,
                    "sub_especialidad": m.sub_especialidad,
                    "universidad_graduacion": m.universidad_graduacion,
                    "nro_MPPS": m.nro_MPPS,
                    "nro_colegiado": m.nro_colegiado,
                    "ciudad": m.ciudad,
                    "estado": m.estado,
                    "telefono": m.telefono,
                    "whatsapp": m.whatsapp,
                    "email": m.email,
                    "fecha_registro": m.fecha_registro.isoformat() if m.fecha_registro else None,
                    "consultorios": [{
                        "id_consultorio": c.id_consultorio,
                        "nombre_clinica": c.nombre_clinica,
                        "piso_consultorio": c.piso_consultorio,
                        "direccion_especifica": c.direccion_especifica,
                        "valor_consulta_rango": c.valor_consulta_rango,
                        "promedio_pacientes_semanal_rango": c.promedio_pacientes_semanal_rango,
                        "horarios_json": c.horarios_json
                    } for c in consultorios]
                })
        
        encuestas_list.append({
            "id_encuesta": e.id_encuesta,
            "nombre_centro": centro.nombre_centro if centro else "Centro Desconocido",
            "ciudad": centro.ciudad if centro else None,
            "estado": centro.estado if centro else None,
            "fecha_verificacion": e.fecha_verificacion.isoformat() if e.fecha_verificacion else None,
            "fuente_informacion": e.fuente_informacion,
            "notas_generales": e.notas_generales,
            "estado_encuesta": e.estado,
            "observacion_supervisor": e.observacion_supervisor,
            "requiere_correccion": getattr(e, "requiere_correccion", False),
            "medicos": medicos_list
        })

    return {
        "id_jornada": jornada.id_jornada,
        "username": u.username if u else "Desconocido",
        "fecha_inicio": jornada.fecha_inicio.isoformat() if jornada.fecha_inicio else None,
        "fecha_fin": jornada.fecha_fin.isoformat() if jornada.fecha_fin else None,
        "estado": jornada.estado,
        "ciudad": jornada.ciudad,
        "estado_geo": jornada.estado_geo,
        "notas": jornada.notas,
        "encuestas": encuestas_list
    }

@router.post("/jornadas")
def create_jornada(
    req: JornadaRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "write", fallback_roles=("admin", "supervisor")))
):
    jornada = JornadaEncuestador(
        id_usuario=req.id_usuario,
        fecha_inicio=req.fecha_inicio,
        fecha_fin=req.fecha_fin,
        estado=req.estado,
        latitud=req.latitud,
        longitud=req.longitud,
        ciudad=req.ciudad,
        estado_geo=req.estado_geo,
        notas=req.notas
    )
    db.add(jornada)
    db.commit()
    db.refresh(jornada)
    return {"success": True, "id_jornada": jornada.id_jornada}

@router.put("/jornadas/{id_jornada}")
def update_jornada(
    id_jornada: int,
    req: JornadaRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "write", fallback_roles=("admin", "supervisor")))
):
    j = db.query(JornadaEncuestador).filter(JornadaEncuestador.id_jornada == id_jornada).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    j.id_usuario = req.id_usuario
    j.fecha_inicio = req.fecha_inicio
    j.fecha_fin = req.fecha_fin
    j.estado = req.estado
    j.latitud = req.latitud
    j.longitud = req.longitud
    j.ciudad = req.ciudad
    j.estado_geo = req.estado_geo
    j.notas = req.notas

    db.commit()
    return {"success": True}

@router.delete("/jornadas/{id_jornada}")
def delete_jornada(
    id_jornada: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "delete", fallback_roles=("admin", "supervisor")))
):
    j = db.query(JornadaEncuestador).filter(JornadaEncuestador.id_jornada == id_jornada).first()
    if not j:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    # Eliminar encuestas de esta jornada
    db.query(EncuestaCentro).filter(EncuestaCentro.id_jornada == id_jornada).delete()
    db.delete(j)
    db.commit()
    return {"success": True}


# --- ENCUESTAS ---

@router.get("/encuestas")
def list_encuestas(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    # Subquery to count doctors per survey in one go
    medicos_count_sub = db.query(
        MedicoCentroEncuesta.id_encuesta,
        func.count(MedicoCentroEncuesta.id_medico).label("medicos_count")
    ).group_by(MedicoCentroEncuesta.id_encuesta).subquery()

    query = db.query(
        EncuestaCentro,
        User.username,
        CentroSalud.nombre_centro,
        CentroSalud.ciudad,
        CentroSalud.estado,
        func.coalesce(medicos_count_sub.c.medicos_count, 0).label("medicos_count")
    ).outerjoin(
        User, User.id == EncuestaCentro.id_usuario
    ).outerjoin(
        CentroSalud, CentroSalud.id_centro == EncuestaCentro.id_centro
    ).outerjoin(
        medicos_count_sub, medicos_count_sub.c.id_encuesta == EncuestaCentro.id_encuesta
    )

    if user_id:
        query = query.filter(EncuestaCentro.id_usuario == user_id)
        
    encuestas = query.order_by(desc(EncuestaCentro.id_encuesta)).all()

    result = []
    for e, username, nombre_centro, ciudad, estado, medicos_count in encuestas:
        result.append({
            "id_encuesta": e.id_encuesta,
            "id_usuario": e.id_usuario,
            "username": username or "Desconocido",
            "id_centro": e.id_centro,
            "nombre_centro": nombre_centro or "Centro Desconocido",
            "ciudad": ciudad,
            "estado_geo": estado,
            "fecha_verificacion": e.fecha_verificacion.isoformat() if e.fecha_verificacion else None,
            "fuente_informacion": e.fuente_informacion,
            "notas_generales": e.notas_generales,
            "id_jornada": e.id_jornada,
            "estado": e.estado,
            "observacion_supervisor": e.observacion_supervisor,
            "requiere_correccion": getattr(e, "requiere_correccion", False),
            "medicos_count": medicos_count,
            "medicos": [None] * medicos_count  # Transparent array representation for compatibility
        })
    return result

@router.post("/encuestas")
def create_encuesta(
    req: EncuestaRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "write", fallback_roles=("admin", "supervisor")))
):
    encuesta = EncuestaCentro(
        id_usuario=req.id_usuario,
        id_centro=req.id_centro,
        id_jornada=req.id_jornada,
        fecha_verificacion=req.fecha_verificacion,
        fuente_informacion=req.fuente_informacion,
        notas_generales=req.notas_generales,
        estado=req.estado,
        observacion_supervisor=req.observacion_supervisor,
        requiere_correccion=req.requiere_correccion
    )
    db.add(encuesta)
    db.commit()
    db.refresh(encuesta)
    return {"success": True, "id_encuesta": encuesta.id_encuesta}

@router.put("/encuestas/{id_encuesta}")
def update_encuesta(
    id_encuesta: int,
    req: EncuestaRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "write", fallback_roles=("admin", "supervisor")))
):
    e = db.query(EncuestaCentro).filter(EncuestaCentro.id_encuesta == id_encuesta).first()
    if not e:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")

    e.id_usuario = req.id_usuario
    e.id_centro = req.id_centro
    e.id_jornada = req.id_jornada
    e.fecha_verificacion = req.fecha_verificacion
    e.fuente_informacion = req.fuente_informacion
    e.notas_generales = req.notas_generales
    e.estado = req.estado
    e.observacion_supervisor = req.observacion_supervisor
    e.requiere_correccion = req.requiere_correccion

    db.commit()
    return {"success": True}

@router.delete("/encuestas/{id_encuesta}")
def delete_encuesta(
    id_encuesta: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "delete", fallback_roles=("admin", "supervisor")))
):
    e = db.query(EncuestaCentro).filter(EncuestaCentro.id_encuesta == id_encuesta).first()
    if not e:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")

    # Eliminar relaciones de médicos asociadas a esta encuesta
    db.query(MedicoCentroEncuesta).filter(MedicoCentroEncuesta.id_encuesta == id_encuesta).delete()
    db.delete(e)
    db.commit()
    return {"success": True}


# --- MEDICOS ---

@router.get("/medicos")
def list_medicos(
    q: str = "",
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    query = db.query(Medico)
    if q.strip():
        search = f"%{q.strip()}%"
        query = query.filter(
            or_(
                Medico.id_medico_externo.ilike(search),
                Medico.nombre1.ilike(search),
                Medico.apellido1.ilike(search)
            )
        )
    medicos = query.order_by(Medico.apellido1, Medico.nombre1).limit(100).all()

    result = []
    for m in medicos:
        consultorios = db.query(MedicoConsultorio).filter(MedicoConsultorio.id_medico == m.id_medico).all()
        result.append({
            "id_medico": m.id_medico,
            "id_medico_externo": m.id_medico_externo,
            "apellido1": m.apellido1,
            "apellido2": m.apellido2,
            "nombre1": m.nombre1,
            "nombre2": m.nombre2,
            "especialidad": m.especialidad,
            "sub_especialidad": m.sub_especialidad,
            "universidad_graduacion": m.universidad_graduacion,
            "nro_MPPS": m.nro_MPPS,
            "nro_colegiado": m.nro_colegiado,
            "ciudad": m.ciudad,
            "estado": m.estado,
            "telefono": m.telefono,
            "whatsapp": m.whatsapp,
            "email": m.email,
            "linkedin": m.linkedin,
            "instagram": m.instagram,
            "consultorios": [
                {
                    "nombre_clinica": c.nombre_clinica,
                    "piso_consultorio": c.piso_consultorio,
                    "direccion_especifica": c.direccion_especifica,
                    "horarios_json": c.horarios_json,
                    "valor_consulta_rango": c.valor_consulta_rango,
                    "promedio_pacientes_semanal_rango": c.promedio_pacientes_semanal_rango
                } for c in consultorios
            ]
        })
    return result

@router.post("/medicos")
def create_medico_centro(
    req: MedicoCentroSaveRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "write", fallback_roles=("admin", "supervisor")))
):
    id_medico = req.id_medico
    if not id_medico:
        if not req.medico_data:
            raise HTTPException(status_code=400, detail="Faltan datos del médico para crear")
        
        # Verificar duplicado por id externo
        existente = db.query(Medico).filter(Medico.id_medico_externo == req.medico_data.id_medico_externo).first()
        if existente:
            id_medico = existente.id_medico
        else:
            m = Medico(
                id_medico_externo=req.medico_data.id_medico_externo,
                apellido1=req.medico_data.apellido1,
                apellido2=req.medico_data.apellido2,
                nombre1=req.medico_data.nombre1,
                nombre2=req.medico_data.nombre2,
                especialidad=req.medico_data.especialidad,
                sub_especialidad=req.medico_data.sub_especialidad,
                universidad_graduacion=req.medico_data.universidad_graduacion,
                nro_MPPS=req.medico_data.nro_MPPS,
                nro_colegiado=req.medico_data.nro_colegiado,
                ciudad=req.medico_data.ciudad,
                estado=req.medico_data.estado,
                telefono=req.medico_data.telefono,
                whatsapp=req.medico_data.whatsapp,
                email=req.medico_data.email,
                linkedin=req.medico_data.linkedin,
                instagram=req.medico_data.instagram
            )
            db.add(m)
            db.flush()
            id_medico = m.id_medico
            
            for cons in req.medico_data.consultorios:
                c = MedicoConsultorio(
                    id_medico=id_medico,
                    nombre_clinica=cons.nombre_clinica,
                    piso_consultorio=cons.piso_consultorio,
                    direccion_especifica=cons.direccion_especifica,
                    horarios_json=cons.horarios_json,
                    valor_consulta_rango=cons.valor_consulta_rango,
                    promedio_pacientes_semanal_rango=cons.promedio_pacientes_semanal_rango
                )
                db.add(c)

    # Vincular a la encuesta
    dup = db.query(MedicoCentroEncuesta).filter(
        MedicoCentroEncuesta.id_encuesta == req.id_encuesta,
        MedicoCentroEncuesta.id_medico == id_medico
    ).first()
    
    if not dup:
        db.add(MedicoCentroEncuesta(id_encuesta=req.id_encuesta, id_medico=id_medico))
    
    db.commit()
    return {"success": True, "id_medico": id_medico}

@router.put("/medicos/{id_medico}")
def update_medico(
    id_medico: int,
    req: MedicoEditRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "write", fallback_roles=("admin", "supervisor")))
):
    m = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not m:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    m.id_medico_externo = req.id_medico_externo
    m.apellido1 = req.apellido1
    m.apellido2 = req.apellido2
    m.nombre1 = req.nombre1
    m.nombre2 = req.nombre2
    m.especialidad = req.especialidad
    m.sub_especialidad = req.sub_especialidad
    m.universidad_graduacion = req.universidad_graduacion
    m.nro_MPPS = req.nro_MPPS
    m.nro_colegiado = req.nro_colegiado
    m.ciudad = req.ciudad
    m.estado = req.estado
    m.telefono = req.telefono
    m.whatsapp = req.whatsapp
    m.email = req.email
    m.linkedin = req.linkedin
    m.instagram = req.instagram

    # Actualizar consultorios: eliminamos y recreamos
    db.query(MedicoConsultorio).filter(MedicoConsultorio.id_medico == id_medico).delete()
    for cons in req.consultorios:
        c = MedicoConsultorio(
            id_medico=id_medico,
            nombre_clinica=cons.nombre_clinica,
            piso_consultorio=cons.piso_consultorio,
            direccion_especifica=cons.direccion_especifica,
            horarios_json=cons.horarios_json,
            valor_consulta_rango=cons.valor_consulta_rango,
            promedio_pacientes_semanal_rango=cons.promedio_pacientes_semanal_rango
        )
        db.add(c)

    db.commit()
    return {"success": True}

@router.delete("/medicos/{id_medico}")
def delete_medico_relacion(
    id_medico: int,
    id_encuesta: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "delete", fallback_roles=("admin", "supervisor")))
):
    # Desvincular de la encuesta
    db.query(MedicoCentroEncuesta).filter(
        MedicoCentroEncuesta.id_encuesta == id_encuesta,
        MedicoCentroEncuesta.id_medico == id_medico
    ).delete()
    db.commit()
    return {"success": True}

# --- CENTROS (REUTILIZADOS) ---

@router.get("/centros")
def get_centros_list(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    centros = db.query(CentroSalud).order_by(CentroSalud.nombre_centro).all()
    return {
        "success": True,
        "centros": [
            {
                "id_centro": c.id_centro,
                "nombre_centro": c.nombre_centro,
                "direccion_completa": c.direccion_completa,
                "ciudad": c.ciudad,
                "estado": c.estado
            } for c in centros
        ]
    }
