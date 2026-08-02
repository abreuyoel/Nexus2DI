"""Centro de Mando Auditoría: tablero de todo lo que se hace en el módulo
Auditor de Campo (app/routes/auditor_campo.py) -- cuestionarios de
cumplimiento por categoría (AUDITORIA_CATEGORIAS), fotos, rutas/PDVs/
clientes auditados. Todo de solo lectura, mismo criterio de permisos que
Centro de Mando "Gestión" (admin/analista)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date, timedelta
from app.db.session import get_db
from app.core.dependencies import require_analyst_or_admin
from app.models.user import Usuario

router = APIRouter(prefix="/api/centro-mando-auditoria", tags=["Centro de Mando Auditoría"])

# Los 6 indicadores de cumplimiento sí/no del cuestionario -- ver
# guardar_auditoria_categoria() en auditor_campo.py para el origen de estos
# nombres de columna.
INDICADORES = [
    ("aplico_planograma", "Aplicó planograma"),
    ("lineamiento_marca", "Lineamiento de marca"),
    ("precio_correcto", "Precio correcto"),
    ("limpieza_correcta", "Limpieza correcta"),
    ("participacion_correcta", "Participación correcta"),
    ("fifo_correcto", "FIFO correcto"),
]


def _where_comun(desde, hasta, id_auditor, id_ruta, id_cliente, id_categoria):
    where = "WHERE m.tipo = 'Auditor de Campo' AND v.fecha_visita >= :d AND v.fecha_visita < DATEADD(day, 1, :h)"
    params = {"d": desde, "h": hasta}
    if id_auditor:
        where += " AND m.id_mercaderista = :ida"
        params["ida"] = id_auditor
    if id_cliente:
        where += " AND c.id_cliente = :idc"
        params["idc"] = id_cliente
    if id_categoria:
        where += " AND ac.id_categoria = :idcat"
        params["idcat"] = id_categoria
    if id_ruta:
        where += """ AND EXISTS (
            SELECT 1 FROM RUTA_PROGRAMACION rp3
            JOIN MERCADERISTAS_RUTAS mr3 ON mr3.id_ruta = rp3.id_ruta
            WHERE rp3.activa = 1 AND rp3.id_punto_interes = p.identificador
              AND mr3.id_mercaderista = v.id_mercaderista AND rp3.id_ruta = :idr
        )"""
        params["idr"] = id_ruta
    return where, params


@router.get("/filtros")
def get_filtros(db: Session = Depends(get_db), _: Usuario = Depends(require_analyst_or_admin)):
    """Catálogos para los dropdowns -- solo lo que efectivamente aparece en
    auditorías ya hechas (no el catálogo completo de mercaderistas/clientes)."""
    auditores = db.execute(text("""
        SELECT DISTINCT m.id_mercaderista, m.nombre
        FROM MERCADERISTAS m
        JOIN VISITAS_MERCADERISTA v ON v.id_mercaderista = m.id_mercaderista
        JOIN AUDITORIA_CATEGORIAS ac ON ac.id_visita = v.id_visita
        WHERE m.tipo = 'Auditor de Campo'
        ORDER BY m.nombre
    """)).fetchall()
    rutas = db.execute(text("""
        SELECT DISTINCT rn.id_ruta, rn.ruta
        FROM RUTAS_NUEVAS rn
        JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rn.id_ruta
        JOIN MERCADERISTAS m ON m.id_mercaderista = mr.id_mercaderista
        WHERE m.tipo = 'Auditor de Campo'
        ORDER BY rn.ruta
    """)).fetchall()
    clientes = db.execute(text("""
        SELECT DISTINCT c.id_cliente, c.cliente
        FROM CLIENTES c
        JOIN VISITAS_MERCADERISTA v ON v.id_cliente = c.id_cliente
        JOIN MERCADERISTAS m ON m.id_mercaderista = v.id_mercaderista
        JOIN AUDITORIA_CATEGORIAS ac ON ac.id_visita = v.id_visita
        WHERE m.tipo = 'Auditor de Campo'
        ORDER BY c.cliente
    """)).fetchall()
    categorias = db.execute(text("""
        SELECT DISTINCT cat.id_categoria, cat.nombre
        FROM CATEGORIAS cat
        JOIN AUDITORIA_CATEGORIAS ac ON ac.id_categoria = cat.id_categoria
        ORDER BY cat.nombre
    """)).fetchall()
    return {
        "auditores": [{"id": r[0], "nombre": r[1]} for r in auditores],
        "rutas": [{"id": r[0], "nombre": r[1]} for r in rutas],
        "clientes": [{"id": r[0], "nombre": r[1]} for r in clientes],
        "categorias": [{"id": r[0], "nombre": r[1]} for r in categorias],
    }


@router.get("/resumen")
def get_resumen(
    desde: Optional[str] = None,
    hasta: Optional[str] = None,
    id_auditor: Optional[int] = None,
    id_ruta: Optional[int] = None,
    id_cliente: Optional[int] = None,
    id_categoria: Optional[int] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    """KPIs + datos de gráficos + log filtrable, todo en una sola llamada
    (el volumen de datos de auditoría -- un cuestionario por categoría
    visitada -- es chico comparado con el de fotos/visitas de mercaderista,
    así que no hace falta paginar ni separar en varias queries)."""
    try:
        hoy = date.today()
        if not desde:
            desde = (hoy - timedelta(days=7)).isoformat()
        if not hasta:
            hasta = hoy.isoformat()

        where, params = _where_comun(desde, hasta, id_auditor, id_ruta, id_cliente, id_categoria)

        rows = db.execute(text(f"""
            SELECT v.id_visita, v.fecha_visita,
                   m.id_mercaderista, m.nombre AS auditor,
                   c.id_cliente, c.cliente,
                   p.identificador AS id_punto, p.punto_de_interes,
                   ISNULL(p.departamento, '') AS departamento, ISNULL(p.ciudad, '') AS ciudad,
                   ac.id_categoria, ISNULL(cat.nombre, CONCAT('Categoría ', ac.id_categoria)) AS categoria,
                   ac.aplico_planograma, ac.lineamiento_marca, ac.precio_correcto, ac.limpieza_correcta,
                   ac.participacion_correcta, ac.fifo_correcto,
                   ac.prox_vencer, ac.prox_vencer_cantidad, ac.prox_vencer_marca,
                   ac.prox_vencer_fecha1, ac.prox_vencer_fecha2,
                   ac.competencia_actividad, ac.competencia_material_pop, ac.competencia_impulsadora,
                   ac.pop_hablador, ac.pop_rompetrafico, ac.pop_otro,
                   ac.promo_nuestra, ac.promo_nuestra_desc, ac.promo_competencia, ac.promo_competencia_desc,
                   ac.exhibicion_adicional, ac.exhibicion_tipos,
                   ISNULL(rinfo.ruta, 'Sin ruta') AS ruta
            FROM AUDITORIA_CATEGORIAS ac
            JOIN VISITAS_MERCADERISTA v ON v.id_visita = ac.id_visita
            JOIN MERCADERISTAS m ON m.id_mercaderista = v.id_mercaderista
            JOIN CLIENTES c ON c.id_cliente = v.id_cliente
            JOIN PUNTOS_INTERES1 p ON p.identificador = v.identificador_punto_interes
            LEFT JOIN CATEGORIAS cat ON cat.id_categoria = ac.id_categoria
            OUTER APPLY (
                SELECT MIN(rn.ruta) AS ruta
                FROM RUTA_PROGRAMACION rp JOIN RUTAS_NUEVAS rn ON rn.id_ruta = rp.id_ruta
                JOIN MERCADERISTAS_RUTAS mr ON mr.id_ruta = rp.id_ruta
                WHERE rp.activa = 1 AND rp.id_punto_interes = p.identificador
                  AND mr.id_mercaderista = v.id_mercaderista
            ) rinfo
            {where}
            ORDER BY v.fecha_visita DESC
        """), params).fetchall()

        log = []
        indicador_counts = {k: {"si": 0, "no": 0} for k, _lbl in INDICADORES}
        competencia_counts = {"actividad": 0, "material_pop": 0, "impulsadora": 0}
        por_dia: dict = {}
        por_auditor: dict = {}
        por_cliente_cat: dict = {}
        vencer = []
        rutas_set, puntos_set, clientes_set = set(), set(), set()

        for r in rows:
            d = dict(r._mapping)
            fecha = d["fecha_visita"]
            dia_str = fecha.date().isoformat() if hasattr(fecha, "date") else str(fecha)[:10]

            si_count = 0
            for key, _lbl in INDICADORES:
                v_ind = d.get(key)
                if v_ind is None:
                    continue
                if v_ind:
                    indicador_counts[key]["si"] += 1
                    si_count += 1
                else:
                    indicador_counts[key]["no"] += 1
            cumplimiento_pct = round(si_count / len(INDICADORES) * 100, 1)

            if d.get("competencia_actividad"):
                competencia_counts["actividad"] += 1
            if d.get("competencia_material_pop"):
                competencia_counts["material_pop"] += 1
            if d.get("competencia_impulsadora"):
                competencia_counts["impulsadora"] += 1

            por_dia[dia_str] = por_dia.get(dia_str, 0) + 1

            a = por_auditor.setdefault(d["id_mercaderista"], {"nombre": d["auditor"], "auditorias": 0, "suma_cumplimiento": 0.0})
            a["auditorias"] += 1
            a["suma_cumplimiento"] += cumplimiento_pct

            ck = (d["cliente"], d["categoria"])
            cc = por_cliente_cat.setdefault(ck, {"cliente": d["cliente"], "categoria": d["categoria"], "auditorias": 0, "suma_cumplimiento": 0.0})
            cc["auditorias"] += 1
            cc["suma_cumplimiento"] += cumplimiento_pct

            rutas_set.add(d["ruta"])
            puntos_set.add(d["id_punto"])
            clientes_set.add(d["id_cliente"])

            if d.get("prox_vencer"):
                vencer.append({
                    "id_visita": d["id_visita"], "fecha": dia_str, "cliente": d["cliente"],
                    "punto_de_interes": d["punto_de_interes"], "categoria": d["categoria"],
                    "cantidad": d.get("prox_vencer_cantidad"), "marca": d.get("prox_vencer_marca"),
                    "fecha1": str(d["prox_vencer_fecha1"]) if d.get("prox_vencer_fecha1") else None,
                    "fecha2": str(d["prox_vencer_fecha2"]) if d.get("prox_vencer_fecha2") else None,
                })

            log.append({
                "id_visita": d["id_visita"], "id_categoria": d["id_categoria"], "fecha": dia_str,
                "auditor": d["auditor"], "cliente": d["cliente"], "ruta": d["ruta"],
                "punto_de_interes": d["punto_de_interes"], "departamento": d["departamento"], "ciudad": d["ciudad"],
                "categoria": d["categoria"], "cumplimiento_pct": cumplimiento_pct,
                "aplico_planograma": d.get("aplico_planograma"), "lineamiento_marca": d.get("lineamiento_marca"),
                "precio_correcto": d.get("precio_correcto"), "limpieza_correcta": d.get("limpieza_correcta"),
                "participacion_correcta": d.get("participacion_correcta"), "fifo_correcto": d.get("fifo_correcto"),
                "prox_vencer": bool(d.get("prox_vencer")),
                "competencia_actividad": bool(d.get("competencia_actividad")),
                "competencia_material_pop": bool(d.get("competencia_material_pop")),
                "competencia_impulsadora": bool(d.get("competencia_impulsadora")),
                "promo_nuestra": bool(d.get("promo_nuestra")), "promo_competencia": bool(d.get("promo_competencia")),
                "exhibicion_adicional": bool(d.get("exhibicion_adicional")),
            })

        total = len(log)
        cumplimiento_prom = round(sum(x["cumplimiento_pct"] for x in log) / total, 1) if total else 0

        # Fotos del módulo (activación/desactivación de PDV + fotos de
        # categoría): estas dos primeras no tienen id_visita (se suben antes
        # de que exista una visita/cliente elegido), así que se cuentan por
        # prefijo de file_path + rango de fecha en vez de JOIN -- no se puede
        # acotar por auditor/cliente/categoría con este dato.
        fotos_totales = db.execute(text("""
            SELECT COUNT(*) FROM FOTOS_TOTALES
            WHERE file_path LIKE 'auditor_campo/%'
              AND fecha_registro >= :d AND fecha_registro < DATEADD(day, 1, :h)
        """), {"d": desde, "h": hasta}).scalar() or 0

        return {
            "success": True, "desde": desde, "hasta": hasta,
            "kpis": {
                "rutas_auditadas": len([r for r in rutas_set if r != "Sin ruta"]),
                "pdvs_visitados": len(puntos_set),
                "clientes_auditados": len(clientes_set),
                "cuestionarios_completados": total,
                "fotos_subidas": int(fotos_totales),
                "cumplimiento_promedio": cumplimiento_prom,
            },
            "charts": {
                "indicadores": [
                    {"indicador": lbl, "si": indicador_counts[k]["si"], "no": indicador_counts[k]["no"]}
                    for k, lbl in INDICADORES
                ],
                "competencia": {
                    "actividad_pct": round(competencia_counts["actividad"] / total * 100, 1) if total else 0,
                    "material_pop_pct": round(competencia_counts["material_pop"] / total * 100, 1) if total else 0,
                    "impulsadora_pct": round(competencia_counts["impulsadora"] / total * 100, 1) if total else 0,
                },
                "por_dia": [{"fecha": k, "auditorias": v} for k, v in sorted(por_dia.items())],
                "por_auditor": sorted([
                    {"auditor": v["nombre"], "auditorias": v["auditorias"],
                     "cumplimiento_promedio": round(v["suma_cumplimiento"] / v["auditorias"], 1)}
                    for v in por_auditor.values()
                ], key=lambda x: x["auditorias"], reverse=True),
                "por_cliente_categoria": sorted([
                    {"cliente": v["cliente"], "categoria": v["categoria"], "auditorias": v["auditorias"],
                     "cumplimiento_promedio": round(v["suma_cumplimiento"] / v["auditorias"], 1)}
                    for v in por_cliente_cat.values()
                ], key=lambda x: x["cumplimiento_promedio"]),
            },
            "alertas_vencimiento": vencer,
            "log": log,
        }
    except Exception as e:
        return {"success": False, "message": str(e), "kpis": {}, "charts": {}, "alertas_vencimiento": [], "log": []}
