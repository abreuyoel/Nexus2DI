from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from datetime import date, timedelta
import pandas as pd
import io
from app.db.session import get_db
from app.core.dependencies import get_current_user, require_analyst_or_admin
from app.modules.auth.entities import Usuario
from app.modules.visits.entities import Visita, Foto
from app.modules.routes.entities import RutaActivada

router = APIRouter(prefix="/api/reports", tags=["Reportería"])


@router.get("/summary")
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

    return {
        "periodo": {"inicio": str(fecha_inicio), "fin": str(fecha_fin)},
        "visitas": {
            "total": total,
            "completadas": completadas,
            "pendientes": pendientes,
            "porcentaje_completadas": round(completadas / total * 100, 1) if total > 0 else 0,
        },
        "fotos": {
            "total": len(fotos),
            "aprobadas": fotos_aprobadas,
            "rechazadas": fotos_rechazadas,
            "pendientes": fotos_pendientes,
        },
    }


@router.get("/chart-data")
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
        from sqlalchemy import func
        results = db.query(
            Visita.fecha,
            func.count(Visita.id).label("total"),
        ).filter(
            Visita.fecha >= fecha_inicio,
            Visita.fecha <= fecha_fin,
        ).group_by(Visita.fecha).order_by(Visita.fecha).all()

        return {
            "labels": [str(r.fecha) for r in results],
            "data": [r.total for r in results],
            "title": "Visitas por Día",
        }

    elif tipo == "fotos_por_estado":
        from sqlalchemy import func
        results = db.query(
            Foto.estado,
            func.count(Foto.id).label("total"),
        ).group_by(Foto.estado).all()

        return {
            "labels": [r.estado for r in results],
            "data": [r.total for r in results],
            "title": "Fotos por Estado",
        }

    return {"labels": [], "data": [], "title": tipo}


@router.get("/activated-routes")
def get_activated_routes(
    db: Session = Depends(get_db),
    _: Usuario = Depends(get_current_user),
):
    today = date.today()
    activadas = db.query(RutaActivada).filter(RutaActivada.fecha == today).all()
    return [{"ruta_id": a.ruta_id, "cedula": a.mercaderista_cedula, "hora": str(a.activada_at)} for a in activadas]


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
        query = """
            SELECT 
                v.id_visita AS [ID Visita],
                v.fecha_visita AS [Fecha],
                v.estado AS [Estado Visita],
                p.punto_de_interes AS [Nombre del PDV],
                p.departamento AS [Departamento / Estado],
                p.clasificacion_de_canal AS [Canal],
                p.jerarquia_nivel_2 AS [Categoría PDV],
                rn.cuadrante AS [Cuadrante],
                m.nombre AS [Mercaderista]
            FROM VISITAS_MERCADERISTA v
            JOIN PUNTOS_INTERES1 p ON v.identificador_punto_interes = p.identificador
            LEFT JOIN RUTAS_NUEVAS rn ON p.identificador = rn.id_punto_interes
            LEFT JOIN MERCADERISTAS m ON v.id_mercaderista = m.id_mercaderista
            WHERE v.id_cliente = :id_cliente
              AND v.fecha_visita >= :fecha_inicio
              AND v.fecha_visita <= :fecha_fin
        """
        params = {
            "id_cliente": id_cliente,
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin
        }

        if cuadrante:
            query += " AND rn.cuadrante = :cuadrante"
            params["cuadrante"] = cuadrante
            
        if departamento:
            query += " AND p.departamento = :departamento"
            params["departamento"] = departamento
            
        if categoria:
            query += " AND (p.jerarquia_nivel_2 = :categoria OR p.clasificacion_de_canal = :categoria)"
            params["categoria"] = categoria

        result = db.execute(text(query), params).fetchall()
        
        if not result:
            df = pd.DataFrame(columns=[
                "ID Visita", "Fecha", "Estado Visita", "Nombre del PDV", 
                "Departamento / Estado", "Canal", "Categoría PDV", "Cuadrante", "Mercaderista"
            ])
        else:
            data = [dict(row._mapping) for row in result]
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
