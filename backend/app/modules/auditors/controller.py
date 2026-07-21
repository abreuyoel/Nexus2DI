import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_admin
from app.modules.auth.entities import Usuario
from app.modules.auditors.entities import AuditLog
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.visits.entities import Visita, Foto, NotificacionRechazoFoto, Activacion
from app.modules.routes.entities import Ruta, RutaActivada
from app.modules.clients.entities import Cliente
from app.modules.visits.dto import FotoResponse, NotificacionRechazoResponse
from app.shared.photo_service import process_and_upload_photo
from app.shared.audit_service import log_action
from app.core.request_ip import get_client_ip

router = APIRouter(tags=["Auditores"])

ENTITY_TYPES = ["Auth", "Usuario", "Foto", "PuntoInteres", "Producto", "Sesion", "Permisos"]
TIPO = "Auditor de Campo"
DIAS = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}


def _es_cedula(cedula) -> bool:
    return str(cedula).strip().isdigit()


def _auditor_id(db: Session, cedula: str) -> Optional[int]:
    if not _es_cedula(cedula):
        return None
    r = db.execute(text(
        "SELECT id_mercaderista FROM MERCADERISTAS WHERE LTRIM(RTRIM(cedula))=LTRIM(RTRIM(:c)) AND tipo=:t"
    ), {"c": cedula, "t": TIPO}).fetchone()
    return r[0] if r else None


