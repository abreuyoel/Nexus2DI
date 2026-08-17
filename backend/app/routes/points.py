from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Union
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin, require_permission
from app.models.user import Usuario
from app.models.punto import PuntoInteres
from app.models.catalogo import (
    TipoNegocio, SubtipoNegocio, Alcance, CanalVenta, DepartamentoGeo, Ciudad,
)
from app.schemas.cliente import PuntoInteresCreate, PuntoInteresUpdate, PuntoInteresResponse, PuntoInteresClienteResponse
from app.services.audit_service import log_action
from app.core.request_ip import get_client_ip

router = APIRouter(prefix="/api/points", tags=["Puntos de Interés"])


def _apply_client_pdv_filter(query, current_user: Usuario, db: Session):
    """Si el usuario es cliente puro (id_rol=1), restringe la consulta de
    PuntoInteres a los que están en RUTA_PROGRAMACION para su id_cliente
    (USUARIOS.id_perfil). Retorna la query sin modificar para otros roles."""
    if current_user.rol != "client" or not current_user.id_perfil:
        return query
    ids_pdv = db.execute(text("""
        SELECT DISTINCT rp.id_punto_interes
        FROM RUTA_PROGRAMACION rp
        WHERE rp.id_cliente = :cid AND rp.activa = 1
    """), {"cid": int(current_user.id_perfil)}).scalars().all()
    if not ids_pdv:
        return query.filter(PuntoInteres.id == None)  # noqa: E711
    return query.filter(PuntoInteres.id.in_(ids_pdv))


@router.get("/", response_model=List[Union[PuntoInteresResponse, PuntoInteresClienteResponse]])
def list_points(
    region: Optional[str] = None,
    ciudad: Optional[str] = None,
    cadena: Optional[str] = None,
    jerarquia_n2: Optional[str] = None,
    jerarquia_n2_2: Optional[str] = None,
    nivel_de_alcance: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    query = db.query(PuntoInteres)
    # Filtrar PDVs por cliente si es rol 'client'
    query = _apply_client_pdv_filter(query, current_user, db)
    if region:
        query = query.filter(PuntoInteres.departamento == region)
    if ciudad:
        query = query.filter(PuntoInteres.ciudad == ciudad)
    if cadena:
        query = query.filter(PuntoInteres.cadena == cadena)
    if jerarquia_n2:
        query = query.filter(PuntoInteres.jerarquia_n2 == jerarquia_n2)
    if jerarquia_n2_2:
        query = query.filter(PuntoInteres.jerarquia_n2_2 == jerarquia_n2_2)
    if nivel_de_alcance:
        query = query.filter(PuntoInteres.nivel_de_alcance == nivel_de_alcance)
    if search:
        query = query.filter(
            PuntoInteres.nombre.ilike(f"%{search}%") |
            PuntoInteres.id.ilike(f"%{search}%")
        )
    rows = query.order_by(PuntoInteres.nombre).offset(skip).limit(limit).all()
    # El cliente no recibe coordenadas geográficas
    if current_user.rol == "client":
        return [PuntoInteresClienteResponse.model_validate(r) for r in rows]
    return rows


@router.post("/", response_model=PuntoInteresResponse, status_code=201)
def create_point(
    data: PuntoInteresCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('points', 'write', fallback_roles=("admin", "analyst", "atc"))),
):
    punto = PuntoInteres(**data.model_dump())
    db.add(punto)
    db.flush()

    log_action(db, action="CREATE_POINT", entity_type="PuntoInteres",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=punto.id, entity_name=getattr(punto, 'nombre', str(punto.id)),
               changes=data.model_dump())
    db.commit()
    db.refresh(punto)
    return punto


