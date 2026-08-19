from fastapi import APIRouter, Depends, HTTPException, status, Request, Body
from app.services.audit_service import log_action
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, text, select
from typing import List, Optional
from datetime import datetime
from app.db.session import get_db, get_async_db
from app.core.dependencies import get_current_user, require_roles, require_analyst_or_admin
from app.core.security import get_password_hash
from app.models.user import Usuario
from app.models.punto import PuntoInteres
from app.models.producto import Producto, Categoria
from app.models.solicitud import Solicitud
from app.schemas.cliente import PuntoInteresCreate, PuntoInteresUpdate, PuntoInteresResponse
from app.schemas.producto import ProductoCreate, ProductoUpdate, ProductoResponse, ProductoListResponse, CategoriaResponse
from app.schemas.solicitud import SolicitudCreate, SolicitudResponse
from app.core.request_ip import get_client_ip

router = APIRouter(prefix="/api/atencion-cliente", tags=["Atención al Cliente"])

TIPOS_SOLICITUD_ANALISTA = ("creacion_usuario", "creacion_pdv", "creacion_producto")


@router.get("/pdv", response_model=List[PuntoInteresResponse])
async def list_pdv(
    activo: Optional[bool] = None,
    region: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    stmt = select(PuntoInteres)
    if activo is not None:
        stmt = stmt.filter(PuntoInteres.activo == activo)
    if region:
        stmt = stmt.filter(PuntoInteres.departamento == region)
    return (await db.execute(stmt.limit(500))).scalars().all()


@router.post("/pdv", response_model=PuntoInteresResponse, status_code=201)
async def create_pdv(
    data: PuntoInteresCreate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    punto = PuntoInteres(**data.model_dump())
    db.add(punto)
    await db.commit()
    await db.refresh(punto)
    return punto


@router.get("/pdv/{punto_id}", response_model=PuntoInteresResponse)
async def get_pdv(punto_id: str, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    punto = (await db.execute(select(PuntoInteres).filter(PuntoInteres.id == punto_id))).scalars().first()
    if not punto:
        raise HTTPException(status_code=404, detail="PDV no encontrado")
    return punto


@router.put("/pdv/{punto_id}", response_model=PuntoInteresResponse)
async def update_pdv(
    punto_id: str,
    data: PuntoInteresUpdate,
    db: AsyncSession = Depends(get_async_db),
    _: Usuario = Depends(get_current_user),
):
    punto = (await db.execute(select(PuntoInteres).filter(PuntoInteres.id == punto_id))).scalars().first()
    if not punto:
        raise HTTPException(status_code=404, detail="PDV no encontrado")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(punto, k, v)
    await db.commit()
    await db.refresh(punto)
    return punto


@router.delete("/pdv/{punto_id}")
async def delete_pdv(punto_id: str, db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    punto = (await db.execute(select(PuntoInteres).filter(PuntoInteres.id == punto_id))).scalars().first()
    if not punto:
        raise HTTPException(status_code=404, detail="PDV no encontrado")
    punto.activo = False
    await db.commit()
    return {"message": "PDV desactivado"}



# ==================== PRODUCTOS ====================

@router.get("/productos", response_model=ProductoListResponse)
async def list_productos(
    skip: int = 0,
    limit: int = 25,
    busqueda: Optional[str] = None,
    categoria: Optional[str] = None,
    fabricante: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_roles("admin")),

):
    """
    Listar productos con paginación y búsqueda full-text.
    Solo accesible para usuarios con rol 'Administrador'.
    
    - skip: Número de productos a saltar (para paginación)
    - limit: Cantidad de productos por página (default 25)
    - busqueda: Busca en SKU, Fabricante y nombre del producto
    - categoria: Filtro por categoría exacta
    - fabricante: Filtro por fabricante exacto
    - tipo_servicio: Filtro por tipo de servicio
    """
    stmt = select(Producto)
    
    # Búsqueda full-text
    if busqueda:
        search_term = f"%{busqueda}%"
        stmt = stmt.filter(
            (Producto.nombre.ilike(search_term)) |
            (Producto.fabricante.ilike(search_term))
        )
    
    # Filtros exactos
    if categoria:
        stmt = stmt.filter(Producto.categoria == categoria)
    if fabricante:
        stmt = stmt.filter(Producto.fabricante == fabricante)
    if tipo_servicio:
        stmt = stmt.filter(Producto.tipo_servicio == tipo_servicio)
    
    # Contar total ANTES de aplicar paginación
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0
    
    # Aplicar paginación
    items = (await db.execute(stmt.order_by(Producto.id).offset(skip).limit(limit))).scalars().all()

    
    # Calcular página actual (1-indexed)
    pagina = (skip // limit) + 1 if limit > 0 else 1
    
    return {
        "total": total,
        "pagina": pagina,
        "items": items
    }


@router.get("/productos/{producto_id}", response_model=ProductoResponse)
async def get_producto(
    producto_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_roles("admin")),
):
    """Obtener un producto específico por ID."""
    producto = (await db.execute(select(Producto).filter(Producto.id == producto_id))).scalars().first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto


@router.post("/productos", response_model=ProductoResponse, status_code=201)
async def create_producto(
    data: ProductoCreate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_roles("admin")),
):
    if not data.nombre or data.nombre.strip() == "":
        raise HTTPException(status_code=400, detail="SKU (nombre) es requerido")
    existente = (await db.execute(select(Producto).filter(Producto.nombre == data.nombre))).scalars().first()
    if existente:
        raise HTTPException(status_code=400, detail="SKU ya existe")
    producto = Producto(**data.model_dump())
    db.add(producto)
    db.flush()
    log_action(db, action="CREATE_PRODUCT", entity_type="Producto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=producto.id, entity_name=data.nombre,
               changes=data.model_dump())
    await db.commit()
    await db.refresh(producto)
    from app.services.realtime import notify_event
    notify_event("product.created", {"id": producto.id, "nombre": producto.nombre})
    return producto


@router.put("/productos/{producto_id}", response_model=ProductoResponse)
async def update_producto(
    producto_id: int,
    data: ProductoUpdate,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_roles("admin")),
):
    producto = (await db.execute(select(Producto).filter(Producto.id == producto_id))).scalars().first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if data.nombre and data.nombre.strip() == "":
        raise HTTPException(status_code=400, detail="SKU no puede estar vacío")
    if data.nombre and data.nombre != producto.nombre:
        existente = (await db.execute(select(Producto).filter(Producto.nombre == data.nombre))).scalars().first()
        if existente:
            raise HTTPException(status_code=400, detail="SKU ya existe")
    changes = data.model_dump(exclude_none=True)
    for k, v in changes.items():
        setattr(producto, k, v)
    log_action(db, action="UPDATE_PRODUCT", entity_type="Producto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=producto_id, entity_name=producto.nombre, changes=changes)
    await db.commit()
    await db.refresh(producto)
    from app.services.realtime import notify_event
    notify_event("product.updated", {"id": producto.id, "nombre": producto.nombre})
    return producto


@router.delete("/productos/{producto_id}")
async def delete_producto(
    producto_id: int,
    request: Request,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_roles("admin")),
):
    producto = (await db.execute(select(Producto).filter(Producto.id == producto_id))).scalars().first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    nombre = producto.nombre
    await db.delete(producto)
    log_action(db, action="DELETE_PRODUCT", entity_type="Producto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=producto_id, entity_name=nombre)
    await db.commit()
    from app.services.realtime import notify_event
    notify_event("product.deleted", {"id": producto_id})
    return {"success": True, "message": "Producto eliminado correctamente"}


@router.get("/productos/listado/categorias", response_model=list[str])
async def list_categorias_productos(
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_roles("admin")),

):
    """Obtener lista de categorías únicas."""
    categorias = (await db.execute(select(Producto.categoria).distinct().filter(Producto.categoria.isnot(None)))).scalars().all()
    return [c[0] for c in categorias]


@router.get("/productos/listado/fabricantes", response_model=list[str])
async def list_fabricantes_productos(
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_roles("admin")),

):
    """Obtener lista de fabricantes únicos."""
    fabricantes = (await db.execute(select(Producto.fabricante).distinct().filter(Producto.fabricante.isnot(None)))).scalars().all()
    return [f[0] for f in fabricantes]


