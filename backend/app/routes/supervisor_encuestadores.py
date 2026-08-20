from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import or_, desc, func, select, delete as sa_delete
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime, date
from pydantic import BaseModel

from app.db.session import get_db, get_async_db
from app.core.dependencies import require_permission
from app.models.user import Usuario as User
from app.models.encuestador import (
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
    consultorios: List[ConsultorioEdit] = []

class MedicoCentroSaveRequest(BaseModel):
    id_encuesta: int
    id_medico: Optional[int] = None  # Si ya existe
    medico_data: Optional[MedicoEditRequest] = None  # Si se crea de cero

# --- ENDPOINTS ---

@router.get("/encuestadores")
async def get_encuestadores(
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    # Trae usuarios con rol admin (8), supervisor (10), analista (11), encuestador (12) o cliente_encuestador (13)
    encuestadores = (await db.execute(select(User).filter(User.id_rol.in_((8, 10, 11, 12, 13))).order_by(User.username))).scalars().all()
    result = []
    for u in encuestadores:
        # Buscar perfil de Encuestador si existe por cédula/username o id_perfil
        nombre_real = u.username
        perf = None
        if u.id_perfil:
            perf = (await db.execute(select(Encuestador).filter(Encuestador.id == u.id_perfil))).scalars().first()
        if not perf:
            try:
                ced = int(u.username)
                perf = (await db.execute(select(Encuestador).filter(Encuestador.cedula == ced))).scalars().first()
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
async def list_jornadas(
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    encuestas_count_sub = (
        select(
            EncuestaCentro.id_jornada,
            func.count(EncuestaCentro.id_encuesta).label("encuestas_count")
        )
        .group_by(EncuestaCentro.id_jornada)
        .subquery()
    )

    stmt = (
        select(
            JornadaEncuestador,
            User.username,
            func.coalesce(encuestas_count_sub.c.encuestas_count, 0).label("encuestas_count")
        )
        .outerjoin(User, User.id == JornadaEncuestador.id_usuario)
        .outerjoin(encuestas_count_sub, encuestas_count_sub.c.id_jornada == JornadaEncuestador.id_jornada)
    )

    if user_id:
        stmt = stmt.filter(JornadaEncuestador.id_usuario == user_id)
    jornadas = (await db.execute(stmt.order_by(desc(JornadaEncuestador.id_jornada)))).all()

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
async def get_jornada_detalle(
    id_jornada: int,
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    jornada = (await db.execute(select(JornadaEncuestador).filter(JornadaEncuestador.id_jornada == id_jornada))).scalars().first()
    if not jornada:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    u = (await db.execute(select(User).filter(User.id == jornada.id_usuario))).scalars().first()

    # Obtener encuestas realizadas en esta jornada
    encuestas = (await db.execute(select(EncuestaCentro).filter(EncuestaCentro.id_jornada == id_jornada))).scalars().all()
    if not encuestas:
        return {
            "id_jornada": jornada.id_jornada,
            "username": u.username if u else "Desconocido",
            "fecha_inicio": jornada.fecha_inicio.isoformat() if jornada.fecha_inicio else None,
            "fecha_fin": jornada.fecha_fin.isoformat() if jornada.fecha_fin else None,
            "estado": jornada.estado,
            "ciudad": jornada.ciudad,
            "estado_geo": jornada.estado_geo,
            "notas": jornada.notas,
            "encuestas": []
        }

    encuesta_ids = [e.id_encuesta for e in encuestas]
    centro_ids = list(set([e.id_centro for e in encuestas if e.id_centro]))

    # Cargar Centros por lote
    centros_raw = (await db.execute(select(CentroSalud).filter(CentroSalud.id_centro.in_(centro_ids)))).scalars().all() if centro_ids else []
    centros_by_id = {c.id_centro: c for c in centros_raw}

    # Cargar Médicos y Consultorios por lote
    medicos_rel_raw = (await db.execute(select(MedicoCentroEncuesta).filter(MedicoCentroEncuesta.id_encuesta.in_(encuesta_ids)))).scalars().all()
    medico_ids = list(set([mr.id_medico for mr in medicos_rel_raw if mr.id_medico]))

    medicos_by_id = {}
    consultorios_by_medico = {}
    if medico_ids:
        medicos_raw = (await db.execute(select(Medico).filter(Medico.id_medico.in_(medico_ids)))).scalars().all()
        medicos_by_id = {m.id_medico: m for m in medicos_raw}

        consultorios_raw = (await db.execute(select(MedicoConsultorio).filter(MedicoConsultorio.id_medico.in_(medico_ids)))).scalars().all()
        for c in consultorios_raw:
            if c.id_medico not in consultorios_by_medico:
                consultorios_by_medico[c.id_medico] = []
            consultorios_by_medico[c.id_medico].append({
                "id_consultorio": c.id_consultorio,
                "nombre_clinica": c.nombre_clinica,
                "piso_consultorio": c.piso_consultorio,
                "direccion_especifica": c.direccion_especifica,
                "valor_consulta_rango": c.valor_consulta_rango,
                "promedio_pacientes_semanal_rango": c.promedio_pacientes_semanal_rango,
                "horarios_json": c.horarios_json
            })

    medicos_rel_by_encuesta = {}
    for mr in medicos_rel_raw:
        if mr.id_encuesta not in medicos_rel_by_encuesta:
            medicos_rel_by_encuesta[mr.id_encuesta] = []
        medicos_rel_by_encuesta[mr.id_encuesta].append(mr.id_medico)

    encuestas_list = []
    for e in encuestas:
        centro = centros_by_id.get(e.id_centro)
        rel_m_ids = medicos_rel_by_encuesta.get(e.id_encuesta, [])
        medicos_list = []
        for m_id in rel_m_ids:
            m = medicos_by_id.get(m_id)
            if m:
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
                    "segunda_universidad_graduacion": m.segunda_universidad_graduacion,
                    "nro_MPPS": m.nro_MPPS,
                    "nro_colegiado": m.nro_colegiado,
                    "ciudad": m.ciudad,
                    "estado": m.estado,
                    "telefono": m.telefono,
                    "whatsapp": m.whatsapp,
                    "email": m.email,
                    "fecha_registro": m.fecha_registro.isoformat() if m.fecha_registro else None,
                    "consultorios": consultorios_by_medico.get(m.id_medico, [])
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
async def create_jornada(
    req: JornadaRequest,
    db: AsyncSession = Depends(get_async_db),
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
    await db.commit()
    await db.refresh(jornada)
    return {"success": True, "id_jornada": jornada.id_jornada}

@router.put("/jornadas/{id_jornada}")
async def update_jornada(
    id_jornada: int,
    req: JornadaRequest,
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "write", fallback_roles=("admin", "supervisor")))
):
    j = (await db.execute(select(JornadaEncuestador).filter(JornadaEncuestador.id_jornada == id_jornada))).scalars().first()
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

    await db.commit()
    return {"success": True}

@router.delete("/jornadas/{id_jornada}")
async def delete_jornada(
    id_jornada: int,
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "delete", fallback_roles=("admin", "supervisor")))
):
    j = (await db.execute(select(JornadaEncuestador).filter(JornadaEncuestador.id_jornada == id_jornada))).scalars().first()
    if not j:
        raise HTTPException(status_code=404, detail="Jornada no encontrada")

    try:
        # 1. Obtener IDs de las encuestas asociadas a esta jornada
        encuestas_ids = (await db.execute(
            select(EncuestaCentro.id_encuesta).filter(EncuestaCentro.id_jornada == id_jornada)
        )).scalars().all()

        # 2. Eliminar relaciones de médicos asociadas a esas encuestas (medico_centro_encuesta)
        if encuestas_ids:
            await db.execute(
                sa_delete(MedicoCentroEncuesta).where(MedicoCentroEncuesta.id_encuesta.in_(encuestas_ids))
            )

        # 3. Eliminar encuestas de la jornada
        await db.execute(sa_delete(EncuestaCentro).where(EncuestaCentro.id_jornada == id_jornada))

        # 4. Eliminar la jornada
        await db.delete(j)
        await db.commit()
        return {"success": True}
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al eliminar jornada: {str(e)}")



# --- ENCUESTAS ---

@router.get("/encuestas")
async def list_encuestas(
    user_id: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    medicos_count_sub = (
        select(
            MedicoCentroEncuesta.id_encuesta,
            func.count(MedicoCentroEncuesta.id_medico).label("medicos_count")
        )
        .group_by(MedicoCentroEncuesta.id_encuesta)
        .subquery()
    )

    stmt = (
        select(
            EncuestaCentro,
            User.username,
            CentroSalud.nombre_centro,
            CentroSalud.ciudad,
            CentroSalud.estado,
            func.coalesce(medicos_count_sub.c.medicos_count, 0).label("medicos_count")
        )
        .outerjoin(User, User.id == EncuestaCentro.id_usuario)
        .outerjoin(CentroSalud, CentroSalud.id_centro == EncuestaCentro.id_centro)
        .outerjoin(medicos_count_sub, medicos_count_sub.c.id_encuesta == EncuestaCentro.id_encuesta)
    )

    if user_id:
        stmt = stmt.filter(EncuestaCentro.id_usuario == user_id)
        
    encuestas = (await db.execute(stmt.order_by(desc(EncuestaCentro.id_encuesta)))).all()

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
async def create_encuesta(
    req: EncuestaRequest,
    db: AsyncSession = Depends(get_async_db),
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
    await db.commit()
    await db.refresh(encuesta)
    return {"success": True, "id_encuesta": encuesta.id_encuesta}

@router.put("/encuestas/{id_encuesta}")
async def update_encuesta(
    id_encuesta: int,
    req: EncuestaRequest,
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "write", fallback_roles=("admin", "supervisor")))
):
    e = (await db.execute(select(EncuestaCentro).filter(EncuestaCentro.id_encuesta == id_encuesta))).scalars().first()
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

    await db.commit()
    return {"success": True}

@router.delete("/encuestas/{id_encuesta}")
async def delete_encuesta(
    id_encuesta: int,
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "delete", fallback_roles=("admin", "supervisor")))
):
    e = (await db.execute(select(EncuestaCentro).filter(EncuestaCentro.id_encuesta == id_encuesta))).scalars().first()
    if not e:
        raise HTTPException(status_code=404, detail="Encuesta no encontrada")

    await db.execute(sa_delete(MedicoCentroEncuesta).where(MedicoCentroEncuesta.id_encuesta == id_encuesta))
    await db.delete(e)
    await db.commit()
    return {"success": True}


