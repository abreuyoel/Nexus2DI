from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin, require_permission
from app.models.user import Usuario
from app.models.producto import (
    Categoria, SubCategoria, Producto, Marca, Productora, Presentacion, Departamento,
    ClasificacionTamano,
)
from app.schemas.producto_catalogo import (
    CategoriaCreate, CategoriaUpdate, CategoriaResponse,
    SubCategoriaCreate, SubCategoriaUpdate, SubCategoriaResponse,
    CatalogoSimple, ProductoCreate, ProductoUpdate, ProductoResponse, ProductoListResponse,
    DepartamentoCreate, DepartamentoUpdate, MarcaCreate, MarcaUpdate,
    PresentacionCreate, PresentacionUpdate, TamanoCreate, TamanoUpdate,
)

router = APIRouter(prefix="/api/productos-catalogos", tags=["Catálogos de Productos"])

# =======================
# CATEGORIAS
# =======================

@router.get("/categorias", response_model=List[CategoriaResponse])
def get_categorias(db: Session = Depends(get_db)):
    """Listar todas las categorías de productos."""
    return db.query(Categoria).all()

@router.post("/categorias", response_model=CategoriaResponse)
def create_categoria(
    cat: CategoriaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'write'))
):
    """Crear una nueva categoría de producto."""
    nueva = Categoria(**cat.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

@router.put("/categorias/{id_categoria}", response_model=CategoriaResponse)
def update_categoria(
    id_categoria: int,
    cat: CategoriaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'write'))
):
    """Actualizar una categoría de producto existente."""
    db_cat = db.query(Categoria).filter(Categoria.id_categoria == id_categoria).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    for key, value in cat.model_dump().items():
        setattr(db_cat, key, value)
        
    db.commit()
    db.refresh(db_cat)
    return db_cat

@router.delete("/categorias/{id_categoria}")
def delete_categoria(
    id_categoria: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'delete'))
):
    """Eliminar una categoría de producto."""
    db_cat = db.query(Categoria).filter(Categoria.id_categoria == id_categoria).first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    # Verificar si está en uso por subcategorías
    en_uso = db.query(SubCategoria).filter(SubCategoria.id_categoria == id_categoria).count()
    if en_uso > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar porque está en uso por {en_uso} subcategorías.")
        
    db.delete(db_cat)
    db.commit()
    return {"detail": "Categoría eliminada"}

# =======================
# SUBCATEGORIAS
# =======================

@router.get("/subcategorias", response_model=List[SubCategoriaResponse])
def get_subcategorias(
    id_categoria: int = Query(None, description="Filtrar por id_categoria"),
    db: Session = Depends(get_db)
):
    """Listar subcategorías, opcionalmente filtradas por categoría."""
    query = db.query(SubCategoria)
    if id_categoria is not None:
        query = query.filter(SubCategoria.id_categoria == id_categoria)
    return query.all()

@router.post("/subcategorias", response_model=SubCategoriaResponse)
def create_subcategoria(
    subcat: SubCategoriaCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'write'))
):
    """Crear una nueva subcategoría de producto."""
    nueva = SubCategoria(**subcat.model_dump())
    db.add(nueva)
    db.commit()
    db.refresh(nueva)
    return nueva

@router.put("/subcategorias/{id_subcategoria}", response_model=SubCategoriaResponse)
def update_subcategoria(
    id_subcategoria: int,
    subcat: SubCategoriaUpdate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'write'))
):
    """Actualizar una subcategoría de producto."""
    db_subcat = db.query(SubCategoria).filter(SubCategoria.id_subcategoria == id_subcategoria).first()
    if not db_subcat:
        raise HTTPException(status_code=404, detail="SubCategoría no encontrada")
    
    for key, value in subcat.model_dump().items():
        setattr(db_subcat, key, value)
        
    db.commit()
    db.refresh(db_subcat)
    return db_subcat

