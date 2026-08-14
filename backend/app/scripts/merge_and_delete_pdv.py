"""Script y helper para reasignar visitas/programación de un PDV duplicado
hacia el PDV principal con más visitas y luego eliminar el PDV duplicado safely.
"""
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text


def reasignar_y_eliminar_pdv(
    db: Session,
    pdv_id_eliminar: str,
    pdv_id_destino: Optional[str] = None
) -> Dict[str, Any]:
    """Reasigna visitas, programaciones y frecuencias del pdv_id_eliminar
    hacia pdv_id_destino (o el PDV candidato con más visitas) y elimina el PDV.
    """
    # 1. Verificar existencia del PDV a eliminar
    pdv_origen = db.execute(
        text("SELECT identificador, nombre_del_punto FROM PUNTOS_INTERES1 WHERE identificador = :pid"),
        {"pid": pdv_id_eliminar}
    ).first()

    if not pdv_origen:
        raise ValueError(f"El PDV origen con identificador '{pdv_id_eliminar}' no existe.")

    # 2. Si no se especificó destino, buscar el PDV candidato con más visitas
    if not pdv_id_destino:
        nombre_origen = pdv_origen.nombre_del_punto or ""
        candidatos = db.execute(
            text("""
                SELECT p.identificador, p.nombre_del_punto, COUNT(v.id) as total_visitas
                FROM PUNTOS_INTERES1 p
                LEFT JOIN VISITAS_MERCADERISTA v ON v.identificador_punto_interes = p.identificador
                WHERE p.identificador != :pid AND p.nombre_del_punto LIKE :nombre
                GROUP BY p.identificador, p.nombre_del_punto
                ORDER BY total_visitas DESC
            """),
            {"pid": pdv_id_eliminar, "nombre": f"%{nombre_origen[:8]}%"}
        ).fetchall()

        if not candidatos:
            candidatos = db.execute(
                text("""
                    SELECT TOP 1 p.identificador, p.nombre_del_punto, COUNT(v.id) as total_visitas
                    FROM PUNTOS_INTERES1 p
                    JOIN VISITAS_MERCADERISTA v ON v.identificador_punto_interes = p.identificador
                    WHERE p.identificador != :pid
                    GROUP BY p.identificador, p.nombre_del_punto
                    ORDER BY total_visitas DESC
                """),
                {"pid": pdv_id_eliminar}
            ).fetchall()

        if not candidatos:
            raise ValueError("No se encontró ningún PDV destino candidato para reasignar las visitas.")

        pdv_id_destino = candidatos[0].identificador

    # 3. Verificar que el destino existe
    pdv_dest = db.execute(
        text("SELECT identificador, nombre_del_punto FROM PUNTOS_INTERES1 WHERE identificador = :pid"),
        {"pid": pdv_id_destino}
    ).first()

    if not pdv_dest:
        raise ValueError(f"El PDV destino '{pdv_id_destino}' no existe.")

    # 4. Reasignar en VISITAS_MERCADERISTA
    res_visitas = db.execute(
        text("UPDATE VISITAS_MERCADERISTA SET identificador_punto_interes = :dest WHERE identificador_punto_interes = :orig"),
        {"dest": pdv_id_destino, "orig": pdv_id_eliminar}
    )
    visitas_movidas = res_visitas.rowcount

    # 5. Reasignar en RUTA_PROGRAMACION
    res_rutas = db.execute(
        text("UPDATE RUTA_PROGRAMACION SET id_punto_interes = :dest WHERE id_punto_interes = :orig"),
        {"dest": pdv_id_destino, "orig": pdv_id_eliminar}
    )
    rutas_movidas = res_rutas.rowcount

    # 6. Reasignar en FRECUENCIAS_PDVS_CLIENTE si existe
    try:
        res_frec = db.execute(
            text("UPDATE FRECUENCIAS_PDVS_CLIENTE SET id_punto_interes = :dest WHERE id_punto_interes = :orig"),
            {"dest": pdv_id_destino, "orig": pdv_id_eliminar}
        )
        frec_movidas = res_frec.rowcount
    except Exception:
        frec_movidas = 0

    # 7. Eliminar PDV origen
    db.execute(
        text("DELETE FROM PUNTOS_INTERES1 WHERE identificador = :orig"),
        {"orig": pdv_id_eliminar}
    )

    db.commit()

    return {
        "success": True,
        "pdv_eliminado": pdv_id_eliminar,
        "pdv_destino": pdv_id_destino,
        "nombre_destino": pdv_dest.nombre_del_punto,
        "visitas_reasignadas": visitas_movidas,
        "rutas_reasignadas": rutas_movidas,
        "frecuencias_reasignadas": frec_movidas
    }
