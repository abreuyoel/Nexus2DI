from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    res = conn.execute(text("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='PUNTOS_INTERES1'"))
    print("PUNTOS_INTERES1:", [r[0] for r in res.fetchall()])

    res = conn.execute(text("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='RUTA_PROGRAMACION'"))
    print("RUTA_PROGRAMACION:", [r[0] for r in res.fetchall()])

    res = conn.execute(text("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='MERCADERISTAS'"))
    print("MERCADERISTAS:", [r[0] for r in res.fetchall()])

    res = conn.execute(text("SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME='RUTAS_NUEVAS'"))
    print("RUTAS_NUEVAS:", [r[0] for r in res.fetchall()])
