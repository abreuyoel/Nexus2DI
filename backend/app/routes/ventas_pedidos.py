"""Módulo de Ventas 2.0 -- pedidos formales con líneas (reemplaza el "monto
total" suelto de vendedor.py), catálogo real, OCR/IA para notas de pedido en
papel, workflow de aprobación/crédito, dashboard y notificaciones.

Mantiene vendedor.py intacto (jornada/PDVs/clientes/solicitar-PDV siguen
igual) -- este archivo agrega todo lo nuevo bajo el mismo prefix /api/vendedor
más un router propio de dashboard, para no romper nada que ya funciona.

Tablas nuevas (ver ddl_ventas.sql): CATALOGO_VENTA, PEDIDOS, PEDIDO_LINEAS,
PEDIDO_NOTAS_OCR, INVENTARIO_CACHE_EXTERNO, CREDITO_CLIENTE. Reusa PRODUCTS
(6072 productos ya existentes, BI/snowflake) como catálogo maestro -- 103 de
esos productos ya están asociados a Dusa (id_cliente=33) vía
CATEGORIAS_CLIENTES (categorías Brandy/Mezcladores/Licor de Vodka/Licores
Fuertes/Whisky).
"""
import difflib
import logging
from datetime import datetime, date, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy import text, select
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db, get_async_db
from app.core.dependencies import get_current_user
from app.core.config import settings
from app.models.user import Usuario as User
from app.services.photo_service import process_and_upload_photo
from app.services import email_service
from app.services.ollama_ocr_service import leer_nota_pedido, OcrExtractionError
from app.services.realtime import notify_event

logger = logging.getLogger("app")

router = APIRouter(prefix="/api/vendedor", tags=["Ventas - Pedidos"])

UMBRAL_PEDIDO_GRANDE = 500.0  # USD -- dispara alerta al supervisor. TODO: configurable por cliente.
ESTADOS_VALIDOS = ["Borrador", "Enviado", "Aprobado", "Rechazado", "Facturado", "Despachado", "Entregado"]
TRANSICIONES_VENDEDOR = {"Borrador": ["Enviado"]}
TRANSICIONES_SUPERVISOR = {
    "Enviado": ["Aprobado", "Rechazado"],
    "Aprobado": ["Facturado"],
    "Facturado": ["Despachado"],
    "Despachado": ["Entregado"],
}


def _check_acceso_ventas(current_user: User):
    if not (current_user.is_vendedor or current_user.is_admin or current_user.is_supervisor):
        raise HTTPException(status_code=403, detail="Acceso denegado al módulo de Ventas.")


def _puede_gestionar(current_user: User) -> bool:
    """Admin/supervisor pueden aprobar, rechazar, ver todo. Un vendedor sólo
    gestiona lo suyo."""
    return current_user.is_admin or current_user.is_supervisor


# ════════════════════════════════════════════════════════════════════
# CATÁLOGO
# ════════════════════════════════════════════════════════════════════

