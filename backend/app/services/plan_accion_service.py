"""Plan de Acción -- Fase 2: calcula qué combinaciones (ruta, PDV, cliente)
siguen debiendo visita en el período actual (semana si su frecuencia es
>=1/semana, mes si es menor) y con qué urgencia, y guarda el resultado
completo en PLAN_ACCION_PENDIENTES (se reemplaza entero en cada corrida).

El universo son las combinaciones activa=1 en RUTA_PROGRAMACION que YA
tuvieron al menos una visita alguna vez (EXISTS sin filtro de fecha en
UNIVERSO_QUERY). Se excluyen las que nunca arrancaron -- con el cliente
todavía en fase piloto, la mayoría de las programaciones activas no había
empezado, y sin este filtro Plan de Acción marcaba como "pendiente" a casi
todo el universo (9281 de 9300) en vez de reflejar atraso real.

Fórmula acordada con el usuario (sesión 2026-08-02):

  Frecuencia >= 1 (semanal+):
    faltantes = round(frecuencia) - visitas_hechas_esta_semana
    dias_disponibles = días hábiles (Lun-Sáb) que quedan hasta el sábado
      incluyendo hoy; si hoy ya es domingo se habilita como único día
      disponible (último recurso, no se toca RUTA_PROGRAMACION.dia)
    urgencia = faltantes / dias_disponibles

  Frecuencia < 1 (mensual -- 0.25/0.5/0.75, sin semana fija):
    faltantes = round(frecuencia * 4) - visitas_hechas_este_mes
    urgencia = faltantes / semanas_restantes_del_mes

  score = urgencia * peso_prioridad(ruta) * peso_tipo

Una visita cuenta para la cuota si está "completa" (existe foto de
activación Y de desactivación, ninguna de las dos Rechazada -- NO exige
que ya estén Aprobada por un analista, solo que el mercaderista haya
hecho el trabajo de campo; exigir aprobación inflaba muchísimo el conteo
porque la revisión administrativa suele ir atrasada respecto al trabajo
real). Si el (PDV, cliente) sigue debiendo visita este período Y alguna
de sus visitas del período tiene una foto Estado='Rechazada' sin
resolver, se clasifica como 'fotos_rechazadas' (peso 0.6); si nunca se
intentó, 'nunca_visitado' (peso 1.0) -- misma cola, menor peso a la
rechazada, tal como lo pidió el usuario.
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import Decimal

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

PESO_PRIORIDAD = {"alta": 3, "media": 2, "baja": 1}
PESO_PRIORIDAD_DEFAULT = 2
PESO_TIPO = {"nunca_visitado": 1.0, "fotos_rechazadas": 0.6}

UNIVERSO_QUERY = """
SELECT rp.id_ruta, rn.ruta AS ruta_nombre,
       rp.id_punto_interes, pi.punto_de_interes, pi.departamento, pi.ciudad,
       rp.id_cliente, c.cliente AS cliente_nombre,
       MAX(rp.prioridad) AS prioridad,
       COUNT(DISTINCT rp.dia) AS dias_programados,
       MAX(f.frecuencia_semanal) AS frecuencia_semanal
FROM RUTA_PROGRAMACION rp
JOIN RUTAS_NUEVAS rn ON rn.id_ruta = rp.id_ruta
LEFT JOIN PUNTOS_INTERES1 pi ON pi.identificador = rp.id_punto_interes
LEFT JOIN CLIENTES c ON c.id_cliente = rp.id_cliente
LEFT JOIN FRECUENCIAS_PDVS_CLIENTE f
       ON f.id_punto_interes = rp.id_punto_interes
      AND f.id_cliente = rp.id_cliente
      AND f.activo = 1
WHERE rp.activa = 1
  AND rp.id_punto_interes IS NOT NULL
  AND rp.id_cliente IS NOT NULL
  -- Piloto en curso: muchas programaciones activa=1 todavía no arrancaron
  -- (nunca tuvieron ni una visita). Esas no están "atrasadas", simplemente
  -- no empezaron -- se excluyen hasta que tengan su primera visita, ahí ya
  -- entran solas al cálculo normal de frecuencia.
  AND EXISTS (
      SELECT 1 FROM VISITAS_MERCADERISTA vm0
      WHERE vm0.identificador_punto_interes = rp.id_punto_interes
        AND vm0.id_cliente = rp.id_cliente
  )
GROUP BY rp.id_ruta, rn.ruta, rp.id_punto_interes, pi.punto_de_interes,
         pi.departamento, pi.ciudad, rp.id_cliente, c.cliente
