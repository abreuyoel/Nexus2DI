from __future__ import annotations

import os
import uuid
from datetime import datetime, date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.modules.auth.entities import Usuario
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.routes.entities import Ruta, RutaProgramacion, PuntoInteres
from app.modules.clients.entities import Cliente
from app.modules.visits.entities import Visita, Foto, Balance
from app.modules.catalogues.entities import Producto
from app.modules.chat.entities import ChatMensaje
from app.modules.merchandisers.dto import (
    MiPerfilResponse, MiPerfilRutaItem, MiRutaResponse, RutaItemResponse, PdvPuntoItem,
    MiVisitaResponse, IniciarVisitaRequest, IniciarVisitaResponse,
    FotosVisitaResponse, FotoTipoGroupResponse, FotoItemResponse,
    ProductoClienteResponse, GuardarBalancesRequest, ChatInboxItemResponse
)
from app.shared.realtime import notify_event

router = APIRouter(prefix="/api/merc", tags=["Mercaderista Portal"])

DAY_MAP_ES = {
    0: "Lunes", 1: "Martes", 2: "Miércoles",
    3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo",
}

FOTO_TIPOS = {
    "gestion_antes":      {"label": "Gestión (Antes)",            "solo_camara": False, "id": 1},
    "gestion_despues":    {"label": "Gestión (Después)",          "solo_camara": False, "id": 2},
    "precios":            {"label": "Precios",                    "solo_camara": False, "id": 3},
    "exhibicion_antes":   {"label": "Exhibición Adic. (Antes)",   "solo_camara": False, "id": 4},
    "exhibicion_despues": {"label": "Exhibición Adic. (Después)", "solo_camara": False, "id": 7},
    "pop_antes":          {"label": "Material POP (Antes)",       "solo_camara": False, "id": 8},
    "pop_despues":        {"label": "Material POP (Después)",     "solo_camara": False, "id": 10},
    "activacion":         {"label": "Activación",                 "solo_camara": True,  "id": 5},
    "desactivacion":      {"label": "Desactivación",              "solo_camara": True,  "id": 6},
}
FOTO_TIPO_TO_ID = {k: v["id"] for k, v in FOTO_TIPOS.items()}
ID_TO_CODIGO = {v["id"]: k for k, v in FOTO_TIPOS.items()}
FOTOS_DIR = "app/static/fotos_mercaderista"


def _get_mercaderista(current_user: Usuario, db: Session) -> Mercaderista:
    try:
        cedula_val = int(current_user.username)
    except ValueError:
        cedula_val = 0

    merc = db.query(Mercaderista).filter(
        Mercaderista.cedula == cedula_val
    ).first()
    if not merc:
        raise HTTPException(status_code=403, detail="Usuario no es mercaderista")
    return merc


def _merc_foto_url(blob_path: Optional[str], foto_id: int) -> Optional[str]:
    if not blob_path:
        return None
    if "fotos_mercaderista" in blob_path or os.path.exists(blob_path):
        return f"/api/merc/foto/{foto_id}"
    try:
        from app.shared.azure_service import azure_service
        return azure_service.get_sas_url(blob_path)
    except Exception:
        return f"/api/merc/foto/{foto_id}"


@router.get("/mi-perfil", response_model=MiPerfilResponse)
def get_mi_perfil(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)
    rutas = db.query(MercaderistaRuta).filter(MercaderistaRuta.mercaderista_id == merc.id).all()
    return MiPerfilResponse(
        id=merc.id,
        nombre=merc.nombre,
        cedula=merc.cedula,
        email=merc.email,
        telefono=merc.telefono,
        rutas=[MiPerfilRutaItem(id_ruta=r.ruta_id, tipo=r.tipo_ruta) for r in rutas]
    )


