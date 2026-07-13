"""
app/routes/mercaderista_portal.py
Endpoints exclusivos para el portal del mercaderista (AppWeb_v2).
Login: username = cedula, id_rol = 5
"""
from __future__ import annotations

import os
import io
import uuid
from datetime import datetime, date, timedelta
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.models.mercaderista import Mercaderista

router = APIRouter(prefix="/api/merc", tags=["Mercaderista Portal"])

# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

DAY_MAP_ES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles",
    3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo",
}

FOTO_TIPOS = {
    "gestion_antes":      {"label": "Gestión (Antes)",            "solo_camara": False, "id": 1},
    "gestion_despues":    {"label": "Gestión (Después)",          "solo_camara": False, "id": 2},
    "precios":            {"label": "Precios",                    "solo_camara": False, "id": 3},
    "exhibicion_antes":   {"label": "Exhibición Adic. (Antes)",   "solo_camara": False, "id": 4},
    "exhibicion_despues": {"label": "Exhibición Adic. (Después)", "solo_camara": False, "id": 7},
    "pop_antes":          {"label": "Material POP (Antes)",       "solo_camara": False, "id": 8},
    "pop_despues":        {"label": "Material POP (Después)",     "solo_camara": False, "id": 10},
    "activacion":         {"label": "Activación",                 "solo_camara": True,  "id": 5},
    "desactivacion":      {"label": "Desactivación",              "solo_camara": True,  "id": 6},
}
FOTO_TIPO_TO_ID = {k: v["id"] for k, v in FOTO_TIPOS.items()}
ID_TO_CODIGO = {v["id"]: k for k, v in FOTO_TIPOS.items()}


def _get_mercaderista(current_user: Usuario, db: Session) -> Mercaderista:
    """Obtiene el Mercaderista de la tabla MERCADERISTAS por cedula = username."""
    try:
        cedula_val = int(current_user.username)
    except ValueError:
        cedula_val = 0

    merc = db.query(Mercaderista).filter(
        Mercaderista.cedula == cedula_val
    ).first()
    if not merc:
        raise HTTPException(status_code=403, detail="Usuario no es mercaderista")
    return merc


# ──────────────────────────────────────────────────────────────────────────────
# 1. Perfil
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/mi-perfil")
def get_mi_perfil(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)

    # Rutas asignadas
    rutas = db.execute(text("""
        SELECT mr.id_mercaderista_ruta, mr.id_ruta, mr.tipo_ruta
        FROM MERCADERISTAS_RUTAS mr
        WHERE mr.id_mercaderista = :id_merc
    """), {"id_merc": merc.id}).fetchall()

    return {
        "id": merc.id,
        "nombre": merc.nombre,
        "cedula": merc.cedula,
        "email": merc.email,
        "telefono": merc.telefono,
        "rutas": [
            {"id_ruta": r.id_ruta, "tipo": r.tipo_ruta}
            for r in rutas
        ],
    }