"""

VISITAS_QUERY = """
SELECT vm.identificador_punto_interes, vm.id_cliente, vm.fecha_visita,
       MAX(CASE WHEN ft.id_tipo_foto = 5 AND (ft.Estado IS NULL OR ft.Estado <> 'Rechazada') THEN 1 ELSE 0 END) AS tiene_act,
       MAX(CASE WHEN ft.id_tipo_foto = 6 AND (ft.Estado IS NULL OR ft.Estado <> 'Rechazada') THEN 1 ELSE 0 END) AS tiene_des,
       MAX(CASE WHEN ft.Estado = 'Rechazada' THEN 1 ELSE 0 END) AS tiene_rechazada
FROM VISITAS_MERCADERISTA vm
LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita
WHERE vm.fecha_visita >= ?
  AND vm.fecha_visita < DATEADD(day, 1, CAST(GETDATE() AS DATE))
  AND vm.identificador_punto_interes IS NOT NULL
  AND vm.id_cliente IS NOT NULL
GROUP BY vm.identificador_punto_interes, vm.id_cliente, vm.fecha_visita
"""


def _execute_with_timeout(db: Session, query: str, params: tuple = (), timeout: int = 30):
    """Mismo patrón que app/routes/centro_mando.py::execute_query -- timeout en
    la CONEXIÓN (conn.timeout), no en el cursor (esta versión de pyodbc no
    tiene Cursor.timeout). Con --workers 1 en uvicorn, una query colgada
    bloquea el thread pool entero hasta que Cloudflare corta en 100s (524) --
    y en el peor caso, mientras la transacción sigue abierta, bloquea también
    lecturas simples de la misma tabla (por eso GET /pendientes se colgaba
    detrás de un POST /recalcular que nunca terminaba). Mejor fallar rápido
    con un error claro."""
    conn = db.connection().connection
    prev_timeout = 0
    try:
        prev_timeout = conn.timeout
        conn.timeout = timeout
    except Exception:
        pass
    try:
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    finally:
        try:
            conn.timeout = prev_timeout
        except Exception:
            pass


def _dias_habiles_restantes_semana(hoy: date) -> int:
    if hoy.weekday() == 6:  # domingo: último recurso, solo hoy
        return 1
    sabado = hoy + timedelta(days=5 - hoy.weekday())
    return (sabado - hoy).days + 1


def _semanas_restantes_mes(hoy: date) -> int:
    if hoy.month == 12:
        primer_dia_prox_mes = date(hoy.year + 1, 1, 1)
    else:
        primer_dia_prox_mes = date(hoy.year, hoy.month + 1, 1)
    ultimo_dia_mes = primer_dia_prox_mes - timedelta(days=1)
    dias_restantes = (ultimo_dia_mes - hoy).days + 1
    return max(1, math.ceil(dias_restantes / 7))


def _peso_prioridad(prioridad: str | None) -> int:
    if not prioridad:
        return PESO_PRIORIDAD_DEFAULT
    return PESO_PRIORIDAD.get(prioridad.strip().lower(), PESO_PRIORIDAD_DEFAULT)


def _to_float(val) -> float:
    if val is None:
        return 0.0
    if isinstance(val, Decimal):
        return float(val)
    return float(val)


def calcular_pendientes(db: Session) -> list[dict]:
    # CAST(GETDATE() AS DATE), no date.today(): el contenedor corre en UTC,
    # y date.today() ya se adelantaba de día (a partir de las 20:00 hora de
    # Caracas, UTC-4) frente a la hora real del negocio -- eso rompía
    # silenciosamente el cálculo de "hoy es domingo, último recurso" y el
    # conteo de días hábiles restantes. GETDATE() ya es consistente con la
    # hora local en el resto de la app (columnas fecha_calculo, etc.).
    hoy = _execute_with_timeout(db, "SELECT CAST(GETDATE() AS DATE)", (), timeout=10)[0][0]
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)
    dias_disp_semana = _dias_habiles_restantes_semana(hoy)
    semanas_disp_mes = _semanas_restantes_mes(hoy)

    universo = _execute_with_timeout(db, UNIVERSO_QUERY, (), timeout=30)
    visitas = _execute_with_timeout(db, VISITAS_QUERY, (inicio_mes,), timeout=30)

    actividad: dict[tuple, dict] = defaultdict(lambda: {
        "hechas_semana": set(), "hechas_mes": set(),
        "rechazada_semana": False, "rechazada_mes": False,
    })
    for id_punto, id_cliente, fecha, tiene_act, tiene_des, tiene_rechazada in visitas:
        if fecha is None:
            continue
        # fecha_visita es DATETIME en la base real (el modelo ORM lo declara
        # Date, pero esta query es raw SQL y pyodbc devuelve el tipo real).
        if isinstance(fecha, datetime):
            fecha = fecha.date()
        completa = bool(tiene_act) and bool(tiene_des)
        rechazada = bool(tiene_rechazada)
        info = actividad[(id_punto, id_cliente)]
        if fecha >= inicio_mes:
            if completa:
                info["hechas_mes"].add(fecha)
            if rechazada:
                info["rechazada_mes"] = True
        if fecha >= inicio_semana:
            if completa:
                info["hechas_semana"].add(fecha)
            if rechazada:
                info["rechazada_semana"] = True

    pendientes: list[dict] = []
    for (id_ruta, ruta_nombre, id_punto_interes, punto_de_interes, departamento, ciudad,
         id_cliente, cliente_nombre, prioridad, dias_programados, frecuencia_semanal) in universo:
        frecuencia = frecuencia_semanal
        if frecuencia is None:
            frecuencia = dias_programados if dias_programados and dias_programados > 0 else 1
        frecuencia = _to_float(frecuencia)
        if frecuencia <= 0:
            continue

        info = actividad.get((id_punto_interes, id_cliente), {
            "hechas_semana": set(), "hechas_mes": set(),
            "rechazada_semana": False, "rechazada_mes": False,
        })

        if frecuencia >= 1:
            periodo = "semana"
            visitas_requeridas = round(frecuencia)
            visitas_hechas = len(info["hechas_semana"])
            dias_disponibles = dias_disp_semana
            faltantes = visitas_requeridas - visitas_hechas
            urgencia = faltantes / dias_disponibles if dias_disponibles else faltantes
            tiene_rechazada = info["rechazada_semana"]
        else:
            periodo = "mes"
            visitas_requeridas = round(frecuencia * 4)
            visitas_hechas = len(info["hechas_mes"])
            dias_disponibles = None
            faltantes = visitas_requeridas - visitas_hechas
            urgencia = faltantes / semanas_disp_mes
            tiene_rechazada = info["rechazada_mes"]

        if faltantes <= 0:
            continue

        tipo_pendiente = "fotos_rechazadas" if tiene_rechazada else "nunca_visitado"
        peso_prioridad = _peso_prioridad(prioridad)
        peso_tipo = PESO_TIPO[tipo_pendiente]
        score = urgencia * peso_prioridad * peso_tipo

        pendientes.append({
            "id_ruta": id_ruta,
            "ruta_nombre": ruta_nombre,
            "id_punto_interes": id_punto_interes,
            "punto_de_interes": punto_de_interes,
            "departamento": departamento,
            "ciudad": ciudad,
            "id_cliente": id_cliente,
            "cliente_nombre": cliente_nombre,
            "prioridad_ruta": prioridad,
            "frecuencia_semanal": frecuencia,
            "periodo": periodo,
            "tipo_pendiente": tipo_pendiente,
            "visitas_requeridas": visitas_requeridas,
            "visitas_hechas": visitas_hechas,
            "visitas_faltantes": faltantes,
            "dias_disponibles": dias_disponibles,
            "urgencia": round(urgencia, 4),
            "score": round(score, 4),
        })

    pendientes.sort(key=lambda p: p["score"], reverse=True)
    return pendientes


_INSERT_COLS = [
    "id_ruta", "ruta_nombre", "id_punto_interes", "punto_de_interes", "departamento", "ciudad",
    "id_cliente", "cliente_nombre", "prioridad_ruta", "frecuencia_semanal", "periodo",
    "tipo_pendiente", "visitas_requeridas", "visitas_hechas", "visitas_faltantes",
    "dias_disponibles", "urgencia", "score",
]

_INSERT_SQL = f"""
    INSERT INTO PLAN_ACCION_PENDIENTES
        ({", ".join(_INSERT_COLS)}, fecha_calculo)
    VALUES
        ({", ".join(["?"] * len(_INSERT_COLS))}, GETDATE())
