from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Type
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin, require_permission
from app.models.user import Usuario
from app.models.punto import PuntoInteres
from app.models.ruta import Ruta
from app.models.catalogo import (
    TipoNegocio, SubtipoNegocio, Alcance, CanalVenta, DepartamentoGeo, Ciudad,
    Cuadrante, Servicio,
)
from app.schemas.catalogo import (
    CatalogoCreate, CatalogoUpdate, CatalogoResponse,
    CiudadCreate, CiudadUpdate, CiudadResponse,
)

router = APIRouter(prefix="/api/catalogos", tags=["Catálogos"])


# Mapping: catalog_key → (usage_model, usage_column, sample_column)
# usage_model/usage_column = dónde se referencia el valor (para validar borrado/rename).
# sample_column = columna a mostrar como ejemplo de registros que lo usan.
CATALOG_USAGE = {
    "tipo-negocio": (PuntoInteres, PuntoInteres.jerarquia_n2, PuntoInteres.id),
    "subtipo-negocio": (PuntoInteres, PuntoInteres.jerarquia_n2_2, PuntoInteres.id),
    "alcance": (PuntoInteres, PuntoInteres.nivel_de_alcance, PuntoInteres.id),
    "canal-venta": (PuntoInteres, PuntoInteres.cadena, PuntoInteres.id),
    "departamentos": (PuntoInteres, PuntoInteres.departamento, PuntoInteres.id),
    "cuadrantes": (Ruta, Ruta.cuadrante, Ruta.nombre),
    "servicios": (Ruta, Ruta.servicio, Ruta.nombre),
}


def _count_usage(db: Session, usage_model, usage_column, value: str) -> int:
    return db.query(usage_model).filter(usage_column == value).count()


def _list_usage_ids(db: Session, usage_column, sample_column, value: str, limit: int = 5) -> list[str]:
    rows = db.query(sample_column).filter(usage_column == value).limit(limit).all()
    return [r[0] for r in rows]


def _ciudad_to_response(c: Ciudad) -> dict:
    return {
        "id": c.id,
        "nombre": c.nombre,
        "activo": c.activo,
        "departamento_id": c.departamento_id,
        "departamento_nombre": c.departamento_geo.nombre if c.departamento_geo else None,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Ciudades — registradas ANTES del genérico para que /ciudades/ no colisione
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/ciudades/", response_model=List[CiudadResponse])
def list_ciudades(
    departamento_id: Optional[int] = None,
    departamento: Optional[str] = None,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = db.query(Ciudad).join(DepartamentoGeo, Ciudad.departamento_id == DepartamentoGeo.id)
    if departamento_id is not None:
        q = q.filter(Ciudad.departamento_id == departamento_id)
    if departamento:
        q = q.filter(DepartamentoGeo.nombre == departamento)
    if activo is not None:
        q = q.filter(Ciudad.activo == activo)
    return [_ciudad_to_response(c) for c in q.order_by(Ciudad.nombre).all()]


@router.post("/ciudades/", response_model=CiudadResponse, status_code=201)
def create_ciudad(
    data: CiudadCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('points', 'write')),
):
    dep = db.query(DepartamentoGeo).filter(DepartamentoGeo.id == data.departamento_id).first()
    if not dep:
        raise HTTPException(status_code=404, detail="Departamento no existe")
    nombre = data.nombre.strip()
    exists = db.query(Ciudad).filter(
        Ciudad.departamento_id == data.departamento_id,
        Ciudad.nombre == nombre,
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail=f"Ya existe '{nombre}' en {dep.nombre}")
    c = Ciudad(nombre=nombre, departamento_id=data.departamento_id, activo=data.activo)
    db.add(c)
    db.commit()
    db.refresh(c)
    return _ciudad_to_response(c)


@router.put("/ciudades/{ciudad_id}", response_model=CiudadResponse)
def update_ciudad(
    ciudad_id: int,
    data: CiudadUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('points', 'write')),
):
    c = db.query(Ciudad).filter(Ciudad.id == ciudad_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")

    old_nombre = c.nombre
    nuevo_nombre = data.nombre.strip() if data.nombre is not None else old_nombre
    nuevo_dep_id = data.departamento_id if data.departamento_id is not None else c.departamento_id

    if nuevo_dep_id != c.departamento_id:
        dep = db.query(DepartamentoGeo).filter(DepartamentoGeo.id == nuevo_dep_id).first()
        if not dep:
            raise HTTPException(status_code=404, detail="Departamento no existe")

    if nuevo_nombre != old_nombre or nuevo_dep_id != c.departamento_id:
        clash = db.query(Ciudad).filter(
            Ciudad.departamento_id == nuevo_dep_id,
            Ciudad.nombre == nuevo_nombre,
            Ciudad.id != ciudad_id,
        ).first()
        if clash:
            raise HTTPException(status_code=409, detail="Ya existe esa ciudad en el departamento")

    if nuevo_nombre != old_nombre:
        db.query(PuntoInteres).filter(PuntoInteres.ciudad == old_nombre).update(
            {PuntoInteres.ciudad: nuevo_nombre}, synchronize_session=False
        )

    c.nombre = nuevo_nombre
    c.departamento_id = nuevo_dep_id
    if data.activo is not None:
        c.activo = data.activo

    db.commit()
    db.refresh(c)
    return _ciudad_to_response(c)


@router.delete("/ciudades/{ciudad_id}")
def delete_ciudad(
    ciudad_id: int,
    force: bool = Query(False),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('points', 'delete')),
):
    c = db.query(Ciudad).filter(Ciudad.id == ciudad_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Ciudad no encontrada")

    usage = _count_usage(db, PuntoInteres, PuntoInteres.ciudad, c.nombre)
    if usage > 0 and not force:
        sample = _list_usage_ids(db, PuntoInteres.ciudad, PuntoInteres.id, c.nombre)
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"No se puede eliminar '{c.nombre}' porque está siendo usada por {usage} punto(s) de venta. Inactive o elimine esos PDV primero, o use ?force=true.",
                "usage_count": usage,
                "sample_pdv_ids": sample,
            },
        )

    db.delete(c)
    db.commit()
    return {"message": "Eliminada", "usage_count": usage, "force": force}


