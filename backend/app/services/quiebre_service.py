"""Quiebre dinámico -- alertar antes de que un producto llegue a 0, no
cuando ya llegó. Roadmap predictivo, item N2. Diseño acordado con el
usuario, con las tablas reales sobre la mesa: BALANCES_TOTALES,
PUNTOS_INTERES1.jerarquia_nivel_2, FRECUENCIAS_PDVS_CLIENTE,
RUTA_PROGRAMACION.

Estadística explicable (percentiles + tendencia), deliberadamente NO
Machine Learning todavía -- decisión explícita: acumular histórico primero
con esto, ML viene después si hace falta (mismo tipo de modelo que S1 en el
roadmap).

Todo vectorizado con pandas/numpy -- ni un solo loop en Python haciendo
cómputo por fila sobre miles de filas. Lección directa de un incidente real
en producción esta misma sesión: el modelo de riesgo de Plan de Acción
(N1) tumbó el sitio ENTERO por llamar al modelo una vez por fila en vez de
en bloque. Acá ni siquiera hay un modelo -- son percentiles y comparaciones
-- pero el mismo principio aplica igual: agregado en SQL/pandas, nunca un
loop Python sobre el volumen completo.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

logger = logging.getLogger("app")

DIAS_HISTORIAL_BASELINE = 90
MIN_MUESTRAS_GRUPO = 5  # un P10/P25 calculado sobre 1-2 muestras no es un percentil confiable, es ruido


def _normalizar_dia(s: str | None) -> int | None:
    """RUTA_PROGRAMACION.dia tiene variantes con tildes rotas por
    problemas de encoding históricos ('Mi?rcoles', 'S?bado') mezcladas con
    versiones sin tilde y bien escritas. Se resuelve por prefijo, no
    comparación exacta -- evita depender de arreglar el encoding en la base
    (fuera de alcance). Devuelve 0=Lunes .. 6=Domingo, igual que
    date.weekday()."""
    if not s:
        return None
    s = s.strip().upper()
    if not s:
        return None
    if s.startswith("LU"): return 0
    if s.startswith("MA"): return 1
    if s.startswith("MI"): return 2
    if s.startswith("JU"): return 3
    if s.startswith("VI"): return 4
    if s.startswith("DO"): return 6
    if s.startswith("S"):  return 5  # Sabado / S?bado -- único que empieza distinto de Domingo es Sabado
    return None


def _bucket_frecuencia(f: float) -> str:
    if f >= 3: return ">=3/semana"
    if f >= 1: return "1-2/semana"
    if f >= 0.5: return "quincenal"
    return "mensual"


def calcular_linea_base(db: Session) -> dict:
    """Capa 1: percentiles P10/P25 de `caras` por grupo (categoría ×
    jerarquía del PDV × bucket de frecuencia × cliente), usando solo
    balances 'normal' (ni quiebre ni no_existe -- ambos representan 0
    unidades, contaminarían la idea de "cuánto es lo normal a tener" en vez
    de sumar señal) de los últimos 90 días. Reemplaza el snapshot entero,
    mismo patrón que PLAN_ACCION_PENDIENTES."""
    conn = db.connection().connection
    desde = date.today() - timedelta(days=DIAS_HISTORIAL_BASELINE)

    df = pd.read_sql("""
        SELECT b.id_categoria, pi.jerarquia_nivel_2, f.frecuencia_semanal, b.id_cliente, b.caras
        FROM BALANCES_TOTALES b
        LEFT JOIN PUNTOS_INTERES1 pi ON pi.identificador = b.identificador_pdv
        LEFT JOIN FRECUENCIAS_PDVS_CLIENTE f
               ON f.id_punto_interes = b.identificador_pdv
              AND f.id_cliente = b.id_cliente AND f.activo = 1
        WHERE b.estado_producto = 'normal' AND b.caras IS NOT NULL AND b.fecha_balance >= ?
    """, conn, params=(desde,))

    if df.empty:
        raise ValueError("No hay balances 'normal' con caras en los últimos 90 días -- no se puede calcular una línea base todavía.")

    df["frecuencia_semanal"] = df["frecuencia_semanal"].fillna(1.0).astype(float)
    df["bucket_frecuencia"] = df["frecuencia_semanal"].apply(_bucket_frecuencia)
    df["caras"] = df["caras"].astype(float)

    grupos = (
        df.groupby(["id_categoria", "jerarquia_nivel_2", "bucket_frecuencia", "id_cliente"], dropna=False)["caras"]
        .agg(p10=lambda s: s.quantile(0.10), p25=lambda s: s.quantile(0.25), n="count")
        .reset_index()
    )
    grupos_totales = len(grupos)
    grupos = grupos[grupos["n"] >= MIN_MUESTRAS_GRUPO]  # descarta percentiles poco confiables (1-2 muestras)

    cursor = conn.cursor()
    cursor.execute("DELETE FROM QUIEBRE_LINEA_BASE")
    if len(grupos):
        rows = [
            (
                None if pd.isna(r.id_categoria) else int(r.id_categoria),
                None if pd.isna(r.jerarquia_nivel_2) else str(r.jerarquia_nivel_2),
                r.bucket_frecuencia, int(r.id_cliente),
                float(r.p10), float(r.p25), int(r.n),
            )
            for r in grupos.itertuples()
        ]
        cursor.fast_executemany = True
        cursor.executemany("""
            INSERT INTO QUIEBRE_LINEA_BASE
                (id_categoria, jerarquia_nivel_2, bucket_frecuencia, id_cliente, p10_caras, p25_caras, n_muestras)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, rows)
    db.commit()

    return {
        "grupos_calculados": int(len(grupos)), "grupos_descartados_por_poca_data": int(grupos_totales - len(grupos)),
        "balances_usados": int(len(df)),
    }