"""


def recalcular_plan_accion(db: Session) -> int:
    pendientes = calcular_pendientes(db)

    # DELETE sin WHERE + INSERT: la tabla queda bloqueada desde el DELETE
    # hasta el commit. Con eso, lo único que puede alargar esa ventana (y
    # bloquear de paso a GET /pendientes) es un INSERT lento -- por eso
    # fast_executemany=True (sin esto, pyodbc hace un round-trip POR FILA:
    # unos pocos miles de filas ya alcanzan para tardar más de un minuto).
    conn = db.connection().connection
    cursor = conn.cursor()
    cursor.execute("DELETE FROM PLAN_ACCION_PENDIENTES")
    if pendientes:
        cursor.fast_executemany = True
        rows = [tuple(p[c] for c in _INSERT_COLS) for p in pendientes]
        cursor.executemany(_INSERT_SQL, rows)
    db.commit()
    return len(pendientes)


# ──────────────────────────────────────────────────────────────────────────
# Fase 3 -- geo-clustering: agrupar pendientes por cercanía real, para
# proponer rutas BCK. Ubicación de un PDV = promedio de lat/lon de sus
# fotos de activación/desactivación (tipo 5/6 -- son con cámara en vivo,
# el GPS viene del EXIF de la foto, confirmado con el usuario que es más
# confiable que la dirección cargada en PUNTOS_INTERES1). Si un PDV nunca
# tuvo esas fotos, se usa PUNTOS_INTERES1.latitud/longitud como respaldo
# (texto con coma decimal -- mismo parseo que ya usa mercaderista_portal.py).
# ──────────────────────────────────────────────────────────────────────────

RADIO_CLUSTER_KM_DEFAULT = 5.0


def _resolver_ubicaciones(db: Session, ids_punto: list[str]) -> dict[str, tuple[float, float]]:
    ids_punto = list(dict.fromkeys(ids_punto))  # dedup preservando orden
    if not ids_punto:
        return {}

    ubicaciones: dict[str, tuple[float, float]] = {}

    placeholders = ", ".join(["?"] * len(ids_punto))
    rows = _execute_with_timeout(db, f"""
        SELECT vm.identificador_punto_interes, AVG(f.latitud), AVG(f.longitud)
        FROM FOTOS_TOTALES f
        JOIN VISITAS_MERCADERISTA vm ON vm.id_visita = f.id_visita
        WHERE f.id_tipo_foto IN (5, 6)
          AND f.latitud IS NOT NULL AND f.longitud IS NOT NULL
          AND vm.identificador_punto_interes IN ({placeholders})
        GROUP BY vm.identificador_punto_interes
    """, tuple(ids_punto), timeout=20)
    for id_punto, lat, lon in rows:
        if lat is not None and lon is not None:
            ubicaciones[id_punto] = (float(lat), float(lon))

    faltantes = [p for p in ids_punto if p not in ubicaciones]
    if faltantes:
        placeholders2 = ", ".join(["?"] * len(faltantes))
        rows2 = _execute_with_timeout(db, f"""
            SELECT identificador, latitud, longitud
            FROM PUNTOS_INTERES1
            WHERE identificador IN ({placeholders2})
        """, tuple(faltantes), timeout=15)
        for id_punto, lat_s, lon_s in rows2:
            if not lat_s or not lon_s:
                continue
            try:
                ubicaciones[id_punto] = (
                    float(str(lat_s).replace(",", ".")),
                    float(str(lon_s).replace(",", ".")),
                )
            except ValueError:
                continue

    return ubicaciones


def _haversine_km(a: tuple[float, float], b: tuple[float, float]) -> float:
    lat1, lon1 = a
    lat2, lon2 = b
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def _agrupar_por_cercania(items: list[dict], radio_km: float) -> list[list[dict]]:
    """Clustering simple por vecindad (greedy, no es k-means ni jerárquico
    óptimo): toma el primer punto sin agrupar como semilla y le suma todo lo
    que esté a <= radio_km, repite con lo que queda. Alcanza para proponer
    grupos razonables sin la complejidad de un clustering "correcto" -- si
    en la práctica arma grupos raros, se ajusta después con datos reales."""
    restantes = list(items)
    grupos: list[list[dict]] = []
    while restantes:
        base = restantes.pop(0)
        grupo = [base]
        if base.get("_ubicacion"):
            i = 0
            while i < len(restantes):
                cand = restantes[i]
                if cand.get("_ubicacion") and _haversine_km(base["_ubicacion"], cand["_ubicacion"]) <= radio_km:
                    grupo.append(restantes.pop(i))
                else:
                    i += 1
        grupos.append(grupo)
    return grupos


MINUTOS_PROMEDIO_DEFAULT = 45  # fallback si el PDV/cliente no tiene fila en HORAS_PROMEDIO_EJECUCION
JORNADA_MINUTOS_DEFAULT = 8 * 60  # capacidad de un backup en un día completo de trabajo


def _resolver_minutos_promedio(db: Session, items: list[dict]) -> dict[tuple, int]:
    """(id_punto_interes, id_cliente) -> minutos_promedio, cruzando
    PUNTOS_INTERES1.jerarquia_nivel_2 -> CAT_TIPO_NEGOCIO -> HORAS_PROMEDIO_EJECUCION.
    jerarquia_nivel_2 (no jerarquia_nivel_2_2, pese a lo que dice el
    comentario del modelo) es la columna que de verdad matchea contra
    CAT_TIPO_NEGOCIO.nombre -- confirmado con datos reales (5098/5116 PDVs)."""
    ids_punto = list(dict.fromkeys(p["id_punto_interes"] for p in items))
    if not ids_punto:
        return {}

    placeholders = ", ".join(["?"] * len(ids_punto))
    punto_tipo_rows = _execute_with_timeout(db, f"""
        SELECT pi.identificador, ctn.id
        FROM PUNTOS_INTERES1 pi
        JOIN CAT_TIPO_NEGOCIO ctn ON ctn.nombre = pi.jerarquia_nivel_2
        WHERE pi.identificador IN ({placeholders})
    """, tuple(ids_punto), timeout=15)
    punto_a_tipo = {id_punto: id_tipo for id_punto, id_tipo in punto_tipo_rows}

    horas_rows = _execute_with_timeout(db, """
        SELECT id_cliente, id_tipo_negocio, minutos_promedio FROM HORAS_PROMEDIO_EJECUCION
    """, (), timeout=15)
    horas_map = {(id_cliente, id_tipo): minutos for id_cliente, id_tipo, minutos in horas_rows}

    resultado: dict[tuple, int] = {}
    for p in items:
        id_tipo = punto_a_tipo.get(p["id_punto_interes"])
        minutos = horas_map.get((p["id_cliente"], id_tipo)) if id_tipo is not None else None
        resultado[(p["id_punto_interes"], p["id_cliente"])] = minutos if minutos is not None else MINUTOS_PROMEDIO_DEFAULT
    return resultado


def calcular_clusters(db: Session, score_min: float = 1.0, radio_km: float = RADIO_CLUSTER_KM_DEFAULT) -> list[dict]:
    """Agrupa por cercanía los pendientes con score >= score_min (críticos
    por defecto -- son los que de verdad importa cubrir con un backup).
    Todavía NO crea rutas ni asigna mercaderista -- Fase 4 hace eso a partir
    de esta propuesta, con confirmación manual del admin."""
    pendientes = calcular_pendientes(db)
    criticos = [p for p in pendientes if p["score"] >= score_min]
    if not criticos:
        return []

    ubicaciones = _resolver_ubicaciones(db, [p["id_punto_interes"] for p in criticos])
    minutos_por_item = _resolver_minutos_promedio(db, criticos)
    for p in criticos:
        p["_ubicacion"] = ubicaciones.get(p["id_punto_interes"])
        p["minutos_estimados"] = minutos_por_item.get((p["id_punto_interes"], p["id_cliente"]), MINUTOS_PROMEDIO_DEFAULT)

    sin_ubicacion = [p for p in criticos if not p["_ubicacion"]]
    con_ubicacion = [p for p in criticos if p["_ubicacion"]]

    grupos = _agrupar_por_cercania(con_ubicacion, radio_km)

    resultado = []
    for grupo in grupos:
        lats = [p["_ubicacion"][0] for p in grupo]
        lons = [p["_ubicacion"][1] for p in grupo]
        minutos_totales = sum(p["minutos_estimados"] for p in grupo)
        for p in grupo:
            p.pop("_ubicacion", None)
        resultado.append({
            "centro_lat": round(sum(lats) / len(lats), 6),
            "centro_lon": round(sum(lons) / len(lons), 6),
            "cantidad_pdvs": len(grupo),
            "score_total": round(sum(p["score"] for p in grupo), 4),
            "score_max": round(max(p["score"] for p in grupo), 4),
            "minutos_totales_estimados": minutos_totales,
            "backups_sugeridos": math.ceil(minutos_totales / JORNADA_MINUTOS_DEFAULT),
            "items": grupo,
        })
    resultado.sort(key=lambda g: g["score_total"], reverse=True)

    if sin_ubicacion:
        minutos_totales = sum(p["minutos_estimados"] for p in sin_ubicacion)
        resultado.append({
            "centro_lat": None,
            "centro_lon": None,
            "cantidad_pdvs": len(sin_ubicacion),
            "score_total": round(sum(p["score"] for p in sin_ubicacion), 4),
            "score_max": round(max(p["score"] for p in sin_ubicacion), 4),
            "minutos_totales_estimados": minutos_totales,
            "backups_sugeridos": math.ceil(minutos_totales / JORNADA_MINUTOS_DEFAULT),
            "items": sin_ubicacion,
            "sin_ubicacion": True,
        })

    return resultado
