"""Check the PRODUCTS table columns in epran-qa"""
import pyodbc

conn_str = (
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=172.174.41.110;"
    "DATABASE=epran-qa;"
    "UID=dev;"
    "PWD=abcd1234*;"
)

conn = pyodbc.connect(conn_str, timeout=10)
cursor = conn.cursor()

# Get columns of the PRODUCTS table
cursor.execute("""
    SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH
    FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'PRODUCTS' AND TABLE_SCHEMA = 'dbo'
    ORDER BY ORDINAL_POSITION
""")

print("=== PRODUCTS table columns ===")
for row in cursor.fetchall():
    print(f"  {row[0]:40s} {row[1]:20s} nullable={row[2]} maxlen={row[3]}")

# Also check if 'inagotable' column exists
cursor.execute("""
    SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'PRODUCTS' AND COLUMN_NAME LIKE '%inagot%'
""")
cnt = cursor.fetchone()[0]
print(f"\n'inagotable' columns found: {cnt}")

# Sample first 3 rows
cursor.execute("SELECT TOP 3 * FROM [dbo].[PRODUCTS]")
rows = cursor.fetchall()
if rows:
    cols = [desc[0] for desc in cursor.description]
    print("\n=== Sample data columns ===")
    print(cols)

conn.close()
