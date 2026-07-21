from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL)

with engine.connect() as conn:
    tables = ["VISITAS_MERCADERISTA", "MERCADERISTAS", "PUNTOS_INTERES1", "CLIENTES"]
    for table in tables:
        print(f"\n--- Columns for {table} ---")
        res = conn.execute(text(f"SELECT TOP 0 * FROM {table}"))
        print(res.keys())
