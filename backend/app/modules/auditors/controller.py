import os
import uuid
from datetime import datetime, date
from typing import List, Optional, Any
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import func, case
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_admin
from app.modules.auth.entities import Usuario
from app.modules.auditors.entities import AuditLog, AuditoriaCategoria
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.visits.entities import Visita, Foto, Activacion
from app.modules.routes.entities import Ruta, RutaActivada, RutaProgramacion, PuntoInteres
from app.modules.clients.entities import Cliente, CategoriaCliente
from app.modules.catalogues.entities import Categoria
from app.shared.photo_service import process_and_upload_photo
from app.modules.auditors.dto import (
    AuditorStatsResponse,
    AuditorRouteResponse,
    ActivarRutaRequest,
    DeactivarRutaRequest,
    AuditorCampoRutaResponse,
    RutaPuntoResponse,
    ActivarRutaCampoRequest,
    NoActivarRutaCampoRequest,
    DesactivarRutaCampoRequest,
    PdvClienteResponse,
    ClienteCategoriaResponse,
    IniciarAuditoriaClienteRequest,
    IniciarAuditoriaClienteResponse,
    GuardarAuditoriaCategoriaRequest,
    FinalizarAuditoriaClienteRequest,
    AuditLogItemResponse,
    AuditLogsPaginatedResponse,
)

router = APIRouter(tags=["Auditores"])

ENTITY_TYPES = ["Auth", "Usuario", "Foto", "PuntoInteres", "Producto", "Sesion", "Permisos"]
TIPO = "Auditor de Campo"
DIAS = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}


def _es_cedula(cedula: Any) -> bool:
    s = str(cedula).strip()
    return s.isdigit()


def _auditor_id(db: Session, cedula: str) -> Optional[int]:
    if not _es_cedula(cedula):
        return None
    try:
        ced_int = int(str(cedula).strip())
    except ValueError:
        return None
    res = db.query(Mercaderista.id).filter(
        Mercaderista.cedula == ced_int,
        Mercaderista.tipo == TIPO
    ).first()
    return res[0] if res else None


def _b(v: Any) -> Optional[int]:
    if v is None:
        return None
    return 1 if v in (True, 1, "1", "si", "Si", "true") else 0