@router.get("/mi-ruta", response_model=MiRutaResponse)
def get_mi_ruta(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)
    hoy = date.today()
    dia_semana = DAY_MAP_ES[hoy.weekday()]

    rutas_rows = (
        db.query(MercaderistaRuta.ruta_id, MercaderistaRuta.tipo_ruta, Ruta.nombre)
        .join(Ruta, MercaderistaRuta.ruta_id == Ruta.id)
        .filter(MercaderistaRuta.mercaderista_id == merc.id)
        .all()
    )
    rutas = [RutaItemResponse(id_ruta=r[0], tipo=r[1], nombre=r[2]) for r in rutas_rows]

    pdvs_rows = (
        db.query(
            RutaProgramacion.id,
            RutaProgramacion.punto_id,
            RutaProgramacion.punto_interes_nombre,
            RutaProgramacion.id_cliente,
            RutaProgramacion.ruta_id,
            RutaProgramacion.prioridad,
            MercaderistaRuta.tipo_ruta,
            PuntoInteres.latitud,
            PuntoInteres.longitud,
            PuntoInteres.cadena,
            PuntoInteres.departamento,
            PuntoInteres.direccion,
            Cliente.nombre
        )
        .distinct()
        .join(MercaderistaRuta, MercaderistaRuta.ruta_id == RutaProgramacion.ruta_id)
        .outerjoin(PuntoInteres, PuntoInteres.id == RutaProgramacion.punto_id)
        .outerjoin(Cliente, Cliente.id == RutaProgramacion.id_cliente)
        .filter(
            MercaderistaRuta.mercaderista_id == merc.id,
            RutaProgramacion.dia == dia_semana,
            RutaProgramacion.activo == True
        )
        .all()
    )

    visitas_hoy = (
        db.query(Visita)
        .filter(
            Visita.mercaderista_id == merc.id,
            Visita.fecha == hoy
        )
        .all()
    )
    visita_por_pdv = {v.punto_id: v for v in visitas_hoy}

    pdvs = []
    for row in pdvs_rows:
        pid = row[1]
        visita = visita_por_pdv.get(pid)
        pdvs.append(PdvPuntoItem(
            id_punto=pid or "",
            nombre=row[2],
            id_cliente=row[3],
            cliente=row[12],
            id_ruta=row[4],
            cadena=row[9],
            region=row[10],
            direccion=row[11],
            tipo_ruta=row[6],
            prioridad=row[5],
            tiene_coords=row[7] is not None and row[8] is not None,
            latitud=float(str(row[7]).replace(",", ".")) if row[7] else None,
            longitud=float(str(row[8]).replace(",", ".")) if row[8] else None,
            visita_id=visita.id if visita else None,
            visitado=visita is not None,
            estado=visita.estado if visita else None,
            estado_data=visita.estado_data if (visita and hasattr(visita, 'estado_data')) else None,
        ))

    return MiRutaResponse(
        dia=dia_semana,
        fecha=str(hoy),
        rutas=rutas,
        pdvs=pdvs
    )


@router.get("/mis-visitas", response_model=List[MiVisitaResponse])
def get_mis_visitas(
    fecha_inicio: Optional[str] = None,
    fecha_fin: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)

    fi = datetime.strptime(fecha_inicio, '%Y-%m-%d').date() if fecha_inicio else date.today()
    ff = datetime.strptime(fecha_fin, '%Y-%m-%d').date() if fecha_fin else date.today()

    sub_fotos = (
        db.query(Foto.visita_id, func.count(Foto.id).label("fotos_count"))
        .group_by(Foto.visita_id)
        .subquery()
    )
    sub_balances = (
        db.query(Balance.visita_id, func.count(Balance.id).label("balances_count"))
        .group_by(Balance.visita_id)
        .subquery()
    )

    rows = (
        db.query(
            Visita.id,
            Visita.fecha,
            Visita.estado,
            Visita.estado_data,
            Visita.observaciones,
            Visita.punto_id,
            PuntoInteres.nombre.label("pdv_nombre"),
            PuntoInteres.cadena,
            PuntoInteres.departamento.label("region"),
            Cliente.nombre.label("cliente_nombre"),
            Visita.id_cliente,
            func.coalesce(sub_fotos.c.fotos_count, 0).label("fotos_count"),
            func.coalesce(sub_balances.c.balances_count, 0).label("balances_count")
        )
        .outerjoin(PuntoInteres, PuntoInteres.id == Visita.punto_id)
        .outerjoin(Cliente, Cliente.id == Visita.id_cliente)
        .outerjoin(sub_fotos, sub_fotos.c.visita_id == Visita.id)
        .outerjoin(sub_balances, sub_balances.c.visita_id == Visita.id)
        .filter(
            Visita.mercaderista_id == merc.id,
            Visita.fecha >= fi,
            Visita.fecha <= ff
        )
        .order_by(Visita.fecha.desc(), Visita.id.desc())
        .all()
    )

    return [
        MiVisitaResponse(
            id_visita=r[0],
            fecha=str(r[1]) if r[1] else None,
            estado=r[2],
            estado_data=r[3],
            observaciones=r[4],
            pdv_nombre=r[6],
            cadena=r[7],
            region=r[8],
            cliente=r[9],
            id_cliente=r[10],
            fotos_count=r[11],
            balances_count=r[12]
        )
        for r in rows
    ]


