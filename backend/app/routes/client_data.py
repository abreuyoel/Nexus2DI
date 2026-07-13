from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from datetime import date, timedelta
from app.db.session import get_db
from app.core.dependencies import get_current_user
from app.models.user import Usuario

router = APIRouter(prefix="/api/client-data", tags=["Client Data"])


def _analyst_filter(user: Usuario, alias: str = "b"):
    """Restringe los balances a los clientes+rutas asignados al analista.

    Espeja `mk_analyst` de centro_mando.py: el analista solo ve un balance si
    (a) el PDV está en alguna ruta asignada al analista (`analistas_rutas`) con
    programación activa, y (b) el cliente del balance está en `ANALISTAS_CLIENTE`.
    Devuelve ("", {}) para usuarios que no son analistas (sin restricción aquí).
    `user.id_perfil` apunta a ANALISTAS.id_analista para el rol analista.
    """
    if not (user.is_analyst and user.id_perfil):
        return "", {}
    frag = f"""
        AND EXISTS (SELECT 1 FROM RUTA_PROGRAMACION rp_a
            JOIN analistas_rutas ar_a ON rp_a.id_ruta = ar_a.id_ruta
            WHERE rp_a.id_punto_interes = {alias}.identificador_pdv
              AND rp_a.activa = 1 AND ar_a.id_analista = :analista_id)
        AND EXISTS (SELECT 1 FROM ANALISTAS_CLIENTE ac_a
            WHERE ac_a.id_cliente = {alias}.id_cliente AND ac_a.id_analista = :analista_id)
    """
    return frag, {"analista_id": int(user.id_perfil)}