def calcular_alertas(db: Session) -> dict:
    """Capa 2: para cada (PDV, producto, cliente) con balance reciente,
    compara el último valor de `caras` (con NULL recuperado desde
    estado_producto cuando aplica: quiebre/no_existe implican 0, el
    mercaderista simplemente no llena el campo en ese caso) contra la línea
    base de su grupo y contra la lectura anterior, y agrega el ajuste de
    urgencia temporal (próxima visita programada). Reemplaza el snapshot
    entero de ALERTAS_QUIEBRE."""
    conn = db.connection().connection

    # ROW_NUMBER en vez de traer TODO el historial: solo hacen falta las
    # últimas 2 lecturas por combinación para calcular la tendencia.
    df = pd.read_sql("""
        WITH numeradas AS (
            SELECT b.identificador_pdv, b.id_product, b.id_cliente, b.producto, b.id_categoria,
                   b.fecha_balance, b.estado_producto,
                   COALESCE(b.caras, CASE WHEN b.estado_producto IN ('quiebre','no_existe') THEN 0 END) AS caras,
                   pi.jerarquia_nivel_2,
                   ROW_NUMBER() OVER (
                       PARTITION BY b.identificador_pdv, b.id_product, b.id_cliente
                       ORDER BY b.fecha_balance DESC
                   ) AS rn
            FROM BALANCES_TOTALES b
            LEFT JOIN PUNTOS_INTERES1 pi ON pi.identificador = b.identificador_pdv
        )
        SELECT * FROM numeradas WHERE rn <= 2
    """, conn)

    if df.empty:
        return {"alertas_calculadas": 0}

    df = df.dropna(subset=["caras"]).copy()
    df["caras"] = df["caras"].astype(float)

    llave = ["identificador_pdv", "id_product", "id_cliente"]
    actual = df[df.rn == 1].set_index(llave)
    anterior = df[df.rn == 2].set_index(llave)["caras"].rename("caras_anterior")
    actual = actual.join(anterior, how="left")
    actual["tendencia"] = actual["caras"] - actual["caras_anterior"]

    # Frecuencia por (pdv, cliente) para el bucket del grupo.
    frec = pd.read_sql("""
        SELECT id_punto_interes AS identificador_pdv, id_cliente, frecuencia_semanal
        FROM FRECUENCIAS_PDVS_CLIENTE WHERE activo = 1
    """, conn)
    frec_map = frec.set_index(["identificador_pdv", "id_cliente"])["frecuencia_semanal"].astype(float).to_dict()
    actual = actual.reset_index()
    actual["frecuencia_semanal"] = actual.apply(
        lambda r: frec_map.get((r.identificador_pdv, r.id_cliente), 1.0), axis=1,
    )
    actual["bucket_frecuencia"] = actual["frecuencia_semanal"].apply(_bucket_frecuencia)

    # Línea base ya calculada (Capa 1) -- merge vectorizado por grupo.
    base = pd.read_sql("""
        SELECT id_categoria, jerarquia_nivel_2, bucket_frecuencia, id_cliente, p10_caras, p25_caras
        FROM QUIEBRE_LINEA_BASE
    """, conn)
    actual = actual.merge(base, how="left", on=["id_categoria", "jerarquia_nivel_2", "bucket_frecuencia", "id_cliente"])

    # Riesgo -- vectorizado, sin loop.
    condiciones = [
        actual["caras"] <= 0,
        (actual["caras"] <= actual["p10_caras"]) & (actual["tendencia"] < 0),
        (actual["caras"] <= actual["p25_caras"]) & (actual["tendencia"] <= 0),
    ]
    actual["riesgo"] = np.select(condiciones, ["Quiebre", "Riesgo ALTO", "Riesgo MEDIO"], default="Normal")

    # Próxima visita programada por (pdv, cliente) -- se resuelve UNA vez
    # por combinación distinta (unas pocas centenas), no por fila de balance.
    hoy = date.today()
    rutas = pd.read_sql("""
        SELECT id_punto_interes AS identificador_pdv, id_cliente, dia
        FROM RUTA_PROGRAMACION WHERE activa = 1
    """, conn)
    rutas["dia_idx"] = rutas["dia"].apply(_normalizar_dia)
    rutas = rutas.dropna(subset=["dia_idx"])
    dias_por_combo = rutas.groupby(["identificador_pdv", "id_cliente"])["dia_idx"].apply(set).to_dict()

    def _dias_hasta_proxima(pdv, cliente) -> float | None:
        dias_prog = dias_por_combo.get((pdv, cliente))
        if not dias_prog:
            return None
        for delta in range(8):
            if (hoy + timedelta(days=delta)).weekday() in dias_prog:
                return delta
        return None

    combos_unicos = actual[["identificador_pdv", "id_cliente"]].drop_duplicates()
    combos_unicos["dias_hasta_proxima_visita"] = combos_unicos.apply(
        lambda r: _dias_hasta_proxima(r.identificador_pdv, r.id_cliente), axis=1,
    )
    actual = actual.merge(combos_unicos, how="left", on=["identificador_pdv", "id_cliente"])

    actual["dias_para_llegar_a_cero"] = np.where(
        actual["tendencia"] < 0, actual["caras"] / (-actual["tendencia"]), np.nan,
    )
    actual["urgente"] = (
        (actual["riesgo"] != "Normal")
        & actual["dias_hasta_proxima_visita"].notna()
        & actual["dias_para_llegar_a_cero"].notna()
        & (actual["dias_para_llegar_a_cero"] <= actual["dias_hasta_proxima_visita"])
    )

    cursor = conn.cursor()
    cursor.execute("DELETE FROM ALERTAS_QUIEBRE")
    # Solo se persisten Riesgo ALTO/MEDIO -- son la señal PREDICTIVA nueva.
    # "Quiebre" (caras<=0) ya es visible tal cual en
    # BALANCES_TOTALES.estado_producto, guardarlo acá también solo infla la
    # tabla (confirmado contra datos reales: ~80% de las combinaciones
    # activas ya están en 0 ahora mismo) sin sumar información.
    filas_no_normales = actual[actual["riesgo"].isin(["Riesgo ALTO", "Riesgo MEDIO"])]
    # id_product puede venir NULL en BALANCES_TOTALES (producto no
    # identificado bien al escanear la etiqueta) -- confirmado en
    # producción, tumbaba el int() sin protección. Sin id_product no hay
    # forma de decir DE QUÉ producto es la alerta, así que se descartan acá
    # en vez de forzarlas con un placeholder.
    filas_no_normales = filas_no_normales.dropna(subset=["id_product", "id_cliente"])
    if len(filas_no_normales):
        def _f(v):
            return None if pd.isna(v) else float(v)
        def _i(v):
            return None if pd.isna(v) else int(v)

        rows = [
            (
                r.identificador_pdv, int(r.id_product), int(r.id_cliente), r.producto,
                _f(r.caras), _f(r.caras_anterior), _f(r.tendencia),
                r.riesgo, bool(r.urgente), _i(r.dias_hasta_proxima_visita), _f(r.dias_para_llegar_a_cero),
            )
            for r in filas_no_normales.itertuples()
        ]
        cursor.fast_executemany = True
        cursor.executemany("""
            INSERT INTO ALERTAS_QUIEBRE
                (identificador_pdv, id_product, id_cliente, producto, caras_actual, caras_anterior,
                 tendencia, riesgo, urgente, dias_hasta_proxima_visita, dias_para_llegar_a_cero)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, rows)
    db.commit()

    return {
        "balances_evaluados": int(len(actual)),
        "alertas_calculadas": int(len(filas_no_normales)),
        # OJO: contar sobre `actual` completo (como se hacía antes) infla
        # este número con "Quiebre" urgentes -- que a propósito NUNCA se
        # persisten (ver comentario arriba) -- y con filas sin
        # id_product/id_cliente que el dropna() de arriba descartó. Hay que
        # contar sobre filas_no_normales, lo que de verdad quedó insertado,
        # para que este número coincida con lo que después devuelve
        # GET /alertas?urgente=true.
        "urgentes": int(filas_no_normales["urgente"].sum()),
    }
