"""Modulo Vendedor.

Flujo (calcado de AppWeb/backend/app/routes/vendedor.py en main, adaptado a
FastAPI + SQL Server real): activar jornada -> lista de PDVs -> lista de
clientes -> registrar visita (vendio/monto o razon de no venta), atada a la
jornada activa del usuario -> ver visitas del dia -> finalizar jornada.
Accion aparte: solicitar creacion de un PDV nuevo (queda como Solicitud
pendiente de aprobacion por ATC, con las fotos embebidas en base64).
"""
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario as User
from app.models.solicitud import Solicitud

router = APIRouter(prefix="/api/vendedor", tags=["Vendedor"])


def check_rol_vendedor(current_user: User):
    if current_user.id_rol != 9 and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Acceso denegado. Solo para Vendedores.")


def _jornada_activa(db: Session, id_usuario: int):
    return db.execute(text("""
        SELECT TOP 1 id_jornada, fecha_inicio FROM VENDEDOR_JORNADAS
        WHERE id_usuario = :u AND estado = 'En Progreso'
        ORDER BY id_jornada DESC
    """), {"u": id_usuario}).fetchone()


def _contar_visitas(db: Session, id_jornada: int) -> int:
    return db.execute(text(
        "SELECT COUNT(*) FROM VENDEDOR_VISITAS WHERE id_jornada = :j"
    ), {"j": id_jornada}).scalar() or 0