@router.get("/productos/listado/tipos-servicio", response_model=list[str])
async def list_tipos_servicio_productos(
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_roles("admin")),

):
    """Obtener lista de tipos de servicio únicos."""
    tipos = (await db.execute(select(Producto.tipo_servicio).distinct().filter(Producto.tipo_servicio.isnot(None)))).scalars().all()
    return [t[0] for t in tipos]


@router.get("/productos/listado/tipos-fabricante", response_model=list[str])
async def list_tipos_fabricante_productos(
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_roles("admin")),

):
    """Obtener lista de tipos de fabricante únicos."""
    tipos = (await db.execute(select(Producto.tipo_fabricante).distinct().filter(Producto.tipo_fabricante.isnot(None)))).scalars().all()
    return [t[0] for t in tipos]


# ==================== CATEGORÍAS ====================

@router.get("/categorias", response_model=List[CategoriaResponse])
async def list_categorias(db: AsyncSession = Depends(get_async_db), _: Usuario = Depends(get_current_user)):
    return (await db.execute(select(Categoria).limit(100))).scalars().all()


@router.get("/solicitudes")
async def get_solicitudes(
    estado: Optional[str] = None,
    tipo: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(get_current_user),
):
    stmt = select(Solicitud)
    if estado:
        stmt = stmt.filter(Solicitud.estado == estado)
    if tipo:
        stmt = stmt.filter(Solicitud.tipo == tipo)
    if current_user.rol == "analyst":
        stmt = stmt.filter(Solicitud.user_id == current_user.id)
    return (await db.execute(stmt.order_by(Solicitud.created_at.desc()).limit(100))).scalars().all()


