"""
Client Photos API – Endpoints para la vista del cliente.
Permite navegar: Regiones → Cadenas → Puntos → Visitas/Fotos
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario
from app.services.visibility import client_route_ids
from datetime import datetime
from typing import Optional
import logging

router = APIRouter(prefix="/api/client", tags=["Client Photos"])
logger = logging.getLogger("app.client_photos")


def _get_cliente_id(user: Usuario, requested_cliente_id: Optional[int] = None) -> int:
    """Resuelve el id_cliente a usar en la query.

    - Cliente normal → su `user.id_perfil` (ignora `requested_cliente_id`).
    - **Coordinador Exclusivo (id_rol=3)** → debe pasar `requested_cliente_id`
      (query param `cliente_id`). Se valida que el cliente exista pero el
      coordinador puede elegir cualquiera con visitas/fotos aprobadas.
    - 403 si el usuario no es cliente.
    - 400 si el coordinador no envió `cliente_id`.
    """
    if not user.is_client:
        raise HTTPException(status_code=403, detail="No autorizado")

    if user.is_coordinador_exclusivo:
        if not requested_cliente_id:
            raise HTTPException(
                status_code=400,
                detail="Debes seleccionar un cliente primero (query param cliente_id)."
            )
        return int(requested_cliente_id)

    if not user.id_perfil:
        raise HTTPException(status_code=400, detail="No tienes un cliente asociado. Contacta al administrador.")
    return user.id_perfil


# ─── SELECTOR DE CLIENTES (solo Coordinador Exclusivo) ──────────────────────
@router.get("/exclusive-clients")
def get_exclusive_clients(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista de clientes para que el Coordinador Exclusivo elija.

    Incluye:
      - Clientes con `id_tipo_cliente = 3` (Exclusivos) → siempre visibles.
      - Clientes con `id_tipo_cliente = 1` (Tradex) que tengan al menos
        una visita con foto aprobada.
    """
    if not current_user.is_coordinador_exclusivo:
        raise HTTPException(status_code=403, detail="Solo Coordinador Exclusivo")

    query = text("""
        SELECT DISTINCT c.id_cliente, c.cliente, c.id_tipo_cliente
        FROM CLIENTES c
        WHERE c.id_tipo_cliente = 3

        UNION

        SELECT DISTINCT c.id_cliente, c.cliente, c.id_tipo_cliente
        FROM CLIENTES c
        INNER JOIN VISITAS_MERCADERISTA vm ON c.id_cliente = vm.id_cliente
        INNER JOIN FOTOS_TOTALES ft ON vm.id_visita = ft.id_visita
        WHERE c.id_tipo_cliente = 1
          AND ft.Estado = 'Aprobada'

        ORDER BY c.cliente
    """)
    rows = db.execute(query).fetchall()
    return [
        {
            "id_cliente": r[0],
            "cliente": r[1],
            "id_tipo_cliente": r[2],
        }
        for r in rows
    ]


# ─── DASHBOARD ───────────────────────────────────────────────────────────────
@router.get("/dashboard")
def get_client_dashboard(
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtener la configuración del dashboard para el cliente."""
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)
    query = text("""
        SELECT url_html, tipo
        FROM dashboard_client
        WHERE id_cliente = :cliente_id
    """)
    row = db.execute(query, {"cliente_id": resolved_cliente_id}).fetchone()

    if not row:
        return {"has_dashboard": False, "url_html": None}

    return {
        "has_dashboard": True,
        "url_html": row[0],
        "tipo": row[1]
    }


# ─── SUMMARY ─────────────────────────────────────────────────────────────────
@router.get("/summary")
def get_client_summary(
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtener un resumen de actividad para el cliente."""
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)

    query_visits = text("""
        SELECT COUNT(*)
        FROM VISITAS_MERCADERISTA vm
        WHERE vm.id_cliente = :cliente_id
          AND vm.fecha_visita >= DATEADD(day, -30, GETDATE())
    """)
    recent_visits = db.execute(query_visits, {"cliente_id": resolved_cliente_id}).scalar() or 0

    query_photos = text("""
        SELECT COUNT(ft.id_foto)
        FROM FOTOS_TOTALES ft
        INNER JOIN VISITAS_MERCADERISTA vm ON ft.id_visita = vm.id_visita
        WHERE vm.id_cliente = :cliente_id
          AND ft.Estado = 'Aprobada'
    """)
    recent_photos = db.execute(query_photos, {"cliente_id": resolved_cliente_id}).scalar() or 0

    query_messages = text("""
        SELECT COUNT(cm.id_mensaje)
        FROM CHAT_MENSAJES_CLIENTE cm
        INNER JOIN VISITAS_MERCADERISTA vm ON cm.id_visita = vm.id_visita
        WHERE vm.id_cliente = :cliente_id
          AND cm.fecha_envio >= DATEADD(hour, -48, GETDATE())
    """)
    recent_messages = db.execute(query_messages, {"cliente_id": resolved_cliente_id}).scalar() or 0

    return {
        "recent_visits": recent_visits,
        "recent_photos": recent_photos,
        "recent_messages": recent_messages,
        "period": "Últimos 30 días"
    }


