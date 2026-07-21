"""Inicialización de catálogos: crea tablas y semilla con valores existentes en PUNTOS_INTERES1."""
import logging
from sqlalchemy import inspect, text, func
from app.db.session import engine, SessionLocal
from app.db.base import Base
from app.modules.catalogues.entities import (
    TipoNegocio, SubtipoNegocio, Alcance, CanalVenta, DepartamentoGeo, Ciudad,
    Cuadrante, Servicio,
)
from app.modules.routes.entities import PuntoInteres, Ruta, RutaProgramacion
from app.modules.visits.entities import FotoRazonRechazo
from app.modules.chat.entities import (
    ChatGrupo, ChatGrupoMensaje, ChatGrupoLectura, ChatGrupoMensajeLectura,
    ChatMensajeGrupoVisita, ChatGrupoVisitaLectura, ChatMensajeLectura,
    ChatConversacion, ChatParticipante
)

logger = logging.getLogger("app")

CATALOG_TABLES = [
    "CAT_TIPO_NEGOCIO",
    "CAT_SUBTIPO_NEGOCIO",
    "CAT_ALCANCE",
    "CAT_CANAL_VENTA",
    "CAT_DEPARTAMENTOS",
    "CAT_CIUDADES",
    "CUADRANTES",
    "SERVICIOS",
    "SUPERVISORES_CLIENTES",
    "FOTOS_RAZONES_RECHAZOS",
    "CHAT_GRUPOS",
    "CHAT_GRUPO_MENSAJES",
    "CHAT_GRUPO_LECTURAS",
    "CHAT_GRUPO_MENSAJE_LECTURAS",
    "CHAT_MENSAJES_GRUPO_VISITA",
    "CHAT_GRUPO_VISITA_LECTURAS",
    "CHAT_MENSAJE_LECTURAS",
    "CHAT_CONVERSACIONES",
    "CHAT_PARTICIPANTES",
]



def ensure_chat_columns() -> None:
    try:
        cols_info = inspect(engine).get_columns("CHAT_MENSAJES_CLIENTE")
        visita_col = next((c for c in cols_info if c["name"] == "id_visita"), None)
        if visita_col and not visita_col.get("nullable", True):
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE CHAT_MENSAJES_CLIENTE ALTER COLUMN id_visita INT NULL"))
            logger.info("Columna CHAT_MENSAJES_CLIENTE.id_visita actualizada a NULLABLE")
    except Exception as e:
        logger.warning(f"No se pudo inspeccionar CHAT_MENSAJES_CLIENTE: {e}")


def ensure_solicitudes_columns() -> None:

    try:
        cols = [c["name"] for c in inspect(engine).get_columns("SOLICITUDES")]
        if "respuesta" not in cols:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE SOLICITUDES ADD respuesta NVARCHAR(MAX) NULL"))
            logger.info("Columna SOLICITUDES.respuesta creada")
    except Exception as e:
        logger.warning(f"No se pudo inspeccionar SOLICITUDES: {e}")


def ensure_route_columns() -> None:

    """Agrega columnas faltantes en RUTAS_NUEVAS (idempotente).
    `id_cliente_exclusivo` existe en la BD de v1 pero no necesariamente en QA."""
    try:
        cols = [c["name"] for c in inspect(engine).get_columns("RUTAS_NUEVAS")]
    except Exception as e:
        logger.warning(f"No se pudo inspeccionar RUTAS_NUEVAS: {e}")
        return
    if "id_cliente_exclusivo" not in cols:
        try:
            with engine.begin() as conn:
                conn.execute(text("ALTER TABLE RUTAS_NUEVAS ADD id_cliente_exclusivo INT NULL"))
            logger.info("Columna RUTAS_NUEVAS.id_cliente_exclusivo creada")
        except Exception as e:
            logger.exception(f"No se pudo crear RUTAS_NUEVAS.id_cliente_exclusivo: {e}")
    _backfill_exclusive_clients()


def _backfill_exclusive_clients() -> None:
    """Rellena id_cliente_exclusivo en rutas Exclusivas (nombre 'Ruta E%') que estén
    en NULL, usando el cliente más frecuente en sus programaciones. Idempotente."""
    db = SessionLocal()
    try:
        rutas = (
            db.query(Ruta)
            .filter(Ruta.nombre.like("Ruta E%"), Ruta.id_cliente_exclusivo.is_(None))
            .all()
        )
        updated = 0
        for r in rutas:
            top = (
                db.query(RutaProgramacion.id_cliente)
                .filter(RutaProgramacion.ruta_id == r.id, RutaProgramacion.id_cliente.isnot(None))
                .group_by(RutaProgramacion.id_cliente)
                .order_by(func.count().desc())
                .first()
            )
            if top:
                r.id_cliente_exclusivo = top[0]
                updated += 1
        if updated:
            db.commit()
            logger.info(f"Backfill cliente exclusivo en {updated} ruta(s) Exclusiva(s)")
    except Exception as e:
        logger.exception(f"Error en backfill de cliente exclusivo: {e}")
        db.rollback()
    finally:
        db.close()


