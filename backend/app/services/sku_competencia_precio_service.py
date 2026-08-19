"""S3 del roadmap predictivo: deriva de precio propio vs. competencia.

Ya existen "Reglas de Alerta de Precio" en el dashboard de Power BI del
cliente -- pero son umbrales estáticos que avisan DESPUÉS de que el precio
ya cruzó la línea. Esto no reemplaza esa regla (sigue viva en Power BI);
la complementa: con el mismo mapeo SKU_COMPETENCIA que ya usa "SKU vs SKU"
(sku_competencia.py) y el precio capturado en cada balance, se suaviza la
tendencia y se alerta cuando la PENDIENTE apunta al umbral, no cuando ya
lo tocó.

Mismo criterio que ventas_pedidos.py::pronostico_pedidos (Holt amortiguado
vía statsmodels) para no introducir una segunda convención de forecasting
en la misma base de código.
"""
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import text
from sqlalchemy.orm import Session, aliased

from app.models.sku_competencia import SkuCompetencia
from app.models.producto import Producto, Marca

logger = logging.getLogger(__name__)

# Por debajo de esto no se ajusta el modelo -- una tendencia estimada con 5
# puntos es ruido, no señal (mismo criterio de mínimos que el resto de los
# módulos predictivos de esta sesión: S4 exige 8 semanas, ventas exige un
# mínimo propio). 6 puntos pareados (mismo día, ambos SKU con precio) es el
# piso razonable para que Holt con tendencia tenga algo que ajustar.
MIN_PUNTOS_DERIVA = 6
HORIZONTE_PROYECCION = 4          # cuántos puntos futuros se proyectan
Z_SCORE_ATENCION = 2.0            # |z| del último residuo para marcar "atención"
UMBRAL_PCT_DEFAULT = 15.0         # % de gap propio-vs-competencia que dispara alerta
                                   # si no se pasa umbral_pct explícito -- valor de
                                   # arranque razonable, no el umbral real de Power BI
                                   # (ese es configuración del cliente, no vive acá).
VENTANA_DIAS = 180                # historial que se considera por SKU pair


def _serie_pareada(db: Session, id_cliente: int, id_producto_cliente: int, id_producto_competencia: int):
    """Precio promedio diario de cada SKU (precio_ds -- dólares, no
    bolívares: en un contexto de devaluación el precio en Bs se mueve por
    inflación, no por posición competitiva real; comparar en USD es lo que
    de verdad refleja si el propio precio se está desalineando del de la
    competencia). Se intersectan las fechas donde AMBOS SKU tienen precio
    -- si un día solo se relevó uno de los dos, ese punto no aporta nada al
    spread y se descarta en vez de rellenarlo con un valor inventado."""
    desde = datetime.utcnow() - timedelta(days=VENTANA_DIAS)
    rows = db.execute(text("""
        SELECT CAST(fecha_balance AS DATE) AS dia, id_product, AVG(precio_ds) AS precio
        FROM BALANCES_TOTALES
        WHERE id_cliente = :id_cliente
          AND id_product IN (:id_propio, :id_comp)
          AND precio_ds IS NOT NULL AND precio_ds > 0
          AND fecha_balance >= :desde
        GROUP BY CAST(fecha_balance AS DATE), id_product
        ORDER BY dia
    """), {
        "id_cliente": id_cliente, "id_propio": id_producto_cliente,
        "id_comp": id_producto_competencia, "desde": desde,
    }).fetchall()

    propio: dict = {}
    comp: dict = {}
    for r in rows:
        (propio if r.id_product == id_producto_cliente else comp)[r.dia] = float(r.precio)

    dias_comunes = sorted(set(propio) & set(comp))
    return [
        {"dia": d, "precio_propio": propio[d], "precio_competencia": comp[d]}
        for d in dias_comunes
    ]


