from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import date as _date, datetime, timedelta
import calendar as _calendar
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.models.user import Usuario

router = APIRouter(prefix="/api/centro-mando", tags=["Centro de Mando"])

def execute_query(db: Session, query: str, params: tuple = (), timeout: int = 0):
    """timeout (segundos, 0 = default del driver): para queries nuevas/no
    probadas contra el volumen real de datos -- si algo sale mal (plan malo,
    bloqueo por un DDL corriendo, etc.) falla rápido con un error claro en
    vez de colgar la conexión (y el thread del pool, con --workers 1) hasta
    que Cloudflare corta en 100s (524).

    Se pone en la CONEXIÓN (conn.timeout), no en el cursor: esta versión de
    pyodbc no tiene Cursor.timeout ('pyodbc.Cursor' object has no attribute
    'timeout') -- eso rompía la llamada ANTES de ejecutar la query, así que
    nunca llegaba a correr. La conexión es del pool de SQLAlchemy y se
    reusa entre requests, así que el timeout se restaura al valor previo al
    salir para no afectar a otras queries que usen esta misma conexión
    después."""
    conn = db.connection().connection
    prev_timeout = 0
    if timeout:
        try:
            prev_timeout = conn.timeout
            conn.timeout = timeout
        except Exception:
            timeout = 0  # no se pudo aplicar -- seguir sin timeout en vez de romper la query
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        if cursor.description:
            rows = cursor.fetchall()
            return rows
        return []
    except Exception as e:
        print(f"Error in execute_query: {e}")
        raise
    finally:
        if timeout:
            try:
                conn.timeout = prev_timeout
            except Exception:
                pass

DIAS_ES = {
    'Monday':    'Lunes',
    'Tuesday':   'Martes',
    'Wednesday': 'Miércoles',
    'Thursday':  'Jueves',
    'Friday':    'Viernes',
    'Saturday':  'Sábado',
    'Sunday':    'Domingo',
}

def _dia_es(fecha: _date) -> str:
    return DIAS_ES[fecha.strftime('%A')]

def _clientes_de_analista(db: Session, analista_id: int) -> List[int]:
    """Clientes que el analista tiene asignados vía analistas_rutas ->
    RUTA_PROGRAMACION (activa=1) — misma fuente de verdad que mk_analyst()."""
    if not analista_id:
        return []
    rows = execute_query(db, """
        SELECT DISTINCT rp.id_cliente
        FROM analistas_rutas ar
        JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = ar.id_ruta
        WHERE ar.id_analista = ? AND rp.activa = 1
    """, (analista_id,))
    return [r[0] for r in rows if r[0] is not None]

def mk_analyst(is_analyst: bool, analista_id: int, vm_a='vm', pin_a='pin', c_a='c'):
    if not (is_analyst and analista_id):
        return "", []
    # Fuente de verdad única: analistas_rutas -> RUTA_PROGRAMACION. Antes esto
    # además exigía una fila en ANALISTAS_CLIENTE (tabla desactualizada) — un
    # analista con ruta asignada pero sin fila ahí quedaba viendo 0 resultados
    # para ese cliente pese a tener acceso real.
    f = f"""
    AND EXISTS (SELECT 1 FROM RUTA_PROGRAMACION rp_a
        JOIN analistas_rutas ar_a ON rp_a.id_ruta = ar_a.id_ruta
        JOIN MERCADERISTAS_RUTAS mr_a ON mr_a.id_ruta = rp_a.id_ruta
        WHERE rp_a.id_punto_interes = {pin_a}.identificador
          AND rp_a.id_cliente = {c_a}.id_cliente
          AND rp_a.activa = 1 AND ar_a.id_analista = ?
          AND mr_a.id_mercaderista = {vm_a}.id_mercaderista)
    """
    return f, [analista_id]

