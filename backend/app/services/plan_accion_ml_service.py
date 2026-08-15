"""Plan de Acción -- entrenamiento del modelo de riesgo de rechazo.

Reemplaza PESO_TIPO (0.6/1.0 fijo a mano, ver plan_accion_service.py) por una
probabilidad entrenada con LightGBM: dado un PDV/cliente, qué tan probable es
que la próxima visita termine con al menos una foto rechazada. Confirmado
contra datos reales de producción antes de construir esto: 19949 visitas,
436 mercaderistas, 5 meses de historial, tasa base de rechazo real 3.86%
(770 visitas) -- suficiente señal real para entrenar, no un dataset de
juguete.

Diseño explícito, no "reemplazar todo por ML": urgencia y peso_prioridad
(en plan_accion_service.py) siguen siendo lógica de negocio válida -- qué
tan atrasado está un PDV, qué tan importante es para el cliente -- y no es
lo que este modelo predice. Lo que este modelo aporta es una mejor
estimación de RIESGO DE CALIDAD, así que se expone como peso_riesgo =
prob_predicha / tasa_base_global: un multiplicador centrado en 1.0 (mismo
orden de magnitud que el PESO_TIPO 0.6/1.0 que reemplaza), no la
probabilidad cruda (que rondaría 0.01-0.30 y rompería en silencio el umbral
score_min=1.0 que ya usa GET /plan-accion/clusters).

Features -- deliberadamente solo las que existen igual en entrenamiento
(sobre visitas históricas) y en inferencia (sobre pendientes actuales), para
no tener comportamiento distinto train/serve:
  - prioridad_num: mismo mapeo que plan_accion_service._peso_prioridad
  - frecuencia_semanal
  - tasa_rechazo_historica_pdv_cliente: % de rechazo de ESTE (PDV,cliente)
    hasta la fecha, ventana expansiva -- en entrenamiento, solo cuenta
    visitas ANTERIORES a la que se está etiquetando (evita fuga de
    información: no se puede usar el futuro para predecir el pasado)
  - tasa_rechazo_historica_cliente: mismo cálculo a nivel de cliente
    completo -- respaldo para PDVs con poco historial propio
  - n_visitas_historicas: cuántas visitas previas tiene este (PDV,cliente)

Validación temporal, no aleatoria: las últimas semanas de historial quedan
afuera del entrenamiento y sirven para medir AUC/average precision reales
-- una visita no debe validarse nunca con datos de después de que ocurrió.
"""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from decimal import Decimal

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

FEATURES = [
    "prioridad_num", "frecuencia_semanal",
    "tasa_rechazo_historica_pdv_cliente", "tasa_rechazo_historica_cliente",
    "n_visitas_historicas",
]

PESO_PRIORIDAD = {"alta": 3, "media": 2, "baja": 1}
PESO_PRIORIDAD_DEFAULT = 2
TASA_BASE_PRIOR = 0.0386  # tasa de rechazo real observada en 19949 visitas -- prior para clientes/PDVs sin historial propio todavía

DIAS_VALIDACION = 21  # ver comentario en entrenar_modelo() -- probado contra 7/10/14/21 días reales
MIN_VISITAS_ENTRENAMIENTO = 500  # con menos que esto no hay señal suficiente para confiar en el modelo


def _peso_prioridad_num(prioridad: str | None) -> int:
    if not prioridad:
        return PESO_PRIORIDAD_DEFAULT
    return PESO_PRIORIDAD.get(prioridad.strip().lower(), PESO_PRIORIDAD_DEFAULT)


def _to_float(v) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