# --- MEDICOS ---

@router.get("/medicos")
async def list_medicos(
    q: str = "",
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    stmt = select(Medico)
    if q.strip():
        search = f"%{q.strip()}%"
        stmt = stmt.filter(
            or_(
                Medico.id_medico_externo.ilike(search),
                Medico.nombre1.ilike(search),
                Medico.apellido1.ilike(search)
            )
        )
    medicos = (await db.execute(stmt.order_by(Medico.apellido1, Medico.nombre1).limit(100))).scalars().all()

    if not medicos:
        return []

    medicos_ids = [m.id_medico for m in medicos]
    consultorios_raw = (await db.execute(
        select(MedicoConsultorio).filter(MedicoConsultorio.id_medico.in_(medicos_ids))
    )).scalars().all()

    consultorios_by_medico = {}
    for c in consultorios_raw:
        if c.id_medico not in consultorios_by_medico:
            consultorios_by_medico[c.id_medico] = []
        consultorios_by_medico[c.id_medico].append({
            "id_consultorio": c.id_consultorio,
            "nombre_clinica": c.nombre_clinica,
            "piso_consultorio": c.piso_consultorio,
            "direccion_especifica": c.direccion_especifica,
            "horarios_json": c.horarios_json,
            "valor_consulta_rango": c.valor_consulta_rango,
            "promedio_pacientes_semanal_rango": c.promedio_pacientes_semanal_rango
        })

    result = []
    for m in medicos:
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
            "consultorios": consultorios_by_medico.get(m.id_medico, [])
        })
    return result

