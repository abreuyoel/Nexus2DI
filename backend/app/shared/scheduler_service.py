import logging
from datetime import date, datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy.orm import Session
from app.db.session import SessionLocal
from app.modules.routes.entities import RutaCambioFuturo, RutaProgramacion
from app.core.config import settings

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler(timezone=settings.SCHEDULER_TIMEZONE)


def ejecutar_cambios_futuros():
    db: Session = SessionLocal()
    try:
        hoy = date.today()
        cambios = db.query(RutaCambioFuturo).filter(
            RutaCambioFuturo.estado == "PENDIENTE",
            RutaCambioFuturo.fecha_ejecucion <= hoy,
        ).all()

        for cambio in cambios:
            try:
                _ejecutar_cambio(db, cambio)
                cambio.estado = "EJECUTADO"
                cambio.fecha_ejecutado = datetime.now()
                db.commit()
                logger.info(f"Cambio {cambio.id} ejecutado exitosamente")
            except Exception as e:
                db.rollback()
                logger.error(f"Error ejecutando cambio {cambio.id}: {e}")
    finally:
        db.close()


def _ejecutar_cambio(db: Session, cambio: RutaCambioFuturo):
    tipo = (cambio.tipo_cambio or "").lower()

    if tipo in ("insert", "agregar", "add"):
        prog = RutaProgramacion(
            ruta_id=cambio.ruta_id,
            punto_id=cambio.id_punto_interes,
            dia=cambio.dia,
            prioridad=cambio.prioridad,
            id_cliente=cambio.id_cliente,
            activo=cambio.activa if cambio.activa is not None else True,
        )
        db.add(prog)

    elif tipo in ("update", "modificacion", "modificación", "modify"):
        prog = db.query(RutaProgramacion).filter(
            RutaProgramacion.ruta_id == cambio.ruta_id,
            RutaProgramacion.punto_id == cambio.id_punto_interes,
        ).first()
        if prog:
            if cambio.dia is not None:
                prog.dia = cambio.dia
            if cambio.prioridad is not None:
                prog.prioridad = cambio.prioridad
            if cambio.activa is not None:
                prog.activo = cambio.activa
            if cambio.id_cliente is not None:
                prog.id_cliente = cambio.id_cliente

    elif tipo in ("delete", "eliminar", "remove"):
        prog = db.query(RutaProgramacion).filter(
            RutaProgramacion.ruta_id == cambio.ruta_id,
            RutaProgramacion.punto_id == cambio.id_punto_interes,
        ).first()
        if prog:
            db.delete(prog)
    else:
        logger.warning(f"Tipo de cambio desconocido: {cambio.tipo_cambio} (id={cambio.id})")


def start_scheduler():
    scheduler.add_job(
        ejecutar_cambios_futuros,
        trigger=IntervalTrigger(minutes=settings.SCHEDULER_INTERVAL_MINUTES),
        id="ejecutar_cambios_futuros",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    logger.info("Scheduler iniciado")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
