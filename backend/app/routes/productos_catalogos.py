from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text, select, func, delete as sa_delete
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from app.db.session import get_db, get_async_db
from app.core.dependencies import get_current_user, require_permission
from app.models.user import Usuario, UserPermission
from app.models.producto import (
    Categoria, SubCategoria, Producto, Marca, Productora, Presentacion, Departamento,
    ClasificacionTamano,
)
from app.models.cliente import CategoriaCliente, Cliente
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
async def get_categorias(db: AsyncSession = Depends(get_async_db)):
    """Listar todas las categorías de productos."""
    return (await db.execute(select(Categoria))).scalars().all()

@router.post("/categorias", response_model=CategoriaResponse)
async def create_categoria(
    cat: CategoriaCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('products.catalogos', 'write'))
):
    """Crear una nueva categoría de producto."""
    nueva = Categoria(**cat.model_dump())
    db.add(nueva)
    await db.commit()
    await db.refresh(nueva)
    return nueva

@router.put("/categorias/{id_categoria}", response_model=CategoriaResponse)
async def update_categoria(
    id_categoria: int,
    cat: CategoriaUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('products.catalogos', 'write'))
):
    """Actualizar una categoría de producto existente."""
    db_cat = (await db.execute(select(Categoria).filter(Categoria.id_categoria == id_categoria))).scalars().first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    for key, value in cat.model_dump().items():
        setattr(db_cat, key, value)
        
    await db.commit()
    await db.refresh(db_cat)
    return db_cat

@router.delete("/categorias/{id_categoria}")
async def delete_categoria(
    id_categoria: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('products.catalogos', 'delete'))
):
    """Eliminar una categoría de producto."""
    db_cat = (await db.execute(select(Categoria).filter(Categoria.id_categoria == id_categoria))).scalars().first()
    if not db_cat:
        raise HTTPException(status_code=404, detail="Categoría no encontrada")
    
    # Verificar si está en uso por subcategorías
    en_uso = (await db.execute(select(func.count(SubCategoria.id_subcategoria)).filter(SubCategoria.id_categoria == id_categoria))).scalar() or 0
    if en_uso > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar porque está en uso por {en_uso} subcategorías.")
        
    await db.delete(db_cat)
    await db.commit()
    return {"detail": "Categoría eliminada"}

# =======================
# SUBCATEGORIAS
# =======================

@router.get("/subcategorias", response_model=List[SubCategoriaResponse])
async def get_subcategorias(
    id_categoria: int = Query(None, description="Filtrar por id_categoria"),
    db: AsyncSession = Depends(get_async_db)
):
    """Listar subcategorías, opcionalmente filtradas por categoría."""
    query = select(SubCategoria)
    if id_categoria is not None:
        query = query.filter(SubCategoria.id_categoria == id_categoria)
    return (await db.execute(query)).scalars().all()

@router.post("/subcategorias", response_model=SubCategoriaResponse)
async def create_subcategoria(
    subcat: SubCategoriaCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('products.catalogos', 'write'))
):
    """Crear una nueva subcategoría de producto."""
    nueva = SubCategoria(**subcat.model_dump())
    db.add(nueva)
    await db.commit()
    await db.refresh(nueva)
    return nueva

@router.put("/subcategorias/{id_subcategoria}", response_model=SubCategoriaResponse)
async def update_subcategoria(
    id_subcategoria: int,
    subcat: SubCategoriaUpdate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('products.catalogos', 'write'))
):
    """Actualizar una subcategoría de producto."""
    db_subcat = (await db.execute(select(SubCategoria).filter(SubCategoria.id_subcategoria == id_subcategoria))).scalars().first()
    if not db_subcat:
        raise HTTPException(status_code=404, detail="SubCategoría no encontrada")
    
    for key, value in subcat.model_dump().items():
        setattr(db_subcat, key, value)
        
    await db.commit()
    await db.refresh(db_subcat)
    return db_subcat