@router.get("/jornada-activa")
def jornada_activa(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    j = _jornada_activa(db, current_user.id)
    if not j:
        return {"success": True, "activa": False}
    return {
        "success": True, "activa": True, "id_jornada": j.id_jornada,
        "fecha_inicio": j.fecha_inicio.isoformat() if j.fecha_inicio else None,
        "visitas": _contar_visitas(db, j.id_jornada),
    }


@router.post("/activar-jornada")
def activar_jornada(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    j = _jornada_activa(db, current_user.id)
    if j:
        return {"success": True, "id_jornada": j.id_jornada,
                "fecha_inicio": j.fecha_inicio.isoformat() if j.fecha_inicio else None, "ya_activa": True}
    db.execute(text(
        "INSERT INTO VENDEDOR_JORNADAS (id_usuario, fecha_inicio, estado) VALUES (:u, GETDATE(), 'En Progreso')"
    ), {"u": current_user.id})
    db.commit()
    j = _jornada_activa(db, current_user.id)
    if not j:
        raise HTTPException(status_code=500, detail="No se pudo crear la jornada")
    return {"success": True, "id_jornada": j.id_jornada, "fecha_inicio": j.fecha_inicio.isoformat() if j.fecha_inicio else None}


@router.post("/finalizar-jornada")
def finalizar_jornada(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    db.execute(text("""
        UPDATE VENDEDOR_JORNADAS SET estado = 'Finalizada', fecha_fin = GETDATE()
        WHERE id_usuario = :u AND estado = 'En Progreso'
    """), {"u": current_user.id})
    db.commit()
    return {"success": True, "message": "Jornada finalizada"}


@router.get("/pdvs")
def get_pdvs(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    rows = db.execute(text("""
        SELECT identificador, punto_de_interes, Direccion, ciudad, localidad
        FROM PUNTOS_INTERES1 ORDER BY punto_de_interes
    """)).fetchall()
    return [{"identificador": r.identificador, "nombre": r.punto_de_interes,
             "direccion": r.Direccion, "ciudad": r.ciudad, "localidad": r.localidad} for r in rows]


@router.get("/clientes")
def get_clientes(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    rows = db.execute(text("SELECT id_cliente, cliente FROM CLIENTES ORDER BY cliente")).fetchall()
    return [{"id_cliente": r.id_cliente, "nombre": r.cliente} for r in rows]


@router.post("/registrar-visita")
def registrar_visita(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    id_punto_interes = payload.get("id_punto_interes")
    id_cliente = payload.get("id_cliente")
    vendio = payload.get("vendio")
    if not id_punto_interes or not id_cliente or vendio is None:
        raise HTTPException(status_code=400, detail="Datos incompletos")

    vendio_bit = 1 if vendio in (True, 1, "1", "true", "True") else 0
    monto = None
    razon = None
    if vendio_bit == 1:
        try:
            monto = float(payload.get("monto"))
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="El monto es requerido y debe ser numérico")
        if monto <= 0:
            raise HTTPException(status_code=400, detail="El monto debe ser mayor que cero")
    else:
        razon = (payload.get("razon_no_venta") or "").strip()
        if not razon:
            raise HTTPException(status_code=400, detail="La razón de no venta es requerida")

    j = _jornada_activa(db, current_user.id)
    if not j:
        raise HTTPException(status_code=400, detail="No tienes una jornada activa. Activa tu ruta primero.")

    lat = payload.get("latitud")
    lon = payload.get("longitud")
    try:
        lat = float(lat) if lat not in (None, "") else None
        lon = float(lon) if lon not in (None, "") else None
    except (TypeError, ValueError):
        lat, lon = None, None

    db.execute(text("""
        INSERT INTO VENDEDOR_VISITAS
            (id_jornada, id_usuario, id_punto_interes, id_cliente, fecha_hora,
             vendio, monto, razon_no_venta, latitud, longitud)
        VALUES (:j, :u, :p, :c, GETDATE(), :v, :m, :r, :lat, :lon)
    """), {
        "j": j.id_jornada, "u": current_user.id, "p": str(id_punto_interes), "c": id_cliente,
        "v": vendio_bit, "m": monto, "r": razon, "lat": lat, "lon": lon,
    })
    db.commit()
    return {"success": True, "message": "Visita registrada", "visitas": _contar_visitas(db, j.id_jornada)}


@router.get("/visitas-hoy")
def visitas_hoy(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    j = _jornada_activa(db, current_user.id)
    if not j:
        return {"success": True, "visitas": []}
    rows = db.execute(text("""
        SELECT vv.fecha_hora, vv.vendio, vv.monto, vv.razon_no_venta,
               pin.punto_de_interes, c.cliente
        FROM VENDEDOR_VISITAS vv
        LEFT JOIN PUNTOS_INTERES1 pin ON pin.identificador = vv.id_punto_interes
        LEFT JOIN CLIENTES c ON c.id_cliente = vv.id_cliente
        WHERE vv.id_jornada = :j
        ORDER BY vv.id_visita_vendedor DESC
    """), {"j": j.id_jornada}).fetchall()
    return {"success": True, "visitas": [{
        "fecha_hora": r.fecha_hora.isoformat() if r.fecha_hora else None,
        "vendio": bool(r.vendio), "monto": float(r.monto) if r.monto is not None else None,
        "razon_no_venta": r.razon_no_venta, "pdv": r.punto_de_interes, "cliente": r.cliente,
    } for r in rows]}


@router.post("/solicitar-pdv")
def solicitar_pdv(payload: dict, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    check_rol_vendedor(current_user)
    nombre = (payload.get("punto_de_interes") or "").strip()
    rif = (payload.get("rif") or "").strip()
    direccion = (payload.get("direccion") or "").strip()
    foto_tienda = payload.get("foto_tienda")
    foto_rif = payload.get("foto_rif")

    faltan = []
    if not nombre: faltan.append("nombre del PDV")
    if not rif: faltan.append("RIF")
    if not direccion: faltan.append("dirección")
    if not foto_tienda: faltan.append("foto de la tienda")
    if not foto_rif: faltan.append("foto del RIF")
    if faltan:
        raise HTTPException(status_code=400, detail="Faltan datos: " + ", ".join(faltan))

    lat = payload.get("latitud")
    lon = payload.get("longitud")
    try:
        lat = float(lat) if lat not in (None, "") else None
        lon = float(lon) if lon not in (None, "") else None
    except (TypeError, ValueError):
        lat, lon = None, None

    datos = {
        "punto_de_interes": nombre, "rif": rif, "direccion": direccion,
        "latitud": lat, "longitud": lon, "foto_tienda": foto_tienda, "foto_rif": foto_rif,
    }
    solicitud = Solicitud(
        user_id=current_user.id, tipo="creacion_pdv",
        descripcion=json.dumps(datos), estado="pendiente", created_at=datetime.now(),
    )
    db.add(solicitud)
    db.commit()
    return {"success": True, "message": "Solicitud de creación de PDV enviada. Espera la aprobación de Atención al Cliente."}