# ════════════════════════════════════════════════════════════════════════════
# 1. Auditor Estadísticas y Rutas (antes routes/auditors.py)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/api/auditor/stats/{cedula}", response_model=AuditorStatsResponse)
def get_auditor_stats(
    cedula: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    if not _es_cedula(cedula):
        raise HTTPException(status_code=400, detail="Cédula inválida")
    ced_int = int(str(cedula).strip())
    merc = db.query(Mercaderista).filter(Mercaderista.cedula == ced_int, Mercaderista.tipo == "Auditor").first()
    if not merc:
        raise HTTPException(status_code=404, detail="Auditor no encontrado")
    today = date.today()
    visitas_hoy = db.query(Visita).filter(
        Visita.mercaderista_id == merc.id,
        Visita.fecha == today,
    ).count()
    activaciones_hoy = db.query(Activacion).filter(
        Activacion.mercaderista_id == merc.id,
        Activacion.fecha == today,
    ).count()
    return AuditorStatsResponse(
        cedula=cedula,
        nombre=merc.nombre_completo,
        visitas_hoy=visitas_hoy,
        activaciones_hoy=activaciones_hoy,
    )


@router.get("/api/auditor/routes/{cedula}", response_model=List[AuditorRouteResponse])
def get_auditor_routes(
    cedula: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    if not _es_cedula(cedula):
        raise HTTPException(status_code=400, detail="Cédula inválida")
    ced_int = int(str(cedula).strip())
    merc = db.query(Mercaderista).filter(Mercaderista.cedula == ced_int).first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    
    routes = (
        db.query(Ruta)
        .join(MercaderistaRuta, Ruta.id == MercaderistaRuta.ruta_id)
        .filter(MercaderistaRuta.mercaderista_id == merc.id)
        .all()
    )
    return [AuditorRouteResponse(id=r.id, nombre=r.nombre or "", activa=r.activa) for r in routes if r]


@router.post("/api/auditor/activate-route")
def activate_route(
    payload: ActivarRutaRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    today = date.today()
    mid = _auditor_id(db, payload.cedula)
    existing = db.query(RutaActivada).filter(
        RutaActivada.ruta_id == payload.ruta_id,
        func.cast(RutaActivada.fecha_hora_activacion, Date) == today,
        RutaActivada.mercaderista_id == mid,
    ).first() if mid else None

    if existing:
        return {"message": "Ruta ya activada"}
    
    activacion = RutaActivada(
        ruta_id=payload.ruta_id,
        fecha_hora_activacion=datetime.now(),
        mercaderista_id=mid,
        estado="En Progreso",
        tipo_activacion="Auditor"
    )
    db.add(activacion)
    db.commit()
    return {"message": "Ruta activada exitosamente"}


@router.post("/api/auditor/deactivate-route")
def deactivate_route(
    payload: DeactivarRutaRequest,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    today = date.today()
    mid = _auditor_id(db, payload.cedula)
    if mid:
        db.query(RutaActivada).filter(
            RutaActivada.ruta_id == payload.ruta_id,
            func.cast(RutaActivada.fecha_hora_activacion, Date) == today,
            RutaActivada.mercaderista_id == mid,
        ).delete(synchronize_session=False)
        db.commit()
    return {"message": "Ruta desactivada"}


@router.post("/api/auditor/upload-activation-photo")
async def upload_activation_photo(
    punto_id: int = Form(...),
    mercaderista_cedula: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    file_bytes = await file.read()
    result = process_and_upload_photo(file_bytes, file.content_type or "image/jpeg", prefix="activaciones")
    return {"blob_path": result["blob_path"], "url": result["url"], "message": "Foto de activación subida"}


@router.post("/api/auditor/save-data")
def save_auditor_data(
    data: dict,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    return {"message": "Datos guardados", "data": data}


# ════════════════════════════════════════════════════════════════════════════
# 2. Auditor de Campo (antes routes/auditor_campo.py)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/api/auditor-campo/rutas/{cedula}", response_model=List[AuditorCampoRutaResponse])
def get_auditor_campo_rutas(cedula: str, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    if not _es_cedula(cedula):
        return []
    ced_int = int(str(cedula).strip())
    today = date.today()

    sub_count = (
        db.query(
            RutaProgramacion.ruta_id.label("id_ruta"),
            func.count(func.distinct(RutaProgramacion.punto_id)).label("total_puntos")
        )
        .filter(RutaProgramacion.activo == True)
        .group_by(RutaProgramacion.ruta_id)
        .subquery()
    )

    sub_active = (
        db.query(RutaActivada.ruta_id.label("id_ruta"))
        .join(Mercaderista, RutaActivada.mercaderista_id == Mercaderista.id)
        .filter(
            Mercaderista.cedula == ced_int,
            RutaActivada.estado == "En Progreso",
            func.cast(RutaActivada.fecha_hora_activacion, Date) == today
        )
        .subquery()
    )

    query = (
        db.query(
            Ruta.id,
            Ruta.nombre,
            func.coalesce(sub_count.c.total_puntos, 0).label("total_puntos"),
            case((sub_active.c.id_ruta.isnot(None), 1), else_=0).label("activa")
        )
        .join(MercaderistaRuta, Ruta.id == MercaderistaRuta.ruta_id)
        .join(Mercaderista, MercaderistaRuta.mercaderista_id == Mercaderista.id)
        .outerjoin(sub_count, Ruta.id == sub_count.c.id_ruta)
        .outerjoin(sub_active, Ruta.id == sub_active.c.id_ruta)
        .filter(
            Mercaderista.cedula == ced_int,
            Mercaderista.tipo == TIPO
        )
        .order_by(Ruta.nombre)
        .all()
    )

    return [
        AuditorCampoRutaResponse(
            id=r[0],
            nombre=r[1] or "",
            total_puntos=r[2] or 0,
            esta_activa=bool(r[3])
        )
        for r in query
    ]


@router.get("/api/auditor-campo/ruta-puntos/{route_id}", response_model=List[RutaPuntoResponse])
def get_ruta_puntos(route_id: int, cedula: str, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    dia = DIAS[datetime.now().weekday()]
    today = date.today()

    sub_act = (
        db.query(Visita.punto_id.label("identificador_punto"))
        .join(Foto, Foto.visita_id == Visita.id)
        .filter(
            Foto.id_tipo_foto == 5,
            func.cast(Foto.fecha_registro, Date) == today
        )
        .subquery()
    )

    query = (
        db.query(
            PuntoInteres.id,
            PuntoInteres.nombre,
            func.max(RutaProgramacion.prioridad).label("prioridad"),
            func.count(func.distinct(RutaProgramacion.id_cliente)).label("total_clientes"),
            case((sub_act.c.identificador_punto.isnot(None), 1), else_=0).label("activado")
        )
        .join(PuntoInteres, RutaProgramacion.punto_id == PuntoInteres.id)
        .outerjoin(sub_act, PuntoInteres.id == sub_act.c.identificador_punto)
        .filter(
            RutaProgramacion.ruta_id == route_id,
            RutaProgramacion.activo == True,
            RutaProgramacion.dia == dia
        )
        .group_by(PuntoInteres.id, PuntoInteres.nombre, sub_act.c.identificador_punto)
        .order_by(PuntoInteres.nombre)
        .all()
    )

    return [
        RutaPuntoResponse(
            id=r[0],
            nombre=r[1] or "",
            prioridad=r[2] or "Media",
            total_clientes=r[3] or 0,
            activado=bool(r[4])
        )
        for r in query
    ]


@router.post("/api/auditor-campo/activar-ruta")
def activar_ruta_campo(payload: ActivarRutaCampoRequest, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    id_ruta, cedula = payload.id_ruta, payload.cedula
    mid = _auditor_id(db, cedula)
    if not mid:
        raise HTTPException(404, "Auditor no encontrado")
    
    today = date.today()
    existing = db.query(RutaActivada).filter(
        RutaActivada.ruta_id == id_ruta,
        RutaActivada.mercaderista_id == mid,
        RutaActivada.estado == "En Progreso",
        func.cast(RutaActivada.fecha_hora_activacion, Date) == today
    ).first()

    if existing:
        return {"success": True, "message": "La ruta ya estaba activa hoy"}

    activacion = RutaActivada(
        ruta_id=id_ruta,
        mercaderista_id=mid,
        fecha_hora_activacion=datetime.now(),
        estado="En Progreso",
        tipo_activacion="Auditor de Campo"
    )
    db.add(activacion)
    db.commit()
    return {"success": True, "message": "Ruta activada"}


@router.post("/api/auditor-campo/no-activar-ruta")
def no_activar_ruta_campo(payload: NoActivarRutaCampoRequest, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    id_ruta, cedula = payload.id_ruta, payload.cedula
    razon = payload.razon.strip()
    if not razon:
        raise HTTPException(400, "La razón es requerida")
    mid = _auditor_id(db, cedula)
    if not mid:
        raise HTTPException(404, "Auditor no encontrado")

    activacion = RutaActivada(
        ruta_id=id_ruta,
        mercaderista_id=mid,
        fecha_hora_activacion=datetime.now(),
        estado="No Activada",
        tipo_activacion="Auditor de Campo",
        motivo_no_activacion=razon
    )
    db.add(activacion)
    db.commit()
    return {"success": True, "message": "No activación registrada"}


@router.post("/api/auditor-campo/desactivar-ruta")
def desactivar_ruta_campo(payload: DesactivarRutaCampoRequest, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    id_ruta, cedula = payload.id_ruta, payload.cedula
    mid = _auditor_id(db, cedula)
    if not mid:
        raise HTTPException(404, "Auditor no encontrado")
    
    today = date.today()
    activaciones = db.query(RutaActivada).filter(
        RutaActivada.ruta_id == id_ruta,
        RutaActivada.mercaderista_id == mid,
        RutaActivada.estado == "En Progreso",
        func.cast(RutaActivada.fecha_hora_activacion, Date) == today
    ).all()

    for act in activaciones:
        act.estado = "Finalizado"
    db.commit()
    return {"success": True, "message": "Ruta desactivada"}


async def _guardar_foto(db: Session, file: UploadFile, point_id, id_tipo_foto, prefix,
                        id_visita=None, categoria=None, lat=None, lon=None):
    raw = await file.read()
    latv, lonv, url = lat, lon, None
    try:
        res = process_and_upload_photo(raw, file.content_type or "image/jpeg", prefix=prefix)
        blob_path = res["blob_path"]
        url = res.get("url")
        if latv is None:
            latv = res.get("latitud")
        if lonv is None:
            lonv = res.get("longitud")
    except Exception:
        base = "app/static/auditor_campo_local"
        os.makedirs(base, exist_ok=True)
        fname = prefix.replace("/", "_") + "_" + uuid.uuid4().hex + ".jpg"
        with open(os.path.join(base, fname), "wb") as fh:
            fh.write(raw)
        blob_path = "auditor_campo_local/" + fname

    nueva_foto = Foto(
        visita_id=id_visita,
        categoria=categoria,
        blob_path=blob_path,
        fecha_registro=datetime.now(),
        id_tipo_foto=id_tipo_foto,
        estado="Aprobada",
        latitud=latv,
        longitud=lonv
    )
    db.add(nueva_foto)
    db.commit()
    db.refresh(nueva_foto)
    return {"id_foto": nueva_foto.id, "url": url, "blob_path": blob_path}


@router.post("/api/auditor-campo/activar-pdv")
async def activar_pdv(point_id: str = Form(...), cedula: str = Form(...),
                      lat: Optional[float] = Form(None), lon: Optional[float] = Form(None),
                      file: UploadFile = File(...), db: Session = Depends(get_db),
                      _: Usuario = Depends(get_current_user)):
    r = await _guardar_foto(db, file, point_id, 5, "auditor_campo/activaciones", lat=lat, lon=lon)
    return {"success": True, "message": "PDV activado", **r}


@router.post("/api/auditor-campo/desactivar-pdv")
async def desactivar_pdv(point_id: str = Form(...), cedula: str = Form(...),
                         lat: Optional[float] = Form(None), lon: Optional[float] = Form(None),
                         file: UploadFile = File(...), db: Session = Depends(get_db),
                         _: Usuario = Depends(get_current_user)):
    r = await _guardar_foto(db, file, point_id, 6, "auditor_campo/desactivaciones", lat=lat, lon=lon)
    return {"success": True, "message": "PDV desactivado", **r}


@router.post("/api/auditor-campo/subir-foto-categoria")
async def subir_foto_categoria(id_visita: int = Form(...), id_categoria: int = Form(...),
                               categoria_nombre: str = Form(None), point_id: str = Form(None),
                               cedula: str = Form(None), lat: Optional[float] = Form(None),
                               lon: Optional[float] = Form(None), file: UploadFile = File(...),
                               db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    r = await _guardar_foto(db, file, point_id, 11, "auditor_campo/categories",
                            id_visita=id_visita, categoria=categoria_nombre, lat=lat, lon=lon)
    return {"success": True, "message": "Foto subida", **r}


@router.get("/api/auditor-campo/pdv-clientes/{point_id}/{route_id}", response_model=List[PdvClienteResponse])
def get_pdv_clientes(point_id: str, route_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    dia = DIAS[datetime.now().weekday()]
    rows = (
        db.query(
            RutaProgramacion.id_cliente,
            Cliente.nombre,
            RutaProgramacion.prioridad
        )
        .distinct()
        .join(Cliente, RutaProgramacion.id_cliente == Cliente.id)
        .filter(
            RutaProgramacion.punto_id == point_id,
            RutaProgramacion.ruta_id == route_id,
            RutaProgramacion.activo == True,
            RutaProgramacion.dia == dia
        )
        .order_by(RutaProgramacion.prioridad.desc(), Cliente.nombre)
        .all()
    )
    return [
        PdvClienteResponse(
            id=r[0],
            nombre=r[1] or "",
            prioridad=r[2] or "Media"
        )
        for r in rows
    ]


@router.get("/api/auditor-campo/cliente-categorias/{cliente_id}", response_model=List[ClienteCategoriaResponse])
def get_cliente_categorias(cliente_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    rows = (
        db.query(
            Categoria.id_categoria,
            Categoria.nombre
        )
        .join(CategoriaCliente, Categoria.id_categoria == CategoriaCliente.id_categoria)
        .filter(CategoriaCliente.id_cliente == cliente_id)
        .order_by(Categoria.nombre)
        .all()
    )
    return [
        ClienteCategoriaResponse(
            id=r[0],
            nombre=r[1] or ""
        )
        for r in rows
    ]


@router.post("/api/auditor-campo/iniciar-auditoria-cliente", response_model=IniciarAuditoriaClienteResponse)
def iniciar_auditoria_cliente(payload: IniciarAuditoriaClienteRequest, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    cliente_id, point_id, cedula = payload.cliente_id, payload.point_id, payload.cedula
    mid = _auditor_id(db, cedula)
    if not mid:
        raise HTTPException(404, "Auditor no encontrado")
    
    today = date.today()
    visita_existente = (
        db.query(Visita.id)
        .filter(
            Visita.mercaderista_id == mid,
            Visita.id_cliente == cliente_id,
            Visita.punto_id == point_id,
            Visita.fecha == today
        )
        .order_by(Visita.id.desc())
        .first()
    )

    if visita_existente:
        vid = visita_existente[0]
    else:
        nueva_visita = Visita(
            mercaderista_id=mid,
            fecha=today,
            estado="Pendiente",
            id_cliente=cliente_id,
            punto_id=point_id,
            estado_data="Activo"
        )
        db.add(nueva_visita)
        db.commit()
        db.refresh(nueva_visita)
        vid = nueva_visita.id

    return IniciarAuditoriaClienteResponse(success=True, id_visita=int(vid))


@router.post("/api/auditor-campo/guardar-auditoria-categoria")
def guardar_auditoria_categoria(payload: GuardarAuditoriaCategoriaRequest, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    d = payload.model_dump()
    nueva_auditoria = AuditoriaCategoria(
        id_visita=d["id_visita"],
        id_categoria=d["id_categoria"],
        aplico_planograma=_b(d.get("aplico_planograma")),
        lineamiento_marca=_b(d.get("lineamiento_marca")),
        precio_correcto=_b(d.get("precio_correcto")),
        limpieza_correcta=_b(d.get("limpieza_correcta")),
        participacion_correcta=_b(d.get("participacion_correcta")),
        fifo_correcto=_b(d.get("fifo_correcto")),
        prox_vencer=_b(d.get("prox_vencer")),
        prox_vencer_cantidad=d.get("prox_vencer_cantidad"),
        prox_vencer_marca=d.get("prox_vencer_marca"),
        prox_vencer_fecha1=d.get("prox_vencer_fecha1") or None,
        prox_vencer_fecha2=d.get("prox_vencer_fecha2") or None,
        competencia_actividad=_b(d.get("competencia_actividad")),
        competencia_material_pop=_b(d.get("competencia_material_pop")),
        competencia_impulsadora=_b(d.get("competencia_impulsadora")),
        pop_hablador=_b(d.get("pop_hablador")),
        pop_rompetrafico=_b(d.get("pop_rompetrafico")),
        pop_otro=d.get("pop_otro"),
        promo_nuestra=_b(d.get("promo_nuestra")),
        promo_nuestra_desc=d.get("promo_nuestra_desc"),
        promo_competencia=_b(d.get("promo_competencia")),
        promo_competencia_desc=d.get("promo_competencia_desc"),
        exhibicion_adicional=_b(d.get("exhibicion_adicional")),
        exhibicion_tipos=d.get("exhibicion_tipos")
    )
    db.add(nueva_auditoria)
    db.commit()
    return {"success": True, "message": "Auditoría de categoría guardada"}


@router.post("/api/auditor-campo/finalizar-auditoria-cliente")
def finalizar_auditoria_cliente(payload: FinalizarAuditoriaClienteRequest, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    visita = db.query(Visita).get(payload.id_visita)
    if not visita:
        raise HTTPException(404, "Visita no encontrada")
    visita.estado = "Finalizada"
    db.commit()
    return {"success": True, "message": "Auditoría del cliente finalizada"}


# ════════════════════════════════════════════════════════════════════════════
# 3. Log de Auditoría Operativo (antes routes/audit.py)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/api/audit/logs", response_model=AuditLogsPaginatedResponse)
def get_audit_logs(
    entity_type: Optional[str] = None,
    action: Optional[str] = None,
    user_id: Optional[int] = None,
    username: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    status: Optional[str] = None,
    limit: int = Query(100, le=500),
    offset: int = 0,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_admin),
):
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if user_id:
        q = q.filter(AuditLog.user_id == user_id)
    if username:
        q = q.filter(AuditLog.username.ilike(f"%{username}%"))
    if from_date:
        q = q.filter(AuditLog.timestamp >= from_date)
    if to_date:
        q = q.filter(AuditLog.timestamp <= to_date)
    if status:
        q = q.filter(AuditLog.status == status)

    total = q.count()
    logs = q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit).all()

    return AuditLogsPaginatedResponse(
        total=total,
        offset=offset,
        limit=limit,
        items=[
            AuditLogItemResponse(
                id=log.id,
                timestamp=log.timestamp,
                user_id=log.user_id,
                username=log.username,
                rol=log.rol,
                ip_address=log.ip_address,
                action=log.action,
                entity_type=log.entity_type,
                entity_id=log.entity_id,
                entity_name=log.entity_name,
                changes=log.changes,
                status=log.status,
            )
            for log in logs
        ],
    )


@router.get("/api/audit/entity-types")
def get_entity_types(_: Usuario = Depends(require_admin)):
    return ENTITY_TYPES
