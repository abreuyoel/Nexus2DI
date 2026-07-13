"""Módulo Auditor de Campo (id_rol 14) para v2.
Flujo: activar ruta -> PDV (foto activación) -> cliente -> por categoría:
fotos (N) + cuestionario (AUDITORIA_CATEGORIAS) -> desactivar PDV -> desactivar ruta.
Reusa el servicio de fotos de v2 (compresión + Azure). SQL crudo para calzar
con el esquema operativo (RUTAS_ACTIVADAS, RUTA_PROGRAMACION, VISITAS_MERCADERISTA,
FOTOS_TOTALES, CATEGORIAS_CLIENTES, AUDITORIA_CATEGORIAS)."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import text
from sqlalchemy.orm import Session
from datetime import datetime
from typing import Optional
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.services.photo_service import process_and_upload_photo

router = APIRouter(prefix="/api/auditor-campo", tags=["Auditor de Campo"])

TIPO = "Auditor de Campo"
DIAS = {0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"}


def _es_cedula(cedula) -> bool:
    return str(cedula).strip().isdigit()


def _auditor_id(db: Session, cedula: str) -> Optional[int]:
    # cedula es INT en MERCADERISTAS: si no es numérica (p.ej. un admin 'Dev'
    # abriendo el módulo) evitamos el error de conversión y devolvemos None.
    if not _es_cedula(cedula):
        return None
    r = db.execute(text(
        "SELECT id_mercaderista FROM MERCADERISTAS WHERE LTRIM(RTRIM(cedula))=LTRIM(RTRIM(:c)) AND tipo=:t"
    ), {"c": cedula, "t": TIPO}).fetchone()
    return r[0] if r else None


# ───────────────── Rutas / PDVs ─────────────────
@router.get("/rutas/{cedula}")
def get_rutas(cedula: str, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
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


@router.get("/ruta-puntos/{route_id}")
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


# ───────────────── Activar / desactivar ruta ─────────────────
@router.post("/activar-ruta")
def activar_ruta(payload: dict, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
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


@router.post("/no-activar-ruta")
def no_activar_ruta(payload: dict, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
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


@router.post("/desactivar-ruta")
def desactivar_ruta(payload: dict, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
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


# ───────────────── Fotos (PDV / categoría) ─────────────────
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
        # Azure no configurado/alcanzable (típico al probar en local): guardamos la
        # foto en disco y continuamos, para no bloquear el flujo. En el servidor con
        # Azure configurado este bloque no se ejecuta.
        import os, uuid
        base = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static", "auditor_campo_local")
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


@router.post("/activar-pdv")
async def activar_pdv(point_id: str = Form(...), cedula: str = Form(...),
                      lat: Optional[float] = Form(None), lon: Optional[float] = Form(None),
                      file: UploadFile = File(...), db: Session = Depends(get_db),
                      _: Usuario = Depends(get_current_user)):
    r = await _guardar_foto(db, file, point_id, 5, "auditor_campo/activaciones", lat=lat, lon=lon)
    return {"success": True, "message": "PDV activado", **r}


@router.post("/desactivar-pdv")
async def desactivar_pdv(point_id: str = Form(...), cedula: str = Form(...),
                         lat: Optional[float] = Form(None), lon: Optional[float] = Form(None),
                         file: UploadFile = File(...), db: Session = Depends(get_db),
                         _: Usuario = Depends(get_current_user)):
    r = await _guardar_foto(db, file, point_id, 6, "auditor_campo/desactivaciones", lat=lat, lon=lon)
    return {"success": True, "message": "PDV desactivado", **r}


@router.post("/subir-foto-categoria")
async def subir_foto_categoria(id_visita: int = Form(...), id_categoria: int = Form(...),
                               categoria_nombre: str = Form(None), point_id: str = Form(None),
                               cedula: str = Form(None), lat: Optional[float] = Form(None),
                               lon: Optional[float] = Form(None), file: UploadFile = File(...),
                               db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    r = await _guardar_foto(db, file, point_id, 11, "auditor_campo/categorias",
                            id_visita=id_visita, categoria=categoria_nombre, lat=lat, lon=lon)
    return {"success": True, "message": "Foto subida", **r}


# ───────────────── Clientes / categorías ─────────────────
@router.get("/pdv-clientes/{point_id}/{route_id}")
def get_pdv_clientes(point_id: str, route_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    dia = DIAS[datetime.now().weekday()]
    rows = db.execute(text("""
        SELECT DISTINCT rp.id_cliente, c.cliente, rp.prioridad
        FROM RUTA_PROGRAMACION rp JOIN CLIENTES c ON rp.id_cliente = c.id_cliente
        WHERE rp.id_punto_interes = :pid AND rp.id_ruta = :rid AND rp.activa = 1 AND rp.dia = :dia
        ORDER BY rp.prioridad DESC, c.cliente
    """), {"pid": point_id, "rid": route_id, "dia": dia}).fetchall()
    return [{"id": r[0], "nombre": r[1], "prioridad": r[2] or "Media"} for r in rows]


@router.get("/cliente-categorias/{cliente_id}")
def get_cliente_categorias(cliente_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    rows = db.execute(text("""
        SELECT c.id_categoria, c.nombre
        FROM CATEGORIAS_CLIENTES cc JOIN CATEGORIAS c ON c.id_categoria = cc.id_categoria
        WHERE cc.id_cliente = :cid ORDER BY c.nombre
    """), {"cid": cliente_id}).fetchall()
    return [{"id": r[0], "nombre": r[1]} for r in rows]


# ───────────────── Auditoría por cliente ─────────────────
@router.post("/iniciar-auditoria-cliente")
def iniciar_auditoria_cliente(payload: dict, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    cliente_id, point_id, cedula = payload.get("cliente_id"), payload.get("point_id"), payload.get("cedula")
    if not cliente_id or not point_id or not cedula:
        raise HTTPException(400, "Datos incompletos")
    mid = _auditor_id(db, cedula)
    if not mid:
        raise HTTPException(404, "Auditor no encontrado")
    # Nota: VISITAS_MERCADERISTA no tiene columna `tipo_visita` en la base real (el modelo/otros
    # endpoints la asumían pero nunca existió como columna física); se distingue una visita de
    # auditor de campo por su `id_mercaderista`, que pertenece exclusivamente a MERCADERISTAS con
    # tipo = 'Auditor de Campo' (ver TIPO arriba), así que basta con filtrar por ese id.
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


@router.post("/guardar-auditoria-categoria")
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


@router.post("/finalizar-auditoria-cliente")
def finalizar_auditoria_cliente(d: dict, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    id_visita = d.get("id_visita")
    if not id_visita:
        raise HTTPException(400, "id_visita requerido")
    db.execute(text("UPDATE VISITAS_MERCADERISTA SET estado='Finalizada' WHERE id_visita=:v"), {"v": int(id_visita)})
    db.commit()
    return {"success": True, "message": "Auditoría del cliente finalizada"}
