from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Type
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin, require_permission
from app.modules.auth.entities import Usuario
from app.modules.routes.entities import PuntoInteres, Ruta
from app.modules.catalogues.entities import (
    TipoNegocio, SubtipoNegocio, Alcance, CanalVenta, DepartamentoGeo, Ciudad,
    Cuadrante, Servicio, Estado, Departamento, Categoria, SubCategoria,
    Productora, Marca, Presentacion, ClasificacionTamano, Producto,
)
from app.modules.catalogues.dto import (
    CatalogoCreate, CatalogoUpdate, CatalogoResponse,
    CiudadCreate, CiudadUpdate, CiudadResponse,
    CategoriaCreate, CategoriaUpdate, CategoriaResponse,
    SubCategoriaCreate, SubCategoriaUpdate, SubCategoriaResponse,
    CatalogoSimple, ProductoCreate, ProductoUpdate, ProductoResponse, ProductoListResponse,
    DepartamentoCreate, DepartamentoUpdate, MarcaCreate, MarcaUpdate,
    PresentacionCreate, PresentacionUpdate, TamanoCreate, TamanoUpdate,
)

router = APIRouter(tags=["Catálogos"])


# ════════════════════════════════════════════════════════════════════════════
# 1. Catálogos Generales (antes routes/catalogos.py)
# ════════════════════════════════════════════════════════════════════════════

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


@router.get("/api/catalogos/ciudades/", response_model=List[CiudadResponse])
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


@router.post("/api/catalogos/ciudades/", response_model=CiudadResponse, status_code=201)
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


@router.put("/api/catalogos/ciudades/{ciudad_id}", response_model=CiudadResponse)
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


@router.delete("/api/catalogos/ciudades/{ciudad_id}")
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


@router.get("/api/catalogos/estados", response_model=List[CatalogoResponse])
def get_estados(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    estados = db.query(Estado).order_by(Estado.nombre).all()
    if not estados:
        departamentos = db.query(DepartamentoGeo).filter(DepartamentoGeo.activo == True).all()
        for dep in departamentos:
            nuevo = Estado(nombre=dep.nombre, activo=True)
            db.add(nuevo)
        db.commit()
        estados = db.query(Estado).order_by(Estado.nombre).all()
        
    return estados


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


@router.get("/api/catalogos/{catalog}/", response_model=List[CatalogoResponse])
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


@router.post("/api/catalogos/{catalog}/", response_model=CatalogoResponse, status_code=201)
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


@router.put("/api/catalogos/{catalog}/{item_id}", response_model=CatalogoResponse)
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


@router.delete("/api/catalogos/{catalog}/{item_id}")
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


# ════════════════════════════════════════════════════════════════════════════
# 2. Catálogos de Productos (antes routes/productos_catalogos.py)
# ════════════════════════════════════════════════════════════════════════════

@router.get("/api/productos-catalogos/categorias", response_model=List[CategoriaResponse])
def get_categorias(db: Session = Depends(get_db)):
    return db.query(Categoria).all()


@router.post("/api/productos-catalogos/categorias", response_model=CategoriaResponse)
def create_categoria(
    cat: CategoriaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'write'))
):
    nueva = Categoria(**cat.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.put("/api/productos-catalogos/categorias/{id_categoria}", response_model=CategoriaResponse)
def update_categoria(
    id_categoria: int,
    cat: CategoriaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'write'))
):
    db_cat = db.query(Categoria).filter(Categoria.id_categoria == id_categoria).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    for key, value in cat.model_dump().items():
        setattr(db_cat, key, value)
        
    db.commit()
    db.refresh(db_cat)
    return db_cat


@router.delete("/api/productos-catalogos/categorias/{id_categoria}")
def delete_categoria(
    id_categoria: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'delete'))
):
    db_cat = db.query(Categoria).filter(Categoria.id_categoria == id_categoria).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    en_uso = db.query(SubCategoria).filter(SubCategoria.id_categoria == id_categoria).count()
    if en_uso > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar porque está en uso por {en_uso} subcategorías.")
        
    db.delete(db_cat)
    db.commit()
    return {"detail": "Categoría eliminada"}


@router.get("/api/productos-catalogos/subcategorias", response_model=List[SubCategoriaResponse])
def get_subcategorias(
    id_categoria: int = Query(None, description="Filtrar por id_categoria"),
    db: Session = Depends(get_db)
):
    query = db.query(SubCategoria)
    if id_categoria is not None:
        query = query.filter(SubCategoria.id_categoria == id_categoria)
    return query.all()


