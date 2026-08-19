"""S1 del roadmap predictivo -- Fase 2 de Quiebre, después de N2.

Deliberadamente ATADO al output de N2 (quiebre_service.py), no a todo el
universo de combinaciones SKU×PDV: N2 ya filtra a las decenas/centenas de
combinaciones en Riesgo ALTO/MEDIO -- son las que de verdad importan
pronosticar. Ajustar un modelo de series de tiempo por separado para CADA
combinación SKU×PDV que existe (podrían ser decenas de miles) sería lento
y de bajo valor: la mayoría están en 'Normal' y no necesitan pronóstico.

Mismo criterio de gate que S2 (ventas_pedidos.py::pronostico_pedidos) y S4
(cobertura_encuestas_service.py): si no hay suficiente historial, se dice
explícitamente -- nunca se inventa una tendencia con pocos puntos. Hoy
(19 ago 2026, N2 recién desplegado) prácticamente ninguna combinación va a
tener las semanas mínimas todavía -- ESO es lo esperado, no un bug. Se
activa solo cuando N2 lleve corriendo el tiempo suficiente.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

logger = logging.getLogger("app")

MIN_SEMANAS_S1 = 8       # mismo orden que S4 -- una tendencia con menos de 2 meses de semanas es ruido
HORIZONTE_SEMANAS_S1 = 6
DIAS_HISTORIAL_S1 = 180  # 180 días ≈ 25 semanas -- suficiente margen sobre el mínimo de 8


def calcular_pronostico_quiebre(db: Session, id_cliente: int | None = None, horizonte_semanas: int = HORIZONTE_SEMANAS_S1) -> dict:
    conn = db.connection().connection
    horizonte_semanas = max(1, min(horizonte_semanas, 12))

    # Población candidata: lo que N2 YA marcó como Riesgo ALTO/MEDIO ahora
    # mismo -- no todo BALANCES_TOTALES. Ver docstring del módulo.
    where_cliente = "AND a.id_cliente = ?" if id_cliente else ""
    params = (id_cliente,) if id_cliente else ()
    candidatos = pd.read_sql(f"""
        SELECT a.identificador_pdv, a.id_product, a.id_cliente, a.producto, a.riesgo
        FROM ALERTAS_QUIEBRE a
        WHERE 1=1 {where_cliente}
    """, conn, params=params)

    if candidatos.empty:
        return {
            "candidatos_de_n2": 0, "con_historial_suficiente": 0,
            "min_semanas_requeridas": MIN_SEMANAS_S1, "pronosticos": [],
        }

    desde = date.today() - timedelta(days=DIAS_HISTORIAL_S1)
    ids_pdv = tuple(candidatos["identificador_pdv"].unique().tolist())
    ids_prod = tuple(int(x) for x in candidatos["id_product"].unique().tolist())

    # Historial semanal de TODAS las combinaciones candidatas de una vez
    # (un solo round-trip a la base, no uno por combinación) -- mismo
    # principio de vectorización de todo el módulo N2.
    balances = pd.read_sql(f"""
        SELECT identificador_pdv, id_product, id_cliente, fecha_balance,
               COALESCE(caras, CASE WHEN estado_producto IN ('quiebre','no_existe') THEN 0 END) AS caras
        FROM BALANCES_TOTALES
        WHERE identificador_pdv IN ({','.join('?' * len(ids_pdv))})
          AND id_product IN ({','.join('?' * len(ids_prod))})
          AND fecha_balance >= ?
    """, conn, params=(*ids_pdv, *ids_prod, desde))
    balances = balances.dropna(subset=["caras"])

    if balances.empty:
        return {
            "candidatos_de_n2": int(len(candidatos)), "con_historial_suficiente": 0,
            "min_semanas_requeridas": MIN_SEMANAS_S1, "pronosticos": [],
        }

    balances["semana"] = pd.to_datetime(balances["fecha_balance"]).dt.to_period("W").apply(lambda p: p.start_time.date())
    # Un valor por semana por combinación: la última lectura de esa semana
    # (no el promedio -- para stock, "cuánto había el viernes" importa más
    # que diluir con lecturas de mitad de semana).
    semanal = (
        balances.sort_values("fecha_balance")
        .groupby(["identificador_pdv", "id_product", "id_cliente", "semana"])["caras"]
        .last()
        .reset_index()
    )

    resultados = []
    con_historial = 0
    for _, cand in candidatos.iterrows():
        llave = (cand.identificador_pdv, int(cand.id_product), int(cand.id_cliente))
        serie = semanal[
            (semanal.identificador_pdv == llave[0]) &
            (semanal.id_product == llave[1]) &
            (semanal.id_cliente == llave[2])
        ].sort_values("semana")

        base = {
            "identificador_pdv": llave[0], "id_product": llave[1], "id_cliente": llave[2],
            "producto": cand.producto, "riesgo_actual_n2": cand.riesgo,
            "semanas_de_historial": int(len(serie)),
        }

        if len(serie) < MIN_SEMANAS_S1:
            resultados.append({
                **base, "suficiente_historial": False,
                "semanas_faltantes": MIN_SEMANAS_S1 - len(serie), "pronostico": [],
            })
            continue

        try:
            y = serie["caras"].to_numpy(dtype=float)
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            modelo = ExponentialSmoothing(y, trend="add", damped_trend=True, initialization_method="estimated").fit()
            pred = [max(0.0, round(float(v), 1)) for v in modelo.forecast(horizonte_semanas)]
            residuos = y - modelo.fittedvalues
            desviacion = float(np.std(residuos)) if len(residuos) > 1 else 0.0

            semana_cero = next((i + 1 for i, v in enumerate(pred) if v <= 0), None)

            con_historial += 1
            resultados.append({
                **base, "suficiente_historial": True,
                "pronostico": [
                    {"semana_offset": i + 1, "caras_esperadas": v,
                     "rango_bajo": max(0.0, round(v - desviacion, 1)), "rango_alto": round(v + desviacion, 1)}
                    for i, v in enumerate(pred)
                ],
                "semanas_hasta_cero_proyectado": semana_cero,
            })
        except Exception as e:
            logger.warning(f"[S1] Fallo el ajuste para {llave}: {e}")
            resultados.append({**base, "suficiente_historial": False, "semanas_faltantes": 0, "pronostico": [], "error_modelo": True})

    return {
        "candidatos_de_n2": int(len(candidatos)),
        "con_historial_suficiente": con_historial,
        "min_semanas_requeridas": MIN_SEMANAS_S1,
        "pronosticos": resultados,
    }