# ─── REGIONES ────────────────────────────────────────────────────────────────
@router.get("/regions")
def get_client_regions(
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtener las regiones geográficas del cliente."""
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)
    query = text("""
        SELECT DISTINCT rn.cuadrante AS region
        FROM RUTAS_NUEVAS rn
        INNER JOIN RUTA_PROGRAMACION rp ON rn.id_ruta = rp.id_ruta
        WHERE rp.id_cliente = :cliente_id
          AND rn.cuadrante IS NOT NULL
          AND rn.cuadrante != ''
        ORDER BY rn.cuadrante
    """)
    rows = db.execute(query, {"cliente_id": resolved_cliente_id}).fetchall()
    return [{"region": r[0]} for r in rows if r[0]]


# ─── CADENAS POR REGIÓN ─────────────────────────────────────────────────────
@router.get("/chains/{region}")
def get_client_chains_by_region(
    region: str,
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtener las cadenas comerciales de una región para el cliente."""
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)
    query = text("""
        SELECT DISTINCT pin.jerarquia_nivel_2_2 AS cadena
        FROM PUNTOS_INTERES1 pin
        INNER JOIN RUTA_PROGRAMACION rp ON pin.identificador = rp.id_punto_interes
        INNER JOIN RUTAS_NUEVAS rn ON rp.id_ruta = rn.id_ruta
        WHERE rp.id_cliente = :cliente_id
          AND rn.cuadrante = :region
          AND pin.jerarquia_nivel_2_2 IS NOT NULL
          AND pin.jerarquia_nivel_2_2 != ''
        ORDER BY pin.jerarquia_nivel_2_2
    """)
    rows = db.execute(query, {"cliente_id": resolved_cliente_id, "region": region}).fetchall()
    return [{"cadena": r[0]} for r in rows if r[0]]


