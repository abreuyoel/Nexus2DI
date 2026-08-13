"""Centro de Mando Auditoría: tablero de todo lo que se hace en el módulo
Auditor de Campo (app/modules/auditors/controller.py) -- cuestionarios de
cumplimiento por categoría (AUDITORIA_CATEGORIAS), fotos, rutas/PDVs/
clientes auditados. Todo de solo lectura, mismo criterio de permisos que
Centro de Mando "Gestión" (admin/analista).

Traducción a SQLAlchemy ORM (DEVELOPMENT.md prohíbe SQL crudo en
controllers): la versión original usaba `db.execute(text(...))` con un OUTER
APPLY para resolver la ruta de cada visita; aquí esa subconsulta correlacionada
se modela con `func.min(Ruta.nombre)` en un scalar subquery correlacionado
(equivale al MIN(rn.ruta) + ISNULL(..., 'Sin ruta') de la versión SQL).
"""
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import exists, func
from sqlalchemy.orm import Session

from app.core.dependencies import require_permission
from app.db.session import get_db
from app.modules.auth.entities import Usuario
from app.modules.auditors.entities import AuditoriaCategoria
from app.modules.catalogues.entities import Categoria
from app.modules.clients.entities import Cliente
from app.modules.merchandisers.entities import Mercaderista, MercaderistaRuta
from app.modules.routes.entities import Ruta, RutaProgramacion, PuntoInteres
from app.modules.visits.entities import Visita, Foto

router = APIRouter(prefix="/api/centro-mando-auditoria", tags=["Centro de Mando Auditoría"])

# Los 6 indicadores de cumplimiento sí/no del cuestionario -- ver
# guardar_auditoria_categoria() en auditors/controller.py para el origen de
# estos nombres de columna.
INDICADORES = [
    ("aplico_planograma", "Aplicó planograma"),
    ("lineamiento_marca", "Lineamiento de marca"),
    ("precio_correcto", "Precio correcto"),
    ("limpieza_correcta", "Limpieza correcta"),
    ("participacion_correcta", "Participación correcta"),
    ("fifo_correcto", "FIFO correcto"),
]


