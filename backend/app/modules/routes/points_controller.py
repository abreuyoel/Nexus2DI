from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin, require_permission
from app.modules.auth.entities import Usuario
from app.modules.routes.entities import PuntoInteres
from app.modules.catalogues.entities import (
    TipoNegocio, SubtipoNegocio, Alcance, CanalVenta, DepartamentoGeo as Departamento, Ciudad,
)
from app.modules.clients.dto import PuntoInteresCreate, PuntoInteresUpdate, PuntoInteresResponse
from app.shared.audit_service import log_action
from app.core.request_ip import get_client_ip

router = APIRouter(prefix="/api/points", tags=["Puntos de Interés"])


def _build_base_query(db: Session, region=None, ciudad=None, cadena=None, jerarquia_n2=None, search=None):
    """Construye la query con filtros reutilizable para list y count."""
    query = db.query(PuntoInteres)
    if region:
        query = query.filter(PuntoInteres.departamento == region)
    if ciudad:
        query = query.filter(PuntoInteres.ciudad == ciudad)
    if cadena:
        query = query.filter(PuntoInteres.cadena == cadena)
    if jerarquia_n2:
        query = query.filter(PuntoInteres.jerarquia_n2 == jerarquia_n2)
    if search:
        query = query.filter(
            (PuntoInteres.nombre.ilike(f"%{search}%")) |
            (PuntoInteres.id.ilike(f"%{search}%"))
        )
    return query


@router.get("")
@router.get("/")
def list_points(
    region: Optional[str] = None,
    ciudad: Optional[str] = None,
    cadena: Optional[str] = None,
    jerarquia_n2: Optional[str] = None,
    search: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Devuelve lista paginada de puntos. Si include_total=true, responde {items, total}."""
    query = _build_base_query(db, region, ciudad, cadena, jerarquia_n2, search)
    total = query.count()
    items = query.order_by(PuntoInteres.id).offset(skip).limit(limit).all()
    return {"items": items, "total": total}


@router.post("")
@router.post("/", response_model=PuntoInteresResponse, status_code=201)
def create_point(
    data: PuntoInteresCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('points', 'write')),
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
    rows = db.query(Departamento.nombre).filter(Departamento.activo == True).order_by(Departamento.nombre).all()
    return [r[0] for r in rows]


@router.get("/cities/list")
def get_cities(
    departamento: Optional[str] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = db.query(Ciudad.nombre).filter(Ciudad.activo == True)
    if departamento:
        q = q.join(Departamento, Ciudad.departamento_id == Departamento.id).filter(
            Departamento.nombre == departamento
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


@router.get("/{point_id}", response_model=PuntoInteresResponse)
def get_point(
    point_id: str,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    punto = db.query(PuntoInteres).filter(PuntoInteres.id == point_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto no encontrado")
    return punto


@router.delete("/{point_id}")
def delete_point(
    point_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('points', 'delete')),
):
    punto = db.query(PuntoInteres).filter(PuntoInteres.id == point_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="Punto no encontrado")
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
    current_user: Usuario = Depends(require_permission('points', 'write')),
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