@router.post("/medicos")
async def create_medico_centro(
    req: MedicoCentroSaveRequest,
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "write", fallback_roles=("admin", "supervisor")))
):
    id_medico = req.id_medico
    if not id_medico:
        if not req.medico_data:
            raise HTTPException(status_code=400, detail="Faltan datos del médico para crear")
        
        # Verificar duplicado por id externo
        existente = (await db.execute(select(Medico).filter(Medico.id_medico_externo == req.medico_data.id_medico_externo))).scalars().first()
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
                segunda_universidad_graduacion=req.medico_data.segunda_universidad_graduacion,
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
    dup = (await db.execute(
        select(MedicoCentroEncuesta).filter(
            MedicoCentroEncuesta.id_encuesta == req.id_encuesta,
            MedicoCentroEncuesta.id_medico == id_medico
        )
    )).scalars().first()
    
    if not dup:
        db.add(MedicoCentroEncuesta(id_encuesta=req.id_encuesta, id_medico=id_medico))

    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        detail = "No se pudo guardar: hay un dato duplicado o inválido."
        if "id_medico_externo" in str(e.orig):
            detail = "No se pudo guardar: la cédula/ID externo ya está en uso por otro médico."
        raise HTTPException(status_code=409, detail=detail)
    return {"success": True, "id_medico": id_medico}

