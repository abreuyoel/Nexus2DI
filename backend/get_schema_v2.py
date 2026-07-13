import sys
import os
sys.path.append('.')
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
tables = ['JORNADAS_ENCUESTADOR', 'encuestas_centro', 'centros_salud', 'medicos', 'medico_centro_encuesta']

for table in tables:
    try:
        r = db.execute(text(f"SELECT COLUMN_NAME, DATA_TYPE, CHARACTER_MAXIMUM_LENGTH FROM information_schema.columns WHERE table_name = '{table}'")).fetchall()
        print(f"\n--- TABLE {table} ---")
        for row in r:
            print(f"{row[0]}: {row[1]} ({row[2]})")
    except Exception as e:
        print(f"Error checking {table}: {e}")