def ensure_catalog_tables() -> None:
    """Crea las tablas de catálogo si no existen, y siembra con valores distintos
    de PUNTOS_INTERES1 la primera vez."""
    ensure_route_columns()
    ensure_solicitudes_columns()
    ensure_chat_columns()


    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    missing = [t for t in CATALOG_TABLES if t not in existing]

    if missing:
        logger.info(f"Creando tablas de catálogo: {missing}")
        # Crear sólo los modelos que faltan
        tables_to_create = [
            t for t in Base.metadata.sorted_tables if t.name in missing
        ]
        Base.metadata.create_all(bind=engine, tables=tables_to_create)
        logger.info("Tablas de catálogo creadas")

    _seed_from_existing_pdv()
    _seed_from_existing_routes()


def _seed_from_existing_routes() -> None:
    """Si CUADRANTES / SERVICIOS están vacías, las rellena con los DISTINCT
    de RUTAS_NUEVAS (cuadrante / servicio)."""
    db = SessionLocal()
    try:
        seed_map = [
            (Cuadrante, Ruta.cuadrante),
            (Servicio, Ruta.servicio),
        ]
        for Model, column in seed_map:
            if db.query(Model).count() > 0:
                continue
            distinct_values = (
                db.query(column).filter(column.isnot(None)).distinct().all()
            )
            seeded = 0
            for (val,) in distinct_values:
                if not val:
                    continue
                val = val.strip()
                if not val:
                    continue
                if not db.query(Model).filter(Model.nombre == val).first():
                    db.add(Model(nombre=val, activo=True))
                    seeded += 1
            if seeded:
                db.commit()
                logger.info(f"Sembrado {Model.__tablename__} con {seeded} valores")
    except Exception as e:
        logger.exception(f"Error sembrando catálogos de rutas: {e}")
        db.rollback()
    finally:
        db.close()


def _seed_from_existing_pdv() -> None:
    """Si una tabla de catálogo está vacía, la rellena con los DISTINCT
    de la columna correspondiente en PUNTOS_INTERES1."""
    db = SessionLocal()
    try:
        seed_map = [
            (TipoNegocio, PuntoInteres.jerarquia_n2),
            (SubtipoNegocio, PuntoInteres.jerarquia_n2_2),
            (Alcance, PuntoInteres.nivel_de_alcance),
            (CanalVenta, PuntoInteres.cadena),
            (DepartamentoGeo, PuntoInteres.departamento),
        ]
        for Model, column in seed_map:
            if db.query(Model).count() > 0:
                continue
            distinct_values = (
                db.query(column).filter(column.isnot(None)).distinct().all()
            )
            seeded = 0
            for (val,) in distinct_values:
                if not val:
                    continue
                val = val.strip()
                if not val:
                    continue
                if not db.query(Model).filter(Model.nombre == val).first():
                    db.add(Model(nombre=val, activo=True))
                    seeded += 1
            if seeded:
                db.commit()
                logger.info(f"Sembrado {Model.__tablename__} con {seeded} valores")

        # Ciudades: necesita asociar con departamento
        if db.query(Ciudad).count() == 0:
            departamentos = {d.nombre: d.id for d in db.query(DepartamentoGeo).all()}
            pares = (
                db.query(PuntoInteres.ciudad, PuntoInteres.departamento)
                .filter(PuntoInteres.ciudad.isnot(None))
                .filter(PuntoInteres.departamento.isnot(None))
                .distinct()
                .all()
            )
            seeded = 0
            seen: set[tuple[int, str]] = set()
            sin_dep = 0
            for ciudad_name, dep_name in pares:
                if not ciudad_name or not dep_name:
                    continue
                ciudad_name = ciudad_name.strip()
                dep_name = dep_name.strip()
                dep_id = departamentos.get(dep_name)
                if not dep_id:
                    sin_dep += 1
                    continue
                key = (dep_id, ciudad_name)
                if key in seen:
                    continue
                seen.add(key)
                db.add(Ciudad(nombre=ciudad_name, departamento_id=dep_id, activo=True))
                seeded += 1
            if seeded:
                db.commit()
                logger.info(f"Sembrado CAT_CIUDADES con {seeded} valores ({sin_dep} ignoradas sin departamento)")
    except Exception as e:
        logger.exception(f"Error sembrando catálogos: {e}")
        db.rollback()
    finally:
        db.close()