@router.get("/clientes")
def listar_clientes(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        # El analista solo debe ver los clientes de SUS rutas asignadas
        # (analistas_rutas -> RUTA_PROGRAMACION, fuente de verdad única — no
        # ANALISTAS_CLIENTE, desactualizada). Admin y coordinador
        # general/exclusivo ven "todos los clientes" sin filtro (es
        # justamente lo que este dropdown/vista debe mostrarles).
        filtro = ""
        params: tuple = ()
        if current_user.is_analyst and current_user.id_perfil:
            filtro = """
                AND EXISTS (SELECT 1 FROM analistas_rutas ar_a
                    WHERE ar_a.id_ruta = rp.id_ruta AND ar_a.id_analista = ?)
            """
            params = (current_user.id_perfil,)

        rows = execute_query(db, f"""
            SELECT DISTINCT c.id_cliente, c.cliente
            FROM CLIENTES c
            JOIN RUTA_PROGRAMACION rp ON rp.id_cliente = c.id_cliente
            WHERE rp.activa = 1 AND c.cliente IS NOT NULL
            {filtro}
            ORDER BY c.cliente
        """, params)
        return {
            "success": True,
            "clientes": [{"id_cliente": r[0], "cliente": r[1]} for r in rows]
        }
    except Exception as e:
        return {"success": False, "message": str(e), "clientes": []}

@router.get("/horas-trabajadas")
def horas_trabajadas(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(require_analyst_or_admin),
):
    """Horas trabajadas y tiempo de traslado por mercaderista en el rango,
    de mayor a menor por horas trabajadas.

    No existe check-in/check-out para mercaderistas (a diferencia de vendedor/
    encuestador, que sí tienen tabla de jornada) -- ambas métricas se
    aproximan con las fotos que cada mercaderista sube (FOTOS_TOTALES.
    fecha_registro), que es el único rastro con timestamp que existe:

    - Horas trabajadas: lapso entre la primera y la última foto de cada día,
      sumado sobre todos los días del rango.
    - Tiempo de traslado: un mismo PDV puede tener más de un cliente (el
      mercaderista no "termina" el PDV hasta hacer gestión de todos), así que
      cambiar de cliente en el MISMO PDV no es traslado. Solo cuenta el lapso
      entre la ÚLTIMA foto en un PDV y la PRIMERA foto en un PDV DISTINTO
      dentro del mismo día -- se calcula con LAG() ordenando las fotos de
      cada mercaderista por día y sumando el lapso cada vez que el PDV
      cambia respecto a la foto anterior.

    Admin ve todos; analista solo los mercaderistas de SUS rutas
    (analistas_rutas -> RUTA_PROGRAMACION -> MERCADERISTAS_RUTAS). Con
    cliente_id (mismo filtro "Cliente" de arriba del dashboard) solo cuenta
    las fotos de visitas de ESE cliente -- igual que resumen-dia/activaciones,
    para que las pestañas queden consistentes entre sí.

    Van DOS queries chicas en vez de una sola con la misma subconsulta
    referenciada 2 veces: la primera versión (CTE "base" reusada por
    "por_dia" Y "transiciones") recalculaba el join completo dos veces por
    llamada y terminó en 524 de Cloudflare (>100s) con el volumen real de
    datos -- no se probó contra ese volumen antes de desplegar. Separarlas
    es más fácil de razonar y cada una se parece a queries ya probadas de
    este archivo. Ambas con timeout explícito: si alguna vuelve a salir
    mal (plan malo, bloqueo por un DDL corriendo, etc.) que falle rápido con
    un error claro en vez de colgar la conexión -- y el thread del pool, con
    --workers 1 -- hasta que el proxy corta solo."""
    try:
        hoy = _date.today()
        if not desde:
            desde = hoy.isoformat()
        if not hasta:
            hasta = desde

        cliente_filter = ""
        params: tuple = (desde, hasta)
        if cliente_id:
            cliente_filter = " AND v.id_cliente = ?"
            params = params + (cliente_id,)

        analyst_filter = ""
        if current_user.is_analyst and current_user.id_perfil:
            analyst_filter = """
                AND EXISTS (
                    SELECT 1 FROM MERCADERISTAS_RUTAS mr
                    JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = mr.id_ruta
                    JOIN analistas_rutas ar ON ar.id_ruta = rp.id_ruta
                    WHERE mr.id_mercaderista = v.id_mercaderista
                      AND ar.id_analista = ? AND rp.activa = 1
                )
            """
            params = params + (current_user.id_perfil,)

        # 1) Horas trabajadas por día (span MIN/MAX), sumadas por mercaderista
        # -- misma forma que ya funcionaba antes del rediseño con traslado.
        horas_rows = execute_query(db, f"""
            SELECT v.id_mercaderista, m.nombre,
                   CAST(f.fecha_registro AS DATE) AS dia,
                   MIN(f.fecha_registro), MAX(f.fecha_registro),
                   COUNT(DISTINCT f.id_visita)
            FROM FOTOS_TOTALES f
            JOIN VISITAS_MERCADERISTA v ON v.id_visita = f.id_visita
            JOIN MERCADERISTAS m ON m.id_mercaderista = v.id_mercaderista
            WHERE f.fecha_registro >= CAST(? AS DATE) AND f.fecha_registro < DATEADD(day, 1, CAST(? AS DATE))
            {cliente_filter}
            {analyst_filter}
            GROUP BY v.id_mercaderista, m.nombre, CAST(f.fecha_registro AS DATE)
        """, params, timeout=20)

        agg: dict = {}
        for mid, nombre, dia, inicio, fin, n_visitas in horas_rows:
            if not inicio or not fin:
                continue
            a = agg.setdefault(mid, {"id_mercaderista": mid, "mercaderista": nombre, "segundos": 0, "dias": 0, "visitas": 0})
            a["segundos"] += int((fin - inicio).total_seconds())
            a["dias"] += 1
            a["visitas"] += n_visitas

        # 2) Tiempo de traslado: única pasada por el PDV de cada foto, sin
        # recalcular el join de arriba -- CTE referenciada una sola vez.
        traslado_rows = execute_query(db, f"""
            WITH base AS (
                SELECT v.id_mercaderista,
                       v.identificador_punto_interes AS pdv,
                       CAST(f.fecha_registro AS DATE) AS dia,
                       f.fecha_registro AS ts
                FROM FOTOS_TOTALES f
                JOIN VISITAS_MERCADERISTA v ON v.id_visita = f.id_visita
                WHERE f.fecha_registro >= CAST(? AS DATE) AND f.fecha_registro < DATEADD(day, 1, CAST(? AS DATE))
                {cliente_filter}
                {analyst_filter}
            ),
            transiciones AS (
                SELECT id_mercaderista, pdv, ts,
                       LAG(pdv) OVER (PARTITION BY id_mercaderista, dia ORDER BY ts) AS pdv_prev,
                       LAG(ts)  OVER (PARTITION BY id_mercaderista, dia ORDER BY ts) AS ts_prev
                FROM base
            )
            SELECT id_mercaderista,
                   SUM(CASE WHEN pdv_prev IS NOT NULL AND pdv_prev <> pdv
                            THEN DATEDIFF(SECOND, ts_prev, ts) ELSE 0 END) AS segundos_traslado
            FROM transiciones
            GROUP BY id_mercaderista
        """, params, timeout=20)
        traslado_map = {mid: int(seg or 0) for mid, seg in traslado_rows}

        out = []
        for a in agg.values():
            dias = a["dias"]
            horas = round(a["segundos"] / 3600, 1)
            seg_trasl = traslado_map.get(a["id_mercaderista"], 0)
            trasl_horas = round(seg_trasl / 3600, 1)
            out.append({
                "id_mercaderista": a["id_mercaderista"],
                "mercaderista": a["mercaderista"],
                "horas_trabajadas": horas,
                "horas_promedio_dia": round(horas / dias, 1) if dias else 0,
                "dias_trabajados": dias,
                "visitas": a["visitas"],
                "tiempo_traslado_horas": trasl_horas,
                "tiempo_traslado_promedio_dia_min": round(seg_trasl / 60 / dias, 1) if dias else 0,
            })
        out.sort(key=lambda x: x["horas_trabajadas"], reverse=True)
        return {"success": True, "desde": desde, "hasta": hasta, "mercaderistas": out}
    except Exception as e:
        return {"success": False, "message": str(e), "mercaderistas": []}

@router.get("/resumen-dia")
def resumen_dia(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        if current_user.is_client and not current_user.rol == 'admin':
            cliente_id = current_user.id_perfil

        # Un analista sin cliente_id explícito veía el resumen agregado de
        # "todos los clientes" del sistema — acá no había NINGÚN filtro de
        # analista, a diferencia de /activaciones (que sí usa mk_analyst()).
        # Se acota a sus propios clientes (analistas_rutas), igual que ahí.
        analista_cliente_ids: List[int] = []
        if current_user.is_analyst and current_user.id_perfil:
            analista_cliente_ids = _clientes_de_analista(db, current_user.id_perfil)
            if cliente_id and cliente_id not in analista_cliente_ids:
                raise HTTPException(status_code=403, detail="No autorizado para este cliente")
        is_analyst_scoped = current_user.is_analyst and current_user.id_perfil and not cliente_id
        if is_analyst_scoped and not analista_cliente_ids:
            return {
                "success": True, "cliente_id": None, "cliente_nombre": "Sin clientes asignados",
                "desde": _date.today().isoformat(), "hasta": _date.today().isoformat(),
                "mercaderistas": {"total_asignados": 0, "planificados_hoy": 0, "activos_hoy": 0,
                                   "faltantes_hoy": 0, "exclusivos": 0, "tradex": 0,
                                   "detalle": [], "faltantes": [], "activos": []},
                "rutas": {"planificadas": 0, "activas": 0, "completadas": 0, "detalle": []},
                "puntos_interes": {"planificados": 0, "activos": 0, "completados": 0, "detalle": []},
                "clientes_tradex": {"planificados": 0, "activos": 0, "completados": 0, "aplica": False},
            }
        cli_ph = ",".join("?" for _ in analista_cliente_ids)

        try:
            d_desde = datetime.strptime(desde, '%Y-%m-%d').date() if desde else _date.today()
            d_hasta = datetime.strptime(hasta, '%Y-%m-%d').date() if hasta else d_desde
        except ValueError:
            raise HTTPException(status_code=400, detail="Fecha inválida")
            
        if d_hasta < d_desde:
            d_hasta = d_desde

        # Calcular day_counts
        day_counts = { 'Lunes':0, 'Martes':0, 'Miércoles':0, 'Jueves':0, 'Viernes':0, 'Sábado':0, 'Domingo':0 }
        curr = d_desde
        while curr <= d_hasta:
            day_counts[_dia_es(curr)] += 1
            curr += timedelta(days=1)
            
        days_in_range = [d for d, c in day_counts.items() if c > 0]
        if not days_in_range:
            days_in_range = ['Lunes'] # fallback

        cliente_tipo = None
        cliente_nombre = "Todos los clientes"
        if cliente_id:
            cli_row = execute_query(db, "SELECT cliente, id_tipo_cliente FROM CLIENTES WHERE id_cliente = ?", (cliente_id,))
            if cli_row:
                cliente_nombre = cli_row[0][0]
                cliente_tipo = cli_row[0][1]
            else:
                cliente_nombre = f"Cliente {cliente_id}"

        serv_filter = " AND rn.servicio = 'Exclusivo'" if cliente_tipo == 3 else ""

        # 1) MERCADERISTAS ASIGNADOS
        if cliente_id:
            merc_asig_q = f"""
                SELECT DISTINCT m.id_mercaderista, m.nombre, m.cedula,
                                ISNULL(m.tipo,'Mercaderista') AS tipo_camp
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = mr.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1 AND rp.id_cliente = ?{serv_filter}
            """
            asignados = execute_query(db, merc_asig_q, (cliente_id,))
        else:
            cli_filter = f" AND rp.id_cliente IN ({cli_ph})" if is_analyst_scoped else ""
            merc_asig_q = f"""
                SELECT DISTINCT m.id_mercaderista, m.nombre, m.cedula,
                                ISNULL(m.tipo,'Mercaderista') AS tipo_camp
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = mr.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1{cli_filter}
            """
            asignados = execute_query(db, merc_asig_q, tuple(analista_cliente_ids))

        asignados_map = {r[0]: {"id_mercaderista": r[0], "nombre": r[1],
                                "cedula": r[2], "tipo_campo": r[3]}
                         for r in asignados}

        # 2) MERCADERISTAS PLANIFICADOS
        ph = ",".join("?" for _ in days_in_range)
        if cliente_id:
            plan_hoy_q = f"""
                SELECT DISTINCT m.id_mercaderista, rp.dia
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta         = mr.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1
                  AND rp.dia IN ({ph}) AND rp.id_cliente = ?{serv_filter}
            """
            plan_hoy = execute_query(db, plan_hoy_q, tuple(days_in_range + [cliente_id]))
        else:
            cli_filter = f" AND rp.id_cliente IN ({cli_ph})" if is_analyst_scoped else ""
            plan_hoy_q = f"""
                SELECT DISTINCT m.id_mercaderista, rp.dia
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta         = mr.id_ruta
                WHERE m.activo = 1 AND rp.activa = 1
                  AND rp.dia IN ({ph}){cli_filter}
            """
            plan_hoy = execute_query(db, plan_hoy_q, tuple(days_in_range + analista_cliente_ids))
            
        plan_counts = {}
        for r in plan_hoy:
            mid = r[0]
            dia = r[1]
            plan_counts[mid] = plan_counts.get(mid, 0) + day_counts.get(dia, 0)
        
        total_planificados = sum(plan_counts.values())

        # 3) MERCADERISTAS QUE ACTIVARON
        if cliente_id:
            activos_hoy_q = f"""
                SELECT DISTINCT ra.id_mercaderista, CAST(ra.fecha_hora_activacion AS DATE)
                FROM RUTAS_ACTIVADAS ra
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = ra.id_ruta
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = ra.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                WHERE ra.fecha_hora_activacion >= CAST(? AS DATE) AND ra.fecha_hora_activacion < DATEADD(day, 1, CAST(? AS DATE))
                  AND mr.id_mercaderista = ra.id_mercaderista
                  AND rp.id_cliente = ?{serv_filter}
            """
            activos_rows = execute_query(db, activos_hoy_q, (d_desde, d_hasta, cliente_id))
        else:
            cli_filter = f" AND rp.id_cliente IN ({cli_ph})" if is_analyst_scoped else ""
            activos_hoy_q = f"""
                SELECT DISTINCT ra.id_mercaderista, CAST(ra.fecha_hora_activacion AS DATE)
                FROM RUTAS_ACTIVADAS ra
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = ra.id_ruta
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = ra.id_ruta
                WHERE ra.fecha_hora_activacion >= CAST(? AS DATE) AND ra.fecha_hora_activacion < DATEADD(day, 1, CAST(? AS DATE))
                  AND mr.id_mercaderista = ra.id_mercaderista{cli_filter}
            """
            activos_rows = execute_query(db, activos_hoy_q, tuple([d_desde, d_hasta] + analista_cliente_ids))
            
        act_counts = {}
        for r in activos_rows:
            mid = r[0]
            act_counts[mid] = act_counts.get(mid, 0) + 1
            
        total_activos = sum(act_counts.values())

        # 4) CLASIFICACIÓN
        if asignados_map:
            ids = list(asignados_map.keys())
            ph2 = ",".join("?" for _ in ids)
            clas_q = f"""
                SELECT mr.id_mercaderista, COUNT(DISTINCT rp.id_cliente) AS n_cli
                FROM MERCADERISTAS_RUTAS mr
                JOIN RUTA_PROGRAMACION rp ON rp.id_ruta = mr.id_ruta
                WHERE mr.id_mercaderista IN ({ph2}) AND rp.activa = 1
                GROUP BY mr.id_mercaderista
            """
            for mid, n in execute_query(db, clas_q, tuple(ids)):
                if cliente_tipo == 3:
                    asignados_map[mid]["tipo_servicio"] = "Exclusivo"
                else:
                    asignados_map[mid]["tipo_servicio"] = "Exclusivo" if n == 1 else "Tradex"
                asignados_map[mid]["n_clientes_asignados"] = int(n)
        for m in asignados_map.values():
            if cliente_tipo == 3:
                m["tipo_servicio"] = "Exclusivo"
            else:
                m.setdefault("tipo_servicio", "Exclusivo")
            m.setdefault("n_clientes_asignados", 1)

        # 5) RUTAS
        if cliente_id:
            rutas_plan_q = f"""
                SELECT DISTINCT rp.id_ruta, rn.ruta, mr.id_mercaderista, m.nombre, rp.dia
                FROM RUTA_PROGRAMACION rp
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph}) AND rp.id_cliente = ?{serv_filter}
            """
            rutas_plan_rows = execute_query(db, rutas_plan_q, tuple(days_in_range + [cliente_id]))
        else:
            cli_filter = f" AND rp.id_cliente IN ({cli_ph})" if is_analyst_scoped else ""
            rutas_plan_q = f"""
                SELECT DISTINCT rp.id_ruta, rn.ruta, mr.id_mercaderista, m.nombre, rp.dia
                FROM RUTA_PROGRAMACION rp
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph}){cli_filter}
            """
            rutas_plan_rows = execute_query(db, rutas_plan_q, tuple(days_in_range + analista_cliente_ids))

        ruta_merc_pairs = {}
        for r in rutas_plan_rows:
            id_ruta = r[0]
            ruta_nombre = r[1]
            id_merc = r[2]
            nombre_merc = r[3]
            dia = r[4]
            k = (id_ruta, id_merc)
            if k not in ruta_merc_pairs:
                ruta_merc_pairs[k] = {
                    "id_ruta": id_ruta, "ruta": ruta_nombre,
                    "id_mercaderista": id_merc, "nombre_mercaderista": nombre_merc,
                    "estado": "Planificada",
                    "planificadas": 0, "activas": 0, "completadas": 0,
                    "pois_plan": 0, "pois_act": 0, "pois_com": 0,
                    "clientes_plan": 0, "clientes_act": 0, "clientes_com": 0
                }
            ruta_merc_pairs[k]["planificadas"] += day_counts.get(dia, 0)

        ra_q = """
            SELECT ra.id_ruta, ra.id_mercaderista, ra.estado, CAST(ra.fecha_hora_activacion AS DATE) as fd
            FROM RUTAS_ACTIVADAS ra
            WHERE ra.fecha_hora_activacion >= CAST(? AS DATE) AND ra.fecha_hora_activacion < DATEADD(day, 1, CAST(? AS DATE))
        """
        ra_rows = execute_query(db, ra_q, (d_desde, d_hasta))

        # Agrupar estado por ruta_merc -- una ruta puede reactivarse y
        # finalizarse varias veces el mismo día (ej. reabrir una ya
        # finalizada), así que NO se suma +1 por cada fila de
        # RUTAS_ACTIVADAS (eso hacía que activas/completadas superaran a
        # planificadas y diera "Pendientes" negativo). Cada ruta/mercaderista
        # cuenta como máximo 1 vez: "Finalizado" si en algún momento del
        # rango llegó a estarlo, "En Progreso" si no.
        ruta_estado_final: dict = {}
        for rid, mid, estado, fd in ra_rows:
            k = (rid, mid)
            if k not in ruta_merc_pairs:
                continue
            if estado == 'Finalizado' or ruta_estado_final.get(k) == 'Finalizado':
                ruta_estado_final[k] = 'Finalizado'
            else:
                ruta_estado_final[k] = 'En Progreso'

        # activas y completadas mutuamente excluyentes (una ruta finalizada
        # NO también cuenta como "activa") -- el frontend hace
        # Pend. = Plan. - Activas - Completadas, así que si se solapan,
        # las completadas se restan dos veces y da "Pendientes" negativo.
        for k, estado_final in ruta_estado_final.items():
            if estado_final == 'Finalizado':
                ruta_merc_pairs[k]["completadas"] = 1
            else:
                ruta_merc_pairs[k]["activas"] = 1

        rutas_planificadas = sum(x["planificadas"] for x in ruta_merc_pairs.values())
        rutas_activas      = sum(x["activas"] for x in ruta_merc_pairs.values())
        rutas_completadas  = sum(x["completadas"] for x in ruta_merc_pairs.values())

        # 6) POIs
        if cliente_id:
            pois_plan_q = f"""
                SELECT DISTINCT rp.id_punto_interes, mr.id_mercaderista,
                                pin.punto_de_interes, rp.id_ruta, rn.ruta, rp.dia,
                                pin.departamento, rp.prioridad
                FROM RUTA_PROGRAMACION rp
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN PUNTOS_INTERES1 pin    ON pin.identificador = rp.id_punto_interes
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph}) AND rp.id_cliente = ?{serv_filter}
            """
            pois_plan_rows = execute_query(db, pois_plan_q, tuple(days_in_range + [cliente_id]))
        else:
            cli_filter = f" AND rp.id_cliente IN ({cli_ph})" if is_analyst_scoped else ""
            pois_plan_q = f"""
                SELECT DISTINCT rp.id_punto_interes, mr.id_mercaderista,
                                pin.punto_de_interes, rp.id_ruta, rn.ruta, rp.dia,
                                pin.departamento, rp.prioridad
                FROM RUTA_PROGRAMACION rp
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN PUNTOS_INTERES1 pin    ON pin.identificador = rp.id_punto_interes
                JOIN MERCADERISTAS m        ON m.id_mercaderista = mr.id_mercaderista
                WHERE rp.activa = 1 AND m.activo = 1
                  AND rp.dia IN ({ph}){cli_filter}
            """
            pois_plan_rows = execute_query(db, pois_plan_q, tuple(days_in_range + analista_cliente_ids))

        # Estado real por PUNTO (no por punto+mercaderista): tiene_act/tiene_des
        # sale de la foto existiendo, sin exigir Estado='Aprobada' -- "activo"/
        # "completado" es sobre lo que el mercaderista YA subió, no sobre lo que
        # el analista ya revisó. Deliberadamente NO se cruza contra qué
        # mercaderista tenía PLANIFICADO ese punto en MERCADERISTAS_RUTAS: si
        # otro cubrió la ruta ese día (cobertura/reemplazo), el punto sigue
        # activado/completado igual, y antes ese cruce lo dejaba en 0 -- tanto
        # acá (detalle de "Ver PDVs") como en el agregado de la tarjeta.
        if cliente_id:
            real_cli_filter = " AND vm.id_cliente = ?"
            real_params = [d_desde, d_hasta, cliente_id]
        else:
            real_cli_filter = f" AND vm.id_cliente IN ({cli_ph})" if is_analyst_scoped else ""
            real_params = [d_desde, d_hasta] + analista_cliente_ids

        pois_reales_q = f"""
            SELECT vm.identificador_punto_interes,
                   MAX(CASE WHEN ft.id_tipo_foto=5 THEN 1 ELSE 0 END) AS tiene_act,
                   MAX(CASE WHEN ft.id_tipo_foto=6 THEN 1 ELSE 0 END) AS tiene_des
            FROM VISITAS_MERCADERISTA vm
            LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita AND ft.id_tipo_foto IN (5,6)
            WHERE vm.fecha_visita >= CAST(? AS DATE) AND vm.fecha_visita < DATEADD(day, 1, CAST(? AS DATE)){real_cli_filter}
            GROUP BY vm.identificador_punto_interes
        """
        pois_reales_rows = execute_query(db, pois_reales_q, tuple(real_params))
        # .strip(): id_punto_interes/identificador_punto_interes pueden venir de
        # columnas CHAR de ancho fijo -- SQL Server las compara ignorando
        # espacios finales (por eso el cruce A/B daba 0 diferencias en SQL),
        # pero pyodbc devuelve el string CRUDO con el padding, y Python sí
        # distingue "AIK0002" de "AIK0002   " -- el cruce en memoria de abajo
        # nunca encontraba el punto real aunque fuera la misma fila.
        real_por_punto = {
            (id_punto or "").strip(): (bool(tiene_act), bool(tiene_des))
            for id_punto, tiene_act, tiene_des in (pois_reales_rows or [])
        }

        pois_status = {}
        for id_punto_raw, id_merc, nombre_punto, id_ruta, ruta_nombre, dia, depto, prio in pois_plan_rows:
            id_punto = (id_punto_raw or "").strip()
            key = (id_punto, id_merc)
            if key not in pois_status:
                pois_status[key] = {
                    "id_punto": id_punto, "punto_de_interes": nombre_punto,
                    "id_mercaderista": id_merc, "id_ruta": id_ruta, "ruta": ruta_nombre,
                    "mercaderista": asignados_map.get(id_merc, {}).get("nombre", "Desconocido"),
                    "departamento": depto, "prioridad": prio,
                    "plan": 0, "act": 0, "com": 0,
                    "clientes_plan": 0, "clientes_act": 0, "clientes_com": 0
                }
            pois_status[key]["plan"] += day_counts.get(dia, 0)
            pois_status[key]["clientes_plan"] += day_counts.get(dia, 0)

        for key, ent in pois_status.items():
            real = real_por_punto.get(key[0])
            if real:
                tiene_act, tiene_des = real
                act = 1 if tiene_act else 0
                com = 1 if (tiene_act and tiene_des) else 0
                ent["act"] = act
                ent["com"] = com
                ent["clientes_act"] = act
                ent["clientes_com"] = com

            pair = ruta_merc_pairs.get((ent["id_ruta"], ent["id_mercaderista"]))
            if pair is not None:
                pair["pois_plan"] += ent["plan"]
                pair["pois_act"] += ent["act"]
                pair["pois_com"] += ent["com"]
                pair["clientes_plan"] += ent["clientes_plan"]
                pair["clientes_act"]  += ent["clientes_act"]
                pair["clientes_com"]  += ent["clientes_com"]

        pois_planificados = sum(v["plan"] for v in pois_status.values())

        # Agregado de la tarjeta: misma fuente (real_por_punto) que el detalle
        # de arriba, cuenta puntos DISTINTOS (no pares punto+mercaderista) para
        # no duplicar un punto compartido por varios mercaderistas planificados.
        pois_activos = pois_completados = 0
        for tiene_act, tiene_des in real_por_punto.values():
            if tiene_act and tiene_des:
                pois_completados += 1
            elif tiene_act:
                pois_activos += 1

        # 7) CLIENTES
        tradex_ids = [mid for mid, m in asignados_map.items()
                      if m.get("tipo_servicio") == "Tradex"]
        clientes_plan = clientes_act = clientes_com = 0

        if tradex_ids:
            ph2 = ",".join("?" for _ in tradex_ids)
            # Este breakdown es intencionalmente cruzado entre TODOS los
            # clientes del mercaderista Tradex — pero para un analista debe
            # quedar acotado a SUS clientes, para no filtrar totales de
            # clientes que no maneja.
            cli_filter = f" AND rp.id_cliente IN ({cli_ph})" if is_analyst_scoped else ""
            tradex_pois_q = f"""
                SELECT rp.id_punto_interes, mr.id_mercaderista, rp.id_cliente, rp.dia
                FROM RUTA_PROGRAMACION rp
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                WHERE rp.activa = 1 AND rp.dia IN ({ph})
                  AND mr.id_mercaderista IN ({ph2}){cli_filter}
            """
            # cli_filter (arriba) solo agrega los placeholders de cli_ph cuando
            # is_analyst_scoped es True -- a diferencia de los demás bloques de
            # esta función, este no ramifica por "if cliente_id", así que hay
            # que condicionar los params de la misma forma o sobran valores
            # sin marcador correspondiente (pyodbc.ProgrammingError: "SQL
            # contains N parameter markers, but M parameters were supplied").
            tradex_cli_params = analista_cliente_ids if is_analyst_scoped else []
            tradex_rows = execute_query(db, tradex_pois_q, tuple(days_in_range + tradex_ids + tradex_cli_params))

            estado_visita_full_q = """
                SELECT vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE),
                       MAX(CASE WHEN ft.id_tipo_foto=5 THEN 1 ELSE 0 END),
                       MAX(CASE WHEN ft.id_tipo_foto=6 THEN 1 ELSE 0 END)
                FROM VISITAS_MERCADERISTA vm
                LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita
                WHERE vm.fecha_visita >= CAST(? AS DATE) AND vm.fecha_visita < DATEADD(day, 1, CAST(? AS DATE))
                GROUP BY vm.identificador_punto_interes, vm.id_mercaderista, vm.id_cliente, CAST(vm.fecha_visita AS DATE)
            """
            ev_full = execute_query(db, estado_visita_full_q, (d_desde, d_hasta))
            ev_full_map = {(r[0], r[1], r[2], r[3]): {"act": bool(r[4]), "des": bool(r[5])}
                           for r in ev_full}
                           
            ev_full_agg = {}
            for (id_p, id_m, id_c, fd), st in ev_full_map.items():
                d = ev_full_agg.setdefault((id_p, id_m, id_c), {"act": 0, "com": 0})
                if st["act"]: d["act"] += 1
                if st["act"] and st["des"]: d["com"] += 1

            t_plan = {}
            for id_punto, id_merc, id_cli, dia in tradex_rows:
                key = (id_punto, id_merc, id_cli)
                t_plan[key] = t_plan.get(key, 0) + day_counts.get(dia, 0)
                
            clientes_plan = sum(t_plan.values())
            for key, plan_cnt in t_plan.items():
                ev = ev_full_agg.get(key)
                if ev:
                    clientes_act += ev["act"]
                    clientes_com += ev["com"]

        # 8) DETALLE
        merc_pois = {}
        for (id_punto, id_merc), ent in pois_status.items():
            d = merc_pois.setdefault(id_merc, {"pois_plan":0, "pois_act":0, "pois_com":0})
            d["pois_plan"] += ent["plan"]
            d["pois_act"] += ent["act"]
            d["pois_com"] += ent["com"]

        merc_rutas = {}
        for (id_ruta, id_merc), ent in ruta_merc_pairs.items():
            d = merc_rutas.setdefault(id_merc, {"rutas_plan":0, "rutas_act":0, "rutas_com":0,
                                                "rutas_nombres": []})
            d["rutas_plan"] += ent["planificadas"]
            d["rutas_act"] += ent["activas"]
            d["rutas_com"] += ent["completadas"]
            if ent["ruta"] not in d["rutas_nombres"]:
                d["rutas_nombres"].append(ent["ruta"])

        mercaderistas_detalle = []
        faltantes = []
        activos = []
        
        for mid, m in asignados_map.items():
            p_cnt = plan_counts.get(mid, 0)
            a_cnt = act_counts.get(mid, 0)
            faltas = max(0, p_cnt - a_cnt)
            
            mp = merc_pois.get(mid, {"pois_plan":0,"pois_act":0,"pois_com":0})
            mr = merc_rutas.get(mid, {"rutas_plan":0,"rutas_act":0,"rutas_com":0,"rutas_nombres":[]})

            estado = ("No planificado" if p_cnt == 0 else
                      ("Faltante" if faltas > 0 else "Activo"))

            det = {
                **m,
                "planificado_hoy":  p_cnt > 0, # compat
                "planificados":     p_cnt,
                "activos":          a_cnt,
                "faltas":           faltas,
                "estado":           estado,
                "rutas_planificadas": mr["rutas_plan"],
                "rutas_activas":      mr["rutas_act"],
                "rutas_completadas":  mr["rutas_com"],
                "rutas_nombres":      mr["rutas_nombres"],
                "pois_planificados":  mp["pois_plan"],
                "pois_activos":       mp["pois_act"],
                "pois_completados":   mp["pois_com"],
            }
            mercaderistas_detalle.append(det)
            if faltas > 0:
                faltantes.append(det)
            if a_cnt > 0:
                activos.append(det)

        prio = {"Faltante":0,"Activo":1,"No planificado":2}
        mercaderistas_detalle.sort(key=lambda x: (prio.get(x["estado"],99), x["nombre"] or ""))
        
        total_faltantes = sum(max(0, plan_counts.get(m, 0) - act_counts.get(m, 0)) for m in plan_counts.keys())

        return {
            "success":         True,
            "cliente_id":      cliente_id,
            "cliente_nombre":  cliente_nombre,
            "desde":           d_desde.isoformat(),
            "hasta":           d_hasta.isoformat(),
            "mercaderistas": {
                "total_asignados":         len(asignados_map),
                "planificados_hoy":        total_planificados,
                "activos_hoy":             total_activos,
                "faltantes_hoy":           total_faltantes,
                "exclusivos":              sum(1 for m in asignados_map.values()
                                               if m["tipo_servicio"] == "Exclusivo"),
                "tradex":                  sum(1 for m in asignados_map.values()
                                               if m["tipo_servicio"] == "Tradex"),
                "detalle":                 mercaderistas_detalle,
                "faltantes":               faltantes,
                "activos":                 activos,
            },
            "rutas": {
                "planificadas":  rutas_planificadas,
                "activas":       rutas_activas,
                "completadas":   rutas_completadas,
                "detalle":       list(ruta_merc_pairs.values()),
            },
            "puntos_interes": {
                "planificados":  pois_planificados,
                "activos":       pois_activos,
                "completados":   pois_completados,
                "detalle":       list(pois_status.values()),
            },
            "clientes_tradex": {
                "planificados":  clientes_plan,
                "activos":       clientes_act,
                "completados":   clientes_com,
                "aplica":        bool(tradex_ids),
            },
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activaciones")
def get_activaciones(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    cliente_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user)
):
    try:
        is_analyst = current_user.rol == 'analyst'
        
        if current_user.is_client and not current_user.rol == 'admin':
            cliente_id = current_user.id_perfil

        if desde and hasta:
            rango_filter = " AND vm.fecha_visita >= CAST(? AS DATE) AND vm.fecha_visita < DATEADD(day, 1, CAST(? AS DATE))"
            rango_params = [desde, hasta]
        else:
            rango_filter = " AND vm.fecha_visita >= CAST(GETDATE() AS DATE) AND vm.fecha_visita < DATEADD(day, 1, CAST(GETDATE() AS DATE))"
            rango_params = []

        analista_id = current_user.id_perfil if is_analyst else None

        af, ap = mk_analyst(is_analyst, analista_id)
        if cliente_id:
            af += " AND c.id_cliente = ?"
            ap = ap + [cliente_id]

        base_query = """
            SELECT
                vm.id_visita,
                c.cliente,
                c.id_cliente,
                pin.punto_de_interes,
                pin.identificador           AS id_punto,
                ISNULL(pin.departamento,'') AS departamento,
                ISNULL(pin.ciudad,'')       AS ciudad,
                m.nombre                    AS mercaderista,
                m.id_mercaderista,
                vm.fecha_visita,
                ISNULL(pin.jerarquia_nivel_2,'') AS tipo_pdv,

                act.id_foto                 AS id_foto_activacion,
                act.file_path               AS file_path_activacion,
                act.fecha_registro          AS fecha_activacion,
                act.Estado                  AS estado_activacion,

                des.id_foto                 AS id_foto_desactivacion,
                des.file_path               AS file_path_desactivacion,
                des.fecha_registro          AS fecha_desactivacion,
                des.Estado                  AS estado_desactivacion,

                ISNULL(ruta_pre.ruta,   'Sin ruta') AS ruta,
                ISNULL(ruta_pre.id_ruta, 0)         AS id_ruta,
                ISNULL(ruta_pre.analista,'')         AS nombre_analista,
                ISNULL(ruta_pre.cuadrante,'')        AS cuadrante,

                ISNULL(chat_pre.no_leidos, 0)        AS mensajes_no_leidos

            FROM VISITAS_MERCADERISTA vm
            JOIN CLIENTES       c   ON vm.id_cliente                  = c.id_cliente
            JOIN PUNTOS_INTERES1 pin ON vm.identificador_punto_interes = pin.identificador
            JOIN MERCADERISTAS  m   ON vm.id_mercaderista             = m.id_mercaderista

            OUTER APPLY (
                SELECT TOP 1 ft.id_visita, ft.id_foto, ft.file_path,
                       ft.fecha_registro, ft.Estado
                FROM FOTOS_TOTALES ft
                WHERE ft.id_visita = vm.id_visita AND ft.id_tipo_foto = 5
                ORDER BY ft.fecha_registro DESC
            ) act

            OUTER APPLY (
                SELECT TOP 1 ft.id_visita, ft.id_foto, ft.file_path,
                       ft.fecha_registro, ft.Estado
                FROM FOTOS_TOTALES ft
                WHERE ft.id_visita = vm.id_visita AND ft.id_tipo_foto = 6
                ORDER BY ft.fecha_registro DESC
            ) des

            OUTER APPLY (
                SELECT TOP 1 rp2.id_punto_interes,
                       rn2.ruta,
                       rn2.id_ruta,
                       a2.nombre_analista AS analista,
                       rn2.cuadrante
                FROM RUTA_PROGRAMACION rp2
                JOIN RUTAS_NUEVAS rn2 ON rp2.id_ruta  = rn2.id_ruta
                JOIN MERCADERISTAS_RUTAS mr2 ON mr2.id_ruta = rn2.id_ruta
                LEFT JOIN analistas_rutas ar2 ON ar2.id_ruta = rn2.id_ruta
                LEFT JOIN analistas a2 ON a2.id_analista = ar2.id_analista
                WHERE rp2.id_punto_interes = pin.identificador AND rp2.activa = 1
                  AND mr2.id_mercaderista = vm.id_mercaderista
                ORDER BY rn2.id_ruta
            ) ruta_pre

            OUTER APPLY (
                SELECT SUM(CASE WHEN visto = 0 AND tipo_mensaje = 'usuario' THEN 1 ELSE 0 END) AS no_leidos
                FROM CHAT_MENSAJES
                WHERE id_visita = vm.id_visita
            ) chat_pre

            WHERE 1=1
        """ + rango_filter + af + " ORDER BY vm.fecha_visita DESC"
        # (antes exigía act.id_foto/des.id_foto no nulos acá -- pero eso
        # filtraba la fila ANTES de que el bloque "Tradex" de abajo pudiera
        # heredarle la foto desde otra visita del mismo punto/mercaderista/
        # día. Resultado: si el PDV de un cliente ya fue activado por otro
        # cliente ese día, su propia visita nunca entraba a "rows" y
        # desaparecía de /activaciones (y por lo tanto de TODAS las
        # pestañas del Centro de Mando, que se alimentan de este mismo
        # endpoint: dashboard, por_mercaderista, pendientes, gestion_por_dia).

        all_params = rango_params + ap
        rows = execute_query(db, base_query, all_params)

        from app.services.azure_service import azure_service
        def _foto_url(path):
            try:
                return azure_service.get_proxy_url(path) if path else None
            except Exception:
                return None

        activaciones = []
        seen_ids = set()
        total_con_activacion = total_con_desactivacion = 0
        total_completas = total_activos_ahora = 0
        rutas_set = set()
        rutas_eje_set = set()

        for row in rows:
            vid = row[0]
            if vid in seen_ids: continue
            seen_ids.add(vid)

            activaciones.append({
                "id_visita":               row[0],
                "cliente":                 row[1],
                "id_cliente":              row[2],
                "punto_de_interes":        row[3],
                "id_punto":                row[4],
                "departamento":            row[5],
                "ciudad":                  row[6],
                "mercaderista":            row[7],
                "id_mercaderista":         row[8],
                "fecha_visita":            row[9].isoformat()  if row[9]  else None,
                "tipo_pdv":                row[10],
                "id_foto_activacion":      row[11],
                "file_path_activacion":    row[12],
                "url_activacion":          _foto_url(row[12]),
                "fecha_activacion":        row[13].isoformat() if row[13] else None,
                "estado_activacion":       row[14],
                "id_foto_desactivacion":   row[15],
                "file_path_desactivacion": row[16],
                "url_desactivacion":       _foto_url(row[16]),
                "fecha_desactivacion":     row[17].isoformat() if row[17] else None,
                "estado_desactivacion":    row[18],
                "ruta":                    row[19],
                "id_ruta":                 row[20],
                "analista":                row[21],
                "mensajes_no_leidos":      row[22],
                "duracion_minutos":        None,
                "estado_presencia":        None,
                "foto_heredada":           False,
            })

        # ── Tradex: 1 PDV visitado = N ejecuciones (una por cliente). La foto de
        # activación/cierre es del PDV → se comparte entre todas las ejecuciones del
        # mismo PDV/mercaderista/día. Así no falta la foto en ninguna y el conteo
        # de "activadas" refleja que el PDV sí fue activado.
        from collections import defaultdict as _dd
        _grp = _dd(list)
        for v in activaciones:
            _grp[(v["id_mercaderista"], v["id_punto"], (v["fecha_visita"] or "")[:10])].append(v)
        for grp in _grp.values():
            act_src = next((x for x in grp if x["id_foto_activacion"]), None)
            des_src = next((x for x in grp if x["id_foto_desactivacion"]), None)
            for x in grp:
                if act_src and not x["id_foto_activacion"]:
                    x["id_foto_activacion"]   = act_src["id_foto_activacion"]
                    x["url_activacion"]       = act_src["url_activacion"]
                    x["file_path_activacion"] = act_src["file_path_activacion"]
                    x["fecha_activacion"]     = act_src["fecha_activacion"]
                    x["foto_heredada"]        = True
                if des_src and not x["id_foto_desactivacion"]:
                    x["id_foto_desactivacion"]   = des_src["id_foto_desactivacion"]
                    x["url_desactivacion"]       = des_src["url_desactivacion"]
                    x["file_path_desactivacion"] = des_src["file_path_desactivacion"]
                    x["fecha_desactivacion"]     = des_src["fecha_desactivacion"]
                    x["foto_heredada"]           = True

        # Recalcular estado, duración y totales DESPUÉS de propagar.
        from datetime import datetime as _dt
        for v in activaciones:
            ta = v["id_foto_activacion"] is not None
            td = v["id_foto_desactivacion"] is not None
            v["estado_presencia"] = "completa" if ta and td else ("activo" if ta else "solo_salida")
            if ta and td and v["fecha_activacion"] and v["fecha_desactivacion"]:
                try:
                    v["duracion_minutos"] = int(
                        (_dt.fromisoformat(v["fecha_desactivacion"]) - _dt.fromisoformat(v["fecha_activacion"])).total_seconds() / 60
                    )
                except Exception:
                    v["duracion_minutos"] = None
            if ta: total_con_activacion += 1
            if td: total_con_desactivacion += 1
            if ta and td: total_completas += 1
            if ta and not td: total_activos_ahora += 1
            if v["id_ruta"] and v["id_ruta"] != 0:
                rutas_set.add(v["id_ruta"])
                if ta: rutas_eje_set.add(v["id_ruta"])

        total = len(activaciones)

        plan_query = """
            SELECT COUNT(DISTINCT vm2.id_visita)
            FROM VISITAS_MERCADERISTA vm2
            JOIN CLIENTES        c2  ON vm2.id_cliente                  = c2.id_cliente
            JOIN PUNTOS_INTERES1 pin2 ON vm2.identificador_punto_interes = pin2.identificador
            WHERE 1=1
        """ + rango_filter.replace("vm.", "vm2.")
        af2, ap2 = mk_analyst(is_analyst, analista_id, 'vm2', 'pin2', 'c2')
        if cliente_id:
            af2 += " AND c2.id_cliente = ?"
            ap2 = ap2 + [cliente_id]
        plan_query += af2
        plan_params = rango_params + ap2
        
        plan_result = execute_query(db, plan_query, plan_params)
        
        total_planificadas = total
        if plan_result and len(plan_result) > 0:
             total_planificadas = int(plan_result[0][0]) if plan_result[0][0] is not None else total

        # ── Planificadas por grupo (denominador real de las tarjetas) ──────────
        # Cuenta visitas planificadas (VISITAS_MERCADERISTA del período) por PDV,
        # por cliente y por mercaderista, respetando el filtro de analista/cliente.
        def _planned_map(group_col: str, extra_join: str = "") -> dict:
            q = (
                "SELECT " + group_col + " AS gid, COUNT(DISTINCT vm2.id_visita) AS cnt "
                "FROM VISITAS_MERCADERISTA vm2 "
                "JOIN CLIENTES c2 ON vm2.id_cliente = c2.id_cliente "
                "JOIN PUNTOS_INTERES1 pin2 ON vm2.identificador_punto_interes = pin2.identificador "
                + extra_join +
                " WHERE 1=1" + rango_filter.replace("vm.", "vm2.") + af2 +
                " GROUP BY " + group_col
            )
            res = execute_query(db, q, plan_params)
            return {r[0]: int(r[1]) for r in (res or []) if r[0] is not None}

        planned_pp = _planned_map("pin2.identificador")
        planned_pc = _planned_map("c2.id_cliente")
        planned_merc = _planned_map(
            "vm2.id_mercaderista",
            "JOIN MERCADERISTAS m2 ON vm2.id_mercaderista = m2.id_mercaderista",
        )

        base_prog             = total_planificadas if total_planificadas > 0 else (total if total > 0 else 1)
        pct_cumplimiento      = round(total_con_activacion / base_prog * 100, 1)
        progreso_activaciones = round(total_con_activacion / base_prog * 100, 1)
        progreso_completas    = round(total_completas      / base_prog * 100, 1)

        # ── Pendientes (basado en la PROGRAMACIÓN de ruta, NO en VISITAS_MERCADERISTA) ──
        # PDV/cliente planificados para el/los día(s) en las rutas asignadas del
        # mercaderista que NO fueron activados. Así incluye a quienes tienen 0 actividad
        # (nunca crearon una visita) — ej. mercaderista que no salió hoy.
        from datetime import timedelta as _tdp, date as _dproute
        if desde and hasta:
            _d0 = _dproute.fromisoformat(desde); _d1 = _dproute.fromisoformat(hasta)
        else:
            _d0 = _d1 = _dproute.today()
        _dias_set = set(); _cur = _d0
        while _cur <= _d1:
            _dias_set.add(_dia_es(_cur)); _cur += _tdp(days=1)
        dias_rango = list(_dias_set)

        pendientes = []
        planned_merc_exec: dict = {}   # mid -> set (id_punto, id_cliente) planificados
        planned_merc_info: dict = {}   # mid -> nombre
        planned_merc_pdvs: dict = {}   # mid -> set id_punto
        planned_merc_clis: dict = {}   # mid -> set id_cliente
        if dias_rango:
            # 'm' (MERCADERISTAS), no 'vmx' -- este query arma "pendientes"
            # desde la programación de ruta (MERCADERISTAS/RUTA_PROGRAMACION),
            # no tiene VISITAS_MERCADERISTA en el FROM. El alias 'vmx' no
            # existía en esta consulta -- pyodbc tiraba 42000 "multi-part
            # identifier vmx.id_mercaderista could not be bound" y tumbaba
            # TODO /activaciones con 500 para cualquier analista, en
            # cualquier fecha (Por Mercaderista, Gestión por Día, Pendientes,
            # Todas las visitas y las tarjetas Por Punto/Por Cliente
            # dependen todas de este mismo endpoint).
            af_p, ap_p = mk_analyst(is_analyst, analista_id, 'm', 'pin', 'c')
            ph_dias = ",".join("?" for _ in dias_rango)
            cli_filter = " AND rp.id_cliente = ?" if cliente_id else ""
            pend_query = f"""
                SELECT DISTINCT
                    m.id_mercaderista, m.nombre AS mercaderista,
                    pin.identificador AS id_punto, pin.punto_de_interes,
                    rp.id_cliente, ISNULL(c.cliente,'') AS cliente,
                    ISNULL(pin.ciudad,'') AS ciudad, ISNULL(rn.ruta,'Sin ruta') AS ruta,
                    ISNULL(pin.departamento,'') AS departamento, ISNULL(rp.prioridad,'') AS prioridad,
                    ISNULL(rn.cuadrante,'') AS cuadrante
                FROM MERCADERISTAS m
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_mercaderista = m.id_mercaderista
                JOIN RUTA_PROGRAMACION rp   ON rp.id_ruta = mr.id_ruta
                JOIN RUTAS_NUEVAS rn        ON rn.id_ruta = rp.id_ruta
                JOIN PUNTOS_INTERES1 pin    ON pin.identificador = rp.id_punto_interes
                LEFT JOIN CLIENTES c        ON c.id_cliente = rp.id_cliente
                WHERE m.activo = 1 AND rp.activa = 1 AND rp.dia IN ({ph_dias}){cli_filter}{af_p}
                ORDER BY m.nombre, ISNULL(c.cliente,'')
            """
            pend_params = list(dias_rango) + ([cliente_id] if cliente_id else []) + ap_p
            pend_rows = execute_query(db, pend_query, pend_params)

            activated_pdv = {(v["id_mercaderista"], v["id_punto"]) for v in activaciones if v["id_foto_activacion"]}
            seen_pend = set()
            for r in (pend_rows or []):
                mid, mnom, idp, pnom, idc, cli, ciu, ruta, depto, prio, cuad = r
                planned_merc_info[mid] = mnom
                planned_merc_exec.setdefault(mid, set()).add((idp, idc))
                planned_merc_pdvs.setdefault(mid, set()).add(idp)
                planned_merc_clis.setdefault(mid, set()).add(idc)
                if (mid, idp) in activated_pdv:   # ese PDV ya fue activado por el merc
                    continue
                key = (idp, idc, mid)
                if key in seen_pend: continue
                seen_pend.add(key)
                pendientes.append({
                    "id_punto": idp, "punto_de_interes": pnom,
                    "cliente": cli, "id_cliente": idc,
                    "mercaderista": mnom, "id_mercaderista": mid,
                    "ciudad": ciu, "ruta": ruta,
                    "departamento": depto, "prioridad": prio, "cuadrante": cuad
                })

        # ── Por mercaderista a nivel EJECUCIÓN (PDV × cliente) ───────────────────
        # planificadas/pendientes salen de la programación de ruta; activadas/completas
        # de las activaciones (con propagación de fotos). Así cuadran y se incluyen
        # también los mercaderistas con 0 actividad.
        act_exec: dict = {}    # mid -> set (id_punto, id_cliente) activadas
        com_exec: dict = {}    # mid -> set completadas
        durs_merc: dict = {}   # mid -> [duraciones]
        activo_now: dict = {}  # mid -> bool (en punto)
        act_pdvs: dict = {}    # mid -> set id_punto (fallback total_puntos)
        act_clis: dict = {}    # mid -> set id_cliente
        nombre_merc: dict = {}
        merc_rutas_set: dict = {}
        merc_deptos_set: dict = {}
        merc_cuads_set: dict = {}
        for v in activaciones:
            mid = v["id_mercaderista"]; nombre_merc[mid] = v["mercaderista"]
            ek = (v["id_punto"], v["id_cliente"])
            if v["id_foto_activacion"]:            act_exec.setdefault(mid, set()).add(ek)
            if v["estado_presencia"] == "completa": com_exec.setdefault(mid, set()).add(ek)
            if v["estado_presencia"] == "activo":   activo_now[mid] = True
            act_pdvs.setdefault(mid, set()).add(v["id_punto"])
            act_clis.setdefault(mid, set()).add(v["id_cliente"])
            if v["duracion_minutos"] is not None:   durs_merc.setdefault(mid, []).append(v["duracion_minutos"])
            if v.get("ruta") and v["ruta"] != "Sin ruta": merc_rutas_set.setdefault(mid, set()).add(v["ruta"])
            if v.get("departamento"): merc_deptos_set.setdefault(mid, set()).add(v["departamento"])
            if v.get("cuadrante"): merc_cuads_set.setdefault(mid, set()).add(v["cuadrante"])

        pend_merc_count: dict = {}
        for p in pendientes:
            mid = p["id_mercaderista"]
            pend_merc_count[mid] = pend_merc_count.get(mid, 0) + 1
            if p.get("ruta") and p["ruta"] != "Sin ruta": merc_rutas_set.setdefault(mid, set()).add(p["ruta"])
            if p.get("departamento"): merc_deptos_set.setdefault(mid, set()).add(p["departamento"])
            if p.get("cuadrante"): merc_cuads_set.setdefault(mid, set()).add(p["cuadrante"])

        all_mids = set(planned_merc_info.keys()) | set(nombre_merc.keys())
        por_mercaderista = []
        for mid in all_mids:
            activadas = len(act_exec.get(mid, set()))
            completas = len(com_exec.get(mid, set()))
            pend = pend_merc_count.get(mid, 0)
            planificadas = len(planned_merc_exec.get(mid, set()))
            if planificadas == 0:
                planificadas = activadas + pend
            planificadas = max(planificadas, activadas, completas)
            total_puntos = len(planned_merc_pdvs.get(mid, set())) or len(act_pdvs.get(mid, set()))
            total_clientes = len(planned_merc_clis.get(mid, set())) or len(act_clis.get(mid, set()))
            deptos_list = list(merc_deptos_set.get(mid, set()))
            deptos_str = " y ".join(deptos_list[:2])
            if len(deptos_list) > 2:
                deptos_str += f" (+{len(deptos_list) - 2})"
            elif not deptos_str:
                deptos_str = "Sin departamento"

            rutas_str = ", ".join(list(merc_rutas_set.get(mid, set())))
            if not rutas_str: rutas_str = "Sin ruta"
            
            cuads_str = ", ".join(list(merc_cuads_set.get(mid, set())))
            if not cuads_str: cuads_str = "Sin cuadrante"

            por_mercaderista.append({
                "nombre": planned_merc_info.get(mid) or nombre_merc.get(mid) or "?",
                "id_mercaderista": mid,
                "total": activadas,
                "planificadas": planificadas,
                "activaciones": activadas,
                "completas": completas,
                "pendientes": pend,
                "pct_activacion": round(activadas / planificadas * 100, 1) if planificadas else 0,
                "pct_completas":  round(completas / planificadas * 100, 1) if planificadas else 0,
                "activo_ahora": activo_now.get(mid, False),
                "total_puntos": total_puntos,
                "total_clientes": total_clientes,
                "duracion_prom": round(sum(durs_merc[mid]) / len(durs_merc[mid])) if durs_merc.get(mid) else None,
                "departamentos_str": deptos_str,
                "rutas_str": rutas_str,
                "cuadrantes_str": cuads_str,
            })
        por_mercaderista.sort(key=lambda x: x["pct_activacion"], reverse=True)

        def _desglose(key_fn, id_fn, planned_map):
            # con = visitas con activación / completas; total = visitas PLANIFICADAS del grupo
            act_m, com_m = {}, {}
            for v in activaciones:
                k = key_fn(v); kid = id_fn(v)
                ta = v["id_foto_activacion"] is not None
                tc = v["estado_presencia"] == "completa"
                for mp, cond in [(act_m, ta), (com_m, tc)]:
                    if kid not in mp:
                        mp[kid] = {"nombre": k, "id": kid, "con": 0}
                    if cond:
                        mp[kid]["con"] += 1
            def _s(mp):
                out = []
                for kid, v in mp.items():
                    # denominador = planificadas; nunca menor que lo ya activado/completado
                    total = max(planned_map.get(kid, 0), v["con"])
                    out.append({
                        "nombre": v["nombre"], "id": kid, "total": total, "con": v["con"],
                        "porcentaje": round(v["con"] / total * 100, 1) if total else 0,
                    })
                return sorted(out, key=lambda x: x["porcentaje"], reverse=True)
            return _s(act_m), _s(com_m)

        pp_act, pp_com = _desglose(lambda v: v["punto_de_interes"], lambda v: v["id_punto"], planned_pp)
        pc_act, pc_com = _desglose(lambda v: v["cliente"], lambda v: v["id_cliente"], planned_pc)

        gpd_af, gpd_ap = mk_analyst(is_analyst, analista_id, 'vm4','pin4','c4')
        if cliente_id:
            gpd_af += " AND c4.id_cliente = ?"
            gpd_ap = gpd_ap + [cliente_id]
        # "total" = TODAS las visitas planificadas del día (mismo criterio que
        # total_planificadas/planned_pp/planned_pc de arriba: VISITAS_MERCADERISTA
        # + CLIENTES + PUNTOS_INTERES1, sin exigir que ya tenga foto). Antes
        # exigía EXISTS de una foto tipo 5/6, así que el denominador solo
        # contaba visitas que YA habían arrancado — un día con 26
        # planificadas y 17 activadas mostraba "17/17" (100%) en vez de
        # "17/26", porque las 9 que faltaron ni entraban en el conteo.
        gestion_query = """
            SELECT CAST(vm4.fecha_visita AS DATE) AS fecha,
                   c4.cliente,
                   COUNT(DISTINCT vm4.id_visita)  AS total,
                   SUM(CASE WHEN act4.id_foto IS NOT NULL THEN 1 ELSE 0 END) AS ejecutadas,
                   SUM(CASE WHEN act4.id_foto IS NOT NULL AND des4.id_foto IS NOT NULL THEN 1 ELSE 0 END) AS completas
            FROM VISITAS_MERCADERISTA vm4
            JOIN CLIENTES c4 ON vm4.id_cliente = c4.id_cliente
            JOIN PUNTOS_INTERES1 pin4 ON vm4.identificador_punto_interes = pin4.identificador
            LEFT JOIN (
                SELECT id_visita, MIN(id_foto) AS id_foto FROM FOTOS_TOTALES
                WHERE id_tipo_foto=5 AND fecha_registro >= DATEADD(day,-8,CAST(GETDATE() AS DATE))
                GROUP BY id_visita
            ) act4 ON act4.id_visita=vm4.id_visita
            LEFT JOIN (
                SELECT id_visita, MIN(id_foto) AS id_foto FROM FOTOS_TOTALES
                WHERE id_tipo_foto=6 AND fecha_registro >= DATEADD(day,-8,CAST(GETDATE() AS DATE))
                GROUP BY id_visita
            ) des4 ON des4.id_visita=vm4.id_visita
            WHERE vm4.fecha_visita >= CAST(DATEADD(day,-6,GETDATE()) AS DATE)
        """ + gpd_af + """
            GROUP BY CAST(vm4.fecha_visita AS DATE), c4.cliente
            ORDER BY fecha DESC, c4.cliente
        """
        gpd_rows = execute_query(db, gestion_query, gpd_ap)
        gpd_c = {}; gpd_f = set()
        for r in gpd_rows:
            fs = r[0].strftime('%Y-%m-%d'); cl = r[1]; gpd_f.add(fs)
            if cl not in gpd_c: gpd_c[cl] = {}
            gpd_c[cl][fs] = {"total":r[2],"ejecutadas":r[3],"completas":r[4],
                             "label":f"{r[3]}/{r[2]}","pct":round(r[3]/r[2]*100,0) if r[2] else 0}
        gestion_por_dia = {"fechas":sorted(list(gpd_f),reverse=True),
                           "clientes":[{"cliente":k,"dias":gpd_c[k]} for k in sorted(gpd_c.keys())]}

        stats = {
            "total_registros":       total,
            "total_planificadas":    total_planificadas,
            "con_activacion":        total_con_activacion,
            "con_desactivacion":     total_con_desactivacion,
            "completas":             total_completas,
            "activos_ahora":         total_activos_ahora,
            "pdvs_pendientes":       len(pendientes),
            "pct_cumplimiento":      pct_cumplimiento,
            "total_rutas":           len(rutas_set),
            "rutas_ejecutadas":      len(rutas_eje_set),
            "progreso_activaciones": progreso_activaciones,
            "progreso_completas":    progreso_completas,
            "pp_activaciones": pp_act, "pp_completas": pp_com,
            "pc_activaciones": pc_act, "pc_completas": pc_com,
        }

        return {
            "success":             True,
            "total":               total,
            "activaciones":        activaciones,
            "stats":               stats,
            "por_mercaderista":    por_mercaderista,
            "pendientes":          pendientes,
            "gestion_por_dia":     gestion_por_dia,
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