@router.post("/iniciar-visita", response_model=IniciarVisitaResponse)
def iniciar_visita(
    payload: IniciarVisitaRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)
    id_punto = payload.id_punto
    id_cliente = payload.id_cliente

    today = date.today()
    existing = db.query(Visita).filter(
        Visita.mercaderista_id == merc.id,
        Visita.punto_id == id_punto,
        Visita.fecha == today
    ).first()

    if existing:
        return IniciarVisitaResponse(id_visita=existing.id, nueva=False)

    visita = Visita(
        mercaderista_id=merc.id,
        fecha=today,
        estado="Pendiente",
        estado_data="Pendiente",
        id_cliente=id_cliente,
        punto_id=id_punto
    )
    db.add(visita)
    db.commit()
    db.refresh(visita)

    notify_event("visit.created", {"id_visita": visita.id, "id_cliente": id_cliente, "id_punto": id_punto})

    return IniciarVisitaResponse(id_visita=visita.id, nueva=True)


@router.get("/ruta/{id_ruta}/pdvs")
def get_pdvs_de_ruta(
    id_ruta: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)
    hoy = date.today()

    pdvs_rows = (
        db.query(
            RutaProgramacion.punto_id,
            RutaProgramacion.punto_interes_nombre,
            RutaProgramacion.id_cliente,
            RutaProgramacion.ruta_id,
            RutaProgramacion.prioridad,
            MercaderistaRuta.tipo_ruta,
            PuntoInteres.latitud,
            PuntoInteres.longitud,
            PuntoInteres.cadena,
            PuntoInteres.departamento,
            PuntoInteres.direccion,
            Cliente.nombre
        )
        .distinct()
        .join(MercaderistaRuta, MercaderistaRuta.ruta_id == RutaProgramacion.ruta_id)
        .outerjoin(PuntoInteres, PuntoInteres.id == RutaProgramacion.punto_id)
        .outerjoin(Cliente, Cliente.id == RutaProgramacion.id_cliente)
        .filter(
            MercaderistaRuta.mercaderista_id == merc.id,
            RutaProgramacion.ruta_id == id_ruta,
            RutaProgramacion.activo == True
        )
        .order_by(RutaProgramacion.punto_interes_nombre)
        .all()
    )

    visitas_hoy = (
        db.query(Visita)
        .filter(
            Visita.mercaderista_id == merc.id,
            Visita.fecha == hoy
        )
        .all()
    )
    visita_por_pdv = {v.punto_id: v for v in visitas_hoy}

    pdvs = []
    for row in pdvs_rows:
        pid = row[0]
        visita = visita_por_pdv.get(pid)
        pdvs.append({
            "id_punto": pid,
            "nombre": row[1],
            "id_cliente": row[2],
            "cliente": row[11],
            "id_ruta": row[3],
            "cadena": row[8],
            "region": row[9],
            "direccion": row[10],
            "tipo_ruta": row[5],
            "prioridad": row[4],
            "tiene_coords": row[6] is not None and row[7] is not None,
            "latitud": float(str(row[6]).replace(",", ".")) if row[6] else None,
            "longitud": float(str(row[7]).replace(",", ".")) if row[7] else None,
            "visita_id": visita.id if visita else None,
            "visitado": visita is not None,
            "estado": visita.estado if visita else None,
            "estado_data": visita.estado_data if (visita and hasattr(visita, 'estado_data')) else None,
        })
    return {"id_ruta": id_ruta, "pdvs": pdvs}