HISTORIAL_QUERY = """
SELECT vm.id_visita, vm.identificador_punto_interes, vm.id_cliente, vm.fecha_visita,
       MAX(CASE WHEN ft.Estado = 'Rechazada' THEN 1 ELSE 0 END) AS rechazada,
       MAX(rp.prioridad) AS prioridad,
       MAX(f.frecuencia_semanal) AS frecuencia_semanal
FROM VISITAS_MERCADERISTA vm
LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita
LEFT JOIN RUTA_PROGRAMACION rp
       ON rp.id_punto_interes = vm.identificador_punto_interes
      AND rp.id_cliente = vm.id_cliente AND rp.activa = 1
LEFT JOIN FRECUENCIAS_PDVS_CLIENTE f
       ON f.id_punto_interes = vm.identificador_punto_interes
      AND f.id_cliente = vm.id_cliente AND f.activo = 1
WHERE vm.identificador_punto_interes IS NOT NULL AND vm.id_cliente IS NOT NULL
  AND vm.fecha_visita IS NOT NULL
GROUP BY vm.id_visita, vm.identificador_punto_interes, vm.id_cliente, vm.fecha_visita
ORDER BY vm.fecha_visita
"""


def _construir_dataset(db: Session):
    """Arma el dataset de entrenamiento con las tasas históricas calculadas
    de forma expansiva (solo con visitas ANTERIORES a cada fila, en orden
    cronológico) para no filtrar información del futuro hacia el pasado."""
    from app.services.plan_accion_service import _execute_with_timeout

    rows = _execute_with_timeout(db, HISTORIAL_QUERY, (), timeout=60)

    pdv_cliente_visto: dict[tuple, list[int]] = {}   # (pdv,cliente) -> [n_visitas, n_rechazos]
    cliente_visto: dict[int, list[int]] = {}          # cliente -> [n_visitas, n_rechazos]

    X, y, fechas = [], [], []
    for id_visita, id_punto, id_cliente, fecha, rechazada, prioridad, frecuencia in rows:
        if fecha is None:
            continue
        fecha_d = fecha.date() if hasattr(fecha, "date") else fecha

        pc = pdv_cliente_visto.setdefault((id_punto, id_cliente), [0, 0])
        cl = cliente_visto.setdefault(id_cliente, [0, 0])
        n_pc, rech_pc = pc
        n_cl, rech_cl = cl

        tasa_cl = (rech_cl / n_cl) if n_cl > 0 else TASA_BASE_PRIOR
        tasa_pc = (rech_pc / n_pc) if n_pc > 0 else tasa_cl

        X.append([_peso_prioridad_num(prioridad), _to_float(frecuencia) or 1.0, tasa_pc, tasa_cl, n_pc])
        y.append(int(rechazada or 0))
        fechas.append(fecha_d)

        # Actualizar DESPUÉS de usar -- para que esta visita no se cuente a sí misma.
        pc[0] += 1; pc[1] += int(rechazada or 0)
        cl[0] += 1; cl[1] += int(rechazada or 0)

    return np.array(X, dtype=float), np.array(y, dtype=int), fechas


