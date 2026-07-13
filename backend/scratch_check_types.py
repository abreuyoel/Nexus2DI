import pyodbc
from app.core.config import settings

# Parse the connection string
# mssql+pyodbc://user:pass@server/db?driver=...
url = settings.DATABASE_URL
# Simple parsing for pyodbc
conn_str = f"DRIVER={{ODBC Driver 17 for SQL Server}};SERVER={settings.DB_SERVER};DATABASE={settings.DB_NAME};UID={settings.DB_USER};PWD={settings.DB_PASSWORD}"

conn = pyodbc.connect(conn_str)
cursor = conn.cursor()
cursor.execute("SELECT TOP 1 * FROM BALANCES_TOTALES")
for column in cursor.description:
    print(f"Column: {column[0]}, Type: {column[1]}")
conn.close()
