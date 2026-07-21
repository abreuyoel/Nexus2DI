"""Crea usuario_permisos: la tabla no existia en epran-qa aunque el modelo
ORM (UserPermission), el endpoint /api/users/{id}/permissions y la pagina
admin de Permisos ya la asumian. Sin ella, todo el sistema de permisos
(incluida la nueva visibilidad de sidebar basada en permisos) fallaba con
'Invalid object name usuario_permisos'."""
from app.db.session import SessionLocal
from sqlalchemy import text

DDL = """
CREATE TABLE usuario_permisos (
  id INT IDENTITY PRIMARY KEY,
  id_usuario INT NOT NULL,
  module VARCHAR(50) NOT NULL,
  can_read BIT NOT NULL DEFAULT 1,
  can_write BIT NOT NULL DEFAULT 0,
  can_delete BIT NOT NULL DEFAULT 0,
  can_see_all BIT NOT NULL DEFAULT 0,
  CONSTRAINT FK_USUARIO_PERMISOS_USUARIO FOREIGN KEY (id_usuario) REFERENCES USUARIOS(id_usuario)
);
"""

if __name__ == "__main__":
    db = SessionLocal()
    existing = db.execute(text(
        "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME = 'usuario_permisos'"
    )).fetchall()
    if existing:
        print("Ya existe, no se crea nada:", existing)
    else:
        db.execute(text(DDL.strip().rstrip(";")))
        db.commit()
        print("Tabla creada.")

    r = db.execute(text(
        "SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE FROM INFORMATION_SCHEMA.COLUMNS "
        "WHERE TABLE_NAME = 'usuario_permisos' ORDER BY ORDINAL_POSITION"
    )).fetchall()
    for row in r:
        print(row)
    db.close()