@router.delete("/subcategorias/{id_subcategoria}")
def delete_subcategoria(
    id_subcategoria: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_permission('products', 'delete'))
):
    """Eliminar una subcategoría de producto."""
    db_subcat = db.query(SubCategoria).filter(SubCategoria.id_subcategoria == id_subcategoria).first()
    if not db_subcat:
        raise HTTPException(status_code=404, detail="SubCategoría no encontrada")
    
    # Verificar si está en uso por productos
    en_uso = db.query(Producto).filter(Producto.id_subcategoria == id_subcategoria).count()
    if en_uso > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar porque está en uso por {en_uso} productos.")

    db.delete(db_subcat)
    db.commit()
    return {"detail": "SubCategoría eliminada"}


# =======================
# CATÁLOGOS PARA DROPDOWNS (marcas, productoras, presentaciones, departamentos)
# =======================

@router.get("/marcas", response_model=List[CatalogoSimple])
def get_marcas(id_productora: Optional[int] = Query(None), db: Session = Depends(get_db)):
    q = db.query(Marca)
    if id_productora is not None:
        q = q.filter(Marca.id_productora == id_productora)
    return [CatalogoSimple(id=m.id_marca, nombre=m.nombre, id_productora=m.id_productora)
            for m in q.order_by(Marca.nombre).all()]


@router.get("/productoras", response_model=List[CatalogoSimple])
def get_productoras(db: Session = Depends(get_db)):
    return [CatalogoSimple(id=p.id_productora, nombre=p.nombre)
            for p in db.query(Productora).order_by(Productora.nombre).all()]


@router.get("/presentaciones", response_model=List[CatalogoSimple])
def get_presentaciones(db: Session = Depends(get_db)):
    return [CatalogoSimple(id=p.id_presentacion, nombre=p.nombre)
            for p in db.query(Presentacion).order_by(Presentacion.nombre).all()]


@router.get("/departamentos", response_model=List[CatalogoSimple])
def get_departamentos(db: Session = Depends(get_db)):
    return [CatalogoSimple(id=d.id_departamento, nombre=d.nombre)
            for d in db.query(Departamento).order_by(Departamento.nombre).all()]


@router.get("/tamanos", response_model=List[CatalogoSimple])
def get_tamanos(db: Session = Depends(get_db)):
    return [CatalogoSimple(id=t.id, nombre=t.nombre)
            for t in db.query(ClasificacionTamano).order_by(ClasificacionTamano.nombre).all()]


@router.post("/tamanos", response_model=CatalogoSimple, status_code=201)
def create_tamano(data: TamanoCreate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    t = ClasificacionTamano(nombre=data.nombre.strip())
    db.add(t); db.commit(); db.refresh(t)
    return CatalogoSimple(id=t.id, nombre=t.nombre)


@router.put("/tamanos/{id_tamano}", response_model=CatalogoSimple)
def update_tamano(id_tamano: int, data: TamanoUpdate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    t = db.query(ClasificacionTamano).filter(ClasificacionTamano.id == id_tamano).first()
    if not t:
        raise HTTPException(404, "Tamaño no encontrado")
    if data.nombre is not None:
        t.nombre = data.nombre.strip()
    db.commit(); db.refresh(t)
    return CatalogoSimple(id=t.id, nombre=t.nombre)


@router.delete("/tamanos/{id_tamano}")
def delete_tamano(id_tamano: int, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'delete'))):
    t = db.query(ClasificacionTamano).filter(ClasificacionTamano.id == id_tamano).first()
    if not t:
        raise HTTPException(404, "Tamaño no encontrado")
    en_uso = db.query(Producto).filter(Producto.id_clasificacion_tamano == id_tamano).count()
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} productos.")
    db.delete(t); db.commit()
    return {"detail": "Tamaño eliminado"}


