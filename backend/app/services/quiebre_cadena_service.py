"""Quiebre por Cadena -- vista agregada de tasa de quiebre por cadena de PDV
(Farmatodo, Locatel, Gama, Automercados Plaza's...) y departamento/categoría,
pensada para venderse a LA CADENA, no a la marca-cliente.

Distinto de N2 (quiebre_service.py) en audiencia y en forma, no en dato:
- N2 alerta a una MARCA sobre SUS SKU antes de que lleguen a cero -- output
  por PDV × producto × cliente, con nombre de producto.
- Esto agrega hacia arriba (cadena, cadena × departamento) SIN atribuir a
  qué marca pertenece cada quiebre -- la cadena ve "12% de quiebre en tu
  categoría licores en tus tiendas de Caracas", no "Dusa está quebrado en
  la sucursal X". Deliberado: EPRAN monitorea SKU por cuenta de marcas
  distintas (a veces competidoras entre sí) -- exponerle a una cadena el
  detalle por marca sin su consentimiento sería un problema de gobierno de
  dato, no solo de producto.

Cobertura parcial a propósito: esto solo puede mostrar quiebre de las
marcas/categorías que EPRAN ya monitorea en esa cadena hoy -- no es un
barrido de tienda completa (eso es Auditor de Data, propuesto y no
construido todavía). Por eso el endpoint también devuelve cuántos
SKU-PDV distintos entraron en el cálculo, para que el material de venta
sea honesto sobre el alcance real.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
from sqlalchemy.orm import Session

DIAS_VENTANA_DEFAULT = 30
MIN_MUESTRAS_CELDA = 5  # misma razón que N2: una tasa sobre 1-2 lecturas es ruido, no señal


def calcular_quiebre_por_cadena(db: Session, dias_ventana: int = DIAS_VENTANA_DEFAULT) -> dict:
    conn = db.connection().connection
    desde = date.today() - timedelta(days=dias_ventana)

    # Última lectura por (PDV, producto) dentro de la ventana -- mismo
    # patrón ROW_NUMBER que usa N2, y el mismo criterio de "sin caras pero
    # marcado quiebre/no_existe = 0 unidades".
    df = pd.read_sql("""
        WITH numeradas AS (
            SELECT b.identificador_pdv, b.id_product, b.id_categoria, b.categoria,
                   b.estado_producto,
                   COALESCE(b.caras, CASE WHEN b.estado_producto IN ('quiebre','no_existe') THEN 0 END) AS caras,
                   pi.jerarquia_nivel_2 AS cadena, pi.departamento,
                   ROW_NUMBER() OVER (
                       PARTITION BY b.identificador_pdv, b.id_product
                       ORDER BY b.fecha_balance DESC
                   ) AS rn
            FROM BALANCES_TOTALES b
            LEFT JOIN PUNTOS_INTERES1 pi ON pi.identificador = b.identificador_pdv
            WHERE b.fecha_balance >= ?
        )
        SELECT * FROM numeradas WHERE rn = 1
    """, conn, params=(desde,))

    if df.empty:
        return {"cadenas": [], "ventana_dias": dias_ventana, "sku_pdv_evaluados": 0}

    df = df.dropna(subset=["caras", "cadena"]).copy()
    df["caras"] = df["caras"].astype(float)
    df["en_quiebre"] = (df["caras"] <= 0) | (df["estado_producto"] == "quiebre")

    total_evaluados = int(len(df))

    # Nivel 1: por cadena sola.
    por_cadena = (
        df.groupby("cadena")
        .agg(sku_pdv_evaluados=("en_quiebre", "count"), en_quiebre=("en_quiebre", "sum"))
        .reset_index()
    )
    por_cadena = por_cadena[por_cadena["sku_pdv_evaluados"] >= MIN_MUESTRAS_CELDA]
    por_cadena["tasa_quiebre_pct"] = (por_cadena["en_quiebre"] / por_cadena["sku_pdv_evaluados"] * 100).round(1)

    # Nivel 2: por cadena × departamento -- el desglose que de verdad es
    # accionable para un gerente de categoría de la cadena.
    df["departamento"] = df["departamento"].fillna("Sin departamento")
    por_depto = (
        df.groupby(["cadena", "departamento"])
        .agg(sku_pdv_evaluados=("en_quiebre", "count"), en_quiebre=("en_quiebre", "sum"))
        .reset_index()
    )
    por_depto = por_depto[por_depto["sku_pdv_evaluados"] >= MIN_MUESTRAS_CELDA]
    por_depto["tasa_quiebre_pct"] = (por_depto["en_quiebre"] / por_depto["sku_pdv_evaluados"] * 100).round(1)

    resultado = []
    for r in por_cadena.itertuples():
        deptos = por_depto[por_depto["cadena"] == r.cadena]
        resultado.append({
            "cadena": r.cadena,
            "sku_pdv_evaluados": int(r.sku_pdv_evaluados),
            "en_quiebre": int(r.en_quiebre),
            "tasa_quiebre_pct": float(r.tasa_quiebre_pct),
            "departamentos": [
                {
                    "departamento": d.departamento,
                    "sku_pdv_evaluados": int(d.sku_pdv_evaluados),
                    "en_quiebre": int(d.en_quiebre),
                    "tasa_quiebre_pct": float(d.tasa_quiebre_pct),
                }
                for d in deptos.itertuples()
            ],
        })

    resultado.sort(key=lambda x: x["tasa_quiebre_pct"], reverse=True)

    return {
        "cadenas": resultado,
        "ventana_dias": dias_ventana,
        "sku_pdv_evaluados": total_evaluados,
        "min_muestras_celda": MIN_MUESTRAS_CELDA,
    }
