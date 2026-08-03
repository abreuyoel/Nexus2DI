"""Plan de Acción -- Fase 2: calcula qué combinaciones (ruta, PDV, cliente)
siguen debiendo visita en el período actual (semana si su frecuencia es
>=1/semana, mes si es menor) y con qué urgencia, y guarda el resultado
completo en PLAN_ACCION_PENDIENTES (se reemplaza entero en cada corrida).

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

Una visita cuenta para la cuota solo si está "completa" (foto de
activación Y desactivación, ambas Estado='Aprobada' -- mismo criterio que
update_resumen.py). Si el (PDV, cliente) sigue debiendo visita este
período Y alguna de sus visitas del período tiene una foto Estado=
'Rechazada' sin resolver, se clasifica como 'fotos_rechazadas' (peso
0.6); si nunca se intentó, 'nunca_visitado' (peso 1.0) -- misma cola,
menor peso a la rechazada, tal como lo pidió el usuario.
"""
from __future__ import annotations

import logging
import math
from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import text
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
GROUP BY rp.id_ruta, rn.ruta, rp.id_punto_interes, pi.punto_de_interes,
         pi.departamento, pi.ciudad, rp.id_cliente, c.cliente
"""

VISITAS_QUERY = """
SELECT vm.identificador_punto_interes, vm.id_cliente, vm.fecha_visita,
       MAX(CASE WHEN ft.id_tipo_foto = 5 AND ft.Estado = 'Aprobada' THEN 1 ELSE 0 END) AS tiene_act,
       MAX(CASE WHEN ft.id_tipo_foto = 6 AND ft.Estado = 'Aprobada' THEN 1 ELSE 0 END) AS tiene_des,
       MAX(CASE WHEN ft.Estado = 'Rechazada' THEN 1 ELSE 0 END) AS tiene_rechazada
FROM VISITAS_MERCADERISTA vm
LEFT JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita
WHERE vm.fecha_visita >= :inicio_mes
  AND vm.fecha_visita < DATEADD(day, 1, CAST(GETDATE() AS DATE))
  AND vm.identificador_punto_interes IS NOT NULL
  AND vm.id_cliente IS NOT NULL
GROUP BY vm.identificador_punto_interes, vm.id_cliente, vm.fecha_visita
"""


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
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    inicio_mes = hoy.replace(day=1)
    dias_disp_semana = _dias_habiles_restantes_semana(hoy)
    semanas_disp_mes = _semanas_restantes_mes(hoy)

    universo = db.execute(text(UNIVERSO_QUERY)).fetchall()
    visitas = db.execute(text(VISITAS_QUERY), {"inicio_mes": inicio_mes}).fetchall()

    actividad: dict[tuple, dict] = defaultdict(lambda: {
        "hechas_semana": set(), "hechas_mes": set(),
        "rechazada_semana": False, "rechazada_mes": False,
    })
    for row in visitas:
        key = (row.identificador_punto_interes, row.id_cliente)
        fecha = row.fecha_visita
        if fecha is None:
            continue
        completa = bool(row.tiene_act) and bool(row.tiene_des)
        rechazada = bool(row.tiene_rechazada)
        info = actividad[key]
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
    for r in universo:
        frecuencia = r.frecuencia_semanal
        if frecuencia is None:
            frecuencia = r.dias_programados if r.dias_programados and r.dias_programados > 0 else 1
        frecuencia = _to_float(frecuencia)
        if frecuencia <= 0:
            continue

        info = actividad.get((r.id_punto_interes, r.id_cliente), {
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
        peso_prioridad = _peso_prioridad(r.prioridad)
        peso_tipo = PESO_TIPO[tipo_pendiente]
        score = urgencia * peso_prioridad * peso_tipo

        pendientes.append({
            "id_ruta": r.id_ruta,
            "ruta_nombre": r.ruta_nombre,
            "id_punto_interes": r.id_punto_interes,
            "punto_de_interes": r.punto_de_interes,
            "departamento": r.departamento,
            "ciudad": r.ciudad,
            "id_cliente": r.id_cliente,
            "cliente_nombre": r.cliente_nombre,
            "prioridad_ruta": r.prioridad,
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


def recalcular_plan_accion(db: Session) -> int:
    pendientes = calcular_pendientes(db)

    db.execute(text("DELETE FROM PLAN_ACCION_PENDIENTES"))
    if pendientes:
        db.execute(text("""
            INSERT INTO PLAN_ACCION_PENDIENTES
                (id_ruta, ruta_nombre, id_punto_interes, punto_de_interes, departamento, ciudad,
                 id_cliente, cliente_nombre, prioridad_ruta, frecuencia_semanal, periodo,
                 tipo_pendiente, visitas_requeridas, visitas_hechas, visitas_faltantes,
                 dias_disponibles, urgencia, score, fecha_calculo)
            VALUES
                (:id_ruta, :ruta_nombre, :id_punto_interes, :punto_de_interes, :departamento, :ciudad,
                 :id_cliente, :cliente_nombre, :prioridad_ruta, :frecuencia_semanal, :periodo,
                 :tipo_pendiente, :visitas_requeridas, :visitas_hechas, :visitas_faltantes,
                 :dias_disponibles, :urgencia, :score, GETDATE())
        """), pendientes)
    db.commit()
    return len(pendientes)