@router.get("/filtros")
def get_filtros(db: Session = Depends(get_db), _: Usuario = Depends(require_permission('centro-mando-auditoria', 'read'))):
    """Catálogos para los dropdowns -- solo lo que efectivamente aparece en
    auditorías ya hechas (no el catálogo completo de mercaderistas/clientes)."""
    auditores = (
        db.query(Mercaderista.id, Mercaderista.nombre)
        .select_from(Mercaderista)
        .join(Visita, Visita.mercaderista_id == Mercaderista.id)
        .join(AuditoriaCategoria, AuditoriaCategoria.id_visita == Visita.id)
        .filter(Mercaderista.tipo == "Auditor de Campo")
        .distinct()
        .order_by(Mercaderista.nombre)
        .all()
    )
    rutas = (
        db.query(Ruta.id, Ruta.nombre)
        .select_from(Ruta)
        .join(MercaderistaRuta, MercaderistaRuta.ruta_id == Ruta.id)
        .join(Mercaderista, Mercaderista.id == MercaderistaRuta.mercaderista_id)
        .filter(Mercaderista.tipo == "Auditor de Campo")
        .distinct()
        .order_by(Ruta.nombre)
        .all()
    )
    clientes = (
        db.query(Cliente.id, Cliente.nombre)
        .select_from(Cliente)
        .join(Visita, Visita.id_cliente == Cliente.id)
        .join(Mercaderista, Mercaderista.id == Visita.mercaderista_id)
        .join(AuditoriaCategoria, AuditoriaCategoria.id_visita == Visita.id)
        .filter(Mercaderista.tipo == "Auditor de Campo")
        .distinct()
        .order_by(Cliente.nombre)
        .all()
    )
    categorias = (
        db.query(Categoria.id_categoria, Categoria.nombre)
        .select_from(Categoria)
        .join(AuditoriaCategoria, AuditoriaCategoria.id_categoria == Categoria.id_categoria)
        .distinct()
        .order_by(Categoria.nombre)
        .all()
    )
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
    _: Usuario = Depends(require_permission('centro-mando-auditoria', 'read')),
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

        d_desde = date.fromisoformat(desde)
        d_hasta = date.fromisoformat(hasta)

        # OUTER APPLY (MIN(rn.ruta)) traducido a scalar subquery
        # correlacionado: devuelve NULL cuando la visita no tiene ruta activa,
        # y Python lo convierte a "Sin ruta" (igual que el ISNULL original).
        ruta_subq = (
            db.query(func.min(Ruta.nombre))
            .select_from(RutaProgramacion)
            .join(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .join(MercaderistaRuta, MercaderistaRuta.ruta_id == RutaProgramacion.ruta_id)
            .filter(
                RutaProgramacion.activo == True,
                RutaProgramacion.punto_id == PuntoInteres.id,
                MercaderistaRuta.mercaderista_id == Visita.mercaderista_id,
            )
            .scalar_subquery()
            .label("ruta")
        )

        q = (
            db.query(
                Visita.id.label("id_visita"),
                Visita.fecha.label("fecha_visita"),
                Mercaderista.id.label("id_mercaderista"),
                Mercaderista.nombre.label("auditor"),
                Cliente.id.label("id_cliente"),
                Cliente.nombre.label("cliente"),
                PuntoInteres.id.label("id_punto"),
                PuntoInteres.nombre.label("punto_de_interes"),
                func.coalesce(PuntoInteres.departamento, "").label("departamento"),
                func.coalesce(PuntoInteres.ciudad, "").label("ciudad"),
                AuditoriaCategoria.id_categoria.label("id_categoria"),
                Categoria.nombre.label("categoria"),
                AuditoriaCategoria.aplico_planograma,
                AuditoriaCategoria.lineamiento_marca,
                AuditoriaCategoria.precio_correcto,
                AuditoriaCategoria.limpieza_correcta,
                AuditoriaCategoria.participacion_correcta,
                AuditoriaCategoria.fifo_correcto,
                AuditoriaCategoria.prox_vencer,
                AuditoriaCategoria.prox_vencer_cantidad,
                AuditoriaCategoria.prox_vencer_marca,
                AuditoriaCategoria.prox_vencer_fecha1,
                AuditoriaCategoria.prox_vencer_fecha2,
                AuditoriaCategoria.competencia_actividad,
                AuditoriaCategoria.competencia_material_pop,
                AuditoriaCategoria.competencia_impulsadora,
                AuditoriaCategoria.promo_nuestra,
                AuditoriaCategoria.promo_competencia,
                AuditoriaCategoria.exhibicion_adicional,
                ruta_subq,
            )
            .select_from(AuditoriaCategoria)
            .join(Visita, Visita.id == AuditoriaCategoria.id_visita)
            .join(Mercaderista, Mercaderista.id == Visita.mercaderista_id)
            .join(Cliente, Cliente.id == Visita.id_cliente)
            .join(PuntoInteres, PuntoInteres.id == Visita.punto_id)
            .outerjoin(Categoria, Categoria.id_categoria == AuditoriaCategoria.id_categoria)
        )

        q = q.filter(Mercaderista.tipo == "Auditor de Campo")
        q = q.filter(Visita.fecha >= d_desde, Visita.fecha < d_hasta + timedelta(days=1))

        if id_auditor:
            q = q.filter(Mercaderista.id == id_auditor)
        if id_cliente:
            q = q.filter(Cliente.id == id_cliente)
        if id_categoria:
            q = q.filter(AuditoriaCategoria.id_categoria == id_categoria)
        if id_ruta:
            q = q.filter(
                exists()
                .where(RutaProgramacion.ruta_id == MercaderistaRuta.ruta_id)
                .where(RutaProgramacion.activo == True)
                .where(RutaProgramacion.punto_id == PuntoInteres.id)
                .where(MercaderistaRuta.mercaderista_id == Visita.mercaderista_id)
                .where(RutaProgramacion.ruta_id == id_ruta)
            )

        q = q.order_by(Visita.fecha.desc())
        rows = q.all()

        log = []
        indicador_counts = {k: {"si": 0, "no": 0} for k, _lbl in INDICADORES}
        competencia_counts = {"actividad": 0, "material_pop": 0, "impulsadora": 0}
        por_dia: dict = {}
        por_auditor: dict = {}
        por_cliente_cat: dict = {}
        vencer = []
        rutas_set, puntos_set, clientes_set = set(), set(), set()

        for row in rows:
            d = dict(row._mapping)
            fecha = d["fecha_visita"]
            dia_str = fecha.date().isoformat() if hasattr(fecha, "date") else str(fecha)[:10]

            # ISNULL(cat.nombre, CONCAT('Categoría ', id_categoria)) resuelto
            # en Python para no depender del CONCAT de SQL Server.
            categoria = d.get("categoria") or f"Categoría {d['id_categoria']}"
            ruta = d.get("ruta") or "Sin ruta"

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

            ck = (d["cliente"], categoria)
            cc = por_cliente_cat.setdefault(ck, {"cliente": d["cliente"], "categoria": categoria, "auditorias": 0, "suma_cumplimiento": 0.0})
            cc["auditorias"] += 1
            cc["suma_cumplimiento"] += cumplimiento_pct

            rutas_set.add(ruta)
            puntos_set.add(d["id_punto"])
            clientes_set.add(d["id_cliente"])

            if d.get("prox_vencer"):
                vencer.append({
                    "id_visita": d["id_visita"], "fecha": dia_str, "cliente": d["cliente"],
                    "punto_de_interes": d["punto_de_interes"], "categoria": categoria,
                    "cantidad": d.get("prox_vencer_cantidad"), "marca": d.get("prox_vencer_marca"),
                    "fecha1": str(d["prox_vencer_fecha1"]) if d.get("prox_vencer_fecha1") else None,
                    "fecha2": str(d["prox_vencer_fecha2"]) if d.get("prox_vencer_fecha2") else None,
                })

            log.append({
                "id_visita": d["id_visita"], "id_categoria": d["id_categoria"], "fecha": dia_str,
                "auditor": d["auditor"], "cliente": d["cliente"], "ruta": ruta,
                "punto_de_interes": d["punto_de_interes"], "departamento": d["departamento"], "ciudad": d["ciudad"],
                "categoria": categoria, "cumplimiento_pct": cumplimiento_pct,
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
        desde_dt = d_desde
        hasta_dt = d_hasta + timedelta(days=1)
        fotos_totales = (
            db.query(func.count())
            .select_from(Foto)
            .filter(
                Foto.blob_path.like("auditor_campo/%"),
                Foto.fecha_registro >= datetime.combine(desde_dt, datetime.min.time()),
                Foto.fecha_registro < datetime.combine(hasta_dt, datetime.min.time()),
            )
            .scalar()
            or 0
        )

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