@router.delete("/subcategorias/{id_subcategoria}")
async def delete_subcategoria(
    id_subcategoria: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_permission('products.catalogos', 'delete'))
):
    """Eliminar una subcategoría de producto."""
    db_subcat = (await db.execute(select(SubCategoria).filter(SubCategoria.id_subcategoria == id_subcategoria))).scalars().first()
    if not db_subcat:
        raise HTTPException(status_code=404, detail="SubCategoría no encontrada")
    
    # Verificar si está en uso por productos
    en_uso = (await db.execute(select(func.count(Producto.id_producto)).filter(Producto.id_subcategoria == id_subcategoria))).scalar() or 0
    if en_uso > 0:
        raise HTTPException(status_code=400, detail=f"No se puede eliminar porque está en uso por {en_uso} productos.")

    await db.delete(db_subcat)
    await db.commit()
    return {"detail": "SubCategoría eliminada"}


# =======================
# CATÁLOGOS PARA DROPDOWNS (marcas, productoras, presentaciones, departamentos)
# =======================

@router.get("/marcas", response_model=List[CatalogoSimple])
async def get_marcas(id_productora: Optional[int] = Query(None), db: AsyncSession = Depends(get_async_db)):
    q = select(Marca)
    if id_productora is not None:
        q = q.filter(Marca.id_productora == id_productora)
    result = await db.execute(q.order_by(Marca.nombre))
    return [CatalogoSimple(id=m.id_marca, nombre=m.nombre, id_productora=m.id_productora)
            for m in result.scalars().all()]


@router.get("/productoras", response_model=List[CatalogoSimple])
async def get_productoras(db: AsyncSession = Depends(get_async_db)):
    return [CatalogoSimple(id=p.id_productora, nombre=p.nombre)
            for p in (await db.execute(select(Productora).order_by(Productora.nombre))).scalars().all()]


@router.get("/presentaciones", response_model=List[CatalogoSimple])
async def get_presentaciones(db: AsyncSession = Depends(get_async_db)):
    return [CatalogoSimple(id=p.id_presentacion, nombre=p.nombre)
            for p in (await db.execute(select(Presentacion).order_by(Presentacion.nombre))).scalars().all()]


@router.get("/departamentos", response_model=List[CatalogoSimple])
async def get_departamentos(db: AsyncSession = Depends(get_async_db)):
    return [CatalogoSimple(id=d.id_departamento, nombre=d.nombre)
            for d in (await db.execute(select(Departamento).order_by(Departamento.nombre))).scalars().all()]


@router.get("/tamanos", response_model=List[CatalogoSimple])
async def get_tamanos(db: AsyncSession = Depends(get_async_db)):
    return [CatalogoSimple(id=t.id, nombre=t.nombre)
            for t in (await db.execute(select(ClasificacionTamano).order_by(ClasificacionTamano.nombre))).scalars().all()]


@router.post("/tamanos", response_model=CatalogoSimple, status_code=201)
async def create_tamano(data: TamanoCreate, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'write'))):
    t = ClasificacionTamano(nombre=data.nombre.strip())
    db.add(t); await db.commit(); await db.refresh(t)
    return CatalogoSimple(id=t.id, nombre=t.nombre)


@router.put("/tamanos/{id_tamano}", response_model=CatalogoSimple)
async def update_tamano(id_tamano: int, data: TamanoUpdate, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'write'))):
    t = (await db.execute(select(ClasificacionTamano).filter(ClasificacionTamano.id == id_tamano))).scalars().first()
    if not t:
        raise HTTPException(404, "Tamaño no encontrado")
    if data.nombre is not None:
        t.nombre = data.nombre.strip()
    await db.commit(); await db.refresh(t)
    return CatalogoSimple(id=t.id, nombre=t.nombre)


@router.delete("/tamanos/{id_tamano}")
async def delete_tamano(id_tamano: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'delete'))):
    t = (await db.execute(select(ClasificacionTamano).filter(ClasificacionTamano.id == id_tamano))).scalars().first()
    if not t:
        raise HTTPException(404, "Tamaño no encontrado")
    en_uso = (await db.execute(select(func.count(Producto.id_producto)).filter(Producto.id_clasificacion_tamano == id_tamano))).scalar() or 0
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} productos.")
    await db.delete(t); await db.commit()
    return {"detail": "Tamaño eliminado"}


