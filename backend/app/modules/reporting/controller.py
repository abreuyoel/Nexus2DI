import io
import pandas as pd
from datetime import date, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.visits.entities import Visita, Foto
from app.modules.routes.entities import RutaActivada, PuntoInteres, Ruta, RutaProgramacion
from app.modules.merchandisers.entities import Mercaderista
from app.modules.reporting.dto import (
    ReportSummaryResponse, PeriodoDto, SummaryVisitasDto, SummaryFotosDto,
    ChartDataResponse, ActivatedRouteItemResponse
)

router = APIRouter(prefix="/api/reports", tags=["Reportería"])


@router.get("/summary", response_model=ReportSummaryResponse)
def get_report_summary(
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    ruta_id: Optional[int] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    if not fecha_inicio:
        fecha_inicio = date.today() - timedelta(days=30)
    if not fecha_fin:
        fecha_fin = date.today()

    query = db.query(Visita).filter(
        Visita.fecha >= fecha_inicio,
        Visita.fecha <= fecha_fin,
    )
    if ruta_id:
        query = query.filter(Visita.ruta_id == ruta_id)

    visitas = query.all()
    total = len(visitas)
    completadas = sum(1 for v in visitas if v.estado == "completada")
    pendientes = sum(1 for v in visitas if v.estado == "pendiente")

    visita_ids = [v.id for v in visitas]
    fotos = db.query(Foto).filter(Foto.visita_id.in_(visita_ids)).all() if visita_ids else []
    fotos_aprobadas = sum(1 for f in fotos if f.estado == "aprobada")
    fotos_rechazadas = sum(1 for f in fotos if f.estado == "rechazada")
    fotos_pendientes = sum(1 for f in fotos if f.estado == "pendiente")

    return ReportSummaryResponse(
        periodo=PeriodoDto(inicio=str(fecha_inicio), fin=str(fecha_fin)),
        visitas=SummaryVisitasDto(
            total=total,
            completadas=completadas,
            pendientes=pendientes,
            porcentaje_completadas=round(completadas / total * 100, 1) if total > 0 else 0.0,
        ),
        fotos=SummaryFotosDto(
            total=len(fotos),
            aprobadas=fotos_aprobadas,
            rechazadas=fotos_rechazadas,
            pendientes=fotos_pendientes,
        ),
    )


@router.get("/chart-data", response_model=ChartDataResponse)
def get_chart_data(
    tipo: str = "visitas_por_dia",
    fecha_inicio: Optional[date] = None,
    fecha_fin: Optional[date] = None,
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    if not fecha_inicio:
        fecha_inicio = date.today() - timedelta(days=30)
    if not fecha_fin:
        fecha_fin = date.today()

    if tipo == "visitas_por_dia":
        results = db.query(
            Visita.fecha,
            func.count(Visita.id).label("total"),
        ).filter(
            Visita.fecha >= fecha_inicio,
            Visita.fecha <= fecha_fin,
        ).group_by(Visita.fecha).order_by(Visita.fecha).all()

        return ChartDataResponse(
            labels=[str(r.fecha) for r in results],
            data=[r.total for r in results],
            title="Visitas por Día",
        )

    elif tipo == "fotos_por_estado":
        results = db.query(
            Foto.estado,
            func.count(Foto.id).label("total"),
        ).group_by(Foto.estado).all()

        return ChartDataResponse(
            labels=[r.estado or "Sin Estado" for r in results],
            data=[r.total for r in results],
            title="Fotos por Estado",
        )

    return ChartDataResponse(labels=[], data=[], title=tipo)


@router.get("/activated-routes", response_model=List[ActivatedRouteItemResponse])
def get_activated_routes(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    today = date.today()
    activadas = db.query(RutaActivada).filter(RutaActivada.fecha == today).all()
    return [
        ActivatedRouteItemResponse(
            ruta_id=a.ruta_id,
            cedula=a.mercaderista_cedula,
            hora=str(a.activada_at) if a.activada_at else None
        )
        for a in activadas
    ]


@router.get("/export-visitas")
def export_visitas_excel(
    id_cliente: int = Query(...),
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    cuadrante: Optional[str] = Query(None),
    departamento: Optional[str] = Query(None),
    categoria: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    try:
        q = (
            db.query(
                Visita.id.label("ID Visita"),
                Visita.fecha.label("Fecha"),
                Visita.estado.label("Estado Visita"),
                PuntoInteres.nombre.label("Nombre del PDV"),
                PuntoInteres.departamento.label("Departamento / Estado"),
                PuntoInteres.cadena.label("Canal"),
                PuntoInteres.jerarquia_n2.label("Categoría PDV"),
                Ruta.cuadrante.label("Cuadrante"),
                Mercaderista.nombre.label("Mercaderista")
            )
            .join(PuntoInteres, Visita.punto_id == PuntoInteres.id)
            .outerjoin(RutaProgramacion, (RutaProgramacion.punto_id == PuntoInteres.id) & (RutaProgramacion.id_cliente == Visita.id_cliente))
            .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .outerjoin(Mercaderista, Visita.mercaderista_id == Mercaderista.id)
            .filter(
                Visita.id_cliente == id_cliente,
                Visita.fecha >= fecha_inicio,
                Visita.fecha <= fecha_fin
            )
        )
        if cuadrante:
            q = q.filter(Ruta.cuadrante == cuadrante)
        if departamento:
            q = q.filter(PuntoInteres.departamento == departamento)
        if categoria:
            q = q.filter((PuntoInteres.jerarquia_n2 == categoria) | (PuntoInteres.cadena == categoria))

        rows = q.all()

        if not rows:
            df = pd.DataFrame(columns=[
                "ID Visita", "Fecha", "Estado Visita", "Nombre del PDV", 
                "Departamento / Estado", "Canal", "Categoría PDV", "Cuadrante", "Mercaderista"
            ])
        else:
            data = [
                {
                    "ID Visita": r[0],
                    "Fecha": str(r[1]) if r[1] else "",
                    "Estado Visita": r[2] or "",
                    "Nombre del PDV": r[3] or "",
                    "Departamento / Estado": r[4] or "",
                    "Canal": r[5] or "",
                    "Categoría PDV": r[6] or "",
                    "Cuadrante": r[7] or "",
                    "Mercaderista": r[8] or ""
                }
                for r in rows
            ]
            df = pd.DataFrame(data)

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Visitas')
            
            workbook = writer.book
            worksheet = writer.sheets['Visitas']
            
            header_format = workbook.add_format({
                'bold': True,
                'bg_color': '#21262d',
                'font_color': '#ffffff',
                'border': 1
            })
            
            for col_num, value in enumerate(df.columns.values):
                worksheet.write(0, col_num, value, header_format)
                column_len = max(df[value].astype(str).map(len).max(), len(value)) + 2
                worksheet.set_column(col_num, col_num, column_len)
                
        output.seek(0)

        filename = f"Reporte_Visitas_{fecha_inicio}_al_{fecha_fin}.xlsx"
        
        headers = {
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
        
        return StreamingResponse(
            output, 
            headers=headers,
            media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/export-visitas/filtros")
def get_export_visitas_filtros(
    id_cliente: int = Query(...),
    fecha_inicio: date = Query(...),
    fecha_fin: date = Query(...),
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    """Devuelve las opciones reales de cuadrantes, departamentos y categorías para el cliente."""
    try:
        q = (
            db.query(
                Ruta.cuadrante,
                PuntoInteres.departamento,
                PuntoInteres.jerarquia_n2,
                PuntoInteres.cadena
            )
            .join(PuntoInteres, Visita.punto_id == PuntoInteres.id)
            .outerjoin(RutaProgramacion, (RutaProgramacion.punto_id == PuntoInteres.id) & (RutaProgramacion.id_cliente == Visita.id_cliente))
            .outerjoin(Ruta, Ruta.id == RutaProgramacion.ruta_id)
            .filter(
                Visita.id_cliente == id_cliente,
                Visita.fecha >= fecha_inicio,
                Visita.fecha <= fecha_fin
            )
            .distinct()
            .all()
        )

        cuadrantes = sorted({r[0] for r in q if r[0]})
        departamentos = sorted({r[1] for r in q if r[1]})
        cats_raw = {r[2] for r in q if r[2]} | {r[3] for r in q if r[3]}
        categorias = sorted({c for c in cats_raw if c})

        return {
            "cuadrantes": cuadrantes,
            "departamentos": departamentos,
            "categorias": categorias,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