@router.post("/departamentos", response_model=CatalogoSimple, status_code=201)
def create_departamento(data: DepartamentoCreate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    d = Departamento(nombre=data.nombre.strip())
    db.add(d); db.commit(); db.refresh(d)
    return CatalogoSimple(id=d.id_departamento, nombre=d.nombre)


@router.put("/departamentos/{id_departamento}", response_model=CatalogoSimple)
def update_departamento(id_departamento: int, data: DepartamentoUpdate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    d = db.query(Departamento).filter(Departamento.id_departamento == id_departamento).first()
    if not d:
        raise HTTPException(404, "Departamento no encontrado")
    if data.nombre is not None:
        d.nombre = data.nombre.strip()
    db.commit(); db.refresh(d)
    return CatalogoSimple(id=d.id_departamento, nombre=d.nombre)


@router.delete("/departamentos/{id_departamento}")
def delete_departamento(id_departamento: int, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'delete'))):
    d = db.query(Departamento).filter(Departamento.id_departamento == id_departamento).first()
    if not d:
        raise HTTPException(404, "Departamento no encontrado")
    en_uso = db.query(Categoria).filter(Categoria.id_departamento == id_departamento).count()
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} categorías.")
    db.delete(d); db.commit()
    return {"detail": "Departamento eliminado"}


@router.post("/marcas", response_model=CatalogoSimple, status_code=201)
def create_marca(data: MarcaCreate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    m = Marca(nombre=data.nombre.strip(), id_productora=data.id_productora)
    db.add(m); db.commit(); db.refresh(m)
    return CatalogoSimple(id=m.id_marca, nombre=m.nombre, id_productora=m.id_productora)


@router.put("/marcas/{id_marca}", response_model=CatalogoSimple)
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


@router.delete("/marcas/{id_marca}")
def delete_marca(id_marca: int, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'delete'))):
    m = db.query(Marca).filter(Marca.id_marca == id_marca).first()
    if not m:
        raise HTTPException(404, "Marca no encontrada")
    en_uso = db.query(Producto).filter(Producto.id_marca == id_marca).count()
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} productos.")
    db.delete(m); db.commit()
    return {"detail": "Marca eliminada"}


@router.post("/presentaciones", response_model=CatalogoSimple, status_code=201)
def create_presentacion(data: PresentacionCreate, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'write'))):
    p = Presentacion(nombre=data.nombre.strip(), clasificacion_tamanos=data.clasificacion_tamanos)
    db.add(p); db.commit(); db.refresh(p)
    return CatalogoSimple(id=p.id_presentacion, nombre=p.nombre)


@router.put("/presentaciones/{id_presentacion}", response_model=CatalogoSimple)
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


@router.delete("/presentaciones/{id_presentacion}")
def delete_presentacion(id_presentacion: int, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'delete'))):
    p = db.query(Presentacion).filter(Presentacion.id_presentacion == id_presentacion).first()
    if not p:
        raise HTTPException(404, "Presentación no encontrada")
    en_uso = db.query(Producto).filter(Producto.id_presentacion == id_presentacion).count()
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} productos.")
    db.delete(p); db.commit()
    return {"detail": "Presentación eliminada"}


# =======================
# PRODUCTOS (snowflake: tabla PRODUCTOS)
# =======================

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


@router.get("/productos", response_model=ProductoListResponse)
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


@router.get("/productos/{producto_id}", response_model=ProductoResponse)
def get_producto(producto_id: int, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    row = _producto_join(db).filter(Producto.id_producto == producto_id).first()
    if not row:
        raise HTTPException(404, "Producto no encontrado")
    return _producto_resp(*row)


@router.post("/productos", response_model=ProductoResponse, status_code=201)
def create_producto(data: ProductoCreate, db: Session = Depends(get_db), current_user: Usuario = Depends(require_permission('products', 'write'))):
    p = Producto(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return get_producto(p.id_producto, db, current_user)


@router.put("/productos/{producto_id}", response_model=ProductoResponse)
def update_producto(producto_id: int, data: ProductoUpdate, db: Session = Depends(get_db), current_user: Usuario = Depends(require_permission('products', 'write'))):
    p = db.query(Producto).filter(Producto.id_producto == producto_id).first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    return get_producto(producto_id, db, current_user)


@router.delete("/productos/{producto_id}")
def delete_producto(producto_id: int, db: Session = Depends(get_db), _: Usuario = Depends(require_permission('products', 'delete'))):
    p = db.query(Producto).filter(Producto.id_producto == producto_id).first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    db.delete(p)
    db.commit()
    return {"detail": "Producto eliminado"}
