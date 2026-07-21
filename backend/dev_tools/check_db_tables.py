import pyodbc
from app.core.config import settings

def check_tables():
    print(f"Connecting to: {settings.DB_SERVER}")
    try:
        conn_str = (
            f"DRIVER={{{settings.DB_DRIVER}}};"
            f"SERVER={settings.DB_SERVER};"
            f"DATABASE={settings.DB_NAME};"
            f"UID={settings.DB_USER};"
            f"PWD={settings.DB_PASSWORD};"
            f"TrustServerCertificate=yes;"
        )
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        for table in ["USUARIOS", "SESIONES_ACTIVAS"]:
            print(f"\nChecking table: {table}")
            try:
                cursor.execute(f"SELECT TOP 1 * FROM {table}")
                columns = [column[0] for column in cursor.description]
                print(f"Columns: {columns}")
            except Exception as e:
                print(f"Error accessing {table}: {e}")
        
        conn.close()
    except Exception as e:
        print(f"Connection failed: {e}")

if __name__ == "__main__":
    check_tables()