# ════════════════════════════════════════════════════════════════════════════
# 1. Auditor Estadísticas y Rutas (antes routes/auditors.py)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/api/auditor/stats/{cedula}")
def get_auditor_stats(
    cedula: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    merc = db.query(Mercaderista).filter(Mercaderista.cedula == cedula, Mercaderista.tipo == "Auditor").first()
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
    return {
        "cedula": cedula,
        "nombre": merc.nombre_completo,
        "visitas_hoy": visitas_hoy,
        "activaciones_hoy": activaciones_hoy,
    }


@router.get("/api/auditor/routes/{cedula}")
def get_auditor_routes(
    cedula: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    merc = db.query(Mercaderista).filter(Mercaderista.cedula == cedula).first()
    if not merc:
        raise HTTPException(status_code=404, detail="Mercaderista no encontrado")
    mr_list = db.query(MercaderistaRuta).filter(
        MercaderistaRuta.mercaderista_id == merc.id,
        MercaderistaRuta.activo == True,
    ).all()
    rutas = [db.query(Ruta).get(mr.ruta_id) for mr in mr_list]
    return [{"id": r.id, "nombre": r.nombre, "activa": r.activa} for r in rutas if r]


@router.post("/api/auditor/activate-route")
def activate_route(
    ruta_id: int,
    cedula: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    today = date.today()
    existing = db.query(RutaActivada).filter(
        RutaActivada.ruta_id == ruta_id,
        RutaActivada.fecha == today,
        RutaActivada.mercaderista_cedula == cedula,
    ).first()
    if existing:
        return {"message": "Ruta ya activada"}
    activacion = RutaActivada(ruta_id=ruta_id, fecha=today, mercaderista_cedula=cedula)
    db.add(activacion)
    db.commit()
    return {"message": "Ruta activada exitosamente"}


@router.post("/api/auditor/deactivate-route")
def deactivate_route(
    ruta_id: int,
    cedula: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    today = date.today()
    db.query(RutaActivada).filter(
        RutaActivada.ruta_id == ruta_id,
        RutaActivada.fecha == today,
        RutaActivada.mercaderista_cedula == cedula,
    ).delete()
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

@router.get("/api/auditor-campo/rutas/{cedula}")
def get_auditor_campo_rutas(cedula: str, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    if not _es_cedula(cedula):
        return []
    rows = db.execute(text("""
        SELECT rn.id_ruta, rn.ruta,
            (SELECT COUNT(DISTINCT rp2.id_punto_interes) FROM RUTA_PROGRAMACION rp2
             WHERE rp2.id_ruta = rn.id_ruta AND rp2.activa = 1) AS total_puntos,
            CASE WHEN EXISTS (
                SELECT 1 FROM RUTAS_ACTIVADAS ra JOIN MERCADERISTAS m2 ON ra.id_mercaderista = m2.id_mercaderista
                WHERE ra.id_ruta = rn.id_ruta AND m2.cedula = :ced AND ra.estado = 'En Progreso'
                AND CAST(ra.fecha_hora_activacion AS DATE) = CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END AS activa
        FROM RUTAS_NUEVAS rn
        JOIN MERCADERISTAS_RUTAS mr ON rn.id_ruta = mr.id_ruta
        JOIN MERCADERISTAS m ON mr.id_mercaderista = m.id_mercaderista
        WHERE m.cedula = :ced AND m.tipo = :tipo
        ORDER BY rn.ruta
    """), {"ced": cedula, "tipo": TIPO}).fetchall()
    return [{"id": r[0], "nombre": r[1], "total_puntos": r[2] or 0, "esta_activa": bool(r[3])} for r in rows]


@router.get("/api/auditor-campo/ruta-puntos/{route_id}")
def get_ruta_puntos(route_id: int, cedula: str, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    dia = DIAS[datetime.now().weekday()]
    rows = db.execute(text("""
        SELECT pin.identificador, pin.punto_de_interes, MAX(rp.prioridad) AS prioridad,
            COUNT(DISTINCT rp.id_cliente) AS total_clientes,
            CASE WHEN EXISTS (
                SELECT 1 FROM FOTOS_TOTALES ft JOIN VISITAS_MERCADERISTA vm ON ft.id_visita = vm.id_visita
                WHERE vm.identificador_punto_interes = pin.identificador AND ft.id_tipo_foto = 5
                AND CAST(ft.fecha_registro AS DATE) = CAST(GETDATE() AS DATE)) THEN 1 ELSE 0 END AS activado
        FROM RUTA_PROGRAMACION rp
        JOIN PUNTOS_INTERES1 pin ON rp.id_punto_interes = pin.identificador
        WHERE rp.id_ruta = :rid AND rp.activa = 1 AND rp.dia = :dia
        GROUP BY pin.identificador, pin.punto_de_interes
        ORDER BY pin.punto_de_interes
    """), {"rid": route_id, "dia": dia}).fetchall()
    return [{"id": r[0], "nombre": r[1], "prioridad": r[2] or "Media",
             "total_clientes": r[3] or 0, "activado": bool(r[4])} for r in rows]


@router.post("/api/auditor-campo/activar-ruta")
def activar_ruta_campo(payload: dict, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    id_ruta, cedula = payload.get("id_ruta"), payload.get("cedula")
    if not id_ruta or not cedula:
        raise HTTPException(400, "Datos incompletos")
    mid = _auditor_id(db, cedula)
    if not mid:
        raise HTTPException(404, "Auditor no encontrado")
    existe = db.execute(text("""SELECT COUNT(*) FROM RUTAS_ACTIVADAS WHERE id_ruta=:r AND id_mercaderista=:m
        AND estado='En Progreso' AND CAST(fecha_hora_activacion AS DATE)=CAST(GETDATE() AS DATE)"""),
        {"r": id_ruta, "m": mid}).scalar()
    if existe and existe > 0:
        return {"success": True, "message": "La ruta ya estaba activa hoy"}
    db.execute(text("""INSERT INTO RUTAS_ACTIVADAS (id_ruta, id_mercaderista, fecha_hora_activacion, estado, tipo_activacion)
        VALUES (:r, :m, GETDATE(), 'En Progreso', 'Auditor de Campo')"""), {"r": id_ruta, "m": mid})
    db.commit()
    return {"success": True, "message": "Ruta activada"}


@router.post("/api/auditor-campo/no-activar-ruta")
def no_activar_ruta_campo(payload: dict, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    id_ruta, cedula = payload.get("id_ruta"), payload.get("cedula")
    razon = (payload.get("razon") or "").strip()
    if not id_ruta or not cedula:
        raise HTTPException(400, "Datos incompletos")
    if not razon:
        raise HTTPException(400, "La razón es requerida")
    mid = _auditor_id(db, cedula)
    if not mid:
        raise HTTPException(404, "Auditor no encontrado")
    db.execute(text("""INSERT INTO RUTAS_ACTIVADAS
        (id_ruta, id_mercaderista, fecha_hora_activacion, estado, tipo_activacion, motivo_no_activacion)
        VALUES (:r, :m, GETDATE(), 'No Activada', 'Auditor de Campo', :razon)"""),
        {"r": id_ruta, "m": mid, "razon": razon})
    db.commit()
    return {"success": True, "message": "No activación registrada"}


@router.post("/api/auditor-campo/desactivar-ruta")
def desactivar_ruta_campo(payload: dict, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    id_ruta, cedula = payload.get("id_ruta"), payload.get("cedula")
    if not id_ruta or not cedula:
        raise HTTPException(400, "Datos incompletos")
    mid = _auditor_id(db, cedula)
    if not mid:
        raise HTTPException(404, "Auditor no encontrado")
    db.execute(text("""UPDATE RUTAS_ACTIVADAS SET estado='Finalizado'
        WHERE id_ruta=:r AND id_mercaderista=:m AND estado='En Progreso'
        AND CAST(fecha_hora_activacion AS DATE)=CAST(GETDATE() AS DATE)"""), {"r": id_ruta, "m": mid})
    db.commit()
    return {"success": True, "message": "Ruta desactivada"}


async def _guardar_foto(db, file: UploadFile, point_id, id_tipo_foto, prefix,
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
    except Exception as ex:
        base = "app/static/auditor_campo_local"
        os.makedirs(base, exist_ok=True)
        fname = prefix.replace("/", "_") + "_" + uuid.uuid4().hex + ".jpg"
        with open(os.path.join(base, fname), "wb") as fh:
            fh.write(raw)
        blob_path = "auditor_campo_local/" + fname

    db.execute(text("""INSERT INTO FOTOS_TOTALES
        (id_visita, categoria, file_path, fecha_registro, id_tipo_foto, Estado, latitud, longitud)
        VALUES (:v, :cat, :fp, GETDATE(), :tf, 'Aprobada', :lat, :lon)"""),
        {"v": id_visita, "cat": categoria, "fp": blob_path, "tf": id_tipo_foto, "lat": latv, "lon": lonv})
    db.commit()
    idf = db.execute(text("SELECT TOP 1 id_foto FROM FOTOS_TOTALES WHERE file_path=:fp ORDER BY id_foto DESC"),
                     {"fp": blob_path}).scalar()
    return {"id_foto": idf, "url": url, "blob_path": blob_path}


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


@router.get("/api/auditor-campo/pdv-clientes/{point_id}/{route_id}")
def get_pdv_clientes(point_id: str, route_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    dia = DIAS[datetime.now().weekday()]
    rows = db.execute(text("""
        SELECT DISTINCT rp.id_cliente, c.cliente, rp.prioridad
        FROM RUTA_PROGRAMACION rp JOIN CLIENTES c ON rp.id_cliente = c.id_cliente
        WHERE rp.id_punto_interes = :pid AND rp.id_ruta = :rid AND rp.activa = 1 AND rp.dia = :dia
        ORDER BY rp.prioridad DESC, c.cliente
    """), {"pid": point_id, "rid": route_id, "dia": dia}).fetchall()
    return [{"id": r[0], "nombre": r[1], "prioridad": r[2] or "Media"} for r in rows]


@router.get("/api/auditor-campo/cliente-categorias/{cliente_id}")
def get_cliente_categorias(cliente_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    rows = db.execute(text("""
        SELECT c.id_categoria, c.nombre
        FROM CATEGORIAS_CLIENTES cc JOIN CATEGORIAS c ON c.id_categoria = cc.id_categoria
        WHERE cc.id_cliente = :cid ORDER BY c.nombre
    """), {"cid": cliente_id}).fetchall()
    return [{"id": r[0], "nombre": r[1]} for r in rows]


@router.post("/api/auditor-campo/iniciar-auditoria-cliente")
def iniciar_auditoria_cliente(payload: dict, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    cliente_id, point_id, cedula = payload.get("cliente_id"), payload.get("point_id"), payload.get("cedula")
    if not cliente_id or not point_id or not cedula:
        raise HTTPException(400, "Datos incompletos")
    mid = _auditor_id(db, cedula)
    if not mid:
        raise HTTPException(404, "Auditor no encontrado")
    existe = db.execute(text("""SELECT TOP 1 id_visita FROM VISITAS_MERCADERISTA
        WHERE id_mercaderista=:m AND id_cliente=:c AND identificador_punto_interes=:p
        AND CAST(fecha_visita AS DATE)=CAST(GETDATE() AS DATE) ORDER BY id_visita DESC"""),
        {"m": mid, "c": cliente_id, "p": point_id}).scalar()
    if existe:
        vid = existe
    else:
        db.execute(text("""INSERT INTO VISITAS_MERCADERISTA
            (id_mercaderista, fecha_visita, estado, id_cliente, identificador_punto_interes, estado_data)
            VALUES (:m, GETDATE(), 'Pendiente', :c, :p, 'Activo')"""),
            {"m": mid, "c": cliente_id, "p": point_id})
        db.commit()
        vid = db.execute(text("""SELECT TOP 1 id_visita FROM VISITAS_MERCADERISTA
            WHERE id_mercaderista=:m AND id_cliente=:c AND identificador_punto_interes=:p
            ORDER BY id_visita DESC"""), {"m": mid, "c": cliente_id, "p": point_id}).scalar()
    if not vid:
        raise HTTPException(500, "No se pudo crear la visita")
    return {"success": True, "id_visita": int(vid)}


def _b(v):
    return None if v is None else (1 if v in (True, 1, "1", "si", "Si", "true") else 0)


@router.post("/api/auditor-campo/guardar-auditoria-categoria")
def guardar_auditoria_categoria(d: dict, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    id_visita, id_categoria = d.get("id_visita"), d.get("id_categoria")
    if not id_visita or not id_categoria:
        raise HTTPException(400, "id_visita e id_categoria requeridos")
    db.execute(text("""INSERT INTO AUDITORIA_CATEGORIAS
        (id_visita, id_categoria, aplico_planograma, lineamiento_marca, precio_correcto, limpieza_correcta,
         participacion_correcta, fifo_correcto, prox_vencer, prox_vencer_cantidad, prox_vencer_marca,
         prox_vencer_fecha1, prox_vencer_fecha2,
         competencia_actividad, competencia_material_pop, competencia_impulsadora,
         pop_hablador, pop_rompetrafico, pop_otro, promo_nuestra, promo_nuestra_desc,
         promo_competencia, promo_competencia_desc, exhibicion_adicional, exhibicion_tipos)
        VALUES (:v, :cat, :ap, :lm, :pc, :lc, :part, :fifo, :pv, :pvc, :pvm,
                :pvf1, :pvf2,
                :ca, :cmp, :ci, :ph, :pr, :po, :pn, :pnd, :pcomp, :pcompd, :ea, :et)"""),
        {"v": int(id_visita), "cat": int(id_categoria),
         "ap": _b(d.get("aplico_planograma")), "lm": _b(d.get("lineamiento_marca")),
         "pc": _b(d.get("precio_correcto")), "lc": _b(d.get("limpieza_correcta")),
         "part": _b(d.get("participacion_correcta")), "fifo": _b(d.get("fifo_correcto")),
         "pv": _b(d.get("prox_vencer")), "pvc": d.get("prox_vencer_cantidad"), "pvm": d.get("prox_vencer_marca"),
         "pvf1": (d.get("prox_vencer_fecha1") or None), "pvf2": (d.get("prox_vencer_fecha2") or None),
         "ca": _b(d.get("competencia_actividad")), "cmp": _b(d.get("competencia_material_pop")),
         "ci": _b(d.get("competencia_impulsadora")), "ph": _b(d.get("pop_hablador")),
         "pr": _b(d.get("pop_rompetrafico")), "po": d.get("pop_otro"),
         "pn": _b(d.get("promo_nuestra")), "pnd": d.get("promo_nuestra_desc"),
         "pcomp": _b(d.get("promo_competencia")), "pcompd": d.get("promo_competencia_desc"),
         "ea": _b(d.get("exhibicion_adicional")), "et": d.get("exhibicion_tipos")})
    db.commit()
    return {"success": True, "message": "Auditoría de categoría guardada"}


@router.post("/api/auditor-campo/finalizar-auditoria-cliente")
def finalizar_auditoria_cliente(d: dict, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    id_visita = d.get("id_visita")
    if not id_visita:
        raise HTTPException(400, "id_visita requerido")
    db.execute(text("UPDATE VISITAS_MERCADERISTA SET estado='Finalizada' WHERE id_visita=:v"), {"v": int(id_visita)})
    db.commit()
    return {"success": True, "message": "Auditoría del cliente finalizada"}


# ════════════════════════════════════════════════════════════════════════════
# 3. Log de Auditoría Operativo (antes routes/audit.py)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/api/audit/logs")
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

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "user_id": log.user_id,
                "username": log.username,
                "rol": log.rol,
                "ip_address": log.ip_address,
                "action": log.action,
                "entity_type": log.entity_type,
                "entity_id": log.entity_id,
                "entity_name": log.entity_name,
                "changes": log.changes,
                "status": log.status,
            }
            for log in logs
        ],
    }


@router.get("/api/audit/entity-types")
def get_entity_types(_: Usuario = Depends(require_admin)):
    return ENTITY_TYPES