@router.post("/solicitudes", response_model=SolicitudResponse, status_code=201)
async def crear_solicitud(
    data: SolicitudCreate,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    """Un analista (o admin) crea una solicitud de usuario/PDV/producto para que ATC la revise."""
    if data.tipo not in TIPOS_SOLICITUD_ANALISTA:
        raise HTTPException(status_code=400, detail=f"Tipo de solicitud no soportado. Use uno de: {', '.join(TIPOS_SOLICITUD_ANALISTA)}")
    sol = Solicitud(
        user_id=current_user.id,
        tipo=data.tipo,
        descripcion=data.descripcion,
        estado="pendiente",
        created_at=datetime.utcnow(),
    )
    db.add(sol)
    await db.commit()
    await db.refresh(sol)
    return sol


import json
from app.models.encuestador import CentroSalud


def _norm_coord(v):
    if v is None:
        return v
    return str(v).strip().replace(',', '.')


async def generar_identificador_pdv(db: AsyncSession, jerarquia: str) -> str:
    """Replica el algoritmo de main:atencion_cliente.py (_crear_pdv_core): reutiliza el
    prefijo de 3 letras del último identificador de la misma jerarquia_nivel_2_2 e
    incrementa su sufijo numérico de 4 dígitos; si no hay ninguno, deriva el prefijo
    de las 3 primeras letras de la jerarquía."""
    ultimo = (
        await db.execute(
            select(PuntoInteres.id)
            .filter(PuntoInteres.jerarquia_n2_2 == jerarquia)
            .order_by(PuntoInteres.id.desc())
        )
    ).scalars().first()
    identificador = None
    prefijo = None
    if ultimo and len(ultimo) >= 7:
        prefijo = ultimo[:3]
        try:
            identificador = f"{prefijo}{int(ultimo[3:7]) + 1:04d}"
        except ValueError:
            identificador = None

    if not identificador:
        prefijo = ''.join(jerarquia.split())[:3].upper().ljust(3, 'X')
        max_row = (
            await db.execute(
                select(PuntoInteres.id)
                .filter(PuntoInteres.id.like(f"{prefijo}%"))
                .order_by(PuntoInteres.id.desc())
            )
        ).scalars().first()
        max_numero = 0
        if max_row and len(max_row) >= 7:
            try:
                max_numero = int(max_row[len(prefijo):len(prefijo) + 4])
            except ValueError:
                max_numero = 0
        identificador = f"{prefijo}{max_numero + 1:04d}"

    if (await db.execute(select(PuntoInteres.id).filter(PuntoInteres.id == identificador))).scalars().first():
        base = int(identificador[3:7])
        for i in range(1, 1000):
            candidato = f"{prefijo}{(base + i):04d}"
            if not (await db.execute(select(PuntoInteres.id).filter(PuntoInteres.id == candidato))).scalars().first():
                identificador = candidato
                break

    return identificador


async def _crear_pdv_desde_solicitud(db: AsyncSession, data: dict) -> str:
    """Crea un PUNTOS_INTERES1 a partir de los datos de una solicitud 'creacion_pdv'
    (nombre/direccion/GPS del analista + campos completados por ATC al aprobar).
    Lanza HTTPException(400) si faltan datos o hay un PDV cercano duplicado.
    Devuelve el identificador generado."""
    nombre = data.get('nombre') or data.get('punto_de_interes')
    direccion = data.get('direccion') or data.get('Direccion')
    latitud = _norm_coord(data.get('latitud'))
    longitud = _norm_coord(data.get('longitud'))
    jerarquia = data.get('jerarquia_n2_2') or data.get('jerarquia_nivel_2_2')

    if not nombre:
        raise HTTPException(status_code=400, detail="Nombre del punto es requerido")
    if not direccion:
        raise HTTPException(status_code=400, detail="Dirección es requerida")
    if not latitud or not longitud:
        raise HTTPException(status_code=400, detail="Coordenadas son requeridas")
    if not jerarquia:
        raise HTTPException(status_code=400, detail="Jerarquía nivel 2_2 es requerida para generar el identificador")

    try:
        lat, lng = float(latitud), float(longitud)
    except ValueError:
        raise HTTPException(status_code=400, detail="Coordenadas inválidas")

    tolerancia = 0.001  # ~111 metros
    cercano = (await db.execute(text("""
        SELECT TOP 1 identificador, punto_de_interes, latitud, longitud
        FROM PUNTOS_INTERES1
        WHERE TRY_CAST(latitud AS FLOAT) IS NOT NULL
          AND TRY_CAST(longitud AS FLOAT) IS NOT NULL
          AND ABS(TRY_CAST(latitud AS FLOAT) - :lat) <= :tol
          AND ABS(TRY_CAST(longitud AS FLOAT) - :lng) <= :tol
    """), {"lat": lat, "lng": lng, "tol": tolerancia})).fetchone()
    if cercano:
        raise HTTPException(status_code=400, detail=f"Ya existe un punto de interés cercano: {cercano[1]} (ID: {cercano[0]})")

    identificador = await generar_identificador_pdv(db, jerarquia)

    punto = PuntoInteres(
        id=identificador,
        nombre=nombre,
        direccion=direccion,
        latitud=latitud,
        longitud=longitud,
        departamento=data.get('departamento'),
        jerarquia_n2=data.get('jerarquia_n2') or data.get('jerarquia_nivel_2'),
        jerarquia_n2_2=jerarquia,
        ciudad=data.get('ciudad'),
        cadena=data.get('cadena') or data.get('clasificacion_de_canal'),
        radio=str(data.get('radio') or 100),
        tiempo_minimo=15,
        fecha_creado=datetime.utcnow(),
        nivel_de_alcance=data.get('nivel_de_alcance'),
        rif=data.get('rif'),
    )
    db.add(punto)
    await db.commit()
    return identificador


@router.post("/solicitudes/{sol_id}/aprobar")
async def aprobar_solicitud(
    sol_id: int,
    completar: dict = Body(default={}),
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_roles("admin", "atc")),
):
    """Aprueba una solicitud. `completar` son los campos que ATC edita/completa
    en el momento de aprobar (el vendedor/analista pudo no haber mandado todos
    los datos, o ATC puede necesitar corregir algo antes de insertar) — se
    sobreponen a los datos originales de la solicitud para los 3 tipos
    autoservicio (creacion_pdv/usuario/producto)."""
    sol = (await db.execute(select(Solicitud).filter(Solicitud.id == sol_id))).scalars().first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if sol.estado == "aprobada":
        raise HTTPException(status_code=400, detail="La solicitud ya estaba aprobada")

    try:
        datos_originales = json.loads(sol.descripcion) if sol.descripcion else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Los datos de la solicitud tienen un formato JSON inválido")

    datos = dict(datos_originales)
    datos.update({k: v for k, v in (completar or {}).items() if v not in (None, '')})

    if sol.tipo == "creacion_centro_salud":
        nuevo_centro = CentroSalud(
            nombre_centro=datos.get("nombre_centro", ""),
            direccion_completa=datos.get("direccion_completa", ""),
            ciudad=datos.get("ciudad"),
            estado=datos.get("estado")
        )
        db.add(nuevo_centro)

    elif sol.tipo == "creacion_pdv":
        # El vendedor/analista envía nombre/dirección/GPS; ATC completa o
        # corrige jerarquía/canal/etc. al aprobar (llegan en `completar`).
        await _crear_pdv_desde_solicitud(db, datos)

    elif sol.tipo == "creacion_usuario":
        username = datos.get("username")
        password = datos.get("password")
        id_rol = datos.get("id_rol")
        if not username or not password or not id_rol:
            raise HTTPException(status_code=400, detail="Faltan campos requeridos: username, password o id_rol")
        if (await db.execute(select(Usuario).filter(Usuario.username == username))).scalars().first():
            raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
        nuevo_usuario = Usuario(
            username=username,
            email=datos.get("email"),
            id_rol=id_rol,
            id_perfil=datos.get("id_perfil"),
            activo=True,
            password=get_password_hash(password),
        )
        db.add(nuevo_usuario)

    elif sol.tipo == "creacion_producto":
        producto_gu = datos.get("producto_gu")
        if not producto_gu:
            raise HTTPException(status_code=400, detail="El nombre del producto (producto_gu) es requerido")
        nuevo_producto = Producto(
            producto_gu=producto_gu,
            cod_prod=datos.get("cod_prod"),
            descripcion_bi=datos.get("descripcion_bi"),
            gramos=datos.get("gramos"),
            inagotable=datos.get("inagotable", False),
            comentario=datos.get("comentario"),
            id_subcategoria=datos.get("id_subcategoria"),
            id_marca=datos.get("id_marca"),
            id_presentacion=datos.get("id_presentacion"),
            id_clasificacion_tamano=datos.get("id_clasificacion_tamano"),
        )
        db.add(nuevo_producto)

    # Si ATC edito datos, deja constancia de los datos finales con los que se aprobo.
    if completar:
        sol.descripcion = json.dumps(datos)
    sol.estado = "aprobada"
    await db.commit()
    return {"message": "Solicitud aprobada"}


@router.post("/solicitudes/{sol_id}/rechazar")
async def rechazar_solicitud(
    sol_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Usuario = Depends(require_roles("admin", "atc")),
):
    sol = (await db.execute(select(Solicitud).filter(Solicitud.id == sol_id))).scalars().first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    sol.estado = "rechazada"
    await db.commit()
    return {"message": "Solicitud rechazada"}