# ─── PUNTOS POR REGIÓN ──────────────────────────────────────────────────────
@router.get("/points/{region}")
def get_client_points_by_region(
    region: str,
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtener los puntos de venta de una región para el cliente."""
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)
    query = text("""
        SELECT DISTINCT
            pin.identificador,
            pin.punto_de_interes,
            pin.jerarquia_nivel_2_2 AS cadena,
            pin.Direccion AS direccion,
            pin.ciudad
        FROM PUNTOS_INTERES1 pin
        INNER JOIN RUTA_PROGRAMACION rp ON pin.identificador = rp.id_punto_interes
        INNER JOIN RUTAS_NUEVAS rn ON rp.id_ruta = rn.id_ruta
        WHERE rp.id_cliente = :cliente_id
          AND rn.cuadrante = :region
        ORDER BY pin.punto_de_interes
    """)
    rows = db.execute(query, {"cliente_id": resolved_cliente_id, "region": region}).fetchall()
    return [
        {
            "identificador": r[0],
            "punto_de_interes": r[1],
            "cadena": r[2] or "Sin cadena",
            "direccion": r[3] or "",
            "ciudad": r[4] or "",
        }
        for r in rows
    ]


# ─── VISITAS + FOTOS DE UN PUNTO ─────────────────────────────────────────────
@router.get("/point/{point_id}/visits")
def get_client_point_visits(
    point_id: str,
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtener las visitas de un punto con sus fotos agrupadas por tipo."""
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)

    visits_query = text("""
        SELECT
            vm.id_visita,
            vm.fecha_visita,
            vm.estado,
            m.nombre AS mercaderista_nombre,
            m.cedula AS mercaderista_cedula
        FROM VISITAS_MERCADERISTA vm
        LEFT JOIN MERCADERISTAS m ON vm.id_mercaderista = m.id_mercaderista
        WHERE vm.identificador_punto_interes = :point_id
          AND vm.id_cliente = :cliente_id
        ORDER BY vm.fecha_visita DESC
    """)
    visit_rows = db.execute(visits_query, {"point_id": point_id, "cliente_id": resolved_cliente_id}).fetchall()

    if not visit_rows:
        return []

    visit_ids = [v[0] for v in visit_rows]

    # Obtener fotos de todas las visitas — dynamic IN params for MSSQL
    placeholders = ", ".join(f":vid_{i}" for i in range(len(visit_ids)))
    photos_query = text(f"""
        SELECT
            ft.id_foto,
            ft.id_visita,
            ft.id_tipo_foto,
            ft.file_path,
            ft.Estado,
            ft.fecha_registro
        FROM FOTOS_TOTALES ft
        WHERE ft.id_visita IN ({placeholders})
          AND ft.Estado = 'Aprobada'
        ORDER BY ft.id_tipo_foto, ft.fecha_registro DESC
    """)
    params = {f"vid_{i}": vid for i, vid in enumerate(visit_ids)}
    photo_rows = db.execute(photos_query, params).fetchall()

    # Generar SAS URLs
    from app.services.azure_service import azure_service
    photos_by_visit: dict[int, list] = {}
    for p in photo_rows:
        vid = p[1]
        if vid not in photos_by_visit:
            photos_by_visit[vid] = []
        url = azure_service.get_proxy_url(p[3]) if p[3] else None
        photos_by_visit[vid].append({
            "id_foto": p[0],
            "id_tipo_foto": p[2],
            "tipo_nombre": _map_tipo_foto(p[2]),
            "url": url,
            "estado": p[4],
            "fecha": str(p[5]) if p[5] else None,
        })

    result = []
    for v in visit_rows:
        fotos = photos_by_visit.get(v[0], [])
        result.append({
            "id_visita": v[0],
            "fecha": str(v[1]) if v[1] else None,
            "estado": v[2],
            "mercaderista": v[3] or "Desconocido",
            "mercaderista_cedula": v[4],
            "total_fotos": len(fotos),
            "fotos": fotos,
        })

    return result


def _map_tipo_foto(id_tipo: int | None) -> str:
    mapping = {
        1: "Gestión Antes",
        2: "Gestión Después",
        3: "Precio",
        4: "Exhibiciones Adicionales",
        8: "Material POP Antes",
        9: "Material POP Después",
    }
    return mapping.get(id_tipo or 0, "Otro")


