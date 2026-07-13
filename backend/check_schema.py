import sys
sys.path.append('.')
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
tables = ['CLIENTES', 'CHAT_MENSAJES', 'CHAT_LECTURAS', 'VISITAS_MERCADERISTA', 'PUNTOS_INTERES1', 'MERCADERISTAS', 'RUTAS_NUEVAS']

for table in tables:
    try:
        r = db.execute(text(f"SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns WHERE table_name = '{table}'")).fetchall()
        print(f"{table}: {[(row[0], row[1]) for row in r]}")
    except Exception as e:
        print(f"Error checking {table}: {e}")