@router.get("/catalogo")
async def get_catalogo(id_cliente: int, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    _check_acceso_ventas(current_user)
    rows = (await db.execute(text("""
        SELECT cv.id_catalogo, cv.id_producto, p.producto_gutrade AS nombre,
               c.nombre AS categoria, m.nombre AS marca,
               cv.precio_unitario, cv.unidades_por_caja, cv.presentacion_venta,
               cv.foto_url, COALESCE(cv.codigo_barras, p.cod_bar) AS codigo_barras,
               cv.descuento_max_pct,
               COALESCE(ie.cantidad_disponible, NULL) AS stock_disponible
        FROM CATALOGO_VENTA cv
        JOIN PRODUCTS p ON p.id_product = cv.id_producto
        LEFT JOIN SUBCATEGORIAS sc ON p.id_subcategoria = sc.id_subcategoria
        LEFT JOIN CATEGORIAS c ON sc.id_categoria = c.id_categoria
        LEFT JOIN MARCAS m ON p.id_marca = m.id_marca
        LEFT JOIN INVENTARIO_CACHE_EXTERNO ie ON ie.id_producto = cv.id_producto AND ie.id_cliente = cv.id_cliente
        WHERE cv.id_cliente = :c AND cv.activo = 1
        ORDER BY c.nombre, p.producto_gutrade
    """), {"c": id_cliente})).fetchall()
    return [{
        "id_catalogo": r.id_catalogo, "id_producto": r.id_producto, "nombre": r.nombre,
        "categoria": r.categoria, "marca": r.marca, "precio_unitario": float(r.precio_unitario),
        "unidades_por_caja": r.unidades_por_caja, "presentacion_venta": r.presentacion_venta,
        "foto_url": r.foto_url, "codigo_barras": r.codigo_barras,
        "descuento_max_pct": float(r.descuento_max_pct or 0),
        "stock_disponible": r.stock_disponible,
    } for r in rows]


@router.get("/catalogo/buscar-codigo-barras")
async def buscar_por_codigo_barras(codigo: str, id_cliente: int, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    _check_acceso_ventas(current_user)
    row = (await db.execute(text("""
        SELECT cv.id_catalogo, cv.id_producto, p.producto_gutrade AS nombre, cv.precio_unitario
        FROM CATALOGO_VENTA cv
        JOIN PRODUCTS p ON p.id_product = cv.id_producto
        WHERE cv.id_cliente = :c AND cv.activo = 1
          AND COALESCE(cv.codigo_barras, p.cod_bar) = :cod
    """), {"c": id_cliente, "cod": codigo})).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Producto no encontrado por ese código de barras")
    return {"id_catalogo": row.id_catalogo, "id_producto": row.id_producto, "nombre": row.nombre, "precio_unitario": float(row.precio_unitario)}


# ════════════════════════════════════════════════════════════════════
# PEDIDOS -- helpers
# ════════════════════════════════════════════════════════════════════

async def _siguiente_numero_pedido(db: AsyncSession) -> str:
    anio = datetime.now().year
    ultimo = (await db.execute(text(
        "SELECT MAX(id_pedido) FROM PEDIDOS"
    ))).scalar() or 0
    return f"PED-{anio}-{ultimo + 1:06d}"


async def _credito_cliente(db: AsyncSession, id_cliente: int):
    return (await db.execute(text(
        "SELECT limite_credito, saldo_actual, dias_mora, bloqueado FROM CREDITO_CLIENTE WHERE id_cliente = :c"
    ), {"c": id_cliente})).fetchone()


async def _armar_pedido_response(db: AsyncSession, id_pedido: int) -> dict:
    p = (await db.execute(text("""
        SELECT pe.id_pedido, pe.numero_pedido, pe.id_cliente, c.cliente AS nombre_cliente,
               pe.id_usuario_vendedor, u.username AS vendedor, pe.identificador_punto_interes,
               pe.fecha, pe.estado, pe.subtotal, pe.descuento_total, pe.impuestos, pe.total,
               pe.latitud, pe.longitud, pe.notas, pe.origen, pe.firma_cliente_url,
               pe.aprobado_por, pe.fecha_aprobacion
        FROM PEDIDOS pe
        JOIN CLIENTES c ON c.id_cliente = pe.id_cliente
        JOIN USUARIOS u ON u.id_usuario = pe.id_usuario_vendedor
        WHERE pe.id_pedido = :id
    """), {"id": id_pedido})).fetchone()
    if not p:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    lineas = (await db.execute(text("""
        SELECT id_linea, id_producto, nombre_producto, cantidad, precio_unitario, descuento_pct, subtotal_linea
        FROM PEDIDO_LINEAS WHERE id_pedido = :id ORDER BY id_linea
    """), {"id": id_pedido})).fetchall()
    return {
        "id_pedido": p.id_pedido, "numero_pedido": p.numero_pedido,
        "id_cliente": p.id_cliente, "cliente": p.nombre_cliente,
        "id_usuario_vendedor": p.id_usuario_vendedor, "vendedor": p.vendedor,
        "identificador_punto_interes": p.identificador_punto_interes,
        "fecha": p.fecha.isoformat() if p.fecha else None, "estado": p.estado,
        "subtotal": float(p.subtotal), "descuento_total": float(p.descuento_total),
        "impuestos": float(p.impuestos), "total": float(p.total),
        "latitud": p.latitud, "longitud": p.longitud, "notas": p.notas, "origen": p.origen,
        "firma_cliente_url": p.firma_cliente_url,
        "aprobado_por": p.aprobado_por,
        "fecha_aprobacion": p.fecha_aprobacion.isoformat() if p.fecha_aprobacion else None,
        "lineas": [{
            "id_linea": l.id_linea, "id_producto": l.id_producto, "nombre_producto": l.nombre_producto,
            "cantidad": l.cantidad, "precio_unitario": float(l.precio_unitario),
            "descuento_pct": float(l.descuento_pct), "subtotal_linea": float(l.subtotal_linea),
        } for l in lineas],
    }


async def _crear_pedido(db: AsyncSession, current_user: User, payload: dict, origen: str = "app") -> dict:
    id_cliente = payload.get("id_cliente")
    lineas_in = payload.get("lineas") or []
    if not id_cliente or not lineas_in:
        raise HTTPException(status_code=400, detail="id_cliente y al menos una línea son requeridos")

    credito = await _credito_cliente(db, id_cliente)
    if credito and credito.bloqueado:
        raise HTTPException(status_code=403, detail=f"Cliente bloqueado por crédito (mora: {credito.dias_mora} días). No se puede registrar el pedido.")

    subtotal = 0.0
    descuento_total = 0.0
    lineas_resueltas = []
    for li in lineas_in:
        id_producto = li.get("id_producto")
        cantidad = li.get("cantidad")
        if not id_producto or not cantidad or cantidad <= 0:
            raise HTTPException(status_code=400, detail="Cada línea necesita id_producto y cantidad > 0")
        cat = (await db.execute(text("""
            SELECT cv.precio_unitario, cv.descuento_max_pct, p.producto_gutrade AS nombre
            FROM CATALOGO_VENTA cv JOIN PRODUCTS p ON p.id_product = cv.id_producto
            WHERE cv.id_producto = :pid AND cv.id_cliente = :cid AND cv.activo = 1
        """), {"pid": id_producto, "cid": id_cliente})).fetchone()
        if not cat:
            raise HTTPException(status_code=400, detail=f"El producto {id_producto} no está en el catálogo de este cliente")
        descuento_pct = float(li.get("descuento_pct") or 0)
        if descuento_pct > float(cat.descuento_max_pct or 0):
            raise HTTPException(status_code=400, detail=f"Descuento de {descuento_pct}% excede el máximo permitido ({cat.descuento_max_pct}%) para {cat.nombre}")
        precio = float(cat.precio_unitario)
        bruto = precio * cantidad
        desc = bruto * descuento_pct / 100
        sub_linea = bruto - desc
        subtotal += bruto
        descuento_total += desc
        lineas_resueltas.append({
            "id_producto": id_producto, "nombre_producto": cat.nombre, "cantidad": cantidad,
            "precio_unitario": precio, "descuento_pct": descuento_pct, "subtotal_linea": sub_linea,
        })

    impuestos = 0.0  # IVA/impuestos: a definir con el cliente -- estructura lista, tasa en 0 por ahora.
    total = subtotal - descuento_total + impuestos
    numero_pedido = await _siguiente_numero_pedido(db)

    ins = (await db.execute(text("""
        INSERT INTO PEDIDOS (numero_pedido, id_cliente, id_usuario_vendedor, identificador_punto_interes,
                              fecha, estado, subtotal, descuento_total, impuestos, total,
                              latitud, longitud, notas, origen, id_visita)
        OUTPUT INSERTED.id_pedido
        VALUES (:num, :cli, :usr, :pdv, GETDATE(), 'Borrador', :sub, :desc, :imp, :tot,
                :lat, :lon, :notas, :origen, :visita)
    """), {
        "num": numero_pedido, "cli": id_cliente, "usr": current_user.id,
        "pdv": payload.get("identificador_punto_interes"),
        "sub": subtotal, "desc": descuento_total, "imp": impuestos, "tot": total,
        "lat": payload.get("latitud"), "lon": payload.get("longitud"),
        "notas": payload.get("notas"), "origen": origen, "visita": payload.get("id_visita"),
    })).fetchone()
    id_pedido = ins.id_pedido

    for l in lineas_resueltas:
        await db.execute(text("""
            INSERT INTO PEDIDO_LINEAS (id_pedido, id_producto, nombre_producto, cantidad, precio_unitario, descuento_pct, subtotal_linea)
            VALUES (:pid, :prod, :nombre, :cant, :precio, :desc, :sub)
        """), {"pid": id_pedido, "prod": l["id_producto"], "nombre": l["nombre_producto"],
                "cant": l["cantidad"], "precio": l["precio_unitario"], "desc": l["descuento_pct"], "sub": l["subtotal_linea"]})

    await db.commit()

    resultado = await _armar_pedido_response(db, id_pedido)

    notify_event("pedido.created", {"id_pedido": id_pedido, "numero_pedido": numero_pedido, "id_cliente": id_cliente, "total": total})

    # Notificaciones best-effort -- nunca deben romper la creación del pedido, ya committeado arriba.
    try:
        cliente_email = (await db.execute(text("SELECT email FROM USUARIOS WHERE id_perfil = :c AND id_rol = 1"), {"c": id_cliente})).scalar()
        if cliente_email:
            email_service.enviar(
                cliente_email, f"Confirmación de pedido {numero_pedido}",
                email_service.html_confirmacion_pedido(numero_pedido, resultado["cliente"], total, resultado["lineas"]),
            )
        if total >= UMBRAL_PEDIDO_GRANDE:
            supervisores = (await db.execute(text("SELECT email FROM USUARIOS WHERE id_rol = 6 AND email IS NOT NULL"))).fetchall()
            for s in supervisores:
                email_service.enviar(
                    s.email, f"Pedido grande: {numero_pedido}",
                    email_service.html_alerta_pedido_grande(numero_pedido, current_user.username, resultado["cliente"], total),
                )
    except Exception as e:
        logger.warning(f"[Ventas] Notificación post-pedido falló (pedido ya guardado, id={id_pedido}): {e!r}")

    return resultado


# ════════════════════════════════════════════════════════════════════
# PEDIDOS -- endpoints
# ════════════════════════════════════════════════════════════════════

@router.post("/pedidos")
async def crear_pedido(payload: dict, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    _check_acceso_ventas(current_user)
    return {"success": True, "pedido": await _crear_pedido(db, current_user, payload, origen="app")}


@router.get("/pedidos")
async def listar_pedidos(
    estado: Optional[str] = None, id_cliente: Optional[int] = None,
    desde: Optional[str] = None, hasta: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user),
):
    _check_acceso_ventas(current_user)
    where = ["1=1"]
    params: dict = {}
    if not _puede_gestionar(current_user):
        where.append("pe.id_usuario_vendedor = :uid")
        params["uid"] = current_user.id
    if estado:
        where.append("pe.estado = :estado")
        params["estado"] = estado
    if id_cliente:
        where.append("pe.id_cliente = :cliente")
        params["cliente"] = id_cliente
    if desde:
        where.append("pe.fecha >= :desde")
        params["desde"] = desde
    if hasta:
        where.append("pe.fecha < DATEADD(day, 1, CAST(:hasta AS DATE))")
        params["hasta"] = hasta

    rows = (await db.execute(text(f"""
        SELECT pe.id_pedido, pe.numero_pedido, pe.id_cliente, c.cliente AS nombre_cliente,
               u.username AS vendedor, pe.fecha, pe.estado, pe.total, pe.origen
        FROM PEDIDOS pe
        JOIN CLIENTES c ON c.id_cliente = pe.id_cliente
        JOIN USUARIOS u ON u.id_usuario = pe.id_usuario_vendedor
        WHERE {' AND '.join(where)}
        ORDER BY pe.id_pedido DESC
    """), params)).fetchall()
    return [{
        "id_pedido": r.id_pedido, "numero_pedido": r.numero_pedido,
        "id_cliente": r.id_cliente, "cliente": r.nombre_cliente, "vendedor": r.vendedor,
        "fecha": r.fecha.isoformat() if r.fecha else None, "estado": r.estado,
        "total": float(r.total), "origen": r.origen,
    } for r in rows]


@router.get("/pedidos/{id_pedido}")
async def detalle_pedido(id_pedido: int, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    _check_acceso_ventas(current_user)
    resultado = await _armar_pedido_response(db, id_pedido)
    if not _puede_gestionar(current_user) and resultado["id_usuario_vendedor"] != current_user.id:
        raise HTTPException(status_code=403, detail="No puedes ver pedidos de otro vendedor")
    return resultado


@router.post("/pedidos/{id_pedido}/estado")
async def cambiar_estado_pedido(id_pedido: int, payload: dict, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    _check_acceso_ventas(current_user)
    nuevo_estado = payload.get("estado")
    if nuevo_estado not in ESTADOS_VALIDOS:
        raise HTTPException(status_code=400, detail=f"Estado inválido. Válidos: {', '.join(ESTADOS_VALIDOS)}")

    actual = (await db.execute(text("SELECT estado, id_usuario_vendedor FROM PEDIDOS WHERE id_pedido = :id"), {"id": id_pedido})).fetchone()
    if not actual:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")

    es_gestor = _puede_gestionar(current_user)
    permitidas = (TRANSICIONES_SUPERVISOR if es_gestor else {}).get(actual.estado, [])
    if not es_gestor:
        if actual.id_usuario_vendedor != current_user.id:
            raise HTTPException(status_code=403, detail="No puedes modificar pedidos de otro vendedor")
        permitidas = TRANSICIONES_VENDEDOR.get(actual.estado, [])
    if nuevo_estado not in permitidas:
        raise HTTPException(status_code=400, detail=f"No se puede pasar de '{actual.estado}' a '{nuevo_estado}' con tu rol")

    if nuevo_estado == "Aprobado":
        await db.execute(text("UPDATE PEDIDOS SET estado=:e, aprobado_por=:u, fecha_aprobacion=GETDATE() WHERE id_pedido=:id"),
                   {"e": nuevo_estado, "u": current_user.id, "id": id_pedido})
    else:
        await db.execute(text("UPDATE PEDIDOS SET estado=:e WHERE id_pedido=:id"), {"e": nuevo_estado, "id": id_pedido})
    await db.commit()

    notify_event("pedido.status_changed", {"id_pedido": id_pedido, "estado": nuevo_estado})
    return {"success": True, "id_pedido": id_pedido, "estado": nuevo_estado}


@router.post("/pedidos/{id_pedido}/firma")
async def subir_firma_pedido(id_pedido: int, file: UploadFile = File(...), db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    _check_acceso_ventas(current_user)
    existe = (await db.execute(text("SELECT id_pedido FROM PEDIDOS WHERE id_pedido = :id"), {"id": id_pedido})).fetchone()
    if not existe:
        raise HTTPException(status_code=404, detail="Pedido no encontrado")
    raw = await file.read()
    res = process_and_upload_photo(raw, file.content_type or "image/jpeg", prefix="ventas/firmas")
    await db.execute(text("UPDATE PEDIDOS SET firma_cliente_url = :url WHERE id_pedido = :id"), {"url": res["blob_path"], "id": id_pedido})
    await db.commit()
    return {"success": True, "url": res.get("url")}


# ════════════════════════════════════════════════════════════════════
# OCR + IA -- notas de pedido en papel
# ════════════════════════════════════════════════════════════════════

def _mejor_match(nombre_texto: str, candidatos: list[dict], umbral: float = 0.45) -> Optional[dict]:
    """Fuzzy match con difflib (stdlib, sin dependencia nueva) contra el
    catálogo real del cliente. Devuelve el candidato con mayor similaridad
    por encima del umbral, o None si nada calza razonablemente -- en ese
    caso el vendedor elige a mano en la pantalla de revisión."""
    mejor, mejor_score = None, 0.0
    texto_norm = nombre_texto.strip().lower()
    for c in candidatos:
        score = difflib.SequenceMatcher(None, texto_norm, c["nombre"].lower()).ratio()
        if score > mejor_score:
            mejor, mejor_score = c, score
    if mejor and mejor_score >= umbral:
        return {**mejor, "similaridad": round(mejor_score, 2)}
    return None


@router.post("/pedidos/ocr")
async def procesar_nota_ocr(
    id_cliente: int = Form(...), file: UploadFile = File(...),
    db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user),
):
    _check_acceso_ventas(current_user)
    raw = await file.read()

    try:
        extraido = await leer_nota_pedido(raw, file.content_type or "image/jpeg")
    except OcrExtractionError as e:
        # Igual guardamos la foto -- el vendedor puede reintentar o cargar a mano,
        # pero la evidencia de la nota física no se pierde.
        foto = process_and_upload_photo(raw, file.content_type or "image/jpeg", prefix="ventas/notas_ocr")
        await db.execute(text("""
            INSERT INTO PEDIDO_NOTAS_OCR (id_usuario, foto_url, estado, error_mensaje)
            VALUES (:u, :url, 'descartado', :err)
        """), {"u": current_user.id, "url": foto["blob_path"], "err": str(e)})
        await db.commit()
        raise HTTPException(status_code=422, detail=str(e))

    foto = process_and_upload_photo(raw, file.content_type or "image/jpeg", prefix="ventas/notas_ocr")

    catalogo = (await db.execute(text("""
        SELECT cv.id_producto, p.producto_gutrade AS nombre, cv.precio_unitario
        FROM CATALOGO_VENTA cv JOIN PRODUCTS p ON p.id_product = cv.id_producto
        WHERE cv.id_cliente = :c AND cv.activo = 1
    """), {"c": id_cliente})).fetchall()
    candidatos = [{"id_producto": r.id_producto, "nombre": r.nombre, "precio_unitario": float(r.precio_unitario)} for r in catalogo]

    productos_propuestos = []
    for p in extraido["productos"]:
        match = _mejor_match(p["nombre_texto"], candidatos)
        productos_propuestos.append({
            "nombre_texto": p["nombre_texto"], "cantidad": p["cantidad"],
            "match": match,
        })

    ins = (await db.execute(text("""
        INSERT INTO PEDIDO_NOTAS_OCR (id_usuario, foto_url, texto_ocr, json_ia, estado)
        OUTPUT INSERTED.id
        VALUES (:u, :url, :texto, :json_ia, 'pendiente_revision')
    """), {
        "u": current_user.id, "url": foto["blob_path"],
        "texto": extraido.get("cliente_texto"),
        "json_ia": __import__("json").dumps(extraido, ensure_ascii=False),
    })).fetchone()

    await db.commit()
    return {
        "success": True, "id_nota_ocr": ins.id, "id_cliente": id_cliente,
        "cliente_texto": extraido.get("cliente_texto"), "fecha_texto": extraido.get("fecha_texto"),
        "notas_texto": extraido.get("notas_texto"), "confianza": extraido.get("confianza"),
        "productos_propuestos": productos_propuestos,
        "aviso": "Revisa cada producto antes de confirmar -- la IA propone, vos decidís." if productos_propuestos else "No se detectaron productos legibles en la foto.",
    }


@router.post("/pedidos/ocr/{id_nota}/confirmar")
async def confirmar_nota_ocr(id_nota: int, payload: dict, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    """El vendedor ya revisó/corrigió la propuesta en pantalla -- acá llega la
    versión final (payload igual al de POST /pedidos), y se crea el pedido
    real con origen='ocr', enlazado a la nota."""
    _check_acceso_ventas(current_user)
    nota = (await db.execute(text("SELECT id, estado FROM PEDIDO_NOTAS_OCR WHERE id = :id"), {"id": id_nota})).fetchone()
    if not nota:
        raise HTTPException(status_code=404, detail="Nota OCR no encontrada")
    if nota.estado == "confirmado":
        raise HTTPException(status_code=400, detail="Esta nota ya fue confirmada")

    resultado = await _crear_pedido(db, current_user, payload, origen="ocr")
    await db.execute(text("UPDATE PEDIDO_NOTAS_OCR SET estado='confirmado', id_pedido=:pid WHERE id=:id"),
               {"pid": resultado["id_pedido"], "id": id_nota})
    await db.commit()
    return {"success": True, "pedido": resultado}


# ════════════════════════════════════════════════════════════════════
# CRÉDITO
# ════════════════════════════════════════════════════════════════════

@router.get("/credito/{id_cliente}")
async def get_credito(id_cliente: int, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    _check_acceso_ventas(current_user)
    c = await _credito_cliente(db, id_cliente)
    if not c:
        return {"id_cliente": id_cliente, "limite_credito": 0, "saldo_actual": 0, "dias_mora": 0, "bloqueado": False, "configurado": False}
    return {"id_cliente": id_cliente, "limite_credito": float(c.limite_credito), "saldo_actual": float(c.saldo_actual),
            "dias_mora": c.dias_mora, "bloqueado": bool(c.bloqueado), "configurado": True}


@router.post("/credito/{id_cliente}")
async def set_credito(id_cliente: int, payload: dict, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Solo un administrador puede configurar crédito")
    existe = (await db.execute(text("SELECT id_cliente FROM CREDITO_CLIENTE WHERE id_cliente = :c"), {"c": id_cliente})).fetchone()
    params = {
        "c": id_cliente, "lim": payload.get("limite_credito", 0), "saldo": payload.get("saldo_actual", 0),
        "mora": payload.get("dias_mora", 0), "bloq": 1 if payload.get("bloqueado") else 0,
    }
    if existe:
        await db.execute(text("""
            UPDATE CREDITO_CLIENTE SET limite_credito=:lim, saldo_actual=:saldo, dias_mora=:mora,
                   bloqueado=:bloq, actualizado_en=GETDATE() WHERE id_cliente=:c
        """), params)
    else:
        await db.execute(text("""
            INSERT INTO CREDITO_CLIENTE (id_cliente, limite_credito, saldo_actual, dias_mora, bloqueado)
            VALUES (:c, :lim, :saldo, :mora, :bloq)
        """), params)
    await db.commit()
    return {"success": True}


METODOS_PAGO_VALIDOS = ["Transferencia", "Efectivo", "Zelle", "Pago Móvil", "Otro"]


@router.post("/credito/{id_cliente}/pago")
async def registrar_pago(id_cliente: int, payload: dict, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    """Registra un cobro/abono puntual -- a diferencia de set_credito (que
    sobrescribe el saldo entero, solo admin), esto lo puede cargar el
    vendedor que cobró en la calle: decrementa saldo_actual y deja un
    registro auditable en PAGOS_CLIENTE (saldo antes/después)."""
    _check_acceso_ventas(current_user)
    try:
        monto = float(payload.get("monto"))
    except (TypeError, ValueError):
        raise HTTPException(status_code=400, detail="El monto es requerido y debe ser numérico")
    if monto <= 0:
        raise HTTPException(status_code=400, detail="El monto debe ser mayor que cero")
    metodo = (payload.get("metodo_pago") or "").strip()
    if metodo not in METODOS_PAGO_VALIDOS:
        raise HTTPException(status_code=400, detail=f"metodo_pago debe ser una de: {', '.join(METODOS_PAGO_VALIDOS)}")
    referencia = (payload.get("referencia") or "").strip() or None
    notas = (payload.get("notas") or "").strip() or None

    c = await _credito_cliente(db, id_cliente)
    saldo_antes = float(c.saldo_actual) if c else 0.0
    saldo_despues = saldo_antes - monto

    if c:
        await db.execute(text(
            "UPDATE CREDITO_CLIENTE SET saldo_actual = :s, actualizado_en = GETDATE() WHERE id_cliente = :c"
        ), {"s": saldo_despues, "c": id_cliente})
    else:
        # Cliente sin fila en CREDITO_CLIENTE todavía (nunca se le configuró
        # límite) -- un pago igual debe quedar registrado, arranca en saldo
        # negativo (a favor del cliente) en vez de fallar.
        await db.execute(text("""
            INSERT INTO CREDITO_CLIENTE (id_cliente, limite_credito, saldo_actual, dias_mora, bloqueado)
            VALUES (:c, 0, :s, 0, 0)
        """), {"c": id_cliente, "s": saldo_despues})

    row = (await db.execute(text("""
        INSERT INTO PAGOS_CLIENTE (id_cliente, monto, metodo_pago, referencia, notas, id_usuario_registro, saldo_antes, saldo_despues)
        OUTPUT INSERTED.id_pago, INSERTED.fecha_pago
        VALUES (:c, :m, :met, :ref, :notas, :u, :sa, :sd)
    """), {
        "c": id_cliente, "m": monto, "met": metodo, "ref": referencia, "notas": notas,
        "u": current_user.id, "sa": saldo_antes, "sd": saldo_despues,
    })).fetchone()
    await db.commit()

    notify_event("credito.pago_registrado", {"id_cliente": id_cliente, "monto": monto, "saldo_despues": saldo_despues})
    return {
        "success": True, "id_pago": row.id_pago,
        "fecha_pago": row.fecha_pago.isoformat() if row.fecha_pago else None,
        "saldo_antes": saldo_antes, "saldo_despues": saldo_despues,
    }


@router.get("/credito/{id_cliente}/pagos")
async def get_pagos_cliente(id_cliente: int, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    _check_acceso_ventas(current_user)
    rows = (await db.execute(text("""
        SELECT pc.id_pago, pc.monto, pc.metodo_pago, pc.referencia, pc.notas,
               pc.fecha_pago, pc.saldo_antes, pc.saldo_despues, u.username AS registrado_por
        FROM PAGOS_CLIENTE pc
        JOIN USUARIOS u ON u.id_usuario = pc.id_usuario_registro
        WHERE pc.id_cliente = :c
        ORDER BY pc.fecha_pago DESC
    """), {"c": id_cliente})).fetchall()
    return [{
        "id_pago": r.id_pago, "monto": float(r.monto), "metodo_pago": r.metodo_pago,
        "referencia": r.referencia, "notas": r.notas,
        "fecha_pago": r.fecha_pago.isoformat() if r.fecha_pago else None,
        "saldo_antes": float(r.saldo_antes), "saldo_despues": float(r.saldo_despues),
        "registrado_por": r.registrado_por,
    } for r in rows]


# ════════════════════════════════════════════════════════════════════
# INVENTARIO (caché externa -- lista para conectar a la futura API de DUSA)
# ════════════════════════════════════════════════════════════════════

@router.get("/inventario/{id_cliente}")
async def get_inventario(id_cliente: int, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    _check_acceso_ventas(current_user)
    rows = (await db.execute(text("""
        SELECT ie.id_producto, p.producto_gutrade AS nombre, ie.cantidad_disponible, ie.fuente, ie.ultima_actualizacion
        FROM INVENTARIO_CACHE_EXTERNO ie JOIN PRODUCTS p ON p.id_product = ie.id_producto
        WHERE ie.id_cliente = :c ORDER BY ie.cantidad_disponible ASC
    """), {"c": id_cliente})).fetchall()
    return [{
        "id_producto": r.id_producto, "nombre": r.nombre, "cantidad_disponible": r.cantidad_disponible,
        "fuente": r.fuente, "ultima_actualizacion": r.ultima_actualizacion.isoformat() if r.ultima_actualizacion else None,
        "quiebre": r.cantidad_disponible <= 0,
    } for r in rows]


@router.post("/inventario/{id_cliente}/sincronizar-manual")
async def sincronizar_inventario_manual(id_cliente: int, payload: dict, db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user)):
    """Carga manual (o desde un job futuro que consuma la API real de DUSA)
    del inventario: payload = {items: [{id_producto, cantidad_disponible}]}.
    Mientras no exista la integración real, esto es lo que alimenta la
    validación de stock del carrito y el dashboard de quiebres."""
    if not (current_user.is_admin or current_user.is_supervisor):
        raise HTTPException(status_code=403, detail="Solo admin/supervisor puede sincronizar inventario")
    items = payload.get("items") or []
    for it in items:
        await db.execute(text("""
            MERGE INVENTARIO_CACHE_EXTERNO AS target
            USING (SELECT :pid AS id_producto, :cid AS id_cliente) AS src
            ON target.id_producto = src.id_producto AND target.id_cliente = src.id_cliente
            WHEN MATCHED THEN UPDATE SET cantidad_disponible = :cant, fuente = :fuente, ultima_actualizacion = GETDATE()
            WHEN NOT MATCHED THEN INSERT (id_producto, id_cliente, cantidad_disponible, fuente, ultima_actualizacion)
                VALUES (:pid, :cid, :cant, :fuente, GETDATE());
        """), {"pid": it["id_producto"], "cid": id_cliente, "cant": it["cantidad_disponible"], "fuente": payload.get("fuente", "MANUAL")})
    await db.commit()
    return {"success": True, "actualizados": len(items)}


# ════════════════════════════════════════════════════════════════════
# DASHBOARD
# ════════════════════════════════════════════════════════════════════

@router.get("/dashboard")
async def dashboard(
    desde: Optional[str] = None, hasta: Optional[str] = None, id_cliente: Optional[int] = None,
    db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user),
):
    _check_acceso_ventas(current_user)
    desde = desde or (date.today() - timedelta(days=30)).isoformat()
    hasta = hasta or date.today().isoformat()

    where = ["pe.fecha >= :desde", "pe.fecha < DATEADD(day, 1, CAST(:hasta AS DATE))", "pe.estado != 'Rechazado'"]
    params: dict = {"desde": desde, "hasta": hasta}
    if not _puede_gestionar(current_user):
        where.append("pe.id_usuario_vendedor = :uid")
        params["uid"] = current_user.id
    if id_cliente:
        where.append("pe.id_cliente = :cliente")
        params["cliente"] = id_cliente
    where_sql = " AND ".join(where)

    resumen = (await db.execute(text(f"""
        SELECT COUNT(*) AS pedidos, COALESCE(SUM(pe.total), 0) AS total_vendido,
               COALESCE(AVG(pe.total), 0) AS ticket_promedio
        FROM PEDIDOS pe WHERE {where_sql}
    """), params)).fetchone()

    por_vendedor = (await db.execute(text(f"""
        SELECT u.username AS vendedor, COUNT(*) AS pedidos, SUM(pe.total) AS total
        FROM PEDIDOS pe JOIN USUARIOS u ON u.id_usuario = pe.id_usuario_vendedor
        WHERE {where_sql} GROUP BY u.username ORDER BY total DESC
    """), params)).fetchall()

    por_dia = (await db.execute(text(f"""
        SELECT CAST(pe.fecha AS DATE) AS dia, SUM(pe.total) AS total, COUNT(*) AS pedidos
        FROM PEDIDOS pe WHERE {where_sql} GROUP BY CAST(pe.fecha AS DATE) ORDER BY dia
    """), params)).fetchall()

    top_productos = await db.execute(text(f"""
        SELECT pl.nombre_producto, SUM(pl.cantidad) AS unidades, SUM(pl.subtotal_linea) AS total
        FROM PEDIDO_LINEAS pl JOIN PEDIDOS pe ON pe.id_pedido = pl.id_pedido
        WHERE {where_sql} GROUP BY pl.nombre_producto ORDER BY total DESC
    """), params).fetchmany(10)

    por_estado = (await db.execute(text(f"""
        SELECT pe.estado, COUNT(*) AS cantidad FROM PEDIDOS pe WHERE {where_sql} GROUP BY pe.estado
    """), params)).fetchall()

    top_clientes = await db.execute(text(f"""
        SELECT c.cliente, COUNT(*) AS pedidos, SUM(pe.total) AS total
        FROM PEDIDOS pe JOIN CLIENTES c ON c.id_cliente = pe.id_cliente
        WHERE {where_sql} GROUP BY c.cliente ORDER BY total DESC
    """), params).fetchmany(10)

    return {
        "periodo": {"desde": desde, "hasta": hasta},
        "resumen": {"pedidos": resumen.pedidos, "total_vendido": float(resumen.total_vendido), "ticket_promedio": float(resumen.ticket_promedio)},
        "por_vendedor": [{"vendedor": r.vendedor, "pedidos": r.pedidos, "total": float(r.total)} for r in por_vendedor],
        "por_dia": [{"dia": r.dia.isoformat(), "total": float(r.total), "pedidos": r.pedidos} for r in por_dia],
        "top_productos": [{"producto": r.nombre_producto, "unidades": r.unidades, "total": float(r.total)} for r in top_productos],
        "por_estado": [{"estado": r.estado, "cantidad": r.cantidad} for r in por_estado],
        "top_clientes": [{"cliente": r.cliente, "pedidos": r.pedidos, "total": float(r.total)} for r in top_clientes],
    }


# ════════════════════════════════════════════════════════════════════
# PRONÓSTICO (roadmap predictivo, item S2)
# ════════════════════════════════════════════════════════════════════

MIN_SEMANAS_PRONOSTICO = 8  # semanas de historial (huecos incluidos) antes de intentar ajustar un modelo
MIN_PEDIDOS_PRONOSTICO = 3  # semanas CON al menos un pedido confirmado -- 8 semanas de calendario con solo 2 pedidos reales no es tendencia, es ruido


@router.get("/pronostico")
async def pronostico_pedidos(
    id_cliente: Optional[int] = None, horizonte_semanas: int = 4,
    db: AsyncSession = Depends(get_async_db), current_user: User = Depends(get_current_user),
):
    """Proyecta el volumen de pedidos (monto total) de las próximas semanas
    por cliente. Agrega PEDIDOS confirmados (no Borrador, no Rechazado -- un
    borrador todavía puede cambiar o nunca enviarse) por semana calendario y
    ajusta un suavizado exponencial con tendencia amortiguada (Holt, vía
    statsmodels) por cliente -- sin componente estacional: con pocos meses de
    historial no hay ciclos suficientes para estimarla en serio, se agrega
    más adelante cuando haya un año+ de datos reales.

    Clientes por debajo de MIN_SEMANAS_PRONOSTICO/MIN_PEDIDOS_PRONOSTICO no
    se pronostican -- se devuelven igual con suficiente_historial=False y
    cuánto falta, para que el frontend explique el motivo en vez de mostrar
    un gráfico vacío sin contexto (mismo criterio que la tendencia de
    competencia de Auditoría de Campo)."""
    _check_acceso_ventas(current_user)
    horizonte_semanas = max(1, min(horizonte_semanas, 12))

    where = ["pe.estado NOT IN ('Borrador', 'Rechazado')"]
    params: dict = {}
    if not _puede_gestionar(current_user):
        where.append("pe.id_usuario_vendedor = :uid")
        params["uid"] = current_user.id
    if id_cliente:
        where.append("pe.id_cliente = :cliente")
        params["cliente"] = id_cliente
    where_sql = " AND ".join(where)

    rows = (await db.execute(text(f"""
        SELECT pe.id_cliente, c.cliente, pe.fecha, pe.total
        FROM PEDIDOS pe JOIN CLIENTES c ON c.id_cliente = pe.id_cliente
        WHERE {where_sql}
        ORDER BY pe.fecha
    """), params)).fetchall()

    por_cliente: dict = {}
    for r in rows:
        fecha = r.fecha.date() if hasattr(r.fecha, "date") else r.fecha
        lunes = fecha - timedelta(days=fecha.weekday())
        info = por_cliente.setdefault(r.id_cliente, {"nombre": r.cliente, "semanas": {}})
        info["semanas"][lunes] = info["semanas"].get(lunes, 0.0) + float(r.total)

    resultados = []
    for id_cli, info in por_cliente.items():
        semanas_ordenadas = sorted(info["semanas"].keys())
        primera, ultima = semanas_ordenadas[0], semanas_ordenadas[-1]

        # Grilla completa de semanas: los huecos cuentan como $0 vendido, no
        # como semanas ausentes -- si no, la tendencia queda inflada al
        # ignorar las semanas flojas.
        grid, cursor = [], primera
        while cursor <= ultima:
            grid.append(cursor)
            cursor += timedelta(weeks=1)
        serie = [info["semanas"].get(s, 0.0) for s in grid]
        n_semanas_con_pedido = sum(1 for v in serie if v > 0)

        historial = {
            "id_cliente": id_cli, "cliente": info["nombre"],
            "semanas_con_historial": len(grid), "semanas_con_pedidos": n_semanas_con_pedido,
            "total_historico": round(sum(serie), 2),
            "serie_historica": [{"semana": s.isoformat(), "total": round(v, 2)} for s, v in zip(grid, serie)],
        }

        if len(grid) < MIN_SEMANAS_PRONOSTICO or n_semanas_con_pedido < MIN_PEDIDOS_PRONOSTICO:
            resultados.append({
                **historial, "suficiente_historial": False,
                "semanas_faltantes": max(0, MIN_SEMANAS_PRONOSTICO - len(grid)),
                "pronostico": [],
            })
            continue

        try:
            import numpy as np
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            y = np.array(serie, dtype=float)
            modelo = ExponentialSmoothing(y, trend="add", damped_trend=True, initialization_method="estimated").fit()
            pred = [max(0.0, round(float(v), 2)) for v in modelo.forecast(horizonte_semanas)]
            residuos = y - modelo.fittedvalues
            desviacion = float(np.std(residuos)) if len(residuos) > 1 else 0.0

            semanas_futuras, cursor = [], ultima + timedelta(weeks=1)
            for _ in range(horizonte_semanas):
                semanas_futuras.append(cursor)
                cursor += timedelta(weeks=1)

            resultados.append({
                **historial, "suficiente_historial": True,
                "pronostico": [
                    {"semana": s.isoformat(), "total_esperado": v,
                     "rango_bajo": max(0.0, round(v - desviacion, 2)), "rango_alto": round(v + desviacion, 2)}
                    for s, v in zip(semanas_futuras, pred)
                ],
            })
        except Exception as e:
            logger.warning(f"[Pronostico] Fallo el ajuste para cliente {id_cli}: {e}")
            resultados.append({**historial, "suficiente_historial": False, "semanas_faltantes": 0, "pronostico": [], "error_modelo": True})

    resultados.sort(key=lambda r: r["total_historico"], reverse=True)
    return {"success": True, "minimo_semanas_requerido": MIN_SEMANAS_PRONOSTICO, "minimo_pedidos_requerido": MIN_PEDIDOS_PRONOSTICO, "clientes": resultados}