@router.post("/departamentos", response_model=CatalogoSimple, status_code=201)
async def create_departamento(data: DepartamentoCreate, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'write'))):
    d = Departamento(nombre=data.nombre.strip())
    db.add(d); await db.commit(); await db.refresh(d)
    return CatalogoSimple(id=d.id_departamento, nombre=d.nombre)


@router.put("/departamentos/{id_departamento}", response_model=CatalogoSimple)
async def update_departamento(id_departamento: int, data: DepartamentoUpdate, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'write'))):
    d = (await db.execute(select(Departamento).filter(Departamento.id_departamento == id_departamento))).scalars().first()
    if not d:
        raise HTTPException(404, "Departamento no encontrado")
    if data.nombre is not None:
        d.nombre = data.nombre.strip()
    await db.commit(); await db.refresh(d)
    return CatalogoSimple(id=d.id_departamento, nombre=d.nombre)


@router.delete("/departamentos/{id_departamento}")
async def delete_departamento(id_departamento: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'delete'))):
    d = (await db.execute(select(Departamento).filter(Departamento.id_departamento == id_departamento))).scalars().first()
    if not d:
        raise HTTPException(404, "Departamento no encontrado")
    en_uso = (await db.execute(select(func.count(Categoria.id_categoria)).filter(Categoria.id_departamento == id_departamento))).scalar() or 0
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} categorías.")
    await db.delete(d); await db.commit()
    return {"detail": "Departamento eliminado"}


@router.post("/marcas", response_model=CatalogoSimple, status_code=201)
async def create_marca(data: MarcaCreate, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'write'))):
    m = Marca(nombre=data.nombre.strip(), id_productora=data.id_productora)
    db.add(m); await db.commit(); await db.refresh(m)
    return CatalogoSimple(id=m.id_marca, nombre=m.nombre, id_productora=m.id_productora)


@router.put("/marcas/{id_marca}", response_model=CatalogoSimple)
async def update_marca(id_marca: int, data: MarcaUpdate, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'write'))):
    m = (await db.execute(select(Marca).filter(Marca.id_marca == id_marca))).scalars().first()
    if not m:
        raise HTTPException(404, "Marca no encontrada")
    if data.nombre is not None:
        m.nombre = data.nombre.strip()
    if data.id_productora is not None:
        m.id_productora = data.id_productora
    await db.commit(); await db.refresh(m)
    return CatalogoSimple(id=m.id_marca, nombre=m.nombre, id_productora=m.id_productora)


@router.delete("/marcas/{id_marca}")
async def delete_marca(id_marca: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'delete'))):
    m = (await db.execute(select(Marca).filter(Marca.id_marca == id_marca))).scalars().first()
    if not m:
        raise HTTPException(404, "Marca no encontrada")
    en_uso = (await db.execute(select(func.count(Producto.id_producto)).filter(Producto.id_marca == id_marca))).scalar() or 0
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} productos.")
    await db.delete(m); await db.commit()
    return {"detail": "Marca eliminada"}


@router.post("/presentaciones", response_model=CatalogoSimple, status_code=201)
async def create_presentacion(data: PresentacionCreate, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'write'))):
    p = Presentacion(nombre=data.nombre.strip(), clasificacion_tamanos=data.clasificacion_tamanos)
    db.add(p); await db.commit(); await db.refresh(p)
    return CatalogoSimple(id=p.id_presentacion, nombre=p.nombre)


@router.put("/presentaciones/{id_presentacion}", response_model=CatalogoSimple)
async def update_presentacion(id_presentacion: int, data: PresentacionUpdate, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'write'))):
    p = (await db.execute(select(Presentacion).filter(Presentacion.id_presentacion == id_presentacion))).scalars().first()
    if not p:
        raise HTTPException(404, "Presentación no encontrada")
    if data.nombre is not None:
        p.nombre = data.nombre.strip()
    if data.clasificacion_tamanos is not None:
        p.clasificacion_tamanos = data.clasificacion_tamanos
    await db.commit(); await db.refresh(p)
    return CatalogoSimple(id=p.id_presentacion, nombre=p.nombre)


