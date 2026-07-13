from app.db.session import SessionLocal
from sqlalchemy import text

db = SessionLocal()
cid = 43

# 1. Visitas últimos 7 días
v7 = db.execute(text(
    "SELECT COUNT(*) FROM VISITAS_MERCADERISTA WHERE id_cliente = :c AND fecha_visita >= DATEADD(day, -7, GETDATE())"
), {"c": cid}).scalar()
print(f"Visitas 7d: {v7}")

# 2. Visitas últimos 30 días
v30 = db.execute(text(
    "SELECT COUNT(*) FROM VISITAS_MERCADERISTA WHERE id_cliente = :c AND fecha_visita >= DATEADD(day, -30, GETDATE())"
), {"c": cid}).scalar()
print(f"Visitas 30d: {v30}")

# 3. Fotos 7 días
f7 = db.execute(text(
    "SELECT COUNT(*) FROM FOTOS_TOTALES ft "
    "INNER JOIN VISITAS_MERCADERISTA vm ON ft.id_visita = vm.id_visita "
    "WHERE vm.id_cliente = :c AND ft.Estado = :e "
    "AND vm.fecha_visita >= DATEADD(day, -7, GETDATE())"
), {"c": cid, "e": "Aprobada"}).scalar()
print(f"Fotos aprobadas 7d: {f7}")

# 4. Buscar tablas de mensajes/chat
tabs = db.execute(text(
    "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME LIKE 'CHAT%' OR TABLE_NAME LIKE 'MENSAJE%'"
)).fetchall()
print(f"Tablas chat/mensaje: {[r[0] for r in tabs]}")

# 5. Estado de fotos disponibles
estados = db.execute(text(
    "SELECT DISTINCT ft.Estado FROM FOTOS_TOTALES ft "
    "INNER JOIN VISITAS_MERCADERISTA vm ON ft.id_visita = vm.id_visita "
    "WHERE vm.id_cliente = :c"
), {"c": cid}).fetchall()
print(f"Estados de fotos: {[r[0] for r in estados]}")

db.close()