@router.get("/regions/list")
def get_regions(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    rows = db.query(DepartamentoGeo.nombre).filter(DepartamentoGeo.activo == True).order_by(DepartamentoGeo.nombre).all()
    return [r[0] for r in rows]


@router.get("/cities/list")
def get_cities(
    departamento: Optional[str] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Lista ciudades activas. Si se pasa ?departamento=Nombre devuelve sólo las
    de ese departamento."""
    q = db.query(Ciudad.nombre).filter(Ciudad.activo == True)
    if departamento:
        q = q.join(DepartamentoGeo, Ciudad.departamento_id == DepartamentoGeo.id).filter(
            DepartamentoGeo.nombre == departamento
        )
    rows = q.order_by(Ciudad.nombre).all()
    return [r[0] for r in rows]


@router.get("/chains/list")
def get_chains(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    rows = db.query(CanalVenta.nombre).filter(CanalVenta.activo == True).order_by(CanalVenta.nombre).all()
    return [r[0] for r in rows]


@router.get("/jerarquia_n2/list")
def get_jerarquia_n2(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    rows = db.query(TipoNegocio.nombre).filter(TipoNegocio.activo == True).order_by(TipoNegocio.nombre).all()
    return [r[0] for r in rows]


@router.get("/jerarquia_n2_2/list")
def get_jerarquia_n2_2(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    rows = db.query(SubtipoNegocio.nombre).filter(SubtipoNegocio.activo == True).order_by(SubtipoNegocio.nombre).all()
    return [r[0] for r in rows]


@router.get("/nivel_alcance/list")
def get_nivel_alcance(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    rows = db.query(Alcance.nombre).filter(Alcance.activo == True).order_by(Alcance.nombre).all()
    return [r[0] for r in rows]


@router.get("/count")
def count_points(
    region: Optional[str] = None,
    ciudad: Optional[str] = None,
    cadena: Optional[str] = None,
    jerarquia_n2: Optional[str] = None,
    jerarquia_n2_2: Optional[str] = None,
    nivel_de_alcance: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    query = db.query(PuntoInteres)
    query = _apply_client_pdv_filter(query, current_user, db)
    if region:
        query = query.filter(PuntoInteres.departamento == region)
    if ciudad:
        query = query.filter(PuntoInteres.ciudad == ciudad)
    if cadena:
        query = query.filter(PuntoInteres.cadena == cadena)
    if jerarquia_n2:
        query = query.filter(PuntoInteres.jerarquia_n2 == jerarquia_n2)
    if jerarquia_n2_2:
        query = query.filter(PuntoInteres.jerarquia_n2_2 == jerarquia_n2_2)
    if nivel_de_alcance:
        query = query.filter(PuntoInteres.nivel_de_alcance == nivel_de_alcance)
    if search:
        query = query.filter(
            PuntoInteres.nombre.ilike(f"%{search}%") |
            PuntoInteres.id.ilike(f"%{search}%")
        )
    return {"total": query.count()}


@router.get("/{point_id}")
def get_point(
    point_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    punto = db.query(PuntoInteres).filter(PuntoInteres.id == point_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto no encontrado")
    # El cliente no recibe coordenadas geográficas
    if current_user.rol == "client":
        return PuntoInteresClienteResponse.model_validate(punto)
    return punto


@router.delete("/{point_id}")
def delete_point(
    point_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('points', 'delete', fallback_roles=("admin", "analyst", "atc"))),
):
    punto = db.query(PuntoInteres).filter(PuntoInteres.id == point_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto no encontrado")

    # Sin este chequeo, el DELETE le pega directo a alguna de las llaves
    # foráneas reales que apuntan a PUNTOS_INTERES1.identificador y SQL
    # Server lo rechaza -- eso salía como 500 sin manejar. Antes solo se
    # revisaba VISITAS_MERCADERISTA; RUTA_PROGRAMACION (el PDV programado en
    # una ruta activa) es la más común y quedaba sin cubrir.
    #
    # OJO: ACTIVACIONES está en el modelo SQLAlchemy (app/models/activacion.py)
    # pero la tabla NUNCA se creó en la base real -- confirmado por el error
    # "Invalid object name 'ACTIVACIONES'" en producción. Por eso NO se
    # revisa acá aunque tenga FK declarada; si en el futuro se crea la tabla
    # de verdad, hay que agregarla de nuevo a esta lista.
    from sqlalchemy import text
    tablas_bloqueantes = [
        ("VISITAS_MERCADERISTA", "identificador_punto_interes", "visitas registradas"),
        ("RUTA_PROGRAMACION", "id_punto_interes", "programación de rutas"),
        ("FRECUENCIAS_PDVS_CLIENTE", "id_punto_interes", "frecuencias de visita configuradas"),
    ]
    motivos = []
    for tabla, columna, etiqueta in tablas_bloqueantes:
        existe = db.execute(
            text(f"SELECT TOP 1 1 FROM {tabla} WHERE {columna} = :pid"),
            {"pid": point_id},
        ).first()
        if existe:
            motivos.append(etiqueta)
    if motivos:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: este punto de venta tiene {', '.join(motivos)}. "
                   "Desactivalo en la programación de rutas en vez de borrarlo.",
        )

    nombre = getattr(punto, 'nombre', point_id)
    db.delete(punto)

    log_action(db, action="DELETE_POINT", entity_type="PuntoInteres",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=point_id, entity_name=nombre)
    db.commit()
    return {"message": "Punto eliminado"}


@router.put("/{point_id}", response_model=PuntoInteresResponse)
def update_point(
    point_id: str,
    data: PuntoInteresUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('points', 'write', fallback_roles=("admin", "analyst", "atc"))),
):
    punto = db.query(PuntoInteres).filter(PuntoInteres.id == point_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto no encontrado")
    changes = data.model_dump(exclude_none=True)
    for key, value in changes.items():
        setattr(punto, key, value)

    log_action(db, action="UPDATE_POINT", entity_type="PuntoInteres",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=point_id, entity_name=getattr(punto, 'nombre', point_id),
               changes=changes)
    db.commit()
    db.refresh(punto)
    return punto


@router.post("/merge-and-delete")
def merge_and_delete_point_endpoint(
    payload: dict,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('points', 'delete', fallback_roles=("admin", "analyst"))),
):
    pdv_eliminar = payload.get("pdv_id_eliminar")
    pdv_destino = payload.get("pdv_id_destino")

    if not pdv_eliminar:
        raise HTTPException(status_code=400, detail="Debe especificar 'pdv_id_eliminar'")

    from app.scripts.merge_and_delete_pdv import reasignar_y_eliminar_pdv
    try:
        res = reasignar_y_eliminar_pdv(db, pdv_eliminar, pdv_destino)
        log_action(db, action="MERGE_DELETE_POINT", entity_type="PuntoInteres",
                   user_id=current_user.id, username=current_user.username, rol=current_user.rol,
                   ip_address=get_client_ip(request),
                   entity_id=pdv_eliminar, entity_name=pdv_eliminar,
                   changes=res)
        return res
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al reasignar y eliminar PDV: {str(e)}")
