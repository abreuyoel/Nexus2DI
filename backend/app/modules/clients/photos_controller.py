import logging
from datetime import datetime, date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario
from app.modules.clients.entities import Cliente, DashboardClient
from app.modules.visits.entities import Visita, Foto
from app.modules.chat.entities import ChatMensaje
from app.modules.routes.entities import Ruta, RutaProgramacion, PuntoInteres
from app.modules.merchandisers.entities import Mercaderista
from app.modules.clients.dto import (
    ExclusiveClientResponse, ClientDashboardResponse, ClientSummaryResponse,
    RegionItemResponse, ChainItemResponse, PointItemResponse
)
from app.shared.visibility import client_route_ids

router = APIRouter(prefix="/api/client", tags=["Client Photos"])
logger = logging.getLogger("app.client_photos")


def _get_cliente_id(user: Usuario, requested_cliente_id: Optional[int] = None) -> int:
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


@router.get("/exclusive-clients", response_model=List[ExclusiveClientResponse])
def get_exclusive_clients(
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not current_user.is_coordinador_exclusivo:
        raise HTTPException(status_code=403, detail="Solo Coordinador Exclusivo")

    c1 = db.query(Cliente.id, Cliente.nombre, Cliente.id_tipo_cliente).filter(Cliente.id_tipo_cliente == 3)
    c2 = (
        db.query(Cliente.id, Cliente.nombre, Cliente.id_tipo_cliente)
        .join(Visita, Cliente.id == Visita.id_cliente)
        .join(Foto, Visita.id == Foto.visita_id)
        .filter(Cliente.id_tipo_cliente == 1, Foto.estado == "Aprobada")
    )
    union_query = c1.union(c2).order_by(Cliente.nombre).all()
    return [
        ExclusiveClientResponse(id_cliente=r[0], cliente=r[1] or "", id_tipo_cliente=r[2])
        for r in union_query
    ]


@router.get("/dashboard", response_model=ClientDashboardResponse)
def get_client_dashboard(
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)
    dash = db.query(DashboardClient).filter(DashboardClient.id_cliente == resolved_cliente_id).first()
    if not dash:
        return ClientDashboardResponse(has_dashboard=False, url_html=None, tipo=None)

    return ClientDashboardResponse(
        has_dashboard=True,
        url_html=dash.url_html,
        tipo=dash.tipo
    )


@router.get("/summary", response_model=ClientSummaryResponse)
def get_client_summary(
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)

    since_30_days = date.today() - timedelta(days=30)
    recent_visits = db.query(Visita).filter(
        Visita.id_cliente == resolved_cliente_id,
        Visita.fecha >= since_30_days
    ).count()

    recent_photos = db.query(Foto).join(Visita, Foto.visita_id == Visita.id).filter(
        Visita.id_cliente == resolved_cliente_id,
        Foto.estado == "Aprobada"
    ).count()

    since_48_hours = datetime.now() - timedelta(hours=48)
    recent_messages = db.query(ChatMensaje).join(Visita, ChatMensaje.visita_id == Visita.id).filter(
        Visita.id_cliente == resolved_cliente_id,
        ChatMensaje.created_at >= since_48_hours
    ).count()

    return ClientSummaryResponse(
        recent_visits=recent_visits,
        recent_photos=recent_photos,
        recent_messages=recent_messages,
        period="Últimos 30 días"
    )


@router.get("/regions", response_model=List[RegionItemResponse])
def get_client_regions(
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)
    rows = (
        db.query(Ruta.cuadrante)
        .distinct()
        .join(RutaProgramacion, Ruta.id == RutaProgramacion.ruta_id)
        .filter(
            RutaProgramacion.id_cliente == resolved_cliente_id,
            Ruta.cuadrante.isnot(None),
            Ruta.cuadrante != ""
        )
        .order_by(Ruta.cuadrante)
        .all()
    )
    return [RegionItemResponse(region=r[0]) for r in rows if r[0]]


@router.get("/chains/{region}", response_model=List[ChainItemResponse])
def get_client_chains_by_region(
    region: str,
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)
    rows = (
        db.query(PuntoInteres.cadena)
        .distinct()
        .join(RutaProgramacion, PuntoInteres.id == RutaProgramacion.punto_id)
        .join(Ruta, RutaProgramacion.ruta_id == Ruta.id)
        .filter(
            RutaProgramacion.id_cliente == resolved_cliente_id,
            Ruta.cuadrante == region,
            PuntoInteres.cadena.isnot(None),
            PuntoInteres.cadena != ""
        )
        .order_by(PuntoInteres.cadena)
        .all()
    )
    return [ChainItemResponse(cadena=r[0]) for r in rows if r[0]]


@router.get("/points/{region}", response_model=List[PointItemResponse])
def get_client_points_by_region(
    region: str,
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)
    rows = (
        db.query(
            PuntoInteres.id,
            PuntoInteres.nombre,
            PuntoInteres.cadena,
            PuntoInteres.direccion,
            PuntoInteres.ciudad
        )
        .distinct()
        .join(RutaProgramacion, PuntoInteres.id == RutaProgramacion.punto_id)
        .join(Ruta, RutaProgramacion.ruta_id == Ruta.id)
        .filter(
            RutaProgramacion.id_cliente == resolved_cliente_id,
            Ruta.cuadrante == region
        )
        .order_by(PuntoInteres.nombre)
        .all()
    )
    return [
        PointItemResponse(
            identificador=r[0],
            punto_de_interes=r[1] or "",
            cadena=r[2] or "Sin cadena",
            direccion=r[3] or "",
            ciudad=r[4] or ""
        )
        for r in rows
    ]


@router.get("/point/{point_id}/visits")
def get_client_point_visits(
    point_id: str,
    cliente_id: Optional[int] = Query(None, description="Solo coordinador exclusivo"),
    current_user: Usuario = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)

    visit_rows = (
        db.query(
            Visita.id,
            Visita.fecha,
            Visita.estado,
            Mercaderista.nombre,
            Mercaderista.cedula
        )
        .outerjoin(Mercaderista, Visita.mercaderista_id == Mercaderista.id)
        .filter(
            Visita.punto_id == point_id,
            Visita.id_cliente == resolved_cliente_id
        )
        .order_by(Visita.fecha.desc())
        .all()
    )

    if not visit_rows:
        return []

    visit_ids = [v[0] for v in visit_rows]

    photo_rows = (
        db.query(
            Foto.id,
            Foto.visita_id,
            Foto.id_tipo_foto,
            Foto.blob_path,
            Foto.estado,
            Foto.fecha_registro
        )
        .filter(
            Foto.visita_id.in_(visit_ids),
            Foto.estado == "Aprobada"
        )
        .order_by(Foto.id_tipo_foto, Foto.fecha_registro.desc())
        .all()
    )

    from app.shared.azure_service import azure_service
    photos_by_visit: dict[int, list] = {}
    for p in photo_rows:
        vid = p[1]
        if vid not in photos_by_visit:
            photos_by_visit[vid] = []
        url = azure_service.get_sas_url(p[3]) if p[3] else None
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
    resolved_cliente_id = _get_cliente_id(current_user, cliente_id)

    route_ids = None
    if current_user.rol == "client":
        route_ids = client_route_ids(db, current_user)

    if not fecha_inicio:
        fecha_inicio_date = date.today()
    else:
        try:
            fecha_inicio_date = datetime.strptime(fecha_inicio, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido (YYYY-MM-DD)")

    if not fecha_fin:
        fecha_fin_date = fecha_inicio_date
    else:
        try:
            fecha_fin_date = datetime.strptime(fecha_fin, '%Y-%m-%d').date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Formato de fecha inválido (YYYY-MM-DD)")

    query = (
        db.query(
            Visita.id.label("id_visita"),
            Visita.fecha.label("fecha_visita"),
            Mercaderista.nombre.label("mercaderista"),
            PuntoInteres.id.label("punto_id"),
            PuntoInteres.nombre.label("punto_nombre"),
            PuntoInteres.departamento.label("departamento"),
            PuntoInteres.ciudad.label("ciudad"),
            func.coalesce(Ruta.nombre, "Sin ruta").label("ruta"),
            PuntoInteres.cadena.label("cadena"),
            Foto.id.label("id_foto"),
            Foto.blob_path.label("file_path"),
            Foto.id_tipo_foto.label("id_tipo_foto"),
            Foto.estado.label("foto_estado"),
            Cliente.nombre.label("cliente_nombre")
        )
        .join(Mercaderista, Visita.mercaderista_id == Mercaderista.id)
        .join(PuntoInteres, Visita.punto_id == PuntoInteres.id)
        .join(Cliente, Visita.id_cliente == Cliente.id)
        .join(Foto, (Foto.visita_id == Visita.id) & (Foto.estado == 'Aprobada') & (Foto.id_tipo_foto.in_([1, 2, 3, 4, 8, 9])))
        .outerjoin(RutaProgramacion, (RutaProgramacion.punto_id == PuntoInteres.id) & (RutaProgramacion.id_cliente == Visita.id_cliente))
        .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
        .filter(
            Visita.id_cliente == resolved_cliente_id,
            Visita.fecha >= fecha_inicio_date,
            Visita.fecha <= fecha_fin_date
        )
    )

    if route_ids is not None:
        if not route_ids:
            return {
                'success': True,
                'fecha_inicio': str(fecha_inicio_date),
                'fecha_fin': str(fecha_fin_date),
                'es_hoy': fecha_inicio_date == date.today() and fecha_fin_date == date.today(),
                'visitas': [],
                'total': 0,
                'filtros': {'rutas': [], 'cadenas': [], 'puntos': []}
            }
        sub_rp_filter = (
            db.query(RutaProgramacion.punto_id)
            .filter(
                RutaProgramacion.punto_id == Visita.punto_id,
                RutaProgramacion.id_cliente == Visita.id_cliente,
                RutaProgramacion.ruta_id.in_(route_ids)
            )
            .subquery()
        )
        query = query.filter(Visita.punto_id.in_(sub_rp_filter))

    if ruta:
        query = query.filter(func.coalesce(Ruta.nombre, "Sin ruta") == ruta)
    if cadena:
        query = query.filter(PuntoInteres.cadena == cadena)
    if punto_id:
        query = query.filter(PuntoInteres.id == punto_id)

    rows = query.order_by(Visita.id.desc(), Foto.id_tipo_foto, Foto.id.desc()).all()

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
    seen_fotos: dict[int, set[int]] = {}
    from app.shared.azure_service import azure_service
    _fast_sas_url = azure_service.get_sas_url

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

        if not visitas_dict[vid]['ruta'] and row[7]:
            visitas_dict[vid]['ruta'] = row[7]

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
                'file_path': url,
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

    base_filter_q = (
        db.query(
            PuntoInteres.id.label("punto_id"),
            PuntoInteres.nombre.label("punto_nombre"),
            PuntoInteres.cadena.label("cadena"),
            func.coalesce(Ruta.nombre, "Sin ruta").label("ruta")
        )
        .join(Visita, Visita.punto_id == PuntoInteres.id)
        .outerjoin(RutaProgramacion, (RutaProgramacion.punto_id == PuntoInteres.id) & (RutaProgramacion.id_cliente == Visita.id_cliente))
        .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
        .filter(
            Visita.id_cliente == resolved_cliente_id,
            Visita.fecha >= fecha_inicio_date,
            Visita.fecha <= fecha_fin_date,
            Visita.estado == "Revisado"
        )
    )
    if route_ids is not None:
        sub_rp_filter = (
            db.query(RutaProgramacion.punto_id)
            .filter(
                RutaProgramacion.punto_id == Visita.punto_id,
                RutaProgramacion.id_cliente == Visita.id_cliente,
                RutaProgramacion.ruta_id.in_(route_ids)
            )
            .subquery()
        )
        base_filter_q = base_filter_q.filter(Visita.punto_id.in_(sub_rp_filter))

    filter_rows = base_filter_q.distinct().all()

    rutas_list = sorted({r[3] for r in filter_rows if r[3]})
    cadenas_list = sorted({r[2] for r in filter_rows if r[2]})

    seen_p = set()
    puntos_list = []
    for r in filter_rows:
        if r[0] and r[0] not in seen_p:
            seen_p.add(r[0])
            puntos_list.append({'id': r[0], 'nombre': r[1] or ""})

    puntos_list.sort(key=lambda x: x['nombre'])

    return {
        'success': True,
        'fecha_inicio': str(fecha_inicio_date),
        'fecha_fin': str(fecha_fin_date),
        'es_hoy': fecha_inicio_date == date.today() and fecha_fin_date == date.today(),
        'visitas': list(visitas_dict.values()),
        'total': len(visitas_dict),
        'filtros': {
            'rutas': rutas_list,
            'cadenas': cadenas_list,
            'puntos': puntos_list,
        }
    }
