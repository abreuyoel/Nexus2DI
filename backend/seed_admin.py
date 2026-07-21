import sys
sys.path.insert(0, '.')

from app.db.session import SessionLocal
from app.core.security import get_password_hash
from sqlalchemy import text

db = SessionLocal()

# Roles requeridos en la base de datos
roles = [
    (1, 'client'), (2, 'analyst'), (3, 'coordinador_exclusivo'),
    (4, 'coordinador_tradex'), (5, 'mercaderista'), (6, 'supervisor'),
    (7, 'auditor'), (8, 'admin'), (9, 'vendedor'), (10, 'atc'),
    (11, 'coordinador_general'), (12, 'encuestador'),
    (13, 'cliente_encuestador'), (14, 'auditor_campo'),
]

for rid, nombre in roles:
    exists = db.execute(text('SELECT 1 FROM ROLES WHERE id_rol=:id'), {'id': rid}).fetchone()
    if not exists:
        db.execute(text('INSERT INTO ROLES (id_rol, nombre) VALUES (:id, :nombre)'), {'id': rid, 'nombre': nombre})
print('Roles insertados/verificados.')

# Crear usuario admin inicial
existe = db.execute(text("SELECT 1 FROM USUARIOS WHERE username='admin'")).fetchone()
if not existe:
    hashed = get_password_hash('Admin1234!')
    db.execute(text('''
        INSERT INTO USUARIOS (username, password_hash, email, id_rol, activo)
        VALUES (:u, :p, :e, :r, 1)
    '''), {'u': 'admin', 'p': hashed, 'e': 'admin@epran.com', 'r': 8})
    print('Usuario admin creado exitosamente. Password: Admin1234!')
else:
    print('El usuario admin ya existe.')

db.commit()
db.close()