# ──────────────────────────────────────────────────────────────────────────────
# 2. Ruta del día
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/mi-ruta")
def get_mi_ruta(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)
    hoy = date.today()
    dia_semana = DAY_MAP_ES[hoy.weekday()]

    # 1. Obtener todas las rutas asignadas al mercaderista
    rutas_rows = db.execute(text("""
        SELECT mr.id_ruta, mr.tipo_ruta, rn.ruta AS nombre_ruta
        FROM MERCADERISTAS_RUTAS mr
        JOIN RUTAS_NUEVAS rn ON rn.id_ruta = mr.id_ruta
        WHERE mr.id_mercaderista = :id_merc
    """), {"id_merc": merc.id}).fetchall()

    rutas = [
        {"id_ruta": r.id_ruta, "tipo": r.tipo_ruta, "nombre": r.nombre_ruta}
        for r in rutas_rows
    ]

    # 2. PDVs programados para hoy
    pdvs_rows = db.execute(text("""
        SELECT DISTINCT
            rp.id_programacion,
            rp.id_punto_interes,
            rp.punto_interes,
            rp.id_cliente,
            rp.id_ruta,
            rp.prioridad,
            mr.tipo_ruta,
            pi.latitud,
            pi.longitud,
            pi.jerarquia_nivel_2   AS cadena,
            pi.jerarquia_nivel_2_2 AS region,
            pi.Direccion           AS direccion,
            c.cliente               AS cliente_nombre
        FROM RUTA_PROGRAMACION rp
        JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
        LEFT JOIN PUNTOS_INTERES1 pi ON pi.identificador = rp.id_punto_interes
        LEFT JOIN CLIENTES c ON c.id_cliente = rp.id_cliente
        WHERE mr.id_mercaderista = :id_merc
          AND rp.dia = :dia
          AND rp.activa = 1
    """), {"id_merc": merc.id, "dia": dia_semana}).fetchall()

    # Visitas ya realizadas hoy
    visitas_hoy = db.execute(text("""
        SELECT identificador_punto_interes, id_visita, estado, estado_data
        FROM VISITAS_MERCADERISTA
        WHERE id_mercaderista = :id_merc
          AND CAST(fecha_visita AS DATE) = :hoy
    """), {"id_merc": merc.id, "hoy": str(hoy)}).fetchall()

    visita_por_pdv = {v.identificador_punto_interes: v for v in visitas_hoy}

    pdvs = []
    for row in pdvs_rows:
        visita = visita_por_pdv.get(row.id_punto_interes)
        pdvs.append({
            "id_punto":      row.id_punto_interes,
            "nombre":        row.punto_interes,
            "id_cliente":    row.id_cliente,
            "cliente":       row.cliente_nombre,
            "id_ruta":       row.id_ruta,
            "cadena":        row.cadena,
            "region":        row.region,
            "direccion":     row.direccion,
            "tipo_ruta":     row.tipo_ruta,
            "prioridad":     row.prioridad,
            "tiene_coords":  row.latitud is not None and row.longitud is not None,
            "latitud":       float(str(row.latitud).replace(",", ".")) if row.latitud else None,
            "longitud":      float(str(row.longitud).replace(",", ".")) if row.longitud else None,
            "visita_id":     visita.id_visita if visita else None,
            "visitado":      visita is not None,
            "estado":        visita.estado if visita else None,
            "estado_data":   visita.estado_data if visita else None,
        })

    return {
        "dia": dia_semana,
        "fecha": str(hoy),
        "rutas": rutas,
        "pdvs": pdvs
    }


# ──────────────────────────────────────────────────────────────────────────────
# 3. Mis Visitas
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/mis-visitas")
def get_mis_visitas(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)

    if not fecha_inicio:
        fecha_inicio = str(date.today())
    if not fecha_fin:
        fecha_fin = str(date.today())

    rows = db.execute(text("""
        SELECT
            v.id_visita,
            v.fecha_visita,
            v.estado,
            v.estado_data,
            v.observaciones,
            v.identificador_punto_interes,
            pi.punto_de_interes  AS pdv_nombre,
            pi.jerarquia_nivel_2 AS cadena,
            pi.jerarquia_nivel_2_2 AS region,
            c.cliente            AS cliente_nombre,
            v.id_cliente
        FROM VISITAS_MERCADERISTA v
        LEFT JOIN PUNTOS_INTERES1 pi ON pi.identificador = v.identificador_punto_interes
        LEFT JOIN CLIENTES c ON c.id_cliente = v.id_cliente
        WHERE v.id_mercaderista = :id_merc
          AND CAST(v.fecha_visita AS DATE) >= :fi
          AND CAST(v.fecha_visita AS DATE) <= :ff
        ORDER BY v.fecha_visita DESC
    """), {"id_merc": merc.id, "fi": fecha_inicio, "ff": fecha_fin}).fetchall()

    result = []
    for r in rows:
        # Contar fotos
        fotos_count = db.execute(text("""
            SELECT COUNT(*) FROM FOTOS_TOTALES WHERE id_visita = :vid
        """), {"vid": r.id_visita}).scalar() or 0

        # Contar balances
        balances_count = db.execute(text("""
            SELECT COUNT(*) FROM BALANCES_TOTALES WHERE id_visita = :vid
        """), {"vid": r.id_visita}).scalar() or 0

        result.append({
            "id_visita":    r.id_visita,
            "fecha":        str(r.fecha_visita),
            "estado":       r.estado,
            "estado_data":  r.estado_data,
            "pdv_nombre":   r.pdv_nombre,
            "cadena":       r.cadena,
            "region":       r.region,
            "cliente":      r.cliente_nombre,
            "id_cliente":   r.id_cliente,
            "observaciones": r.observaciones,
            "fotos_count":  fotos_count,
            "balances_count": balances_count,
        })
    return result


