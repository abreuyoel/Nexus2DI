from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, func, case, text
from typing import List, Any, Optional
from datetime import datetime, timedelta

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario as User
from app.models.encuestador import JornadaEncuestador, CentroSalud, EncuestaCentro, Medico, MedicoCentroEncuesta
router = APIRouter(prefix="/api/cliente-encuestador", tags=["Cliente Encuestador"])

def check_rol_cliente_encuestador(current_user: User):
    if current_user.id_rol != 13 and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso denegado. Solo para Cliente Encuestador.")

def get_base_query(db: Session):
    return db.query(MedicoCentroEncuesta, EncuestaCentro, Medico, CentroSalud, User).join(
        EncuestaCentro, EncuestaCentro.id_encuesta == MedicoCentroEncuesta.id_encuesta
    ).join(
        Medico, Medico.id_medico == MedicoCentroEncuesta.id_medico
    ).join(
        CentroSalud, CentroSalud.id_centro == EncuestaCentro.id_centro
    ).join(
        User, User.id == EncuestaCentro.id_usuario
    )

def apply_filters(query, req: Request):
    q_params = req.query_params
    
    fdesde = q_params.get("fecha_desde")
    fhasta = q_params.get("fecha_hasta")
    if fdesde: query = query.filter(EncuestaCentro.fecha_verificacion >= fdesde)
    if fhasta: query = query.filter(EncuestaCentro.fecha_verificacion <= fhasta)
    
    def apply_in(col, param_name):
        vals = q_params.getlist(param_name)
        if len(vals) == 1 and ',' in vals[0]:
            vals = [v.strip() for v in vals[0].split(',')]
        vals = [v for v in vals if v]
        if vals:
            return query.filter(col.in_(vals))
        return query
        
    query = apply_in(Medico.estado, "estados")
    query = apply_in(Medico.ciudad, "ciudades")
    query = apply_in(Medico.especialidad, "especialidades")
    query = apply_in(Medico.sub_especialidad, "sub_especialidades")
    query = apply_in(Medico.universidad_graduacion, "universidades")
    query = apply_in(CentroSalud.id_centro, "centros")
    query = apply_in(EncuestaCentro.id_usuario, "encuestadores")
    query = apply_in(EncuestaCentro.fuente_informacion, "fuentes")
    query = apply_in(MedicoCentroEncuesta.valor_consulta_rango, "valor_consulta_rangos")
    query = apply_in(MedicoCentroEncuesta.promedio_pacientes_semanal_rango, "promedio_pacientes_rangos")
    
    dias = q_params.getlist("dias_consulta")
    if len(dias) == 1 and ',' in dias[0]: dias = [d.strip() for d in dias[0].split(',')]
    dias = [d for d in dias if d]
    if dias:
        ors = []
        for d in dias:
            ors.append(MedicoCentroEncuesta.dias_consulta.ilike(f"%{d}%"))
            ors.append(MedicoCentroEncuesta.dias_consulta2.ilike(f"%{d}%"))
        query = query.filter(or_(*ors))
        
    return query