@router.put("/medicos/{id_medico}")
async def update_medico(
    id_medico: int,
    req: MedicoEditRequest,
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "write", fallback_roles=("admin", "supervisor")))
):
    m = (await db.execute(select(Medico).filter(Medico.id_medico == id_medico))).scalars().first()
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

    await db.execute(sa_delete(MedicoConsultorio).where(MedicoConsultorio.id_medico == id_medico))
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

    # Antes esto no atrapaba nada: cualquier violación de constraint (ej.
    # id_medico_externo duplicado -- UNIQUE+NOT NULL, ver medicos.id_medico_
    # externo) subía como 500 genérico "Error interno del servidor", sin
    # decir cuál campo chocó. Con esto el analista/supervisor al menos ve
    # QUÉ chocó en vez de un error opaco -- no arregla la causa de fondo
    # (eso necesita el dato real del médico que está fallando).
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        detail = "No se pudo guardar: hay un dato duplicado o inválido."
        if "id_medico_externo" in str(e.orig):
            detail = "No se pudo guardar: la cédula/ID externo ya está en uso por otro médico."
        raise HTTPException(status_code=409, detail=detail)
    return {"success": True}

@router.delete("/medicos/{id_medico}")
async def delete_medico_relacion(
    id_medico: int,
    id_encuesta: int,
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "delete", fallback_roles=("admin", "supervisor")))
):
    await db.execute(
        sa_delete(MedicoCentroEncuesta).where(
            MedicoCentroEncuesta.id_encuesta == id_encuesta,
            MedicoCentroEncuesta.id_medico == id_medico
        )
    )
    await db.commit()
    return {"success": True}

# --- CENTROS ---

class CentroSaludCreateReq(BaseModel):
    nombre_centro: str
    direccion_completa: str
    ciudad: Optional[str] = None
    estado: Optional[str] = None

@router.get("/centros")
async def get_centros_list(
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "read", fallback_roles=("admin", "supervisor")))
):
    centros = (await db.execute(select(CentroSalud).order_by(CentroSalud.nombre_centro))).scalars().all()
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

@router.post("/centros")
async def create_centro_salud(
    req: CentroSaludCreateReq,
    db: AsyncSession = Depends(get_async_db),
    _: User = Depends(require_permission("supervisor-encuestadores", "write", fallback_roles=("admin", "supervisor")))
):
    nombre = req.nombre_centro.strip()
    direccion = req.direccion_completa.strip()
    if not nombre or not direccion:
        raise HTTPException(status_code=400, detail="El nombre del centro y la dirección completa son obligatorios.")

    try:
        nuevo_centro = CentroSalud(
            nombre_centro=nombre,
            direccion_completa=direccion,
            ciudad=req.ciudad.strip() if req.ciudad else None,
            estado=req.estado.strip() if req.estado else None
        )
        db.add(nuevo_centro)
        await db.commit()
        await db.refresh(nuevo_centro)
        return {
            "success": True,
            "id_centro": nuevo_centro.id_centro,
            "nombre_centro": nuevo_centro.nombre_centro,
            "message": "Centro de salud creado exitosamente."
        }
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear el centro de salud: {str(e)}")