@router.delete("/presentaciones/{id_presentacion}")
async def delete_presentacion(id_presentacion: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products.catalogos', 'delete'))):
    p = (await db.execute(select(Presentacion).filter(Presentacion.id_presentacion == id_presentacion))).scalars().first()
    if not p:
        raise HTTPException(404, "Presentación no encontrada")
    en_uso = (await db.execute(select(func.count(Producto.id_producto)).filter(Producto.id_presentacion == id_presentacion))).scalar() or 0
    if en_uso > 0:
        raise HTTPException(400, f"No se puede eliminar: está en uso por {en_uso} productos.")
    await db.delete(p); await db.commit()
    return {"detail": "Presentación eliminada"}


# =======================
# PRODUCTOS (snowflake: tabla PRODUCTOS)
# =======================

async def _producto_join(db: AsyncSession, current_user: Optional[Usuario] = None):
    stmt = (
        select(Producto, SubCategoria, Categoria, Marca, Productora, Presentacion, Departamento, ClasificacionTamano)
        .outerjoin(SubCategoria, SubCategoria.id_subcategoria == Producto.id_subcategoria)
        .outerjoin(Categoria, Categoria.id_categoria == SubCategoria.id_categoria)
        .outerjoin(Marca, Marca.id_marca == Producto.id_marca)
        .outerjoin(Productora, Productora.id_productora == Marca.id_productora)
        .outerjoin(Presentacion, Presentacion.id_presentacion == Producto.id_presentacion)
        .outerjoin(Departamento, Departamento.id_departamento == Categoria.id_departamento)
        .outerjoin(ClasificacionTamano, ClasificacionTamano.id == Producto.id_clasificacion_tamano)
    )
    # Un analista solo debe ver productos de las categorías asociadas a SUS
    # clientes (CATEGORIAS_CLIENTES), mismo criterio de alcance que ya se usa
    # en centro_mando.py/client_data.py/frecuencias_pdvs_cliente.py -- antes
    # este endpoint no filtraba nada acá y un analista veía el catálogo
    # completo de todos los clientes.
    if current_user is not None and current_user.is_analyst and current_user.id_perfil:
        ids_cliente = [
            r[0] for r in (await db.execute(text("""
                SELECT DISTINCT rp.id_cliente
                FROM analistas_rutas ar
                JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = ar.id_ruta
                WHERE ar.id_analista = :analista_id AND rp.activa = 1
            """), {"analista_id": int(current_user.id_perfil)})).fetchall()
            if r[0] is not None
        ]
        if not ids_cliente:
            return stmt.filter(Producto.id_producto == None)  # noqa: E711 -- sin clientes asignados, sin productos
        cats_subq = select(CategoriaCliente.id_categoria).filter(CategoriaCliente.id_cliente.in_(ids_cliente))
        stmt = stmt.filter(Categoria.id_categoria.in_(cats_subq))
    # Cliente puro (id_rol=1): id_perfil = id_cliente en CLIENTES.
    elif current_user is not None and current_user.rol == "client" and current_user.id_perfil:
        # "Solo propios" (pedido por Flora Foods, 19-20 ago): reusa el
        # checkbox de usuario_permisos que ya existe para module='products'
        # ("Categoría completa" / "Solo propios" en Permisos, fila
        # "Productos"). Cuando está en can_see_all=False, el alcance del
        # cliente pasa a ser directamente "todo lo que es de MI PRODUCTORA"
        # (columna ya poblada en PRODUCTS/MARCAS, visible en la tabla como
        # "Flora Food") -- ESTO REEMPLAZA el filtro de CATEGORIAS_CLIENTES
        # de abajo, no se suma a él.
        #
        # Primer intento (20 ago) usaba SKU_COMPETENCIA.id_producto_cliente
        # -- se revirtió porque esa tabla es para pares de comparación
        # (qué SKU propio se enfrenta a cuál de la competencia, uno a uno),
        # no un catálogo completo de "todo lo mío" -- para Flora Foods
        # estaba vacía o incompleta y el filtro daba 0 productos.
        #
        # Segundo intento (20 ago) SUMABA el filtro de productora al de
        # CATEGORIAS_CLIENTES en vez de reemplazarlo -- se corrigió (21 ago)
        # porque CATEGORIAS_CLIENTES es un mapeo manual que puede quedar
        # desactualizado respecto del catálogo real: a Flora Foods le
        # faltaba ahí la categoría ARROZ, así que 9 de sus 31 productos
        # reales (confirmado en vivo contra PRODUCTORAS/PRODUCTS) quedaban
        # ocultos igual con "Solo propios" activado -- el módulo Data
        # (client_data.py::_solo_propios_filter), que solo filtra por
        # productora sin tocar CATEGORIAS_CLIENTES, sí mostraba los 31,
        # y esa discrepancia (22 vs 31) fue la señal de que el filtro de
        # categoría no debía seguir aplicando encima del de productora.
        perm = (await db.execute(
            select(UserPermission).filter(
                UserPermission.user_id == current_user.id,
                UserPermission.module == "products",
            )
        )).scalars().first()
        # OJO -- ya NO exige perm.can_read acá (20 ago, segundo intento). El
        # toggle "Solo propios" del frontend solo controla can_see_all -- el
        # can_read de esta misma fila depende del dropdown de "Lectura"
        # (state === 'allow'), un control aparte que el admin nunca toca al
        # activar el toggle. Con la condición vieja, activar "Solo propios"
        # sin TAMBIÉN poner Lectura=Permitir para Productos no hacía nada
        # (Flora Foods lo confirmó: activó el toggle, siguió viendo todo).
        # "is False" estricto (no solo falsy) es clave: las filas migradas
        # en bloque para el resto de los clientes (client_role_modules.sql)
        # nunca tocan can_see_all y quedan en NULL -- tratar NULL como
        # "restringir" les rompería el catálogo completo a todos los demás.
        solo_propios_activo = perm is not None and perm.can_see_all is False

        id_productora_propia = None
        if solo_propios_activo:
            cliente_row = (await db.execute(
                select(Cliente.id_productora).filter(Cliente.id == int(current_user.id_perfil))
            )).first()
            id_productora_propia = cliente_row[0] if cliente_row else None

        if solo_propios_activo and id_productora_propia:
            stmt = stmt.filter(Productora.id_productora == id_productora_propia)
        elif solo_propios_activo:
            # can_see_all=False pero nadie configuró CLIENTES.id_productora
            # todavía -- mejor mostrar vacío y explícito (ver /productos-
            # catalogos/mi-productora abajo, que el frontend puede usar
            # para avisarlo) que mostrar la categoría completa igual,
            # que es justo lo que "Solo propios" dice que NO debe pasar.
            stmt = stmt.filter(Producto.id_producto == None)  # noqa: E711
        else:
            # Sin "Solo propios": alcance clásico por categorías asignadas
            # en CATEGORIAS_CLIENTES.
            cats_subq = select(CategoriaCliente.id_categoria).filter(
                CategoriaCliente.id_cliente == int(current_user.id_perfil)
            )
            stmt = stmt.filter(Categoria.id_categoria.in_(cats_subq))
    elif current_user is not None and current_user.rol == "client" and not current_user.id_perfil:
        # Cliente sin id_perfil configurado → sin acceso a productos
        return stmt.filter(Producto.id_producto == None)  # noqa: E711
    return stmt


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


def _apply_producto_filtros(
    stmt, *, busqueda=None, id_departamento=None, id_categoria=None, id_subcategoria=None,
    id_marca=None, id_productora=None, id_presentacion=None, id_clasificacion_tamano=None,
    inagotable=None, exclude: Optional[str] = None,
):
    """Filtros de /productos, reusados también por /productos/filtros-disponibles
    (que necesita aplicar TODOS los filtros MENOS el de la propia faceta que
    está calculando -- `exclude` -- para no reducir sus propias opciones a 1
    apenas se elige un valor)."""
    if busqueda:
        like = f"%{busqueda}%"
        stmt = stmt.filter((Producto.producto_gu.ilike(like)) | (Producto.cod_prod.ilike(like)))
    if exclude != "departamento" and id_departamento is not None:
        stmt = stmt.filter(Departamento.id_departamento == id_departamento)
    if exclude != "categoria" and id_categoria is not None:
        if id_categoria == -1:
            stmt = stmt.filter(SubCategoria.id_categoria.is_(None))
        else:
            stmt = stmt.filter(SubCategoria.id_categoria == id_categoria)
    if exclude != "subcategoria" and id_subcategoria is not None:
        stmt = stmt.filter(Producto.id_subcategoria == id_subcategoria)
    if exclude != "marca" and id_marca is not None:
        stmt = stmt.filter(Producto.id_marca == id_marca)
    if exclude != "productora" and id_productora is not None:
        stmt = stmt.filter(Productora.id_productora == id_productora)
    if exclude != "presentacion" and id_presentacion is not None:
        stmt = stmt.filter(Producto.id_presentacion == id_presentacion)
    if exclude != "tamano" and id_clasificacion_tamano is not None:
        stmt = stmt.filter(Producto.id_clasificacion_tamano == id_clasificacion_tamano)
    if inagotable is not None:
        stmt = stmt.filter(Producto.inagotable == inagotable)
    return stmt


@router.get("/mi-productora")
async def mi_productora(db: AsyncSession = Depends(get_async_db), current_user: Usuario = Depends(get_current_user)):
    """Diagnóstico rápido para 'Solo propios' (Permisos > Productos,
    can_see_all=False): confirma si el cliente tiene CLIENTES.id_productora
    configurada -- si no, el filtro devuelve todo vacío a propósito en vez
    de mostrar la categoría completa (ver _producto_join). Sirve para no
    volver a confundir "no configurado" con "0 productos propios reales"."""
    if current_user.rol != "client" or not current_user.id_perfil:
        return {"aplica": False}
    row = (await db.execute(
        select(Cliente.id_productora, Productora.nombre)
        .outerjoin(Productora, Productora.id_productora == Cliente.id_productora)
        .filter(Cliente.id == int(current_user.id_perfil))
    )).first()
    perm = (await db.execute(
        select(UserPermission).filter(UserPermission.user_id == current_user.id, UserPermission.module == "products")
    )).scalars().first()
    return {
        "aplica": True,
        "solo_propios_activo": bool(perm is not None and perm.can_see_all is False),
        "id_productora": row[0] if row else None,
        "productora_nombre": row[1] if row else None,
        "configurado": bool(row and row[0]),
    }


@router.get("/productos", response_model=ProductoListResponse)
async def list_productos(
    busqueda: Optional[str] = Query(None),
    id_departamento: Optional[int] = Query(None),
    id_categoria: Optional[int] = Query(None),
    id_subcategoria: Optional[int] = Query(None),
    id_marca: Optional[int] = Query(None),
    id_productora: Optional[int] = Query(None),
    id_presentacion: Optional[int] = Query(None),
    id_clasificacion_tamano: Optional[int] = Query(None),
    inagotable: Optional[bool] = Query(None),
    skip: int = 0,
    limit: int = 25,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(get_current_user),
):
    base_stmt = await _producto_join(db, current_user)
    stmt = _apply_producto_filtros(
        base_stmt, busqueda=busqueda, id_departamento=id_departamento, id_categoria=id_categoria,
        id_subcategoria=id_subcategoria, id_marca=id_marca, id_productora=id_productora,
        id_presentacion=id_presentacion, id_clasificacion_tamano=id_clasificacion_tamano, inagotable=inagotable,
    )
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    limit = max(1, limit)
    rows = (await db.execute(stmt.order_by(Producto.producto_gu).offset(skip).limit(limit))).all()
    return ProductoListResponse(
        total=total, pagina=(skip // limit + 1),
        items=[_producto_resp(*r) for r in rows],
    )


@router.get("/productos/filtros-disponibles")
async def productos_filtros_disponibles(
    busqueda: Optional[str] = Query(None),
    id_departamento: Optional[int] = Query(None),
    id_categoria: Optional[int] = Query(None),
    id_subcategoria: Optional[int] = Query(None),
    id_marca: Optional[int] = Query(None),
    id_productora: Optional[int] = Query(None),
    id_presentacion: Optional[int] = Query(None),
    id_clasificacion_tamano: Optional[int] = Query(None),
    inagotable: Optional[bool] = Query(None),
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Para que los filtros de Productos cascadeen: dado lo que ya está
    elegido (ej. una productora), devuelve solo los departamentos/categorías/
    subcategorías/marcas/productoras/presentaciones/tamaños que EXISTEN entre
    _{productos que matchean esa selección -- en vez de listas fijas de
    todo el catálogo. Cada faceta se calcula excluyendo su propio filtro
    (`exclude`) para no colapsarse a una sola opción apenas se la elige."""
    kwargs = dict(
        busqueda=busqueda, id_departamento=id_departamento, id_categoria=id_categoria,
        id_subcategoria=id_subcategoria, id_marca=id_marca, id_productora=id_productora,
        id_presentacion=id_presentacion, id_clasificacion_tamano=id_clasificacion_tamano, inagotable=inagotable,
    )

    async def opts(exclude: str, id_col, nombre_col):
        base_stmt = await _producto_join(db, current_user)
        filtered = _apply_producto_filtros(base_stmt, exclude=exclude, **kwargs)
        stmt = select(id_col, nombre_col).select_from(filtered.subquery()).distinct()
        rows = (await db.execute(stmt)).all()
        return sorted(
            [{"id": r[0], "nombre": r[1]} for r in rows if r[0] is not None and r[1] is not None],
            key=lambda x: x["nombre"],
        )

    return {
        "departamentos": await opts("departamento", Departamento.id_departamento, Departamento.nombre),
        "categorias": await opts("categoria", Categoria.id_categoria, Categoria.nombre),
        "subcategorias": await opts("subcategoria", SubCategoria.id_subcategoria, SubCategoria.nombre),
        "marcas": await opts("marca", Marca.id_marca, Marca.nombre),
        "productoras": await opts("productora", Productora.id_productora, Productora.nombre),
        "presentaciones": await opts("presentacion", Presentacion.id_presentacion, Presentacion.nombre),
        "tamanos": await opts("tamano", ClasificacionTamano.id, ClasificacionTamano.nombre),
    }


@router.get("/productos/{producto_id}", response_model=ProductoResponse)
async def get_producto(producto_id: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    stmt = await _producto_join(db)
    row = (await db.execute(stmt.filter(Producto.id_producto == producto_id))).first()
    if not row:
        raise HTTPException(404, "Producto no encontrado")
    return _producto_resp(*row)


@router.post("/productos", response_model=ProductoResponse, status_code=201)
async def create_producto(data: ProductoCreate, db: AsyncSession = Depends(get_async_db), current_user: Usuario = Depends(require_permission('products', 'write'))):
    p = Producto(**data.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return await get_producto(p.id_producto, db, current_user)


@router.put("/productos/{producto_id}", response_model=ProductoResponse)
async def update_producto(producto_id: int, data: ProductoUpdate, db: AsyncSession = Depends(get_async_db), current_user: Usuario = Depends(require_permission('products', 'write'))):
    p = (await db.execute(select(Producto).filter(Producto.id_producto == producto_id))).scalars().first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    await db.commit()
    return await get_producto(producto_id, db, current_user)


@router.delete("/productos/{producto_id}")
async def delete_producto(producto_id: int, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(require_permission('products', 'delete'))):
    p = (await db.execute(select(Producto).filter(Producto.id_producto == producto_id))).scalars().first()
    if not p:
        raise HTTPException(404, "Producto no encontrado")
    await db.delete(p)
    await db.commit()
    return {"detail": "Producto eliminado"}
