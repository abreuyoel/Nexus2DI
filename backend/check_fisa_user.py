import pyodbc
conn = pyodbc.connect(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=172.174.41.110;"
    "DATABASE=epran-qa;"
    "UID=dev;"
    "PWD=abcd1234*;"
    "TrustServerCertificate=yes"
)
cursor = conn.cursor()
cursor.execute("SELECT id_cliente, cliente FROM CLIENTES WHERE cliente LIKE '%fisa%' OR cliente LIKE '%Fisa%' OR cliente LIKE '%FISA%'")
rows = cursor.fetchall()
print("=== Clientes matching Fisa ===")
for r in rows:
    print(f"  id_cliente={r[0]}, nombre={r[1]}")
    cursor.execute("SELECT COUNT(*) FROM VISITAS_MERCADERISTA vm JOIN FOTOS_TOTALES ft ON ft.id_visita = vm.id_visita WHERE vm.id_cliente = ? AND ft.Estado = 'Aprobada'", r[0])
    cnt = cursor.fetchone()
    print(f"  -> Approved photos: {cnt[0]}")

# Also list all clients for reference
print("\n=== ALL Clients ===")
cursor.execute("SELECT id_cliente, cliente, id_tipo_cliente FROM CLIENTES ORDER BY id_cliente")
for r in cursor.fetchall():
    print(f"  id={r[0]}, nombre={r[1]}, tipo={r[2]}")

conn.close()
