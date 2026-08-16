from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func
from typing import List, Any, Optional
from datetime import datetime
from pydantic import BaseModel

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario as User
from app.models.encuestador import JornadaEncuestador, CentroSalud, EncuestaCentro, Medico, MedicoCentroEncuesta, MedicoConsultorio, CatalogoEncuestador
from app.schemas.encuestador import JornadaActivarRequest, CentroSaludCreate, EncuestaCentroCreate, MedicoCentroCreate

router = APIRouter(prefix="/api/encuestador", tags=["Encuestador"])

def check_rol_encuestador(current_user: User):
    # 12 = Encuestador (trabajo de campo). 13 = Cliente Encuestador/IQVIA --
    # además de ver el BI, puede entrar a activar jornadas y cargar médicos
    # como cualquier encuestador (decisión explícita, no es un descuido).
    if current_user.id_rol not in (12, 13) and not current_user.is_admin:
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
    
    # Prevenir duplicados si la cola offline reintenta el POST por timeout
    search_str = f'%"nombre_centro": "{req.nombre_centro.strip()}"%'
    existente = db.query(Solicitud).filter(
        Solicitud.user_id == current_user.id,
        Solicitud.tipo == "creacion_centro_salud",
        Solicitud.estado == "pendiente",
        Solicitud.descripcion.like(search_str)
    ).first()
    
    if existente:
        return {
            "success": True,
            "solicitud_id": existente.id,
            "message": "Solicitud ya estaba registrada (reintento de cola offline)."
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
    
    medicos_resp = []
    for m, mce in medicos_cargados:
        first_consultorio = db.query(MedicoConsultorio).filter(MedicoConsultorio.id_medico == m.id_medico).first()
        val = first_consultorio.valor_consulta_rango if first_consultorio else 'N/A'
        pacs = first_consultorio.promedio_pacientes_semanal_rango if first_consultorio else 'N/A'
        medicos_resp.append({
            "id_medico_centro": mce.id_medico_centro,
            "id_medico": m.id_medico,
            "id_medico_externo": m.id_medico_externo,
            "apellido1": m.apellido1,
            "apellido2": m.apellido2,
            "nombre1": m.nombre1,
            "nombre2": m.nombre2,
            "especialidad": m.especialidad,
            "valor_consulta_rango": val,
            "promedio_pacientes_semanal_rango": pacs
        })
    
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
        "medicos": medicos_resp
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
        if existente.id_centro == req.id_centro:
            # Si es el mismo centro, es un reintento de la cola offline que falló por timeout
            # pero sí llegó a crearse en el backend. Devolver éxito para destrabar la cola.
            return {"success": True, "id_encuesta": existente.id_encuesta, "id_jornada": jornada.id_jornada}
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
    # Mismo riesgo de carrera que medico-centro (ver comentario ahí): el
    # SELECT de "existente" de arriba no es atómico con el INSERT. El índice
    # único filtrado UQ_encuesta_abierta_por_jornada (solo WHERE estado=
    # 'Abierta') es la protección real -- si se pierde la carrera, se
    # devuelve la encuesta que sí ganó en vez de un 500.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        ganadora = db.query(EncuestaCentro).filter(
            EncuestaCentro.id_jornada == jornada.id_jornada,
            EncuestaCentro.estado == 'Abierta'
        ).first()
        if ganadora:
            return {"success": True, "id_encuesta": ganadora.id_encuesta, "id_jornada": jornada.id_jornada}
        raise HTTPException(status_code=409, detail="Ya tienes una encuesta abierta.")
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
                "segunda_universidad_graduacion": m.segunda_universidad_graduacion,
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
        if not req.apellido1 or not req.apellido2 or not req.nombre1 or not req.especialidad or not req.ciudad or not req.estado:
            raise HTTPException(status_code=400, detail="Faltan campos obligatorios del médico")
            
        existente = None
        if req.id_medico_externo and req.id_medico_externo != "000000" and req.id_medico_externo.strip() != "":
            existente = db.query(Medico).filter(Medico.id_medico_externo == req.id_medico_externo).first()
        else:
            # Si no hay cédula, intentamos evitar duplicar el mismo médico en reintentos offline de la cola
            # matcheando por nombre exacto.
            existente = db.query(Medico).filter(
                func.lower(Medico.nombre1) == req.nombre1.lower(),
                func.lower(Medico.apellido1) == req.apellido1.lower(),
                func.lower(Medico.especialidad) == req.especialidad.lower()
            ).order_by(desc(Medico.id_medico)).first()
            
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
                segunda_universidad_graduacion=req.segunda_universidad_graduacion,
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
        id_medico=id_medico
    )
    db.add(m_c_e)

    for cons in req.consultorios:
        nuevo_consultorio = MedicoConsultorio(
            id_medico=id_medico,
            nombre_clinica=cons.nombre_clinica,
            piso_consultorio=cons.piso_consultorio,
            direccion_especifica=cons.direccion_especifica,
            horarios_json=cons.horarios_json,
            valor_consulta_rango=cons.valor_consulta_rango,
            promedio_pacientes_semanal_rango=cons.promedio_pacientes_semanal_rango
        )
        db.add(nuevo_consultorio)

    # El SELECT de arriba (dup) NO alcanza solo: con 2 réplicas del backend
    # corriendo en paralelo, dos requests casi simultáneas -- doble tap del
    # encuestador, o el reintento automático de la cola offline mientras el
    # primer intento seguía en vuelo con mala señal -- pueden pasar el
    # chequeo las dos antes de que ninguna haga commit. Es la causa
    # confirmada de médicos duplicados reportada en campo. El índice único
    # UQ_medico_centro_encuesta (ver migración SQL) es la protección real:
    # si se pierde la carrera acá, el commit falla con IntegrityError y se
    # trata como éxito (ya quedó registrado por el otro intento), en vez de
    # tirarle un 500 al encuestador -- y al ser una sola transacción, los
    # MedicoConsultorio de arriba se revierten con el rollback, así que
    # tampoco quedan consultorios duplicados sueltos.
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        cnt = db.query(func.count(MedicoCentroEncuesta.id_medico_centro)).filter(
            MedicoCentroEncuesta.id_encuesta == encuesta.id_encuesta
        ).scalar() or 0
        return {
            "success": True,
            "id_medico": id_medico,
            "id_encuesta": encuesta.id_encuesta,
            "medicos_en_centro": cnt,
            "ya_registrado": True,
        }

    cnt = db.query(func.count(MedicoCentroEncuesta.id_medico_centro)).filter(
        MedicoCentroEncuesta.id_encuesta == encuesta.id_encuesta
    ).scalar() or 0

    return {
        "success": True,
        "id_medico": id_medico,
        "id_encuesta": encuesta.id_encuesta,
        "medicos_en_centro": cnt
    }