@router.get("/visita/{visita_id}/fotos", response_model=FotosVisitaResponse)
def get_fotos_visita(
    visita_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    rows = (
        db.query(Foto.id, Foto.id_tipo_foto, Foto.blob_path, Foto.estado, Foto.fecha_registro)
        .filter(Foto.visita_id == visita_id)
        .order_by(Foto.id)
        .all()
    )

    por_codigo: dict = {k: [] for k in FOTO_TIPOS.keys()}
    for r in rows:
        cod = ID_TO_CODIGO.get(r[1])
        if not cod:
            continue
        por_codigo[cod].append(FotoItemResponse(
            id_foto=r[0],
            estado=r[3],
            fecha=str(r[4]) if r[4] else None,
            url=_merc_foto_url(r[2], r[0]),
        ))

    tipos_info = [
        FotoTipoGroupResponse(
            codigo=k,
            label=v["label"],
            solo_camara=v["solo_camara"],
            fotos=por_codigo.get(k, []),
        )
        for k, v in FOTO_TIPOS.items()
    ]
    return FotosVisitaResponse(visita_id=visita_id, tipos=tipos_info)


@router.post("/fotos/upload")
async def upload_foto(
    visita_id: int = Form(...),
    tipo_foto: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    if tipo_foto not in FOTO_TIPOS:
        raise HTTPException(status_code=400, detail=f"Tipo de foto inválido: {tipo_foto}")

    file_bytes = await file.read()
    ext = (file.filename or "foto.jpg").rsplit(".", 1)[-1].lower()
    if ext not in ("jpg", "jpeg", "png", "webp"):
        ext = "jpg"

    blob_path = None
    try:
        from app.shared.photo_service import process_and_upload_photo
        result = process_and_upload_photo(file_bytes, file.content_type or "image/jpeg")
        blob_path = result.get("blob_path")
    except Exception:
        pass

    if not blob_path:
        os.makedirs(FOTOS_DIR, exist_ok=True)
        fname = f"{uuid.uuid4().hex}.{ext}"
        fpath = os.path.join(FOTOS_DIR, fname)
        with open(fpath, "wb") as f:
            f.write(file_bytes)
        blob_path = fpath

    id_tipo = FOTO_TIPO_TO_ID.get(tipo_foto)
    if not id_tipo:
        raise HTTPException(status_code=400, detail=f"Tipo de foto inválido: {tipo_foto}")

    ahora = datetime.now()
    foto = Foto(
        visita_id=visita_id,
        id_tipo_foto=id_tipo,
        blob_path=blob_path,
        fecha_registro=ahora,
        estado="pendiente"
    )
    db.add(foto)
    db.commit()
    db.refresh(foto)

    notify_event("photo.uploaded", {"id_foto": foto.id, "visita_id": visita_id, "tipo_foto": tipo_foto})

    return {"id_foto": foto.id, "url": _merc_foto_url(blob_path, foto.id), "estado": "pendiente"}


@router.delete("/foto/{foto_id}")
def delete_merc_foto(
    foto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    foto = db.query(Foto).filter(Foto.id == foto_id).first()
    if foto:
        db.delete(foto)
        db.commit()
        notify_event("photo.deleted", {"id_foto": foto_id})
    return {"deleted": foto_id}


@router.get("/foto/{foto_id}")
def get_foto(
    foto_id: int,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from fastapi.responses import FileResponse, RedirectResponse
    foto = db.query(Foto.blob_path).filter(Foto.id == foto_id).first()
    if not foto or not foto[0]:
        raise HTTPException(status_code=404, detail="Foto no encontrada")
    file_path = foto[0]
    if os.path.exists(file_path):
        return FileResponse(file_path)
    try:
        from app.shared.azure_service import azure_service
        return RedirectResponse(azure_service.get_sas_url(file_path))
    except Exception:
        raise HTTPException(status_code=404, detail="Archivo no disponible")


@router.get("/productos", response_model=List[ProductoClienteResponse])
def get_productos_cliente(
    id_cliente: int = Query(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from app.modules.catalogues.entities import Subcategoria, CategoriaCliente, Marca, Productora, Categoria
    rows = (
        db.query(
            Producto.id_producto,
            Producto.producto_gu,
            Categoria.nombre,
            Productora.nombre
        )
        .join(Subcategoria, Subcategoria.id == Producto.id_subcategoria)
        .join(CategoriaCliente, (CategoriaCliente.id_categoria == Subcategoria.id_categoria) & (CategoriaCliente.id_cliente == id_cliente))
        .outerjoin(Categoria, Categoria.id == Subcategoria.id_categoria)
        .outerjoin(Marca, Marca.id == Producto.id_marca)
        .outerjoin(Productora, Productora.id == Marca.id_productora)
        .order_by(Categoria.nombre, Producto.producto_gu)
        .all()
    )

    return [
        ProductoClienteResponse(
            id=r[0],
            sku=r[1],
            categoria=r[2],
            fabricante=r[3]
        )
        for r in rows
    ]


@router.post("/balances")
def guardar_balances(
    payload: GuardarBalancesRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)
    visita_id = payload.visita_id
    productos = payload.productos
    id_cliente = payload.id_cliente

    if not visita_id or not productos:
        raise HTTPException(status_code=400, detail="visita_id y productos son requeridos")

    vis = db.query(Visita).filter(Visita.id == visita_id).first()
    if not vis:
        raise HTTPException(status_code=404, detail="Visita no encontrada")
    id_pdv = vis.punto_id

    now = datetime.now()
    for p in productos:
        b = Balance(
            id_cliente=id_cliente or merc.id,
            fecha_balance=now,
            identificador_pdv=id_pdv,
            mercaderista=merc.nombre,
            producto=p.sku or "",
            fabricante=p.fabricante or "",
            categoria=p.categoria or "",
            inv_inicial=p.inv_inicial or 0,
            inv_final=p.inv_final or 0,
            inv_deposito=p.inv_deposito or 0,
            caras=p.caras or 0,
            precio_bs=p.precio_bs or 0.0,
            precio_ds=p.precio_ds or 0.0,
            visita_id=visita_id
        )
        db.add(b)

    vis.estado_data = "Cargado"
    db.commit()
    return {"success": True, "productos_guardados": len(productos)}


@router.get("/chat/inbox", response_model=List[ChatInboxItemResponse])
def get_chat_inbox(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    merc = _get_mercaderista(current_user, db)

    sub_msgs_count = (
        db.query(ChatMensaje.visita_id, func.count(ChatMensaje.id).label("total_msgs"))
        .group_by(ChatMensaje.visita_id)
        .subquery()
    )

    sub_last_msg = (
        db.query(
            ChatMensaje.visita_id,
            ChatMensaje.mensaje.label("ultimo_msg"),
            ChatMensaje.created_at.label("ultimo_at")
        )
        .order_by(ChatMensaje.created_at.desc())
        .subquery()
    )

    rows = (
        db.query(
            Visita.id,
            Visita.fecha,
            Visita.estado,
            PuntoInteres.nombre.label("pdv_nombre"),
            Cliente.nombre.label("cliente_nombre"),
            func.coalesce(sub_msgs_count.c.total_msgs, 0).label("total_msgs"),
            sub_last_msg.c.ultimo_msg,
            sub_last_msg.c.ultimo_at
        )
        .join(sub_msgs_count, sub_msgs_count.c.visita_id == Visita.id)
        .outerjoin(sub_last_msg, sub_last_msg.c.visita_id == Visita.id)
        .outerjoin(PuntoInteres, PuntoInteres.id == Visita.punto_id)
        .outerjoin(Cliente, Cliente.id == Visita.id_cliente)
        .filter(Visita.mercaderista_id == merc.id)
        .order_by(sub_last_msg.c.ultimo_at.desc())
        .all()
    )

    return [
        ChatInboxItemResponse(
            id_visita=r[0],
            fecha=str(r[1]) if r[1] else None,
            estado=r[2],
            pdv_nombre=r[3],
            cliente=r[4],
            total_msgs=r[5],
            ultimo_msg=r[6],
            ultimo_at=str(r[7]) if r[7] else None,
            no_leidos=0
        )
        for r in rows
    ]
