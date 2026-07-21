"""Fix Fisa user: assign id_rol=1 (Cliente) and id_perfil=43 (Laboratorios Fisa)"""
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

# Before
cursor.execute("SELECT id_usuario, username, id_rol, id_perfil FROM USUARIOS WHERE id_usuario = 430")
before = cursor.fetchone()
print(f"BEFORE: id={before[0]}, username={before[1]}, id_rol={before[2]}, id_perfil={before[3]}")

# Update
cursor.execute("UPDATE USUARIOS SET id_rol = 1, id_perfil = 43 WHERE id_usuario = 430")
conn.commit()

# After
cursor.execute("SELECT id_usuario, username, id_rol, id_perfil FROM USUARIOS WHERE id_usuario = 430")
after = cursor.fetchone()
print(f"AFTER:  id={after[0]}, username={after[1]}, id_rol={after[2]}, id_perfil={after[3]}")

print("\nDone! User Fisa now has id_rol=1 (Cliente) and id_perfil=43 (Laboratorios Fisa)")
conn.close()