# ─── MIS VISITAS (GLOBAL) ───────────────────────────────────────────────────
@router.get("/mis-visitas")
def get_client_mis_visitas(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    ruta: Optional[str] = None,
    cadena: Optional[str] = None,
    punto_id: Optional[str] = None,
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Obtener todas las visitas del cliente en un rango de fechas, con filtros."""
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)

    # Un cliente sin filas en CLIENTES_RUTAS ve TODAS las rutas de su cliente
    # (sin restricción); si tiene alguna fila, solo ve esas rutas. Esto no
    # aplica al coordinador exclusivo (su alcance de clientes es otro mecanismo).
    route_ids = None
    if current_user.rol == "client":
        route_ids = client_route_ids(db, current_user)
    route_filter_sql = ""
    if route_ids is not None:
        ids_csv = ",".join(str(int(i)) for i in route_ids) if route_ids else "-1"
        route_filter_sql = f"""
          AND EXISTS (
              SELECT 1 FROM RUTA_PROGRAMACION rp_f
              WHERE rp_f.id_punto_interes = vm.identificador_punto_interes
                AND rp_f.id_cliente = vm.id_cliente
                AND rp_f.id_ruta IN ({ids_csv})
          )
        """

    if not fecha_inicio:
        fecha_inicio_sql = datetime.now().strftime('%Y%m%d')
        fecha_inicio_res = datetime.now().strftime('%Y-%m-%d')
    else:
        try:
            parsed = datetime.strptime(fecha_inicio, '%Y-%m-%d')
            fecha_inicio_sql = parsed.strftime('%Y%m%d')
            fecha_inicio_res = fecha_inicio
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido (YYYY-MM-DD)")

    if not fecha_fin:
        fecha_fin_sql = fecha_inicio_sql
        fecha_fin_res = fecha_inicio_res
    else:
        try:
            parsed = datetime.strptime(fecha_fin, '%Y-%m-%d')
            fecha_fin_sql = parsed.strftime('%Y%m%d')
            fecha_fin_res = fecha_fin
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido (YYYY-MM-DD)")

    # Query principal de visitas
    query_str = """
        SELECT
            vm.id_visita,
            vm.fecha_visita,
            m.nombre                        AS mercaderista,
            pin.identificador               AS punto_id,
            pin.punto_de_interes            AS punto_nombre,
            pin.departamento,
            pin.ciudad,
            ISNULL(rn.ruta, 'Sin ruta')     AS ruta,
            pin.jerarquia_nivel_2_2         AS cadena,
            ft.id_foto,
            ft.file_path,
            ft.id_tipo_foto,
            ft.estado                       AS foto_estado,
            c.cliente                       AS cliente_nombre
        FROM VISITAS_MERCADERISTA vm
        JOIN MERCADERISTAS m         ON vm.id_mercaderista = m.id_mercaderista
        JOIN PUNTOS_INTERES1 pin     ON vm.identificador_punto_interes = pin.identificador
        JOIN CLIENTES c              ON vm.id_cliente = c.id_cliente
        JOIN FOTOS_TOTALES ft        ON ft.id_visita = vm.id_visita AND ft.estado = 'Aprobada' AND ft.id_tipo_foto IN (1,2,3,4,8,9)
        LEFT JOIN RUTA_PROGRAMACION rp ON rp.id_punto_interes = pin.identificador AND rp.id_cliente = vm.id_cliente
        LEFT JOIN RUTAS_NUEVAS rn    ON rn.id_ruta = rp.id_ruta
        WHERE vm.id_cliente = :cliente_id
          AND CAST(vm.fecha_visita AS DATE) >= :fecha_inicio_sql
          AND CAST(vm.fecha_visita AS DATE) <= :fecha_fin_sql
    """
    query_str += route_filter_sql
    params = {"cliente_id": resolved_cliente_id, "fecha_inicio_sql": fecha_inicio_sql, "fecha_fin_sql": fecha_fin_sql}

    if ruta:
        query_str += " AND ISNULL(rn.ruta, 'Sin ruta') = :ruta"
        params["ruta"] = ruta
    if cadena:
        query_str += " AND pin.jerarquia_nivel_2_2 = :cadena"
        params["cadena"] = cadena
    if punto_id:
        query_str += " AND pin.identificador = :punto_id"
        params["punto_id"] = punto_id

    query_str += " ORDER BY vm.id_visita DESC, ft.id_tipo_foto, ft.id_foto DESC"
    
    rows = db.execute(text(query_str), params).fetchall()

    CATEGORIAS_CONFIG = {
        1: ('Gestión', 'Gestión'),
        2: ('Gestión', 'Gestión'),
        3: ('Precio', 'Precio'),
        4: ('Exhibiciones', 'Exhibiciones Adicionales'),
        5: ('Activación', 'Activación'),
        6: ('Desactivación', 'Desactivación'),
        8: ('Material POP Antes', 'Material POP Antes'),
        9: ('Material POP Despues', 'Material POP Despues'),
    }

    visitas_dict = {}
    seen_fotos: dict[int, set[int]] = {}  # vid -> set de id_foto ya agregadas
    from app.services.azure_service import azure_service

    # Pre-compute a fast SAS URL builder to avoid per-blob crypto overhead
    _fast_sas_url = azure_service.get_proxy_url  # fallback
    try:
        from app.core.config import settings
        import urllib.parse
        from azure.storage.blob import generate_blob_sas, BlobSasPermissions
        from datetime import timedelta, timezone as tz
        _account_key = None
        cs = settings.AZURE_STORAGE_CONNECTION_STRING
        if cs:
            for part in cs.split(';'):
                if part.startswith('AccountKey='):
                    _account_key = part[len('AccountKey='):]
                    break
        if _account_key:
            _now = datetime.now(tz.utc)
            _expiry = (_now + timedelta(days=2)).replace(hour=0, minute=0, second=0, microsecond=0)
            _base_url = f"https://{settings.AZURE_ACCOUNT_NAME}.blob.core.windows.net/{settings.AZURE_CONTAINER_NAME}"
            _sas_cache: dict[str, str] = {}
            def _fast_sas_url(blob_name: str, hours: int = 2) -> str:
                if blob_name in _sas_cache:
                    return _sas_cache[blob_name]
                encoded = urllib.parse.quote(blob_name, safe='/')
                sas = generate_blob_sas(
                    account_name=settings.AZURE_ACCOUNT_NAME,
                    container_name=settings.AZURE_CONTAINER_NAME,
                    blob_name=blob_name,
                    account_key=_account_key,
                    permission=BlobSasPermissions(read=True),
                    expiry=_expiry,
                )
                url = f"{_base_url}/{encoded}?{sas}"
                _sas_cache[blob_name] = url
                return url
    except Exception:
        pass  # fallback to azure_service.get_proxy_url

    for row in rows:
        vid = row[0]
        if vid not in visitas_dict:
            visitas_dict[vid] = {
                'id_visita': vid,
                'fecha_visita': str(row[1]) if row[1] else None,
                'mercaderista': row[2] or '',
                'punto_id': row[3],
                'punto_nombre': row[4] or '',
                'departamento': row[5] or '',
                'ciudad': row[6] or '',
                'ruta': row[7] or '',
                'cadena': row[8] or '',
                'cliente_nombre': row[13] or '',
                'total_fotos': 0,
                'preview_foto': None,
                'fotos_por_categoria': {
                    'Gestión': [],
                    'Precio': [],
                    'Exhibiciones Adicionales': [],
                    'Activación': [],
                    'Desactivación': [],
                    'Material POP Antes': [],
                    'Material POP Despues': [],
                    'Otros': []
                }
            }
            seen_fotos[vid] = set()

        # Si la región no se había capturado aún (puede haber varias rutas para el punto)
        # tomamos la primera no-nula que aparezca.
        if not visitas_dict[vid]['ruta'] and row[7]:
            visitas_dict[vid]['ruta'] = row[7]

        # Foto (si hay y no duplicada por el JOIN con RUTA_PROGRAMACION)
        if row[9] and row[9] not in seen_fotos[vid]:
            seen_fotos[vid].add(row[9])
            id_tipo = row[11]
            cat_key, cat_label = CATEGORIAS_CONFIG.get(id_tipo, (f'Tipo {id_tipo}', 'Otros'))
            
            tipo_desc_map = {
                1: 'Antes', 2: 'Después', 3: 'Precio',
                4: 'Exhibiciones', 5: 'Activación', 6: 'Desactivación',
                8: 'Material POP Antes', 9: 'Material POP Después'
            }

            url = _fast_sas_url(row[10]) if row[10] else None

            foto = {
                'id_foto': row[9],
                'file_path': url, # Use the SAS URL instead of the raw path for the frontend
                'id_tipo_foto': id_tipo,
                'tipo_desc': tipo_desc_map.get(id_tipo, f'Tipo {id_tipo}'),
                'categoria': cat_label,
                'estado': row[12],
                'fecha': str(row[1]) if row[1] else None,
                'id_visita': vid,
            }

            cat_bucket = visitas_dict[vid]['fotos_por_categoria']
            if cat_label in cat_bucket:
                cat_bucket[cat_label].append(foto)
            else:
                cat_bucket['Otros'].append(foto)
                
            visitas_dict[vid]['total_fotos'] += 1
            if not visitas_dict[vid]['preview_foto']:
                visitas_dict[vid]['preview_foto'] = url

    # ─── Filtros encadenados (estilo "facets") ─────────────────────────────────
    # Para cada dropdown se excluye su propio filtro y se aplican los demás.
    # Así el usuario puede cambiar de selección sin que la opción actual desaparezca.
    base_where = """
        FROM VISITAS_MERCADERISTA vm
        JOIN PUNTOS_INTERES1 pin     ON vm.identificador_punto_interes = pin.identificador
        LEFT JOIN RUTA_PROGRAMACION rp ON rp.id_punto_interes = pin.identificador AND rp.id_cliente = vm.id_cliente
        LEFT JOIN RUTAS_NUEVAS rn    ON rn.id_ruta = rp.id_ruta
        WHERE vm.id_cliente = :cliente_id
          AND CAST(vm.fecha_visita AS DATE) >= :fecha_inicio_sql
          AND CAST(vm.fecha_visita AS DATE) <= :fecha_fin_sql
    """
    base_where += route_filter_sql
    base_params = {"cliente_id": resolved_cliente_id, "fecha_inicio_sql": fecha_inicio_sql, "fecha_fin_sql": fecha_fin_sql}

    def _build(extra_clauses: str, extra_params: dict, select_cols: str, order_by: str):
        sql = f"SELECT DISTINCT {select_cols} {base_where} {extra_clauses} ORDER BY {order_by}"
        return db.execute(text(sql), {**base_params, **extra_params}).fetchall()

    # Rutas: aplican filtros cadena + punto (no ruta)
    ruta_extra, ruta_params = "", {}
    if cadena:
        ruta_extra += " AND pin.jerarquia_nivel_2_2 = :cadena"; ruta_params["cadena"] = cadena
    if punto_id:
        ruta_extra += " AND pin.identificador = :punto_id"; ruta_params["punto_id"] = punto_id
    rutas_rows = _build(ruta_extra, ruta_params, "ISNULL(rn.ruta, 'Sin ruta') AS ruta", "ISNULL(rn.ruta, 'Sin ruta')")
    rutas = sorted({r[0] for r in rutas_rows if r[0]})

    # Cadenas: aplican filtros region + punto (no cadena)
    cadena_extra, cadena_params = "", {}
    if ruta:
        cadena_extra += " AND ISNULL(rn.ruta, 'Sin ruta') = :ruta"; cadena_params["ruta"] = ruta
    if punto_id:
        cadena_extra += " AND pin.identificador = :punto_id"; cadena_params["punto_id"] = punto_id
    cadenas_rows = _build(cadena_extra, cadena_params, "pin.jerarquia_nivel_2_2 AS cadena", "pin.jerarquia_nivel_2_2")
    cadenas = sorted({r[0] for r in cadenas_rows if r[0]})

    # Puntos: aplican filtros region + cadena (no punto)
    punto_extra, punto_params = "", {}
    if ruta:
        punto_extra += " AND ISNULL(rn.ruta, 'Sin ruta') = :ruta"; punto_params["ruta"] = ruta
    if cadena:
        punto_extra += " AND pin.jerarquia_nivel_2_2 = :cadena"; punto_params["cadena"] = cadena
    puntos_rows = _build(
        punto_extra, punto_params,
        "pin.identificador AS punto_id, pin.punto_de_interes AS punto_nombre",
        "pin.punto_de_interes",
    )
    seen = set()
    puntos_uniq = []
    for r in puntos_rows:
        if r[0] and r[0] not in seen:
            seen.add(r[0])
            puntos_uniq.append({'id': r[0], 'nombre': r[1]})

    return {
        'success': True,
        'fecha_inicio': fecha_inicio_res,
        'fecha_fin': fecha_fin_res,
        'es_hoy': fecha_inicio_res == datetime.now().strftime('%Y-%m-%d') and fecha_fin_res == datetime.now().strftime('%Y-%m-%d'),
        'visitas': list(visitas_dict.values()),
        'total': len(visitas_dict),
        'filtros': {
            'rutas': rutas,
            'cadenas': cadenas,
            'puntos': puntos_uniq,
        }
    }