# ─────────────────────────────────────────────────────────────────────────────
# Estados - registrados antes del genérico
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/estados", response_model=List[CatalogoResponse])
def get_estados(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    from app.models.catalogo import Estado
    estados = db.query(Estado).order_by(Estado.nombre).all()
    if not estados:
        departamentos = db.query(DepartamentoGeo).filter(DepartamentoGeo.activo == True).all()
        for dep in departamentos:
            nuevo = Estado(nombre=dep.nombre, activo=True)
            db.add(nuevo)
        db.commit()
        estados = db.query(Estado).order_by(Estado.nombre).all()
        
    return estados


# ─────────────────────────────────────────────────────────────────────────────
# Catálogos genéricos: tipo-negocio, subtipo-negocio, alcance, canal-venta,
# departamentos. Usa columna correspondiente de PuntoInteres para validar uso.
# ─────────────────────────────────────────────────────────────────────────────

GENERIC_CATALOGS: dict[str, Type] = {
    "tipo-negocio": TipoNegocio,
    "subtipo-negocio": SubtipoNegocio,
    "alcance": Alcance,
    "canal-venta": CanalVenta,
    "departamentos": DepartamentoGeo,
    "cuadrantes": Cuadrante,
    "servicios": Servicio,
}


def _resolve_generic(catalog: str) -> Type:
    if catalog not in GENERIC_CATALOGS:
        raise HTTPException(status_code=404, detail=f"Catálogo '{catalog}' no existe")
    return GENERIC_CATALOGS[catalog]


@router.get("/{catalog}/", response_model=List[CatalogoResponse])
def list_catalog(
    catalog: str,
    activo: Optional[bool] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    Model = _resolve_generic(catalog)
    q = db.query(Model)
    if activo is not None:
        q = q.filter(Model.activo == activo)
    return q.order_by(Model.nombre).all()


@router.post("/{catalog}/", response_model=CatalogoResponse, status_code=201)
def create_catalog_item(
    catalog: str,
    data: CatalogoCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('points', 'write')),
):
    Model = _resolve_generic(catalog)
    nombre = data.nombre.strip()
    if db.query(Model).filter(Model.nombre == nombre).first():
        raise HTTPException(status_code=409, detail=f"Ya existe '{nombre}'")
    item = Model(nombre=nombre, activo=data.activo)
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{catalog}/{item_id}", response_model=CatalogoResponse)
def update_catalog_item(
    catalog: str,
    item_id: int,
    data: CatalogoUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('points', 'write')),
):
    Model = _resolve_generic(catalog)
    item = db.query(Model).filter(Model.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")

    old_nombre = item.nombre

    if data.nombre is not None:
        nuevo = data.nombre.strip()
        if nuevo != old_nombre:
            if db.query(Model).filter(Model.nombre == nuevo).first():
                raise HTTPException(status_code=409, detail=f"Ya existe '{nuevo}'")
            usage_model, usage_column, _sample = CATALOG_USAGE[catalog]
            db.query(usage_model).filter(usage_column == old_nombre).update(
                {usage_column: nuevo}, synchronize_session=False
            )
            item.nombre = nuevo

    if data.activo is not None:
        item.activo = data.activo

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{catalog}/{item_id}")
def delete_catalog_item(
    catalog: str,
    item_id: int,
    force: bool = Query(False, description="Si true, elimina aunque hayan PDV referenciados"),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_permission('points', 'delete')),
):
    Model = _resolve_generic(catalog)
    item = db.query(Model).filter(Model.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="No encontrado")

    usage_model, usage_column, sample_column = CATALOG_USAGE[catalog]
    usage = _count_usage(db, usage_model, usage_column, item.nombre)
    if usage > 0 and not force:
        sample = _list_usage_ids(db, usage_column, sample_column, item.nombre)
        unidad = "ruta(s)" if usage_model is Ruta else "punto(s) de venta"
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"No se puede eliminar '{item.nombre}' porque está siendo usado por {usage} {unidad}. Reasigne o elimine esos registros primero, o use ?force=true para eliminar de todos modos (quedarán sin este valor).",
                "usage_count": usage,
                "sample_pdv_ids": sample,
            },
        )

    db.delete(item)
    db.commit()
    return {"message": "Eliminado", "usage_count": usage, "force": force}