# ──────────────────────────────────────────────────────────────────────────────
# 4. Iniciar Visita
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/iniciar-visita")
def iniciar_visita(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)
    id_punto = payload.get("id_punto")
    id_cliente = payload.get("id_cliente")

    if not id_punto or not id_cliente:
        raise HTTPException(status_code=400, detail="id_punto e id_cliente son requeridos")

    # Verificar si ya existe visita hoy para ese PDV
    existing = db.execute(text("""
        SELECT id_visita FROM VISITAS_MERCADERISTA
        WHERE id_mercaderista = :mid
          AND identificador_punto_interes = :pid
          AND CAST(fecha_visita AS DATE) = :hoy
    """), {"mid": merc.id, "pid": id_punto, "hoy": str(date.today())}).fetchone()

    if existing:
        return {"id_visita": existing.id_visita, "nueva": False}

    # Crear nueva visita
    # Nota: VISITAS_MERCADERISTA no tiene columna `tipo_visita` en la base real; se omite.
    db.execute(text("""
        INSERT INTO VISITAS_MERCADERISTA
            (id_mercaderista, fecha_visita, estado, estado_data, id_cliente, identificador_punto_interes)
        VALUES
            (:mid, :fecha, 'Pendiente', 'Pendiente', :cid, :pid)
    """), {
        "mid": merc.id,
        "fecha": datetime.now(),
        "cid": id_cliente,
        "pid": id_punto,
    })
    db.commit()

    new_id = db.execute(text("""
        SELECT MAX(id_visita) FROM VISITAS_MERCADERISTA
        WHERE id_mercaderista = :mid AND identificador_punto_interes = :pid
    """), {"mid": merc.id, "pid": id_punto}).scalar()

    from app.services.realtime import notify_event
    notify_event("visit.created", {"id_visita": new_id, "id_cliente": id_cliente, "id_punto": id_punto})

    return {"id_visita": new_id, "nueva": True}