@router.post("/api/productos-catalogos/subcategorias", response_model=SubCategoriaResponse)
def create_subcategoria(
    subcat: SubCategoriaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'write'))
):
    nueva = SubCategoria(**subcat.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva


@router.put("/api/productos-catalogos/subcategorias/{id_subcategoria}", response_model=SubCategoriaResponse)
def update_subcategoria(
    id_subcategoria: int,
    subcat: SubCategoriaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'write'))
):
    db_subcat = db.query(SubCategoria).filter(SubCategoria.id_subcategoria == id_subcategoria).first()
    if not db_subcat:
        raise HTTPException(status_code=404, detail="SubCategoría no encontrada")
    
    for key, value in subcat.model_dump().items():
        setattr(db_subcat, key, value)
        
    db.commit()
    db.refresh(db_subcat)
    return db_subcat


@router.delete("/api/productos-catalogos/subcategorias/{id_subcategoria}")
def delete_subcategoria(
    id_subcategoria: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'delete'))
):
    db_subcat = db.query(SubCategoria).filter(SubCategoria.id_subcategoria == id_subcategoria).first()
    if not db_subcat:
        raise HTTPException(status_code=404, detail="SubCategoría no encontrada")
    
    en_uso = db.query(Producto).filter(Producto.id_subcategoria == id_subcategoria).count()
    if en_uso > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar porque está en uso por {en_uso} productos.")

    db.delete(db_subcat)
    db.commit()
    return {"detail": "SubCategoría eliminada"}


@router.get("/api/productos-catalogos/marcas", response_model=List[CatalogoSimple])
def get_marcas(id_productora: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Marca)
    if id_productora is not None:
        q = q.filter(Marca.id_productora == id_productora)
    return [CatalogoSimple(id=m.id_marca, nombre=m.nombre, id_productora=m.id_productora)
            for m in q.order_by(Marca.nombre).all()]


@router.get("/api/productos-catalogos/productoras", response_model=List[CatalogoSimple])
def get_productoras(db: Session = Depends(get_db)):
    return [CatalogoSimple(id=p.id_productora, nombre=p.nombre)
            for p in db.query(Productora).order_by(Productora.nombre).all()]


@router.get("/api/productos-catalogos/presentaciones", response_model=List[CatalogoSimple])
def get_presentaciones(db: Session = Depends(get_db)):
    return [CatalogoSimple(id=p.id_presentacion, nombre=p.nombre)
            for p in db.query(Presentacion).order_by(Presentacion.nombre).all()]


@router.get("/api/productos-catalogos/departamentos", response_model=List[CatalogoSimple])
def get_departamentos_prod(db: Session = Depends(get_db)):
    return [CatalogoSimple(id=d.id_departamento, nombre=d.nombre)
            for d in db.query(Departamento).order_by(Departamento.nombre).all()]


@router.get("/api/productos-catalogos/tamanos", response_model=List[CatalogoSimple])
def get_tamanos(db: Session = Depends(get_db)):
    return [CatalogoSimple(id=t.id, nombre=t.nombre)
            for t in db.query(ClasificacionTamano).order_by(ClasificacionTamano.nombre).all()]


@router.post("/api/productos-catalogos/tamanos", response_model=CatalogoSimple, status_code=201)
def create_tamano(data: TamanoCreate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    t = ClasificacionTamano(nombre=data.nombre.strip())
    db.add(t); db.commit(); db.refresh(t)
    return CatalogoSimple(id=t.id, nombre=t.nombre)


@router.put("/api/productos-catalogos/tamanos/{id_tamano}", response_model=CatalogoSimple)
def update_tamano(id_tamano: int, data: TamanoUpdate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    t = db.query(ClasificacionTamano).filter(ClasificacionTamano.id == id_tamano).first()
    if not t:
        raise HTTPException(404, "Tamaño no encontrado")
    if data.nombre is not None:
        t.nombre = data.nombre.strip()
    db.commit(); db.refresh(t)
    return CatalogoSimple(id=t.id, nombre=t.nombre)


@router.delete("/api/productos-catalogos/tamanos/{id_tamano}")
def delete_tamano(id_tamano: int, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'delete'))):
    t = db.query(ClasificacionTamano).filter(ClasificacionTamano.id == id_tamano).first()
    if not t:
        raise HTTPException(404, "Tamaño no encontrado")
    en_uso = db.query(Producto).filter(Producto.id_clasificacion_tamano == id_tamano).count()
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} productos.")
    db.delete(t); db.commit()
    return {"detail": "Tamaño eliminado"}