@router.get("/filters")
def get_client_data_filters(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from app.services.visibility import coordinator_client_ids
    visible_ids = coordinator_client_ids(db, current_user) if current_user.is_client else None

    # We will get distinct products, chains, regions, pdvs, and mercaderistas
    query_params = {}
    where_clause = "WHERE 1=1"
    if visible_ids is not None:
        if not visible_ids:
            return {
                "productos": [], "mercaderistas": [], "pdvs": [], "cadenas": [], "regiones": [],
                "categorias": [], "departamentos": [], "cuadrantes": [], "estados": []
            }
        where_clause += f" AND b.id_cliente IN ({','.join(str(int(i)) for i in visible_ids)})"

    af, ap = _analyst_filter(current_user)
    where_clause += af
    query_params.update(ap)

    # Get distinct productos
    productos = db.execute(text(f"SELECT DISTINCT producto FROM BALANCES_TOTALES b {where_clause} AND producto IS NOT NULL"), query_params).scalars().all()

    # Get distinct mercaderistas
    mercaderistas = db.execute(text(f"SELECT DISTINCT mercaderista FROM BALANCES_TOTALES b {where_clause} AND mercaderista IS NOT NULL"), query_params).scalars().all()

    # Get distinct categorias (categoría de producto, columna propia de BALANCES_TOTALES)
    categorias = db.execute(text(f"SELECT DISTINCT categoria FROM BALANCES_TOTALES b {where_clause} AND categoria IS NOT NULL"), query_params).scalars().all()

    # Get distinct PDVs (identificadores)
    pdvs = db.execute(text(f"""
        SELECT DISTINCT p.identificador, p.punto_de_interes
        FROM BALANCES_TOTALES b
        JOIN PUNTOS_INTERES1 p ON b.identificador_pdv = p.identificador
        {where_clause}
    """), query_params).fetchall()

    # Get distinct cadenas
    cadenas = db.execute(text(f"""
        SELECT DISTINCT p.jerarquia_nivel_2 as cadena
        FROM BALANCES_TOTALES b
        JOIN PUNTOS_INTERES1 p ON b.identificador_pdv = p.identificador
        {where_clause} AND p.jerarquia_nivel_2 IS NOT NULL
    """), query_params).scalars().all()

    # Get distinct regions
    regiones = db.execute(text(f"""
        SELECT DISTINCT p.jerarquia_nivel_2_2 as region
        FROM BALANCES_TOTALES b
        JOIN PUNTOS_INTERES1 p ON b.identificador_pdv = p.identificador
        {where_clause} AND p.jerarquia_nivel_2_2 IS NOT NULL
    """), query_params).scalars().all()

    # Get distinct departamentos
    departamentos = db.execute(text(f"""
        SELECT DISTINCT p.departamento
        FROM BALANCES_TOTALES b
        JOIN PUNTOS_INTERES1 p ON b.identificador_pdv = p.identificador
        {where_clause} AND p.departamento IS NOT NULL
    """), query_params).scalars().all()

    # Get distinct cuadrantes (via RUTA_PROGRAMACION -> RUTAS_NUEVAS; RUTAS_NUEVAS no tiene FK directa
    # a punto_interes, y un punto puede tener varias filas de programación activa, por eso se agrega con MIN)
    cuadrantes = db.execute(text(f"""
        SELECT DISTINCT rc.cuadrante
        FROM BALANCES_TOTALES b
        JOIN PUNTOS_INTERES1 p ON b.identificador_pdv = p.identificador
        LEFT JOIN (
            SELECT rp.id_punto_interes, MIN(rn.cuadrante) AS cuadrante
            FROM RUTA_PROGRAMACION rp
            JOIN RUTAS_NUEVAS rn ON rp.id_ruta = rn.id_ruta
            WHERE rp.activa = 1 AND rn.cuadrante IS NOT NULL
            GROUP BY rp.id_punto_interes
        ) rc ON rc.id_punto_interes = p.identificador
        {where_clause} AND rc.cuadrante IS NOT NULL
    """), query_params).scalars().all()

    # Get distinct estados (estado de la visita)
    estados = db.execute(text(f"""
        SELECT DISTINCT v.estado
        FROM BALANCES_TOTALES b
        LEFT JOIN VISITAS_MERCADERISTA v ON b.id_visita = v.id_visita
        {where_clause} AND v.estado IS NOT NULL
    """), query_params).scalars().all()

    return {
        "productos": sorted(productos),
        "mercaderistas": sorted(mercaderistas),
        "pdvs": [{"id": p.identificador, "nombre": p.punto_de_interes} for p in pdvs],
        "cadenas": sorted(cadenas),
        "regiones": sorted(regiones),
        "categorias": sorted(categorias),
        "departamentos": sorted(departamentos),
        "cuadrantes": sorted(cuadrantes),
        "estados": sorted(estados)
    }

@router.get("/balances")
def get_client_balances(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    producto: Optional[str] = None,
    cadena: Optional[str] = None,
    region: Optional[str] = None,
    pdv: Optional[str] = None,
    mercaderista: Optional[str] = None,
    visita_id: Optional[int] = None,
    categoria: Optional[str] = None,
    departamento: Optional[str] = None,
    cuadrante: Optional[str] = None,
    estado: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    from app.services.visibility import coordinator_client_ids
    visible_ids = coordinator_client_ids(db, current_user) if current_user.is_client else None

    # Default to last 30 days if no dates provided
    if not fecha_inicio and not fecha_fin:
        fecha_fin = date.today()
        fecha_inicio = fecha_fin - timedelta(days=30)

    query_str = """
        SELECT
            b.id_balance,
            b.fecha_balance,
            b.id_visita as visita_id,
            p.jerarquia_nivel_2_2 as region,
            p.jerarquia_nivel_2 as cadena,
            p.punto_de_interes as pdv_nombre,
            p.departamento as departamento,
            rc.cuadrante as cuadrante,
            v.estado as estado,
            b.mercaderista,
            b.producto,
            b.categoria,
            b.inv_inicial,
            b.inv_final,
            b.inv_deposito,
            b.caras,
            b.precio_bs,
            b.precio_ds
        FROM BALANCES_TOTALES b
        LEFT JOIN PUNTOS_INTERES1 p ON b.identificador_pdv = p.identificador
        LEFT JOIN (
            SELECT rp.id_punto_interes, MIN(rn.cuadrante) AS cuadrante
            FROM RUTA_PROGRAMACION rp
            JOIN RUTAS_NUEVAS rn ON rp.id_ruta = rn.id_ruta
            WHERE rp.activa = 1 AND rn.cuadrante IS NOT NULL
            GROUP BY rp.id_punto_interes
        ) rc ON rc.id_punto_interes = p.identificador
        LEFT JOIN VISITAS_MERCADERISTA v ON b.id_visita = v.id_visita
        WHERE 1=1
    """
    
    params = {}

    if visible_ids is not None:
        if not visible_ids:
            return []
        query_str += f" AND b.id_cliente IN ({','.join(str(int(i)) for i in visible_ids)})"

    af, ap = _analyst_filter(current_user)
    query_str += af
    params.update(ap)

    if fecha_inicio:
        query_str += " AND b.fecha_balance >= :fecha_inicio"
        params["fecha_inicio"] = fecha_inicio
        
    if fecha_fin:
        # Add 1 day to include the entire end date
        query_str += " AND b.fecha_balance < :fecha_fin_plus_one"
        params["fecha_fin_plus_one"] = fecha_fin + timedelta(days=1)
        
    if producto:
        query_str += " AND b.producto = :producto"
        params["producto"] = producto
        
    if cadena:
        query_str += " AND p.jerarquia_nivel_2 = :cadena"
        params["cadena"] = cadena
        
    if region:
        query_str += " AND p.jerarquia_nivel_2_2 = :region"
        params["region"] = region
        
    if pdv:
        query_str += " AND b.identificador_pdv = :pdv"
        params["pdv"] = pdv
        
    if mercaderista:
        query_str += " AND b.mercaderista = :mercaderista"
        params["mercaderista"] = mercaderista
        
    if visita_id:
        query_str += " AND b.id_visita = :visita_id"
        params["visita_id"] = visita_id

    if categoria:
        query_str += " AND b.categoria = :categoria"
        params["categoria"] = categoria

    if departamento:
        query_str += " AND p.departamento = :departamento"
        params["departamento"] = departamento

    if cuadrante:
        query_str += " AND rc.cuadrante = :cuadrante"
        params["cuadrante"] = cuadrante

    if estado:
        query_str += " AND v.estado = :estado"
        params["estado"] = estado

    query_str += " ORDER BY b.fecha_balance DESC"

    rows = db.execute(text(query_str), params).fetchall()

    results = []
    for row in rows:
        results.append({
            "id_balance": row.id_balance,
            "fecha_balance": str(row.fecha_balance) if row.fecha_balance else None,
            "visita_id": row.visita_id,
            "region": row.region,
            "cadena": row.cadena,
            "pdv_nombre": row.pdv_nombre,
            "departamento": row.departamento,
            "cuadrante": row.cuadrante,
            "estado": row.estado,
            "mercaderista": row.mercaderista,
            "producto": row.producto,
            "categoria": row.categoria,
            "inv_inicial": row.inv_inicial,
            "inv_final": row.inv_final,
            "inv_deposito": row.inv_deposito,
            "caras": row.caras,
            "precio_bs": row.precio_bs,
            "precio_ds": row.precio_ds
        })
        
    return results
