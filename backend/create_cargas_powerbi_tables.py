import logging
from sqlalchemy import text
from app.db.session import engine

logger = logging.getLogger(__name__)

def init_cargas_powerbi_tables():
    """Asegura la creación del módulo 'cargas-powerbi' y la tabla 'dashboard_client' con 'es_principal'."""
    sql_statements = [
        """
        DECLARE @id_dash INT;
        SELECT @id_dash = id_modulo FROM MODULOS WHERE clave = 'dashboard';

        IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'cargas-powerbi')
        BEGIN
            INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
            VALUES ('cargas-powerbi', 'Cargas de Power BI', NULL, 'modulo', '/cargas-powerbi', 'cloud_upload', 12, 1);
        END
        ELSE
        BEGIN
            UPDATE MODULOS
            SET id_padre = NULL,
                nombre = 'Cargas de Power BI',
                ruta = '/cargas-powerbi',
                icono = 'cloud_upload'
            WHERE clave = 'cargas-powerbi';
        END

        IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'dashboard-powerbi')
        BEGIN
            INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
            VALUES ('dashboard-powerbi', 'Power BI', @id_dash, 'modulo', '/dashboard?view=powerbi', 'bar_chart', 1, 1);
        END
        """,
        """
        IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dashboard_client')
        BEGIN
            CREATE TABLE dbo.dashboard_client (
                id_dashboard INT IDENTITY(1,1) PRIMARY KEY,
                id_cliente INT NOT NULL,
                nombre NVARCHAR(255) NULL,
                url_html NVARCHAR(MAX) NOT NULL,
                tipo NVARCHAR(50) DEFAULT 'powerbi',
                fecha_creacion DATETIME DEFAULT GETDATE(),
                activo BIT DEFAULT 1,
                es_principal BIT DEFAULT 0
            );
        END
        """,
        """
        IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'dashboard_client')
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.dashboard_client') AND name = 'id_dashboard')
            BEGIN
                ALTER TABLE dbo.dashboard_client ADD id_dashboard INT IDENTITY(1,1) NOT NULL PRIMARY KEY;
            END
            IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.dashboard_client') AND name = 'nombre')
            BEGIN
                ALTER TABLE dbo.dashboard_client ADD nombre NVARCHAR(255) NULL;
            END
            IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.dashboard_client') AND name = 'fecha_creacion')
            BEGIN
                ALTER TABLE dbo.dashboard_client ADD fecha_creacion DATETIME DEFAULT GETDATE();
            END
            IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.dashboard_client') AND name = 'activo')
            BEGIN
                ALTER TABLE dbo.dashboard_client ADD activo BIT DEFAULT 1;
            END
            IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.dashboard_client') AND name = 'es_principal')
            BEGIN
                ALTER TABLE dbo.dashboard_client ADD es_principal BIT DEFAULT 0;
            END
        END
        """,
        """
        IF EXISTS (SELECT 1 FROM sys.tables WHERE name = 'usuario_permisos')
        BEGIN
            INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete)
            SELECT u.id_usuario, m.clave, 1, 1, 1
            FROM USUARIOS u
            CROSS JOIN (VALUES ('cargas-powerbi'), ('dashboard-powerbi')) AS m(clave)
            WHERE u.id_rol IN (8, 2, 3, 4, 11)
              AND NOT EXISTS (
                  SELECT 1 FROM usuario_permisos up
                  WHERE up.id_usuario = u.id_usuario AND up.module = m.clave
              );
        END
        """
    ]

    try:
        with engine.begin() as conn:
            for stmt in sql_statements:
                conn.execute(text(stmt))
        logger.info("Tabla dashboard_client (con es_principal) inicializada correctamente.")
    except Exception as e:
        logger.error(f"Error al inicializar cargas-powerbi: {e}")

if __name__ == "__main__":
    init_cargas_powerbi_tables()