@router.get("/filtros")
def api_filtros(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_cliente_encuestador(current_user)
    
    especialidades = [r[0] for r in db.query(Medico.especialidad).distinct().filter(Medico.especialidad != None).order_by(Medico.especialidad).all()]
    sub_especialidades = [r[0] for r in db.query(Medico.sub_especialidad).distinct().filter(Medico.sub_especialidad != None).order_by(Medico.sub_especialidad).all()]
    estados = [r[0] for r in db.query(Medico.estado).distinct().filter(Medico.estado != None).order_by(Medico.estado).all()]
    ciudades = [r[0] for r in db.query(Medico.ciudad).distinct().filter(Medico.ciudad != None).order_by(Medico.ciudad).all()]
    universidades = [r[0] for r in db.query(Medico.universidad_graduacion).distinct().filter(Medico.universidad_graduacion != None).order_by(Medico.universidad_graduacion).all()]
    
    centros = [{"id_centro": r.id_centro, "nombre_centro": r.nombre_centro} for r in db.query(CentroSalud.id_centro, CentroSalud.nombre_centro).order_by(CentroSalud.nombre_centro).all()]
    encuestadores = [{"id_usuario": r.id, "username": r.username} for r in db.query(User.id, User.username).join(EncuestaCentro, EncuestaCentro.id_usuario == User.id).distinct().order_by(User.username).all()]
    
    fuentes = [r[0] for r in db.query(EncuestaCentro.fuente_informacion).distinct().filter(EncuestaCentro.fuente_informacion != None).order_by(EncuestaCentro.fuente_informacion).all()]
    valor_rangos = [r[0] for r in db.query(MedicoCentroEncuesta.valor_consulta_rango).distinct().order_by(MedicoCentroEncuesta.valor_consulta_rango).all()]
    pac_rangos = [r[0] for r in db.query(MedicoCentroEncuesta.promedio_pacientes_semanal_rango).distinct().order_by(MedicoCentroEncuesta.promedio_pacientes_semanal_rango).all()]
    
    return {
        "success": True,
        "especialidades": especialidades,
        "sub_especialidades": sub_especialidades,
        "estados": estados,
        "ciudades": ciudades,
        "universidades": universidades,
        "centros": centros,
        "encuestadores": encuestadores,
        "fuentes": fuentes,
        "valor_consulta_rangos": valor_rangos,
        "promedio_pacientes_rangos": pac_rangos,
        "dias_consulta": ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
    }

@router.get("/kpis")
def api_kpis(request: Request, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_cliente_encuestador(current_user)
    q = apply_filters(get_base_query(db), request)
    
    total_medicos = q.with_entities(func.count(func.distinct(Medico.id_medico))).scalar() or 0
    total_centros = q.with_entities(func.count(func.distinct(CentroSalud.id_centro))).scalar() or 0
    total_especialidades = q.with_entities(func.count(func.distinct(Medico.especialidad))).scalar() or 0
    total_estados = q.with_entities(func.count(func.distinct(Medico.estado))).scalar() or 0
    total_ciudades = q.with_entities(func.count(func.distinct(Medico.ciudad))).scalar() or 0
    total_encuestas = q.with_entities(func.count(func.distinct(EncuestaCentro.id_encuesta))).scalar() or 0
    
    thirty_days_ago = datetime.utcnow().date() - timedelta(days=30)
    encuestas_30d = q.filter(EncuestaCentro.fecha_verificacion >= thirty_days_ago).with_entities(func.count(func.distinct(EncuestaCentro.id_encuesta))).scalar() or 0
    
    dos_cons = q.filter(MedicoCentroEncuesta.clinica2_nombre != None, MedicoCentroEncuesta.clinica2_nombre != '').with_entities(func.count(func.distinct(Medico.id_medico))).scalar() or 0
    pct_dos = round((dos_cons * 100.0) / total_medicos, 1) if total_medicos else 0.0
    
    # We can do exact calculations for whatsapp, email, etc. by filtering
    wa = q.filter(Medico.whatsapp != None, Medico.whatsapp != '').with_entities(func.count(func.distinct(Medico.id_medico))).scalar() or 0
    em = q.filter(Medico.email != None, Medico.email != '').with_entities(func.count(func.distinct(Medico.id_medico))).scalar() or 0
    tel = q.filter(Medico.telefono != None, Medico.telefono != '').with_entities(func.count(func.distinct(Medico.id_medico))).scalar() or 0
    ig = q.filter(Medico.instagram != None, Medico.instagram != '').with_entities(func.count(func.distinct(Medico.id_medico))).scalar() or 0
    li = q.filter(Medico.linkedin != None, Medico.linkedin != '').with_entities(func.count(func.distinct(Medico.id_medico))).scalar() or 0
    
    def pct(x): return round((x * 100.0) / total_medicos, 1) if total_medicos else 0.0
    
    # --- CHART DATA ---
    esp_data = q.with_entities(Medico.especialidad, func.count(func.distinct(Medico.id_medico))).group_by(Medico.especialidad).all()
    esp_chart = [{"name": r[0] or "N/A", "value": r[1]} for r in esp_data]

    est_data = q.with_entities(Medico.estado, func.count(func.distinct(Medico.id_medico))).group_by(Medico.estado).all()
    est_chart = [{"name": r[0] or "N/A", "value": r[1]} for r in est_data]

    uni_data = q.with_entities(Medico.universidad_graduacion, func.count(func.distinct(Medico.id_medico))).group_by(Medico.universidad_graduacion).all()
    uni_chart = [{"name": r[0] or "N/A", "value": r[1]} for r in uni_data]

    cen_data = q.with_entities(CentroSalud.nombre_centro, func.count(func.distinct(Medico.id_medico))).group_by(CentroSalud.nombre_centro).all()
    cen_chart = [{"name": r[0] or "N/A", "value": r[1]} for r in cen_data]

    val_data = q.with_entities(MedicoCentroEncuesta.valor_consulta_rango, func.count(func.distinct(Medico.id_medico))).group_by(MedicoCentroEncuesta.valor_consulta_rango).all()
    val_chart = [{"name": r[0] or "N/A", "value": r[1]} for r in val_data]

    pac_data = q.with_entities(MedicoCentroEncuesta.promedio_pacientes_semanal_rango, func.count(func.distinct(Medico.id_medico))).group_by(MedicoCentroEncuesta.promedio_pacientes_semanal_rango).all()
    pac_chart = [{"name": r[0] or "N/A", "value": r[1]} for r in pac_data]
    
    enc_data = q.with_entities(User.username, func.count(func.distinct(Medico.id_medico)), func.count(func.distinct(CentroSalud.id_centro)), func.count(func.distinct(EncuestaCentro.id_encuesta))).group_by(User.username).all()
    enc_ranking = [{"encuestador": r[0], "medicos": r[1], "centros": r[2], "encuestas": r[3]} for r in enc_data]

    dias_data = q.with_entities(MedicoCentroEncuesta.dias_consulta).all()
    dias_count = {"Lunes": 0, "Martes": 0, "Miércoles": 0, "Jueves": 0, "Viernes": 0, "Sábado": 0, "Domingo": 0}
    for (dias_str,) in dias_data:
        if dias_str:
            for d in dias_count.keys():
                if d.lower() in dias_str.lower():
                    dias_count[d] += 1
    dias_chart = [{"name": k, "value": v} for k, v in dias_count.items()]
    
    return {
        "success": True,
        "total_medicos": total_medicos,
        "total_centros": total_centros,
        "total_especialidades": total_especialidades,
        "total_estados": total_estados,
        "total_ciudades": total_ciudades,
        "total_encuestas": total_encuestas,
        "encuestas_30d": encuestas_30d,
        "medicos_con_2do_consultorio": dos_cons,
        "pct_2do_consultorio": pct_dos,
        "pct_whatsapp": pct(wa),
        "pct_email": pct(em),
        "pct_telefono": pct(tel),
        "pct_instagram": pct(ig),
        "pct_linkedin": pct(li),
        "charts": {
            "especialidades": esp_chart,
            "estados": est_chart,
            "universidades": uni_chart,
            "centros": cen_chart,
            "valor_consulta": val_chart,
            "pacientes_semana": pac_chart,
            "dias_consulta": dias_chart,
            "ranking_encuestadores": enc_ranking
        }
    }

@router.get("/medicos")
def api_medicos_tabla(request: Request, q: str = "", page: int = 1, per_page: int = 25, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_cliente_encuestador(current_user)
    
    base_q = apply_filters(get_base_query(db), request)
    
    if q.strip():
        search = f"%{q.strip()}%"
        base_q = base_q.filter(
            or_(
                Medico.id_medico_externo.ilike(search),
                Medico.apellido1.ilike(search),
                Medico.apellido2.ilike(search),
                Medico.nombre1.ilike(search),
                Medico.nombre2.ilike(search),
                Medico.especialidad.ilike(search),
                CentroSalud.nombre_centro.ilike(search)
            )
        )
        
    total = base_q.with_entities(func.count(func.distinct(Medico.id_medico))).scalar() or 0
    offset = (page - 1) * per_page
    
    rows = base_q.with_entities(
        Medico.id_medico, Medico.id_medico_externo, 
        Medico.apellido1, Medico.apellido2, Medico.nombre1, Medico.nombre2,
        Medico.especialidad, Medico.sub_especialidad, Medico.universidad_graduacion,
        Medico.ciudad, Medico.estado, Medico.telefono, Medico.whatsapp, Medico.email,
        CentroSalud.nombre_centro, MedicoCentroEncuesta.valor_consulta_rango,
        MedicoCentroEncuesta.promedio_pacientes_semanal_rango, MedicoCentroEncuesta.dias_consulta,
        EncuestaCentro.fecha_verificacion, User.username
    ).order_by(desc(EncuestaCentro.fecha_verificacion), Medico.apellido1).offset(offset).limit(per_page).all()
    
    medicos = []
    for r in rows:
        n2 = f" {r.nombre2}" if r.nombre2 else ""
        a2 = f" {r.apellido2}" if r.apellido2 else ""
        nombre_completo = f"{r.apellido1}{a2}, {r.nombre1}{n2}"
        medicos.append({
            "id_medico": r.id_medico,
            "id_medico_externo": r.id_medico_externo,
            "nombre_completo": nombre_completo,
            "especialidad": r.especialidad,
            "sub_especialidad": r.sub_especialidad,
            "universidad": r.universidad_graduacion,
            "ciudad": r.ciudad,
            "estado": r.estado,
            "telefono": r.telefono,
            "whatsapp": r.whatsapp,
            "email": r.email,
            "centro": r.nombre_centro,
            "valor_consulta_rango": r.valor_consulta_rango,
            "promedio_pacientes": r.promedio_pacientes_semanal_rango,
            "dias_consulta": r.dias_consulta,
            "fecha_verificacion": r.fecha_verificacion.isoformat() if r.fecha_verificacion else None,
            "encuestador": r.username
        })
        
    return {
        "success": True, "total": total, "page": page, "per_page": per_page,
        "medicos": medicos
    }
