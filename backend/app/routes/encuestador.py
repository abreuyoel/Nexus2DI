from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func
from typing import List, Any
from datetime import datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario as User
from app.models.encuestador import JornadaEncuestador, CentroSalud, EncuestaCentro, Medico, MedicoCentroEncuesta
from app.schemas.encuestador import JornadaActivarRequest, CentroSaludCreate, EncuestaCentroCreate, MedicoCentroCreate

router = APIRouter(prefix="/api/encuestador", tags=["Encuestador"])

def check_rol_encuestador(current_user: User):
    if current_user.id_rol != 12 and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso denegado. Solo para Encuestadores.")

@router.get("/jornada-activa")
def api_jornada_activa(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    jornada = db.query(JornadaEncuestador).filter(
        JornadaEncuestador.id_usuario == current_user.id,
        JornadaEncuestador.estado == 'En Progreso'
    ).order_by(desc(JornadaEncuestador.id_jornada)).first()
    
    if not jornada:
        return {"success": True, "activa": False}
        
    medicos_registrados = db.query(func.count(MedicoCentroEncuesta.id_medico_centro)).join(
        EncuestaCentro, EncuestaCentro.id_encuesta == MedicoCentroEncuesta.id_encuesta
    ).filter(EncuestaCentro.id_jornada == jornada.id_jornada).scalar() or 0
    
    centros_visitados = db.query(func.count(func.distinct(EncuestaCentro.id_centro))).filter(
        EncuestaCentro.id_jornada == jornada.id_jornada
    ).scalar() or 0
    
    return {
        "success": True,
        "activa": True,
        "id_jornada": jornada.id_jornada,
        "fecha_inicio": jornada.fecha_inicio.isoformat() if jornada.fecha_inicio else None,
        "ciudad": jornada.ciudad,
        "estado_geo": jornada.estado_geo,
        "medicos_registrados": medicos_registrados,
        "centros_visitados": centros_visitados
    }

@router.post("/activar-jornada")
def api_activar_jornada(req: JornadaActivarRequest, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    existente = db.query(JornadaEncuestador).filter(
        JornadaEncuestador.id_usuario == current_user.id,
        JornadaEncuestador.estado == 'En Progreso'
    ).first()
    if existente:
        return {"success": True, "id_jornada": existente.id_jornada, "ya_activa": True}
        
    nueva_jornada = JornadaEncuestador(
        id_usuario=current_user.id,
        estado='En Progreso',
        latitud=req.latitud,
        longitud=req.longitud,
        ciudad=req.ciudad.strip() if req.ciudad else None,
        estado_geo=req.estado_geo.strip() if req.estado_geo else None
    )
    db.add(nueva_jornada)
    db.commit()
    db.refresh(nueva_jornada)
    
    return {
        "success": True, 
        "id_jornada": nueva_jornada.id_jornada, 
        "fecha_inicio": nueva_jornada.fecha_inicio.isoformat() if nueva_jornada.fecha_inicio else None
    }

@router.post("/finalizar-jornada")
def api_finalizar_jornada(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    jornada = db.query(JornadaEncuestador).filter(
        JornadaEncuestador.id_usuario == current_user.id,
        JornadaEncuestador.estado == 'En Progreso'
    ).first()
    
    if jornada:
        # Cerrar encuestas abiertas
        encuestas_abiertas = db.query(EncuestaCentro).filter(
            EncuestaCentro.id_jornada == jornada.id_jornada,
            EncuestaCentro.estado == 'Abierta'
        ).all()
        for e in encuestas_abiertas:
            e.estado = 'Cerrada'
            
        jornada.estado = 'Finalizada'
        jornada.fecha_fin = datetime.utcnow()
        db.commit()
        
    return {"success": True, "message": "Jornada finalizada"}

@router.get("/centros")
def api_centros_list(q: str = "", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    query = db.query(CentroSalud)
    if q.strip():
        search = f"%{q.strip()}%"
        query = query.filter(
            or_(
                CentroSalud.nombre_centro.ilike(search),
                CentroSalud.ciudad.ilike(search),
                CentroSalud.estado.ilike(search)
            )
        )
    centros = query.order_by(CentroSalud.nombre_centro).limit(50).all()
    
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

import json
from app.models.solicitud import Solicitud

@router.post("/centros")
def api_centros_create(req: CentroSaludCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    datos_centro = {
        "nombre_centro": req.nombre_centro.strip(),
        "direccion_completa": req.direccion_completa.strip(),
        "ciudad": req.ciudad.strip() if req.ciudad else None,
        "estado": req.estado.strip() if req.estado else None
    }
    
    nueva_solicitud = Solicitud(
        user_id=current_user.id,
        tipo="creacion_centro_salud",
        descripcion=json.dumps(datos_centro),
        estado="pendiente"
    )
    db.add(nueva_solicitud)
    db.commit()
    db.refresh(nueva_solicitud)
    
    return {
        "success": True,
        "solicitud_id": nueva_solicitud.id,
        "message": "Solicitud de creación de centro enviada a Atención al Cliente para su aprobación."
    }

@router.get("/encuesta-abierta")
def api_encuesta_abierta(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    jornada = db.query(JornadaEncuestador).filter(
        JornadaEncuestador.id_usuario == current_user.id,
        JornadaEncuestador.estado == 'En Progreso'
    ).first()
    
    if not jornada:
        return {"success": True, "tiene_encuesta": False, "jornada_activa": False}
        
    encuesta = db.query(EncuestaCentro, CentroSalud).join(
        CentroSalud, CentroSalud.id_centro == EncuestaCentro.id_centro
    ).filter(
        EncuestaCentro.id_jornada == jornada.id_jornada,
        EncuestaCentro.estado == 'Abierta'
    ).order_by(desc(EncuestaCentro.id_encuesta)).first()
    
    if not encuesta:
        return {"success": True, "tiene_encuesta": False, "jornada_activa": True, "id_jornada": jornada.id_jornada}
        
    ec, cs = encuesta
    
    medicos_cargados = db.query(Medico, MedicoCentroEncuesta).join(
        MedicoCentroEncuesta, MedicoCentroEncuesta.id_medico == Medico.id_medico
    ).filter(
        MedicoCentroEncuesta.id_encuesta == ec.id_encuesta
    ).order_by(desc(MedicoCentroEncuesta.id_medico_centro)).all()
    
    return {
        "success": True,
        "tiene_encuesta": True,
        "jornada_activa": True,
        "id_jornada": jornada.id_jornada,
        "id_encuesta": ec.id_encuesta,
        "id_centro": cs.id_centro,
        "nombre_centro": cs.nombre_centro,
        "ciudad": cs.ciudad,
        "estado": cs.estado,
        "fecha_verificacion": ec.fecha_verificacion.isoformat() if ec.fecha_verificacion else None,
        "fuente_informacion": ec.fuente_informacion,
        "medicos": [
            {
                "id_medico_centro": mce.id_medico_centro,
                "id_medico_externo": m.id_medico_externo,
                "apellido1": m.apellido1,
                "apellido2": m.apellido2,
                "nombre1": m.nombre1,
                "nombre2": m.nombre2,
                "especialidad": m.especialidad,
                "valor_consulta_rango": mce.valor_consulta_rango,
                "promedio_pacientes_semanal_rango": mce.promedio_pacientes_semanal_rango
            } for m, mce in medicos_cargados
        ]
    }

@router.post("/encuestas")
def api_encuestas_crear(req: EncuestaCentroCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    jornada = db.query(JornadaEncuestador).filter(
        JornadaEncuestador.id_usuario == current_user.id,
        JornadaEncuestador.estado == 'En Progreso'
    ).first()
    
    if not jornada:
        raise HTTPException(status_code=400, detail="Debes activar una jornada primero")
        
    existente = db.query(EncuestaCentro).filter(
        EncuestaCentro.id_jornada == jornada.id_jornada,
        EncuestaCentro.estado == 'Abierta'
    ).first()
    
    if existente:
        raise HTTPException(status_code=409, detail=f"Ya tienes una encuesta abierta. Ciérrala antes de iniciar otra (ID {existente.id_encuesta}).")
        
    nueva_encuesta = EncuestaCentro(
        id_usuario=current_user.id,
        id_centro=req.id_centro,
        id_jornada=jornada.id_jornada,
        fecha_verificacion=datetime.utcnow().date(),
        fuente_informacion=req.fuente_informacion,
        notas_generales=req.notas_generales,
        estado='Abierta'
    )
    db.add(nueva_encuesta)
    db.commit()
    db.refresh(nueva_encuesta)
    
    return {"success": True, "id_encuesta": nueva_encuesta.id_encuesta, "id_jornada": jornada.id_jornada}

@router.post("/encuestas/{id_encuesta}/cerrar")
def api_encuesta_cerrar(id_encuesta: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    encuesta = db.query(EncuestaCentro).filter(
        EncuestaCentro.id_encuesta == id_encuesta,
        EncuestaCentro.id_usuario == current_user.id
    ).first()
    
    if encuesta:
        encuesta.estado = 'Cerrada'
        db.commit()
        
    return {"success": True}

@router.get("/medicos/buscar")
def api_medicos_buscar(q: str = "", db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    if not q.strip():
        return {"success": True, "medicos": []}
        
    search = f"%{q.strip()}%"
    medicos = db.query(Medico).filter(
        or_(
            Medico.id_medico_externo.ilike(search),
            Medico.apellido1.ilike(search),
            Medico.apellido2.ilike(search),
            Medico.nombre1.ilike(search),
            Medico.nombre2.ilike(search)
        )
    ).order_by(Medico.apellido1, Medico.nombre1).limit(25).all()
    
    return {
        "success": True,
        "medicos": [
            {
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
                "instagram": m.instagram
            } for m in medicos
        ]
    }

@router.post("/medico-centro")
def api_medico_centro_save(req: MedicoCentroCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    jornada = db.query(JornadaEncuestador).filter(
        JornadaEncuestador.id_usuario == current_user.id,
        JornadaEncuestador.estado == 'En Progreso'
    ).first()
    if not jornada:
        raise HTTPException(status_code=400, detail="No tienes jornada activa")
        
    encuesta = db.query(EncuestaCentro).filter(
        EncuestaCentro.id_jornada == jornada.id_jornada,
        EncuestaCentro.estado == 'Abierta'
    ).first()
    if not encuesta:
        raise HTTPException(status_code=400, detail="No tienes encuesta abierta")
        
    id_medico = req.id_medico
    if not id_medico:
        # Create or find medico
        if not req.id_medico_externo or not req.apellido1 or not req.nombre1 or not req.especialidad or not req.ciudad or not req.estado:
            raise HTTPException(status_code=400, detail="Faltan campos obligatorios del médico")
            
        existente = db.query(Medico).filter(Medico.id_medico_externo == req.id_medico_externo).first()
        if existente:
            id_medico = existente.id_medico
        else:
            nuevo_medico = Medico(
                id_medico_externo=req.id_medico_externo,
                apellido1=req.apellido1,
                apellido2=req.apellido2,
                nombre1=req.nombre1,
                nombre2=req.nombre2,
                especialidad=req.especialidad,
                sub_especialidad=req.sub_especialidad,
                universidad_graduacion=req.universidad_graduacion,
                nro_MPPS=req.nro_MPPS,
                nro_colegiado=req.nro_colegiado,
                ciudad=req.ciudad,
                estado=req.estado,
                telefono=req.telefono,
                whatsapp=req.whatsapp,
                email=req.email,
                linkedin=req.linkedin,
                instagram=req.instagram
            )
            db.add(nuevo_medico)
            db.commit()
            db.refresh(nuevo_medico)
            id_medico = nuevo_medico.id_medico
            
    dup = db.query(MedicoCentroEncuesta).filter(
        MedicoCentroEncuesta.id_encuesta == encuesta.id_encuesta,
        MedicoCentroEncuesta.id_medico == id_medico
    ).first()
    
    if dup:
        raise HTTPException(status_code=409, detail="Este médico ya fue registrado en esta encuesta del centro.")
        
    m_c_e = MedicoCentroEncuesta(
        id_encuesta=encuesta.id_encuesta,
        id_medico=id_medico,
        piso_consultorio=req.piso_consultorio,
        horarios_consulta=req.horarios_consulta,
        dias_consulta=req.dias_consulta,
        direccion_especifica=req.direccion_especifica,
        clinica2_nombre=req.clinica2_nombre,
        piso_consultorio2=req.piso_consultorio2,
        horarios_consulta2=req.horarios_consulta2,
        dias_consulta2=req.dias_consulta2,
        direccion_especifica2=req.direccion_especifica2,
        valor_consulta_rango=req.valor_consulta_rango,
        promedio_pacientes_semanal_rango=req.promedio_pacientes_semanal_rango
    )
    db.add(m_c_e)
    db.commit()
    
    cnt = db.query(func.count(MedicoCentroEncuesta.id_medico_centro)).filter(
        MedicoCentroEncuesta.id_encuesta == encuesta.id_encuesta
    ).scalar() or 0
    
    return {
        "success": True, 
        "id_medico": id_medico,
        "id_encuesta": encuesta.id_encuesta,
        "medicos_en_centro": cnt
    }

@router.get("/catalogos")
def api_catalogos(current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    return {
        "valor_consulta_rangos": [
            "Menos de 30$", "Entre 30$ a 50$", "Entre 50$ a 60$",
            "Entre 60$ a 100$", "Más de 100$"
        ],
        "promedio_pacientes_rangos": [
            "1 a 5 pacientes", "6 a 10 pacientes", "11 a 15 pacientes",
            "16 a 20 pacientes", "21 a 30 pacientes", "Más de 30 pacientes"
        ],
        "fuentes_informacion": [
            "Visita presencial", "Llamada telefónica", "Referencia",
            "Página web del centro", "Redes sociales", "Otra"
        ],
        "dias_consulta": ["Lunes", "Martes", "Miércoles", "Jueves",
                          "Viernes", "Sábado", "Domingo"]
    }
