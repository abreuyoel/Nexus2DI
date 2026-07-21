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
from app.models.user import Usuario
from app.models.visita import Visita
from app.models.foto import Foto
from app.models.ruta import RutaActivada
from app.models.punto import PuntoInteres

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

@router.get("/export-visitas-filtros")
def get_export_visitas_filtros(
    id_cliente: int = Query(...),
    fecha_inicio: Optional[date] = Query(None),
    fecha_fin: Optional[date] = Query(None),
    db: Session = Depends(get_db),
    _: Usuario = Depends(require_analyst_or_admin),
):
    """Valores reales (SELECT DISTINCT) de cuadrante/departamento/categoría
    para ESTE cliente -- alimenta los dropdowns del modal de exportar Excel
    en vez de que el usuario tipee texto libre a ciegas. Mismos JOINs que
    export_visitas_excel, para que lo que aparece acá SIEMPRE tenga
    resultados si se usa como filtro ahí."""
    params: dict = {"id_cliente": id_cliente}
    fecha_filter = ""
    if fecha_inicio:
        fecha_filter += " AND v.fecha_visita >= :fecha_inicio"
        params["fecha_inicio"] = fecha_inicio
    if fecha_fin:
        fecha_filter += " AND v.fecha_visita <= :fecha_fin"
        params["fecha_fin"] = fecha_fin

    cuadrantes = db.execute(text(f"""
        SELECT DISTINCT rc.cuadrante
        FROM VISITAS_MERCADERISTA v
        JOIN PUNTOS_INTERES1 p ON v.identificador_punto_interes = p.identificador
        LEFT JOIN (
            SELECT rp.id_punto_interes, MIN(rn.cuadrante) AS cuadrante
            FROM RUTA_PROGRAMACION rp
            JOIN RUTAS_NUEVAS rn ON rp.id_ruta = rn.id_ruta
            WHERE rp.activa = 1 AND rn.cuadrante IS NOT NULL
            GROUP BY rp.id_punto_interes
        ) rc ON rc.id_punto_interes = p.identificador
        WHERE v.id_cliente = :id_cliente AND rc.cuadrante IS NOT NULL {fecha_filter}
    """), params).scalars().all()

    departamentos = db.execute(text(f"""
        SELECT DISTINCT p.departamento
        FROM VISITAS_MERCADERISTA v
        JOIN PUNTOS_INTERES1 p ON v.identificador_punto_interes = p.identificador
        WHERE v.id_cliente = :id_cliente AND p.departamento IS NOT NULL {fecha_filter}
    """), params).scalars().all()

    categorias = db.execute(text(f"""
        SELECT DISTINCT valor FROM (
            SELECT p.jerarquia_nivel_2 AS valor
            FROM VISITAS_MERCADERISTA v
            JOIN PUNTOS_INTERES1 p ON v.identificador_punto_interes = p.identificador
            WHERE v.id_cliente = :id_cliente {fecha_filter}
            UNION
            SELECT p.clasificacion_de_canal AS valor
            FROM VISITAS_MERCADERISTA v
            JOIN PUNTOS_INTERES1 p ON v.identificador_punto_interes = p.identificador
            WHERE v.id_cliente = :id_cliente {fecha_filter}
        ) x WHERE valor IS NOT NULL
    """), params).scalars().all()

    return {
        "cuadrantes": sorted(cuadrantes),
        "departamentos": sorted(departamentos),
        "categorias": sorted(categorias),
    }


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
        # Base query to get visit info along with PDV and routes
        query = """
            SELECT
                v.id_visita AS [ID Visita],
                v.fecha_visita AS [Fecha],
                v.estado AS [Estado Visita],
                p.punto_de_interes AS [Nombre del PDV],
                p.departamento AS [Departamento / Estado],
                p.clasificacion_de_canal AS [Canal],
                p.jerarquia_nivel_2 AS [Categoría PDV],
                rc.cuadrante AS [Cuadrante],
                m.nombre AS [Mercaderista]
            FROM VISITAS_MERCADERISTA v
            JOIN PUNTOS_INTERES1 p ON v.identificador_punto_interes = p.identificador
            LEFT JOIN (
                SELECT rp.id_punto_interes, MIN(rn.cuadrante) AS cuadrante
                FROM RUTA_PROGRAMACION rp
                JOIN RUTAS_NUEVAS rn ON rp.id_ruta = rn.id_ruta
                WHERE rp.activa = 1 AND rn.cuadrante IS NOT NULL
                GROUP BY rp.id_punto_interes
            ) rc ON rc.id_punto_interes = p.identificador
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
            query += " AND rc.cuadrante = :cuadrante"
            params["cuadrante"] = cuadrante
            
        if departamento:
            query += " AND p.departamento = :departamento"
            params["departamento"] = departamento
            
        if categoria:
            query += " AND (p.jerarquia_nivel_2 = :categoria OR p.clasificacion_de_canal = :categoria)"
            params["categoria"] = categoria

        # Execute query
        result = db.execute(text(query), params).fetchall()
        
        # Convert to pandas DataFrame
        if not result:
            # Empty dataframe with headers if no data
            df = pd.DataFrame(columns=[
                "ID Visita", "Fecha", "Estado Visita", "Nombre del PDV", 
                "Departamento / Estado", "Canal", "Categoría PDV", "Cuadrante", "Mercaderista"
            ])
        else:
            # Convert sequence of rows to dicts
            data = [dict(row._mapping) for row in result]
            df = pd.DataFrame(data)

        # Write DataFrame to a BytesIO stream
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df.to_excel(writer, index=False, sheet_name='Visitas')
            
            # Formatting
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
                # Auto-fit columns
                column_len = max(df[value].astype(str).map(len).max(), len(value)) + 2
                worksheet.set_column(col_num, col_num, column_len)
                
        output.seek(0)

        # Build filename
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