def entrenar_modelo(db: Session) -> dict:
    """Entrena y persiste un modelo nuevo en PLAN_ACCION_MODELO_RIESGO.
    Lanza ValueError (con el motivo) si no hay suficiente historial todavía
    -- calcular_pendientes() sigue con PESO_TIPO fijo hasta que esto pase."""
    import lightgbm as lgb
    from sklearn.metrics import roc_auc_score, average_precision_score

    X, y, fechas = _construir_dataset(db)
    n_total = len(y)
    if n_total < MIN_VISITAS_ENTRENAMIENTO:
        raise ValueError(f"Solo hay {n_total} visitas con historial -- hacen falta al menos {MIN_VISITAS_ENTRENAMIENTO} para entrenar algo confiable.")

    # Corte por DÍAS fijos, no por porcentaje de filas: el volumen de visitas
    # creció muy desigual durante el pilotaje (514 en marzo vs 9268 en lo que
    # va de agosto, confirmado contra datos reales), así que un corte por
    # porcentaje termina validando contra apenas 2-3 días (todo el volumen
    # está pegado al final) -- probado contra datos reales con ventanas de
    # 7/10/14/21 días: el AUC en validación MEJORA cuanto más grande la
    # ventana (0.54 con 7 días -> 0.64 con 21), no empeora, así que 21 días
    # (menos filas de entrenamiento, pero una validación mucho más estable y
    # con más casos positivos: 316 vs 133) da el modelo más confiable, no el
    # que más datos ve.
    ultima_fecha = max(fechas)
    corte_validacion = ultima_fecha - timedelta(days=DIAS_VALIDACION)
    es_train = np.array([f < corte_validacion for f in fechas])
    X_train, y_train = X[es_train], y[es_train]
    X_val, y_val = X[~es_train], y[~es_train]

    if y_train.sum() < 10 or y_val.sum() < 3:
        raise ValueError("Muy pocos casos positivos (fotos rechazadas) en el corte de entrenamiento/validación todavía.")

    tasa_base = float(y.mean())
    train_set = lgb.Dataset(X_train, label=y_train, feature_name=FEATURES)
    modelo = lgb.train(
        {
            "objective": "binary", "metric": "auc", "verbosity": -1,
            "num_leaves": 15, "min_data_in_leaf": 30, "learning_rate": 0.05,
            "scale_pos_weight": (1 - tasa_base) / tasa_base,  # compensa el desbalance (~3.9% positivos)
        },
        train_set, num_boost_round=200,
    )

    pred_val = modelo.predict(X_val)
    auc = float(roc_auc_score(y_val, pred_val)) if len(set(y_val)) > 1 else None
    ap = float(average_precision_score(y_val, pred_val)) if len(set(y_val)) > 1 else None

    metricas = {
        "auc_validacion": round(auc, 4) if auc is not None else None,
        "average_precision_validacion": round(ap, 4) if ap is not None else None,
        "tasa_base_global": round(tasa_base, 4),
        "n_entrenamiento": int(len(y_train)), "n_validacion": int(len(y_val)),
        "positivos_entrenamiento": int(y_train.sum()), "positivos_validacion": int(y_val.sum()),
        "corte_validacion": corte_validacion.isoformat(),
        "ultima_fecha_historial": ultima_fecha.isoformat(),
    }
    logger.info(f"[PlanAccionML] Entrenado: {metricas}")

    modelo_texto = modelo.model_to_string()
    db.execute(text("UPDATE PLAN_ACCION_MODELO_RIESGO SET activo = 0 WHERE activo = 1"))
    db.execute(text("""
        INSERT INTO PLAN_ACCION_MODELO_RIESGO
            (modelo_texto, features_json, metricas_json, tasa_base_global, n_entrenamiento, n_validacion, activo)
        VALUES (:m, :f, :met, :t, :ne, :nv, 1)
    """), {
        "m": modelo_texto, "f": json.dumps(FEATURES), "met": json.dumps(metricas),
        "t": tasa_base, "ne": len(y_train), "nv": len(y_val),
    })
    db.commit()
    return metricas


def cargar_modelo_vigente(db: Session):
    """(booster, features, tasa_base) del último modelo activo, o None si
    todavía no se entrenó ninguno -- calcular_pendientes() cae de vuelta al
    PESO_TIPO fijo en ese caso, sin romper nada."""
    import lightgbm as lgb
    row = db.execute(text("""
        SELECT TOP 1 modelo_texto, features_json, tasa_base_global
        FROM PLAN_ACCION_MODELO_RIESGO WHERE activo = 1 ORDER BY fecha_entrenamiento DESC
    """)).fetchone()
    if not row:
        return None
    modelo = lgb.Booster(model_str=row.modelo_texto)
    return modelo, json.loads(row.features_json), float(row.tasa_base_global)