@router.get("/ruta/{id_ruta}/pdvs")
def get_pdvs_de_ruta(
    id_ruta: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """TODOS los PDV de una ruta (sin filtro de día). Para que aparezcan al ejecutar la ruta."""
    merc = _get_mercaderista(current_user, db)
    hoy = date.today()
    pdvs_rows = db.execute(text("""
        SELECT DISTINCT
            rp.id_punto_interes, rp.punto_interes, rp.id_cliente, rp.id_ruta, rp.prioridad,
            mr.tipo_ruta, pi.latitud, pi.longitud,
            pi.jerarquia_nivel_2 AS cadena, pi.jerarquia_nivel_2_2 AS region,
            pi.Direccion AS direccion, c.cliente AS cliente_nombre
        FROM RUTA_PROGRAMACION rp
        JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
        LEFT JOIN PUNTOS_INTERES1 pi ON pi.identificador = rp.id_punto_interes
        LEFT JOIN CLIENTES c ON c.id_cliente = rp.id_cliente
        WHERE mr.id_mercaderista = :id_merc AND rp.id_ruta = :id_ruta AND rp.activa = 1
        ORDER BY rp.punto_interes
    """), {"id_merc": merc.id, "id_ruta": id_ruta}).fetchall()

    visitas_hoy = db.execute(text("""
        SELECT identificador_punto_interes, id_visita, estado, estado_data
        FROM VISITAS_MERCADERISTA
        WHERE id_mercaderista = :id_merc AND CAST(fecha_visita AS DATE) = :hoy
    """), {"id_merc": merc.id, "hoy": str(hoy)}).fetchall()
    visita_por_pdv = {v.identificador_punto_interes: v for v in visitas_hoy}

    pdvs = []
    for row in pdvs_rows:
        visita = visita_por_pdv.get(row.id_punto_interes)
        pdvs.append({
            "id_punto": row.id_punto_interes, "nombre": row.punto_interes,
            "id_cliente": row.id_cliente, "cliente": row.cliente_nombre,
            "id_ruta": row.id_ruta, "cadena": row.cadena, "region": row.region,
            "direccion": row.direccion, "tipo_ruta": row.tipo_ruta, "prioridad": row.prioridad,
            "tiene_coords": row.latitud is not None and row.longitud is not None,
            "latitud": float(str(row.latitud).replace(",", ".")) if row.latitud else None,
            "longitud": float(str(row.longitud).replace(",", ".")) if row.longitud else None,
            "visita_id": visita.id_visita if visita else None,
            "visitado": visita is not None,
            "estado": visita.estado if visita else None,
            "estado_data": visita.estado_data if visita else None,
        })
    return {"id_ruta": id_ruta, "pdvs": pdvs}


# ──────────────────────────────────────────────────────────────────────────────
# 5. Fotos de una Visita
# ──────────────────────────────────────────────────────────────────────────────

def _merc_foto_url(blob_path, foto_id):
    """URL para mostrar la foto: SAS de Azure si es blob, o el endpoint local."""
    if not blob_path:
        return None
    if "fotos_mercaderista" in blob_path or os.path.exists(blob_path):
        return f"/api/merc/foto/{foto_id}"
    try:
        from app.services.azure_service import azure_service
        return azure_service.get_sas_url(blob_path)
    except Exception:
        return f"/api/merc/foto/{foto_id}"


@router.get("/visita/{visita_id}/fotos")
def get_fotos_visita(
    visita_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Lee SOLO de FOTOS_TOTALES. Devuelve por tipo una LISTA de fotos (varias por subtipo)."""
    rows = db.execute(text("""
        SELECT id_foto, id_tipo_foto, file_path, Estado, fecha_registro
        FROM FOTOS_TOTALES
        WHERE id_visita = :vid
        ORDER BY id_foto
    """), {"vid": visita_id}).fetchall()

    por_codigo: dict = {k: [] for k in FOTO_TIPOS.keys()}
    for r in rows:
        cod = ID_TO_CODIGO.get(r.id_tipo_foto)
        if not cod:
            continue
        por_codigo[cod].append({
            "id_foto": r.id_foto,
            "estado":  r.Estado,
            "fecha":   str(r.fecha_registro) if r.fecha_registro else None,
            "url":     _merc_foto_url(r.file_path, r.id_foto),
        })

    tipos_info = [
        {
            "codigo":      k,
            "label":       v["label"],
            "solo_camara": v["solo_camara"],
            "fotos":       por_codigo.get(k, []),
        }
        for k, v in FOTO_TIPOS.items()
    ]
    return {"visita_id": visita_id, "tipos": tipos_info}


# ──────────────────────────────────────────────────────────────────────────────
# 6. Subir Foto
# ──────────────────────────────────────────────────────────────────────────────

FOTOS_DIR = "app/static/fotos_mercaderista"

@router.post("/fotos/upload")
async def upload_foto(
    visita_id: int = Form(...),
    tipo_foto: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if tipo_foto not in FOTO_TIPOS:
        raise HTTPException(status_code=400, detail=f"Tipo de foto inválido: {tipo_foto}")

    file_bytes = await file.read()
    ext = (file.filename or "foto.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"

    # Intentar usar photo_service (blob) si está configurado
    blob_path = None
    try:
        from app.services.photo_service import process_and_upload_photo
        result = process_and_upload_photo(file_bytes, file.content_type or "image/jpeg")
        blob_path = result.get("blob_path")
    except Exception:
        pass

    # Fallback: guardar localmente
    if not blob_path:
        os.makedirs(FOTOS_DIR, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.{ext}"
        fpath = os.path.join(FOTOS_DIR, fname)
        with open(fpath, "wb") as f:
            f.write(file_bytes)
        blob_path = fpath

    # Guardar SOLO en FOTOS_TOTALES con el id_tipo_foto real (lo que lee la revisión).
    id_tipo = FOTO_TIPO_TO_ID.get(tipo_foto)
    if not id_tipo:
        raise HTTPException(status_code=400, detail=f"Tipo de foto inválido: {tipo_foto}")
    ahora = datetime.now()
    db.execute(text("""
        INSERT INTO FOTOS_TOTALES (id_visita, id_tipo_foto, file_path, fecha_registro, Estado)
        VALUES (:vid, :tipo_id, :path, :fecha, 'pendiente')
    """), {"vid": visita_id, "tipo_id": id_tipo, "path": blob_path, "fecha": ahora})
    db.commit()

    new_id = db.execute(text("""
        SELECT MAX(id_foto) FROM FOTOS_TOTALES
        WHERE id_visita = :vid AND id_tipo_foto = :tipo_id AND file_path = :path
    """), {"vid": visita_id, "tipo_id": id_tipo, "path": blob_path}).scalar()

    from app.services.realtime import notify_event
    notify_event("photo.uploaded", {"id_foto": new_id, "visita_id": visita_id, "tipo_foto": tipo_foto})

    return {"id_foto": new_id, "url": _merc_foto_url(blob_path, new_id), "estado": "pendiente"}


@router.delete("/foto/{foto_id}")
def delete_merc_foto(
    foto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Elimina una foto (para reemplazar/quitar) de FOTOS_TOTALES."""
    db.execute(text("DELETE FROM FOTOS_RAZONES_RECHAZOS WHERE id_foto = :fid"), {"fid": foto_id})
    db.execute(text("DELETE FROM FOTOS_TOTALES WHERE id_foto = :fid"), {"fid": foto_id})
    db.commit()
    from app.services.realtime import notify_event
    notify_event("photo.deleted", {"id_foto": foto_id})
    return {"deleted": foto_id}


# ──────────────────────────────────────────────────────────────────────────────
# 7. Servir foto (fallback local)
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/foto/{foto_id}")
def get_foto(
    foto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from fastapi.responses import FileResponse, RedirectResponse
    row = db.execute(text(
        "SELECT file_path FROM FOTOS_TOTALES WHERE id_foto = :fid"
    ), {"fid": foto_id}).fetchone()
    if not row or not row.file_path:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    if os.path.exists(row.file_path):
        return FileResponse(row.file_path)
    try:
        from app.services.azure_service import azure_service
        return RedirectResponse(azure_service.get_sas_url(row.file_path))
    except Exception:
        raise HTTPException(status_code=404, detail="Archivo no disponible")


# ──────────────────────────────────────────────────────────────────────────────
# 8. Productos del cliente
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/productos")
def get_productos_cliente(
    id_cliente: int = Query(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Productos del cliente vía modelo SNOWFLAKE:
    #   PRODUCTOS -> SUBCATEGORIAS -> CATEGORIAS, filtrado por las categorías del
    #   cliente (CATEGORIAS_CLIENTES). 'fabricante' se toma de la productora de la
    #   marca. (Antes usaba el PRODUCTS operativo por id_fabricante, ya migrado.)
    rows = db.execute(text("""
        SELECT p.id_product, p.producto_gutrade, cat.nombre AS categoria, pr.nombre AS fabricante
        FROM PRODUCTS p
        JOIN SUBCATEGORIAS sc ON sc.id_subcategoria = p.id_subcategoria
        JOIN CATEGORIAS_CLIENTES cc ON cc.id_categoria = sc.id_categoria AND cc.id_cliente = :cid
        LEFT JOIN CATEGORIAS cat ON cat.id_categoria = sc.id_categoria
        LEFT JOIN MARCAS m ON m.id_marca = p.id_marca
        LEFT JOIN PRODUCTORAS pr ON pr.id_productora = m.id_productora
        ORDER BY cat.nombre, p.producto_gutrade
    """), {"cid": id_cliente}).fetchall()

    return [
        {
            "id": r.id_product,
            "sku": r.producto_gutrade,
            "fabricante": r.fabricante,
            "categoria": r.categoria,
        }
        for r in rows
    ]


# ──────────────────────────────────────────────────────────────────────────────
# 9. Guardar Balances
# ──────────────────────────────────────────────────────────────────────────────

@router.post("/balances")
def guardar_balances(
    payload: dict,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)
    visita_id  = payload.get("visita_id")
    productos  = payload.get("productos", [])
    id_cliente = payload.get("id_cliente")

    if not visita_id or not productos:
        raise HTTPException(status_code=400, detail="visita_id y productos son requeridos")

    # Obtener identificador_pdv de la visita
    vis = db.execute(text("""
        SELECT identificador_punto_interes FROM VISITAS_MERCADERISTA WHERE id_visita = :vid
    """), {"vid": visita_id}).fetchone()
    if not vis:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    id_pdv = vis.identificador_punto_interes

    now = datetime.now()
    for p in productos:
        sku       = p.get("sku", "")
        fabricante = p.get("fabricante", "")
        categoria  = p.get("categoria", "")

        # Insertar en BALANCES_TOTALES
        db.execute(text("""
            INSERT INTO BALANCES_TOTALES (
                id_cliente, fecha_balance, identificador_pdv, mercaderista,
                producto, fabricante, categoria,
                inv_inicial, inv_final, inv_deposito, caras,
                precio_bs, precio_ds, FEFO, id_visita,
                fecha_inicio_modificacion, fecha_modificacion
            ) VALUES (
                :cid, :fecha, :pdv, :merc,
                :sku, :fab, :cat,
                :ii, :if_, :id_, :caras,
                :pbs, :pds, :fefo, :vid,
                :fi, :fm
            )
        """), {
            "cid":   id_cliente or merc.id,
            "fecha": now,
            "pdv":   id_pdv,
            "merc":  merc.nombre,
            "sku":   sku,
            "fab":   fabricante,
            "cat":   categoria,
            "ii":    p.get("inv_inicial", 0),
            "if_":   p.get("inv_final", 0),
            "id_":   p.get("inv_deposito", 0),
            "caras": p.get("caras", 0),
            "pbs":   p.get("precio_bs") or 0,
            "pds":   p.get("precio_ds") or 0,
            "fefo":  p.get("fifo"),
            "vid":   visita_id,
            "fi":    now,
            "fm":    now,
        })

    # Actualizar estado_data de la visita
    db.execute(text("""
        UPDATE VISITAS_MERCADERISTA
        SET estado_data = 'Cargado'
        WHERE id_visita = :vid
    """), {"vid": visita_id})

    db.commit()
    return {"success": True, "productos_guardados": len(productos)}


# ──────────────────────────────────────────────────────────────────────────────
# 10. Chat inbox del mercaderista
# ──────────────────────────────────────────────────────────────────────────────

@router.get("/chat/inbox")
def get_chat_inbox(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)

    rows = db.execute(text("""
        SELECT
            v.id_visita,
            v.fecha_visita,
            v.estado,
            pi.punto_de_interes  AS pdv_nombre,
            c.cliente            AS cliente_nombre,
            (SELECT COUNT(*) FROM CHAT_MENSAJES cm WHERE cm.id_visita = v.id_visita) AS total_msgs,
            (SELECT TOP 1 cm.mensaje FROM CHAT_MENSAJES cm
             WHERE cm.id_visita = v.id_visita ORDER BY cm.fecha_envio DESC) AS ultimo_msg,
            (SELECT TOP 1 cm.fecha_envio FROM CHAT_MENSAJES cm
             WHERE cm.id_visita = v.id_visita ORDER BY cm.fecha_envio DESC) AS ultimo_at,
            (SELECT COUNT(*) FROM CHAT_MENSAJES cm
             LEFT JOIN CHAT_LECTURAS cl ON cl.id_mensaje = cm.id_mensaje
                AND cl.id_usuario = :id_usuar
             WHERE cm.id_visita = v.id_visita
               AND cl.id_lectura IS NULL
               AND cm.username != :cedula) AS no_leidos
        FROM VISITAS_MERCADERISTA v
        LEFT JOIN PUNTOS_INTERES1 pi ON pi.identificador = v.identificador_punto_interes
        LEFT JOIN CLIENTES c ON c.id_cliente = v.id_cliente
        WHERE v.id_mercaderista = :id_merc
          AND EXISTS (
            SELECT 1 FROM CHAT_MENSAJES cm WHERE cm.id_visita = v.id_visita
          )
        ORDER BY ultimo_at DESC
    """), {"id_merc": merc.id, "cedula": str(merc.cedula), "id_usuar": merc.id}).fetchall()

    return [
        {
            "id_visita":    r.id_visita,
            "fecha":        str(r.fecha_visita),
            "estado":       r.estado,
            "pdv_nombre":   r.pdv_nombre,
            "cliente":      r.cliente_nombre,
            "total_msgs":   r.total_msgs,
            "ultimo_msg":   r.ultimo_msg,
            "ultimo_at":    str(r.ultimo_at) if r.ultimo_at else None,
            "no_leidos":    r.no_leidos or 0,
        }
        for r in rows
    ]