@router.get("/medico/{id_medico}")
def api_medico_detalle(id_medico: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Datos completos de un médico ya registrado + todos sus consultorios,
    para precargar el formulario en modo edición. El médico es una entidad
    global (compartida entre todos los centros donde se lo haya registrado,
    matcheada por id_medico_externo) -- por eso acá aparecen TODOS sus
    consultorios, no solo los de la encuesta/centro desde donde se entró a
    editar. Es el mismo dato que ya se ve al buscar un médico existente en
    el formulario de alta, solo que ahora también se puede guardar."""
    check_rol_encuestador(current_user)

    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    consultorios = db.query(MedicoConsultorio).filter(MedicoConsultorio.id_medico == id_medico).order_by(MedicoConsultorio.id_consultorio).all()

    return {
        "success": True,
        "id_medico": medico.id_medico,
        "id_medico_externo": medico.id_medico_externo,
        "apellido1": medico.apellido1,
        "apellido2": medico.apellido2,
        "nombre1": medico.nombre1,
        "nombre2": medico.nombre2,
        "especialidad": medico.especialidad,
        "sub_especialidad": medico.sub_especialidad,
        "universidad_graduacion": medico.universidad_graduacion,
        "segunda_universidad_graduacion": medico.segunda_universidad_graduacion,
        "nro_MPPS": medico.nro_MPPS,
        "nro_colegiado": medico.nro_colegiado,
        "ciudad": medico.ciudad,
        "estado": medico.estado,
        "telefono": medico.telefono,
        "whatsapp": medico.whatsapp,
        "email": medico.email,
        "linkedin": medico.linkedin,
        "instagram": medico.instagram,
        "consultorios": [
            {
                "id_consultorio": c.id_consultorio,
                "nombre_clinica": c.nombre_clinica,
                "piso_consultorio": c.piso_consultorio,
                "direccion_especifica": c.direccion_especifica,
                "valor_consulta_rango": c.valor_consulta_rango,
                "promedio_pacientes_semanal_rango": c.promedio_pacientes_semanal_rango,
                "horarios_json": c.horarios_json,
            } for c in consultorios
        ],
    }

@router.post("/medico/{id_medico}/editar")
def api_medico_editar(id_medico: int, req: MedicoCentroCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Edita los datos propios del médico y reemplaza por completo su lista
    de consultorios (delete-then-insert, mismo shape que el alta) -- más
    simple y menos propenso a errores que tratar de diffear cuál consultorio
    es cuál cuando el formulario no manda ids estables por fila."""
    check_rol_encuestador(current_user)

    medico = db.query(Medico).filter(Medico.id_medico == id_medico).first()
    if not medico:
        raise HTTPException(status_code=404, detail="Médico no encontrado")

    if not req.apellido1 or not req.apellido2 or not req.nombre1 or not req.especialidad or not req.ciudad or not req.estado:
        raise HTTPException(status_code=400, detail="Faltan campos obligatorios del médico")

    medico.apellido1 = req.apellido1
    medico.apellido2 = req.apellido2
    medico.nombre1 = req.nombre1
    medico.nombre2 = req.nombre2
    medico.especialidad = req.especialidad
    medico.sub_especialidad = req.sub_especialidad
    medico.universidad_graduacion = req.universidad_graduacion
    medico.segunda_universidad_graduacion = req.segunda_universidad_graduacion
    medico.nro_MPPS = req.nro_MPPS
    medico.nro_colegiado = req.nro_colegiado
    medico.ciudad = req.ciudad
    medico.estado = req.estado
    medico.telefono = req.telefono
    medico.whatsapp = req.whatsapp
    medico.email = req.email
    medico.linkedin = req.linkedin
    medico.instagram = req.instagram
    # id_medico_externo (cédula) NO se toca acá -- es la clave con la que se
    # matchea "¿ya existe este médico?" al buscarlo desde otro centro;
    # cambiarla desde acá podría duplicarlo en vez de identificarlo.

    db.query(MedicoConsultorio).filter(MedicoConsultorio.id_medico == id_medico).delete()
    for cons in req.consultorios:
        db.add(MedicoConsultorio(
            id_medico=id_medico,
            nombre_clinica=cons.nombre_clinica,
            piso_consultorio=cons.piso_consultorio,
            direccion_especifica=cons.direccion_especifica,
            horarios_json=cons.horarios_json,
            valor_consulta_rango=cons.valor_consulta_rango,
            promedio_pacientes_semanal_rango=cons.promedio_pacientes_semanal_rango,
        ))

    db.commit()
    return {"success": True, "id_medico": id_medico}

@router.get("/catalogos")
def api_catalogos(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    especialidades = db.query(CatalogoEncuestador.nombre).filter(CatalogoEncuestador.tipo == "especialidad").order_by(CatalogoEncuestador.nombre).all()
    estados = db.query(CatalogoEncuestador.nombre).filter(CatalogoEncuestador.tipo == "estado").order_by(CatalogoEncuestador.nombre).all()
    ciudades = db.query(CatalogoEncuestador.nombre).filter(CatalogoEncuestador.tipo == "ciudad").order_by(CatalogoEncuestador.nombre).all()
    universidades = db.query(CatalogoEncuestador.nombre).filter(CatalogoEncuestador.tipo == "universidad").order_by(CatalogoEncuestador.nombre).all()

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
                          "Viernes", "Sábado", "Domingo"],
        "especialidades": [e[0] for e in especialidades],
        "estados": [est[0] for est in estados],
        "ciudades": [c[0] for c in ciudades],
        "universidades": [u[0] for u in universidades],
    }