def calcular_deriva_precio(db: Session, id_cliente: int, umbral_pct: float = UMBRAL_PCT_DEFAULT) -> list[dict]:
    ProductoCliente = aliased(Producto)
    ProductoComp = aliased(Producto)
    MarcaCliente = aliased(Marca)
    MarcaComp = aliased(Marca)

    mapeos = (
        db.query(SkuCompetencia, ProductoCliente, MarcaCliente, ProductoComp, MarcaComp)
        .join(ProductoCliente, ProductoCliente.id_producto == SkuCompetencia.id_producto_cliente)
        .outerjoin(MarcaCliente, MarcaCliente.id_marca == ProductoCliente.id_marca)
        .join(ProductoComp, ProductoComp.id_producto == SkuCompetencia.id_producto_competencia)
        .outerjoin(MarcaComp, MarcaComp.id_marca == ProductoComp.id_marca)
        .filter(SkuCompetencia.id_cliente == id_cliente, SkuCompetencia.activo == True)
        .order_by(ProductoCliente.producto_gu, ProductoComp.producto_gu)
        .all()
    )

    resultados = []
    for sc, pcli, mcli, pcomp, mcomp in mapeos:
        base = {
            "id_sku_competencia": sc.id,
            "producto_cliente": pcli.producto_gu,
            "marca_cliente": mcli.nombre if mcli else None,
            "producto_competencia": pcomp.producto_gu,
            "marca_competencia": mcomp.nombre if mcomp else None,
            "umbral_pct": umbral_pct,
        }

        serie = _serie_pareada(db, id_cliente, sc.id_producto_cliente, sc.id_producto_competencia)
        if len(serie) < MIN_PUNTOS_DERIVA:
            resultados.append({
                **base, "suficiente_historial": False, "n_puntos": len(serie),
                "puntos_faltantes": MIN_PUNTOS_DERIVA - len(serie),
                "estado": "sin_datos", "spread_actual_pct": None,
                "serie_historica": [
                    {"dia": p["dia"].isoformat(), "spread_pct": round((p["precio_propio"] - p["precio_competencia"]) / p["precio_competencia"] * 100, 2)}
                    for p in serie
                ],
                "proyeccion": [],
            })
            continue

        spread = [(p["precio_propio"] - p["precio_competencia"]) / p["precio_competencia"] * 100 for p in serie]

        try:
            import numpy as np
            from statsmodels.tsa.holtwinters import ExponentialSmoothing
            y = np.array(spread, dtype=float)
            modelo = ExponentialSmoothing(y, trend="add", damped_trend=True, initialization_method="estimated").fit()
            proyectado = [float(v) for v in modelo.forecast(HORIZONTE_PROYECCION)]

            residuos = y - modelo.fittedvalues
            desviacion = float(np.std(residuos)) if len(residuos) > 1 else 0.0
            z_ultimo = float(residuos[-1] / desviacion) if desviacion > 0 else 0.0

            spread_actual = float(y[-1])
            ya_cruzo = abs(spread_actual) >= umbral_pct
            # "la pendiente apunta al umbral, no cuando ya lo tocó": mira si
            # el propio umbral queda del lado correcto del signo actual del
            # spread (si hoy el propio precio está por debajo, el umbral que
            # importa vigilar es +umbral_pct, no -umbral_pct, y viceversa) y
            # si CUALQUIER punto proyectado lo alcanza.
            umbral_relevante = umbral_pct if spread_actual >= 0 else -umbral_pct
            va_a_cruzar = any(
                (v >= umbral_relevante if umbral_relevante > 0 else v <= umbral_relevante)
                for v in proyectado
            )

            if ya_cruzo:
                estado = "critico"
            elif va_a_cruzar:
                estado = "alerta"
            elif abs(z_ultimo) >= Z_SCORE_ATENCION:
                estado = "atencion"
            else:
                estado = "ok"

            resultados.append({
                **base, "suficiente_historial": True, "n_puntos": len(serie),
                "estado": estado,
                "spread_actual_pct": round(spread_actual, 2),
                "z_score_ultimo_residuo": round(z_ultimo, 2),
                "serie_historica": [
                    {"dia": p["dia"].isoformat(), "spread_pct": round(s, 2)}
                    for p, s in zip(serie, spread)
                ],
                "proyeccion": [round(v, 2) for v in proyectado],
            })
        except Exception as e:
            logger.warning(f"[DerivaPrecio] Fallo el ajuste para SKU pair {sc.id}: {e}")
            resultados.append({
                **base, "suficiente_historial": False, "n_puntos": len(serie),
                "puntos_faltantes": 0, "estado": "sin_datos", "spread_actual_pct": None,
                "serie_historica": [], "proyeccion": [], "error_modelo": True,
            })

    return resultados