@router.post("/api/productos-catalogos/departamentos", response_model=CatalogoSimple, status_code=201)
def create_departamento_prod(data: DepartamentoCreate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    d = Departamento(nombre=data.nombre.strip())
    db.add(d); db.commit(); db.refresh(d)
    return CatalogoSimple(id=d.id_departamento, nombre=d.nombre)


@router.put("/api/productos-catalogos/departamentos/{id_departamento}", response_model=CatalogoSimple)
def update_departamento_prod(id_departamento: int, data: DepartamentoUpdate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    d = db.query(Departamento).filter(Departamento.id_departamento == id_departamento).first()
    if not d:
        raise HTTPException(404, "Departamento no encontrado")
    if data.nombre is not None:
        d.nombre = data.nombre.strip()
    db.commit(); db.refresh(d)
    return CatalogoSimple(id=d.id_departamento, nombre=d.nombre)


@router.delete("/api/productos-catalogos/departamentos/{id_departamento}")
def delete_departamento_prod(id_departamento: int, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'delete'))):
    d = db.query(Departamento).filter(Departamento.id_departamento == id_departamento).first()
    if not d:
        raise HTTPException(404, "Departamento no encontrado")
    en_uso = db.query(Categoria).filter(Categoria.id_departamento == id_departamento).count()
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} categorías.")
    db.delete(d); db.commit()
    return {"detail": "Departamento eliminado"}


@router.post("/api/productos-catalogos/marcas", response_model=CatalogoSimple, status_code=201)
def create_marca(data: MarcaCreate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    m = Marca(nombre=data.nombre.strip(), id_productora=data.id_productora)
    db.add(m); db.commit(); db.refresh(m)
    return CatalogoSimple(id=m.id_marca, nombre=m.nombre, id_productora=m.id_productora)


@router.put("/api/productos-catalogos/marcas/{id_marca}", response_model=CatalogoSimple)
def update_marca(id_marca: int, data: MarcaUpdate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    m = db.query(Marca).filter(Marca.id_marca == id_marca).first()
    if not m:
        raise HTTPException(404, "Marca no encontrada")
    if data.nombre is not None:
        m.nombre = data.nombre.strip()
    if data.id_productora is not None:
        m.id_productora = data.id_productora
    db.commit(); db.refresh(m)
    return CatalogoSimple(id=m.id_marca, nombre=m.nombre, id_productora=m.id_productora)


@router.delete("/api/productos-catalogos/marcas/{id_marca}")
def delete_marca(id_marca: int, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'delete'))):
    m = db.query(Marca).filter(Marca.id_marca == id_marca).first()
    if not m:
        raise HTTPException(404, "Marca no encontrada")
    en_uso = db.query(Producto).filter(Producto.id_marca == id_marca).count()
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} productos.")
    db.delete(m); db.commit()
    return {"detail": "Marca eliminada"}


@router.post("/api/productos-catalogos/presentaciones", response_model=CatalogoSimple, status_code=201)
def create_presentacion(data: PresentacionCreate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    p = Presentacion(nombre=data.nombre.strip(), clasificacion_tamanos=data.clasificacion_tamanos)
    db.add(p); db.commit(); db.refresh(p)
    return CatalogoSimple(id=p.id_presentacion, nombre=p.nombre)


@router.put("/api/productos-catalogos/presentaciones/{id_presentacion}", response_model=CatalogoSimple)
def update_presentacion(id_presentacion: int, data: PresentacionUpdate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    p = db.query(Presentacion).filter(Presentacion.id_presentacion == id_presentacion).first()
    if not p:
        raise HTTPException(404, "Presentación no encontrada")
    if data.nombre is not None:
        p.nombre = data.nombre.strip()
    if data.clasificacion_tamanos is not None:
        p.clasificacion_tamanos = data.clasificacion_tamanos
    db.commit(); db.refresh(p)
    return CatalogoSimple(id=p.id_presentacion, nombre=p.nombre)


@router.delete("/api/productos-catalogos/presentaciones/{id_presentacion}")
def delete_presentacion(id_presentacion: int, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'delete'))):
    p = db.query(Presentacion).filter(Presentacion.id_presentacion == id_presentacion).first()
    if not p:
        raise HTTPException(404, "Presentación no encontrada")
    en_uso = db.query(Producto).filter(Producto.id_presentacion == id_presentacion).count()
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} productos.")
    db.delete(p); db.commit()
    return {"detail": "Presentación eliminada"}


