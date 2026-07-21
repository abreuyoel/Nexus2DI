import json
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Body, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_roles, require_analyst_or_admin
from app.core.security import get_password_hash
from app.modules.auth.entities import Usuario
from app.modules.routes.entities import PuntoInteres
from app.modules.catalogues.entities import Producto, Categoria
from app.modules.customer_service.entities import Solicitud
from app.modules.surveyors.entities import CentroSalud
from app.modules.clients.dto import PuntoInteresCreate, PuntoInteresUpdate, PuntoInteresResponse
from app.modules.catalogues.dto import ProductoCreate, ProductoUpdate, ProductoResponse, ProductoListResponse, CategoriaResponse
from app.modules.customer_service.dto import SolicitudCreate, SolicitudResponse, AprobarSolicitudRequest
from app.shared.audit_service import log_action
from app.shared.realtime import notify_event
from app.core.request_ip import get_client_ip

router = APIRouter(prefix="/api/atencion-cliente", tags=["Atención al Cliente"])

TIPOS_SOLICITUD_ANALISTA = ("creacion_usuario", "creacion_pdv", "creacion_producto")


# ==================== PDVS ====================

@router.get("/pdv", response_model=List[PuntoInteresResponse])
def list_pdv(
    activo: Optional[bool] = None,
    region: Optional[str] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    query = db.query(PuntoInteres)
    if activo is not None:
        query = query.filter(PuntoInteres.activo == activo)
    if region:
        query = query.filter(PuntoInteres.departamento == region)
    return query.limit(500).all()


@router.post("/pdv", response_model=PuntoInteresResponse, status_code=201)
def create_pdv(
    data: PuntoInteresCreate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    punto = PuntoInteres(**data.model_dump())
    db.add(punto)
    db.commit()
    db.refresh(punto)
    return punto


@router.get("/pdv/{punto_id}", response_model=PuntoInteresResponse)
def get_pdv(punto_id: str, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    punto = db.query(PuntoInteres).filter(PuntoInteres.id == punto_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="PDV no encontrado")
    return punto


@router.put("/pdv/{punto_id}", response_model=PuntoInteresResponse)
def update_pdv(
    punto_id: str,
    data: PuntoInteresUpdate,
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    punto = db.query(PuntoInteres).filter(PuntoInteres.id == punto_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="PDV no encontrado")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(punto, k, v)
    db.commit()
    db.refresh(punto)
    return punto


@router.delete("/pdv/{punto_id}")
def delete_pdv(punto_id: str, db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    punto = db.query(PuntoInteres).filter(PuntoInteres.id == punto_id).first()
    if not punto:
        raise HTTPException(status_code=404, detail="PDV no encontrado")
    punto.activo = False
    db.commit()
    return {"message": "PDV desactivado"}


# ==================== PRODUCTOS ====================

@router.get("/productos", response_model=ProductoListResponse)
def list_productos(
    skip: int = 0,
    limit: int = 25,
    busqueda: Optional[str] = None,
    categoria: Optional[str] = None,
    fabricante: Optional[str] = None,
    tipo_servicio: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("admin")),
):
    query = db.query(Producto)
    
    if busqueda:
        search_term = f"%{busqueda}%"
        query = query.filter(
            (Producto.producto_gu.ilike(search_term)) |
            (Producto.comentario.ilike(search_term))
        )
    
    if categoria:
        query = query.filter(Producto.id_categoria == int(categoria))
    
    total = query.count()
    items = query.order_by(Producto.id_producto).offset(skip).limit(limit).all()
    pagina = (skip // limit) + 1 if limit > 0 else 1
    
    output_items = []
    for p in items:
        output_items.append(ProductoResponse(
            id=p.id_producto,
            producto_gu=p.producto_gu,
            cod_prod=p.cod_prod,
            descripcion_bi=p.descripcion_bi,
            gramos=p.gramos,
            inagotable=p.inagotable,
            comentario=p.comentario,
            id_subcategoria=p.id_subcategoria,
            id_marca=p.id_marca,
            id_presentacion=p.id_presentacion,
            id_clasificacion_tamano=p.id_clasificacion_tamano,
        ))

    return {
        "total": total,
        "pagina": pagina,
        "items": output_items
    }


@router.get("/productos/{producto_id}", response_model=ProductoResponse)
def get_producto(
    producto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("admin")),
):
    producto = db.query(Producto).filter(Producto.id_producto == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return ProductoResponse(
        id=producto.id_producto,
        producto_gu=producto.producto_gu,
        cod_prod=producto.cod_prod,
        descripcion_bi=producto.descripcion_bi,
        gramos=producto.gramos,
        inagotable=producto.inagotable,
        comentario=producto.comentario,
        id_subcategoria=producto.id_subcategoria,
        id_marca=producto.id_marca,
        id_presentacion=producto.id_presentacion,
        id_clasificacion_tamano=producto.id_clasificacion_tamano,
    )


@router.post("/productos", response_model=ProductoResponse, status_code=201)
def create_producto(
    data: ProductoCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("admin")),
):
    if not data.producto_gu or data.producto_gu.strip() == "":
        raise HTTPException(status_code=400, detail="El nombre del producto (producto_gu) es requerido")
    existente = db.query(Producto).filter(Producto.producto_gu == data.producto_gu).first()
    if existente:
        raise HTTPException(status_code=400, detail="Producto ya existe")
    producto = Producto(**data.model_dump())
    db.add(producto)
    db.flush()
    log_action(db, action="CREATE_PRODUCT", entity_type="Producto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=producto.id_producto, entity_name=data.producto_gu,
               changes=data.model_dump())
    db.commit()
    db.refresh(producto)
    notify_event("product.created", {"id": producto.id_producto, "nombre": producto.producto_gu})
    return ProductoResponse(
        id=producto.id_producto,
        producto_gu=producto.producto_gu,
        cod_prod=producto.cod_prod,
        descripcion_bi=producto.descripcion_bi,
        gramos=producto.gramos,
        inagotable=producto.inagotable,
        comentario=producto.comentario,
        id_subcategoria=producto.id_subcategoria,
        id_marca=producto.id_marca,
        id_presentacion=producto.id_presentacion,
        id_clasificacion_tamano=producto.id_clasificacion_tamano,
    )


@router.put("/productos/{producto_id}", response_model=ProductoResponse)
def update_producto(
    producto_id: int,
    data: ProductoUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("admin")),
):
    producto = db.query(Producto).filter(Producto.id_producto == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if data.producto_gu and data.producto_gu.strip() == "":
        raise HTTPException(status_code=400, detail="El nombre no puede estar vacío")
    if data.producto_gu and data.producto_gu != producto.producto_gu:
        existente = db.query(Producto).filter(Producto.producto_gu == data.producto_gu).first()
        if existente:
            raise HTTPException(status_code=400, detail="Producto ya existe")
    changes = data.model_dump(exclude_none=True)
    for k, v in changes.items():
        setattr(producto, k, v)
    log_action(db, action="UPDATE_PRODUCT", entity_type="Producto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=producto_id, entity_name=producto.producto_gu, changes=changes)
    db.commit()
    db.refresh(producto)
    notify_event("product.updated", {"id": producto.id_producto, "nombre": producto.producto_gu})
    return ProductoResponse(
        id=producto.id_producto,
        producto_gu=producto.producto_gu,
        cod_prod=producto.cod_prod,
        descripcion_bi=producto.descripcion_bi,
        gramos=producto.gramos,
        inagotable=producto.inagotable,
        comentario=producto.comentario,
        id_subcategoria=producto.id_subcategoria,
        id_marca=producto.id_marca,
        id_presentacion=producto.id_presentacion,
        id_clasificacion_tamano=producto.id_clasificacion_tamano,
    )


@router.delete("/productos/{producto_id}")
def delete_producto(
    producto_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("admin")),
):
    producto = db.query(Producto).filter(Producto.id_producto == producto_id).first()
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    nombre = producto.producto_gu
    db.delete(producto)
    log_action(db, action="DELETE_PRODUCT", entity_type="Producto",
               user_id=current_user.id, username=current_user.username, rol=current_user.rol,
               ip_address=get_client_ip(request),
               entity_id=producto_id, entity_name=nombre)
    db.commit()
    notify_event("product.deleted", {"id": producto_id})
    return {"success": True, "message": "Producto eliminado correctamente"}


@router.get("/productos/listado/categorias", response_model=List[str])
def list_categorias_productos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("admin")),
):
    categorias = db.query(Categoria.nombre).distinct().filter(Categoria.nombre.isnot(None)).all()
    return [c[0] for c in categorias]


@router.get("/productos/listado/fabricantes", response_model=List[str])
def list_fabricantes_productos(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("admin")),
):
    from app.modules.catalogues.entities import Productora
    fabricantes = db.query(Productora.nombre).distinct().filter(Productora.nombre.isnot(None)).all()
    return [f[0] for f in fabricantes]


# ==================== CATEGORÍAS ====================

@router.get("/categorias", response_model=List[CategoriaResponse])
def list_categorias(db: Session = Depends(get_db), _: Usuario = Depends(get_current_user)):
    cats = db.query(Categoria).limit(100).all()
    return [CategoriaResponse(id=c.id_categoria, nombre=c.nombre) for c in cats]


# ==================== SOLICITUDES ====================

@router.get("/solicitudes", response_model=List[SolicitudResponse])
def get_solicitudes(
    estado: Optional[str] = None,
    type_filter: Optional[str] = Query(None, alias="tipo"),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    query = db.query(Solicitud)
    if estado:
        query = query.filter(Solicitud.estado == estado)
    if type_filter:
        query = query.filter(Solicitud.tipo == type_filter)
    if current_user.rol == "analyst":
        query = query.filter(Solicitud.user_id == current_user.id)
    return query.order_by(Solicitud.created_at.desc()).limit(100).all()


@router.post("/solicitudes", response_model=SolicitudResponse, status_code=201)
def crear_solicitud(
    data: SolicitudCreate,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
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
    db.commit()
    db.refresh(sol)
    return sol


def _norm_coord(v):
    if v is None:
        return v
    return str(v).strip().replace(',', '.')


def _generar_identificador_pdv(db: Session, jerarquia: str) -> str:
    ultimo = (
        db.query(PuntoInteres.id)
        .filter(PuntoInteres.jerarquia_n2_2 == jerarquia)
        .order_by(PuntoInteres.id.desc())
        .first()
    )
    identificador = None
    prefijo = None
    if ultimo and ultimo[0] and len(ultimo[0]) >= 7:
        prefijo = ultimo[0][:3]
        try:
            identificador = f"{prefijo}{int(ultimo[0][3:7]) + 1:04d}"
        except ValueError:
            identificador = None

    if not identificador:
        prefijo = ''.join(jerarquia.split())[:3].upper().ljust(3, 'X')
        max_row = (
            db.query(PuntoInteres.id)
            .filter(PuntoInteres.id.like(f"{prefijo}%"))
            .order_by(PuntoInteres.id.desc())
            .first()
        )
        max_numero = 0
        if max_row and max_row[0] and len(max_row[0]) >= 7:
            try:
                max_numero = int(max_row[0][len(prefijo):len(prefijo) + 4])
            except ValueError:
                max_numero = 0
        identificador = f"{prefijo}{max_numero + 1:04d}"

    if db.query(PuntoInteres.id).filter(PuntoInteres.id == identificador).first():
        base = int(identificador[3:7])
        for i in range(1, 1000):
            candidato = f"{prefijo}{(base + i):04d}"
            if not db.query(PuntoInteres.id).filter(PuntoInteres.id == candidato).first():
                identificador = candidato
                break

    return identificador


def _crear_pdv_desde_solicitud(db: Session, data: dict) -> str:
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

    tolerancia = 0.001
    pts = (
        db.query(PuntoInteres.id, PuntoInteres.nombre, PuntoInteres.latitud, PuntoInteres.longitud)
        .filter(PuntoInteres.latitud.isnot(None), PuntoInteres.longitud.isnot(None))
        .all()
    )
    for p_id, p_name, p_lat, p_lng in pts:
        try:
            plat = float(str(p_lat).replace(',', '.').strip())
            plng = float(str(p_lng).replace(',', '.').strip())
            if abs(plat - lat) <= tolerancia and abs(plng - lng) <= tolerancia:
                raise HTTPException(
                    status_code=400,
                    detail=f"Ya existe un punto de interés cercano: {p_name} (ID: {p_id})"
                )
        except (ValueError, TypeError):
            continue

    identificador = _generar_identificador_pdv(db, jerarquia)

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
    db.commit()
    return identificador


@router.post("/solicitudes/{sol_id}/aprobar")
def aprobar_solicitud(
    sol_id: int,
    payload: Optional[AprobarSolicitudRequest] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("admin", "atc")),
):
    sol = db.query(Solicitud).filter(Solicitud.id == sol_id).first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")

    if sol.estado == "aprobada":
        raise HTTPException(status_code=400, detail="La solicitud ya estaba aprobada")

    try:
        datos_originales = json.loads(sol.descripcion) if sol.descripcion else {}
    except (json.JSONDecodeError, TypeError, ValueError):
        raise HTTPException(status_code=400, detail="Los datos de la solicitud tienen un formato JSON inválido")

    completar = payload.completar if payload and payload.completar else {}

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
        _crear_pdv_desde_solicitud(db, datos)

    elif sol.tipo == "creacion_usuario":
        username = datos.get("username")
        password = datos.get("password")
        id_rol = datos.get("id_rol")
        if not username or not password or not id_rol:
            raise HTTPException(status_code=400, detail="Faltan campos requeridos: username, password o id_rol")
        if db.query(Usuario).filter(Usuario.username == username).first():
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

    if completar:
        sol.descripcion = json.dumps(datos)
    sol.estado = "aprobada"
    db.commit()
    return {"message": "Solicitud aprobada"}


@router.post("/solicitudes/{sol_id}/rechazar")
def rechazar_solicitud(
    sol_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_roles("admin", "atc")),
):
    sol = db.query(Solicitud).filter(Solicitud.id == sol_id).first()
    if not sol:
        raise HTTPException(status_code=404, detail="Solicitud no encontrada")
    sol.estado = "rechazada"
    db.commit()
    return {"message": "Solicitud rechazada"}