def resolver_tasas_riesgo(db: Session) -> dict:
    """Snapshot de HOY (no expansivo -- acá no hay fuga de información
    posible, es inferencia sobre el futuro, no entrenamiento sobre el
    pasado) de tasa de rechazo por (pdv,cliente) y por cliente, para
    alimentar predecir_peso_riesgo() sobre los pendientes actuales."""
    from app.services.plan_accion_service import _execute_with_timeout
    rows = _execute_with_timeout(db, """
        SELECT identificador_punto_interes, id_cliente, COUNT(*) AS n, SUM(rechazada) AS r
        FROM (
            SELECT vm.id_visita, vm.identificador_punto_interes, vm.id_cliente,
                   MAX(CASE WHEN ft.Estado = 'Rechazada' THEN 1 ELSE 0 END) AS rechazada
            FROM VISITAS_MERCADERISTA vm
            LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita
            WHERE vm.identificador_punto_interes IS NOT NULL AND vm.id_cliente IS NOT NULL
            GROUP BY vm.id_visita, vm.identificador_punto_interes, vm.id_cliente
        ) t
        GROUP BY identificador_punto_interes, id_cliente
    """, (), timeout=30)

    por_pdv_cliente: dict[tuple, tuple[int, int]] = {}
    por_cliente: dict[int, list[int]] = {}
    for id_punto, id_cliente, n, r in rows:
        r = r or 0
        por_pdv_cliente[(id_punto, id_cliente)] = (int(n), int(r))
        cl = por_cliente.setdefault(id_cliente, [0, 0])
        cl[0] += int(n); cl[1] += r

    return {"por_pdv_cliente": por_pdv_cliente, "por_cliente": por_cliente}


def predecir_peso_riesgo(modelo_info, tasas: dict, id_punto_interes: str, id_cliente: int,
                          prioridad: str | None, frecuencia_semanal: float) -> float:
    """Predicción de UN solo pendiente -- no usar esto en un loop sobre
    muchas filas, cada llamada paga el overhead de cruzar a C++ por
    separado. Para calcular_pendientes() (que recorre potencialmente miles
    de filas) usar predecir_peso_riesgo_batch()."""
    modelo, _features, tasa_base = modelo_info
    n_pc, rech_pc = tasas["por_pdv_cliente"].get((id_punto_interes, id_cliente), (0, 0))
    n_cl, rech_cl = tasas["por_cliente"].get(id_cliente, [0, 0])
    tasa_cl = (rech_cl / n_cl) if n_cl > 0 else TASA_BASE_PRIOR
    tasa_pc = (rech_pc / n_pc) if n_pc > 0 else tasa_cl

    x = np.array([[_peso_prioridad_num(prioridad), frecuencia_semanal or 1.0, tasa_pc, tasa_cl, n_pc]], dtype=float)
    prob = float(modelo.predict(x)[0])
    peso = prob / tasa_base if tasa_base > 0 else 1.0
    return max(0.3, min(peso, 3.0))


def predecir_peso_riesgo_batch(modelo_info, tasas: dict, filas: list[tuple]) -> list[float]:
    """Versión vectorizada: arma la matriz de features de TODOS los
    pendientes de una vez y hace UNA sola llamada a modelo.predict() en vez
    de una por fila. Con miles de pendientes reales, mil llamadas
    individuales a un modelo de árboles (cada una cruzando a C++ y volviendo)
    saturaban el único worker del proceso y bloqueaban la app ENTERA, no
    solo Plan de Acción -- confirmado en vivo en producción (504 en cascada
    en endpoints sin ninguna relación, como /auth/me, mientras corría
    /recalcular). `filas` = [(id_punto_interes, id_cliente, prioridad,
    frecuencia_semanal), ...]."""
    modelo, _features, tasa_base = modelo_info
    if not filas:
        return []

    X = np.empty((len(filas), 5), dtype=float)
    for i, (id_punto_interes, id_cliente, prioridad, frecuencia_semanal) in enumerate(filas):
        n_pc, rech_pc = tasas["por_pdv_cliente"].get((id_punto_interes, id_cliente), (0, 0))
        n_cl, rech_cl = tasas["por_cliente"].get(id_cliente, [0, 0])
        tasa_cl = (rech_cl / n_cl) if n_cl > 0 else TASA_BASE_PRIOR
        tasa_pc = (rech_pc / n_pc) if n_pc > 0 else tasa_cl
        X[i] = (_peso_prioridad_num(prioridad), frecuencia_semanal or 1.0, tasa_pc, tasa_cl, n_pc)

    probs = modelo.predict(X)  # una sola llamada al modelo para las N filas
    if tasa_base > 0:
        pesos = probs / tasa_base
    else:
        pesos = np.ones(len(filas))
    return [float(max(0.3, min(p, 3.0))) for p in pesos]