class CatalogoCreate(BaseModel):
    tipo: str  # 'especialidad', 'estado', 'ciudad', 'universidad'
    nombre: str

@router.post("/catalogos")
def api_catalogos_create(req: CatalogoCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    
    tipo = req.tipo.strip().lower()
    nombre = req.nombre.strip()
    
    if tipo not in ("especialidad", "estado", "ciudad", "universidad"):
        raise HTTPException(status_code=400, detail="Tipo de catálogo inválido")
    if not nombre:
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
        
    existente = db.query(CatalogoEncuestador).filter(
        CatalogoEncuestador.tipo == tipo,
        CatalogoEncuestador.nombre == nombre
    ).first()
    
    if existente:
        return {"success": True, "id": existente.id, "message": "Elemento ya existe"}
        
    nuevo = CatalogoEncuestador(tipo=tipo, nombre=nombre)
    db.add(nuevo)
    db.commit()
    db.refresh(nuevo)
    
    return {"success": True, "id": nuevo.id, "message": "Elemento agregado"}

@router.get("/catalogos-gestion")
def api_catalogos_gestion(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    items = db.query(CatalogoEncuestador).order_by(CatalogoEncuestador.tipo, CatalogoEncuestador.nombre).all()
    return {
        "success": True,
        "items": [{"id": i.id, "tipo": i.tipo, "nombre": i.nombre} for i in items]
    }

@router.delete("/catalogos/{id_catalogo}")
def api_catalogos_delete(id_catalogo: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    item = db.query(CatalogoEncuestador).filter(CatalogoEncuestador.id == id_catalogo).first()
    if not item:
        raise HTTPException(status_code=404, detail="Elemento no encontrado")
    db.delete(item)
    db.commit()
    return {"success": True, "message": "Elemento eliminado"}

# --- ENDPOINTS DE CORRECCIONES DE SUPERVISOR ---

class EncuestaCentroUpdate(BaseModel):
    fuente_informacion: str
    notas_generales: Optional[str] = None

@router.get("/correcciones-pendientes")
def api_correcciones_pendientes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_encuestador(current_user)
    encuestas = db.query(EncuestaCentro).filter(
        EncuestaCentro.id_usuario == current_user.id,
        EncuestaCentro.requiere_correccion == True
    ).order_by(desc(EncuestaCentro.id_encuesta)).all()
    
    result = []
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
                    "especialidad": m.especialidad,
                    "sub_especialidad": m.sub_especialidad,
                    "universidad_graduacion": m.universidad_graduacion,
                    "segunda_universidad_graduacion": m.segunda_universidad_graduacion,
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
        
        result.append({
            "id_encuesta": e.id_encuesta,
            "id_centro": e.id_centro,
            "nombre_centro": centro.nombre_centro if centro else "Centro Desconocido",
            "ciudad": centro.ciudad if centro else None,
            "estado_geo": centro.estado if centro else None,
            "fecha_verificacion": e.fecha_verificacion.isoformat() if e.fecha_verificacion else None,
            "fuente_informacion": e.fuente_informacion,
            "notas_generales": e.notas_generales,
            "observacion_supervisor": e.observacion_supervisor,
            "requiere_correccion": True,
            "medicos": medicos_list
        })
    return result

@router.put("/encuestas/{id_encuesta}")
def api_encuesta_corregir(
    id_encuesta: int,
    req: EncuestaCentroUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_rol_encuestador(current_user)
    encuesta = db.query(EncuestaCentro).filter(
        EncuestaCentro.id_encuesta == id_encuesta,
        EncuestaCentro.id_usuario == current_user.id
    ).first()
    
    if not encuesta:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada o no te pertenece")
        
    if not getattr(encuesta, "requiere_correccion", False) and encuesta.estado != "Abierta":
        raise HTTPException(status_code=400, detail="Esta encuesta no requiere correcciones ni está en progreso.")
        
    encuesta.fuente_informacion = req.fuente_informacion
    encuesta.notas_generales = req.notas_generales
    encuesta.requiere_correccion = False  # Al guardar la corrección, se quita la alerta
    
    db.commit()
    return {"success": True, "message": "Encuesta corregida exitosamente"}

class ConsultorioUpdate(BaseModel):
    nombre_clinica: str
    piso_consultorio: Optional[str] = None
    direccion_especifica: Optional[str] = None
    horarios_json: Optional[str] = None
    valor_consulta_rango: str
    promedio_pacientes_semanal_rango: str

class MedicoCentroUpdateReq(BaseModel):
    id_medico_externo: str
    apellido1: str
    apellido2: Optional[str] = None
    nombre1: str
    nombre2: Optional[str] = None
    especialidad: str
    sub_especialidad: Optional[str] = None
    universidad_graduacion: Optional[str] = None
    segunda_universidad_graduacion: Optional[str] = None
    nro_MPPS: Optional[str] = None
    nro_colegiado: Optional[str] = None
    ciudad: str
    estado: str
    telefono: Optional[str] = None
    whatsapp: Optional[str] = None
    email: Optional[str] = None
    linkedin: Optional[str] = None
    instagram: Optional[str] = None
    consultorios: List[ConsultorioUpdate] = []

@router.put("/medicos/{id_medico}")
def api_medico_corregir(
    id_medico: int,
    req: MedicoCentroUpdateReq,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    check_rol_encuestador(current_user)
    
    # Verificar que el médico esté registrado en una encuesta de este usuario
    vinculo = db.query(MedicoCentroEncuesta).join(
        EncuestaCentro, EncuestaCentro.id_encuesta == MedicoCentroEncuesta.id_encuesta
    ).filter(
        MedicoCentroEncuesta.id_medico == id_medico,
        EncuestaCentro.id_usuario == current_user.id
    ).first()
    
    if not vinculo:
        raise HTTPException(status_code=403, detail="No tienes permisos para modificar este médico")
        
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
    m.segunda_universidad_graduacion = req.segunda_universidad_graduacion
    m.nro_MPPS = req.nro_MPPS
    m.nro_colegiado = req.nro_colegiado
    m.ciudad = req.ciudad
    m.estado = req.estado
    m.telefono = req.telefono
    m.whatsapp = req.whatsapp
    m.email = req.email
    m.linkedin = req.linkedin
    m.instagram = req.instagram

    # Actualizar consultorios
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
    return {"success": True, "message": "Datos de médico actualizados correctamente"}

