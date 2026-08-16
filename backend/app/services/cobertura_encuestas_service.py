"""Curva de cobertura de encuestas médicas -- roadmap predictivo, item S4.
Cuántos médicos nuevos se registran por semana en cada estado (hoy:
Distrito Capital y Miranda, los únicos en CATALOGOS_ENCUESTADOR). No es una
serie estacionaria como demanda de producto -- es un proceso que se satura
(universo finito de médicos por zona), así que se ajusta una curva
logística sobre el ACUMULADO en vez de ARIMA sobre el semanal.

logística(t) = L / (1 + e^(-k*(t - x0)))
  L  = techo estimado de médicos alcanzables en la zona
  k  = qué tan rápido se acerca al techo
  x0 = semana del punto de inflexión (máxima velocidad de registro)

Con pocas semanas de historial cualquier ajuste de 3 parámetros es puro
sobreajuste -- 2 puntos pasan exactos por cualquier curva con margen de
sobra. Por eso hay un mínimo duro de semanas Y de médicos antes de
intentar el fit, más un piso de R² para aceptarlo; por debajo de eso se
devuelve el histórico real (útil igual para ver la serie semanal en el
gráfico) pero sin proyección -- mismo patrón de "no alcanza el dato
todavía" que ya usan S2 (pronóstico de pedidos) y S7 (tendencia de
competencia)."""
import json
import logging
from datetime import timedelta

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

logger = logging.getLogger("app")

MIN_SEMANAS_CURVA = 8
MIN_MEDICOS_ZONA = 20
UMBRAL_R2 = 0.6
SEMANAS_PROYECCION = 12


def _logistic(t, L, k, x0):
    return L / (1 + np.exp(-k * (t - x0)))


def _fit_logistic(semanas_idx: np.ndarray, acumulado: np.ndarray):
    from scipy.optimize import curve_fit

    L0 = acumulado[-1] * 1.5
    p0 = [L0, 0.5, semanas_idx[-1] / 2]
    bounds = ([acumulado[-1], 0.01, -10.0], [acumulado[-1] * 20, 5.0, semanas_idx[-1] + 52])
    popt, _ = curve_fit(_logistic, semanas_idx, acumulado, p0=p0, bounds=bounds, maxfev=5000)
    pred = _logistic(semanas_idx, *popt)
    ss_res = float(np.sum((acumulado - pred) ** 2))
    ss_tot = float(np.sum((acumulado - acumulado.mean()) ** 2))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0.0
    return popt, r2


def calcular_cobertura(db: Session) -> dict:
    conn = db.connection().connection

    catalogo = pd.read_sql("SELECT nombre FROM CATALOGOS_ENCUESTADOR WHERE tipo = 'estado'", conn)
    if catalogo.empty:
        raise ValueError("No hay estados en CATALOGOS_ENCUESTADOR -- no hay zonas que calcular.")

    medicos = pd.read_sql("SELECT estado, fecha_registro FROM medicos WHERE fecha_registro IS NOT NULL", conn)
    if medicos.empty:
        raise ValueError("No hay médicos registrados todavía.")

    # Match case-insensitive contra el catálogo -- la data tiene variantes
    # de captura libre anteriores al catálogo estandarizado ("Distrito
    # capital" vs "Distrito Capital", o directamente basura como "estado",
    # "Bahia") que se descartan solas al no matchear ningún estado canónico.
    mapa = {n.strip().lower(): n.strip() for n in catalogo["nombre"]}
    medicos["estado_norm"] = medicos["estado"].astype(str).str.strip().str.lower().map(mapa)
    medicos = medicos.dropna(subset=["estado_norm"])
    medicos["fecha_registro"] = pd.to_datetime(medicos["fecha_registro"])

    cursor = conn.cursor()
    cursor.execute("DELETE FROM COBERTURA_ENCUESTAS_CURVA")

    resultados = []
    for estado in sorted(set(mapa.values())):
        sub = medicos[medicos["estado_norm"] == estado]
        n_medicos = len(sub)
        if n_medicos == 0:
            continue

        # Semana ancla lunes (W-SUN agrupa domingo-a-sábado; start_time cae
        # en lunes) -- eje estable para el índice de tiempo del ajuste.
        semanas = sub["fecha_registro"].dt.to_period("W-SUN").apply(lambda p: p.start_time.date())
        semanal = semanas.value_counts().sort_index()

        semana_inicio = semanal.index.min()
        # Rellena semanas sin registros con 0 -- si no, el índice de tiempo
        # queda con huecos y el ajuste logístico ve una escala de semana
        # incorrecta (semanas "saltadas" cuentan como si no existieran).
        todas_semanas = pd.date_range(semana_inicio, semanal.index.max(), freq="7D").date
        semanal = semanal.reindex(todas_semanas, fill_value=0)
        acumulado = semanal.cumsum()
        n_semanas = len(semanal)

        serie = [
            {"semana": str(s), "nuevos": int(n), "acumulado": int(a)}
            for s, n, a in zip(semanal.index, semanal.values, acumulado.values)
        ]

        curva_valida = False
        L = k = x0 = r2 = None
        proyeccion = None

        if n_semanas >= MIN_SEMANAS_CURVA and n_medicos >= MIN_MEDICOS_ZONA:
            try:
                t = np.arange(n_semanas, dtype=float)
                y = acumulado.values.astype(float)
                (L, k, x0), r2 = _fit_logistic(t, y)
                if r2 >= UMBRAL_R2 and L > 0 and k > 0:
                    curva_valida = True
                    t_proy = np.arange(n_semanas, n_semanas + SEMANAS_PROYECCION, dtype=float)
                    y_proy = _logistic(t_proy, L, k, x0)
                    proyeccion = [
                        {"semana": str(semana_inicio + timedelta(weeks=int(tt))), "proyectado": round(float(yy), 1)}
                        for tt, yy in zip(t_proy, y_proy)
                    ]
                else:
                    logger.info(f"[CoberturaEncuestas] {estado}: ajuste con R²={r2:.2f} por debajo del umbral ({UMBRAL_R2}), se descarta")
            except Exception as e:
                logger.warning(f"[CoberturaEncuestas] {estado}: no se pudo ajustar la curva -- {e}")

        cursor.execute("""
            INSERT INTO COBERTURA_ENCUESTAS_CURVA
                (estado, n_semanas_historial, n_medicos_total, curva_valida,
                 asintota_l, tasa_crecimiento_k, semana_punto_medio_x0, r2,
                 semana_inicio, serie_json, proyeccion_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            estado, n_semanas, n_medicos, curva_valida,
            float(L) if L is not None else None,
            float(k) if k is not None else None,
            float(x0) if x0 is not None else None,
            float(r2) if r2 is not None else None,
            semana_inicio, json.dumps(serie),
            json.dumps(proyeccion) if proyeccion is not None else None,
        ))
        resultados.append({"estado": estado, "n_medicos": n_medicos, "n_semanas": n_semanas, "curva_valida": curva_valida})

    db.commit()
    logger.info(f"[CoberturaEncuestas] Recalculado: {resultados}")
    return {"zonas_calculadas": len(resultados), "detalle": resultados}