# ════════════════════════════════════════════════════════════════════════════
# 3. Productos (antes en productos_catalogos.py)
# ════════════════════════════════════════════════════════════════════════════

def _producto_join(db: Session):
    return (
        db.query(Producto, SubCategoria, Categoria, Marca, Productora, Presentacion, Departamento, ClasificacionTamano)
        .outerjoin(SubCategoria, SubCategoria.id_subcategoria == Producto.id_subcategoria)
        .outerjoin(Categoria, Categoria.id_categoria == SubCategoria.id_categoria)
        .outerjoin(Marca, Marca.id_marca == Producto.id_marca)
        .outerjoin(Productora, Productora.id_productora == Marca.id_productora)
        .outerjoin(Presentacion, Presentacion.id_presentacion == Producto.id_presentacion)
        .outerjoin(Departamento, Departamento.id_departamento == Categoria.id_departamento)
        .outerjoin(ClasificacionTamano, ClasificacionTamano.id == Producto.id_clasificacion_tamano)
    )


def _producto_resp(p, sc, cat, m, pr, pres, dep, tam) -> ProductoResponse:
    return ProductoResponse(
        id=p.id_producto, producto_gu=p.producto_gu, cod_prod=p.cod_prod,
        descripcion_bi=p.descripcion_bi, gramos=p.gramos,
        inagotable=p.inagotable, comentario=p.comentario,
        id_subcategoria=p.id_subcategoria, subcategoria=(sc.nombre if sc else None),
        id_categoria=(cat.id_categoria if cat else None), categoria=(cat.nombre if cat else None),
        id_marca=p.id_marca, marca=(m.nombre if m else None),
        fabricante=(pr.nombre if pr else None),
        id_presentacion=p.id_presentacion, presentacion=(pres.nombre if pres else None),
        id_departamento=(dep.id_departamento if dep else None),
        departamento=(dep.nombre if dep else None),
        id_clasificacion_tamano=(tam.id if tam else None),
        tamano=(tam.nombre if tam else None),
    )


@router.get("/api/productos-catalogos/productos", response_model=ProductoListResponse)
def list_productos(
    busqueda: Optional[str] = Query(None),
    id_categoria: Optional[int] = Query(None),
    id_subcategoria: Optional[int] = Query(None),
    id_marca: Optional[int] = Query(None),
    skip: int = 0,
    limit: int = 25,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    q = _producto_join(db)
    if busqueda:
        like = f"%{busqueda}%"
        q = q.filter((Producto.producto_gu.ilike(like)) | (Producto.cod_prod.ilike(like)))
    if id_categoria is not None:
        q = q.filter(SubCategoria.id_categoria == id_categoria)
    if id_subcategoria is not None:
        q = q.filter(Producto.id_subcategoria == id_subcategoria)
    if id_marca is not None:
        q = q.filter(Producto.id_marca == id_marca)
    total = q.count()
    limit = max(1, limit)
    rows = q.order_by(Producto.producto_gu).offset(skip).limit(limit).all()
    return ProductoListResponse(
        total=total, pagina=(skip // limit + 1),
        items=[_producto_resp(*r) for r in rows],
    )


@router.get("/api/productos-catalogos/productos/{producto_id}", response_model=ProductoResponse)
def get_producto(producto_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    row = _producto_join(db).filter(Producto.id_producto == producto_id).first()
    if not row:
        raise HTTPException(404, "Producto no encontrado")
    return _producto_resp(*row)


@router.post("/api/productos-catalogos/productos", response_model=ProductoResponse, status_code=201)
def create_producto(data: ProductoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(require_permission('products', 'write'))):
    p = Producto(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return get_producto(p.id_producto, db, current_user)


@router.put("/api/productos-catalogos/productos/{producto_id}", response_model=ProductoResponse)
def update_producto(producto_id: int, data: ProductoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(require_permission('products', 'write'))):
    p = db.query(Producto).filter(Producto.id_producto == producto_id).first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    return get_producto(producto_id, db, current_user)


@router.delete("/api/productos-catalogos/productos/{producto_id}")
def delete_producto(producto_id: int, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'delete'))):
    p = db.query(Producto).filter(Producto.id_producto == producto_id).first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    db.delete(p)
    db.commit()
    return {"detail": "Producto eliminado"}
