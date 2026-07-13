import sys
import os
sys.path.append('.')
from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
tables = ['USUARIOS']

for table in tables:
    try:
        r = db.execute(text(f"SELECT COLUMN_NAME, DATA_TYPE FROM information_schema.columns WHERE table_name = '{table}'")).fetchall()
        print(f"\n--- TABLE {table} ---")
        for row in r:
            print(f"{row[0]}: {row[1]}")
    except Exception as e:
        print(f"Error checking {table}: {e}")
