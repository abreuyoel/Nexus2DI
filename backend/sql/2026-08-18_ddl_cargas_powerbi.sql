-- ============================================================
-- DDL & Registros de Permisos para "Cargas de Power BI" y "Dashboard Power BI"
-- ============================================================

DECLARE @id_dash INT;
SELECT @id_dash = id_modulo FROM MODULOS WHERE clave = 'dashboard';

-- 1. Insertar / Actualizar módulo 'cargas-powerbi' como módulo RAÍZ independiente
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

-- 2. Insertar / Actualizar submódulo 'dashboard-powerbi' como HIJO de Dashboard
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'dashboard-powerbi')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
    VALUES ('dashboard-powerbi', 'Power BI', @id_dash, 'modulo', '/dashboard?view=powerbi', 'bar_chart', 1, 1);
END
ELSE
BEGIN
    UPDATE MODULOS
    SET id_padre = @id_dash,
        nombre = 'Power BI',
        ruta = '/dashboard?view=powerbi',
        icono = 'bar_chart'
    WHERE clave = 'dashboard-powerbi';
END
GO

-- 3. Asegurar estructura de la tabla dashboard_client con columna es_principal
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
ELSE
BEGIN
    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.dashboard_client') AND name = 'id_dashboard')
        ALTER TABLE dbo.dashboard_client ADD id_dashboard INT IDENTITY(1,1) NOT NULL PRIMARY KEY;

    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.dashboard_client') AND name = 'nombre')
        ALTER TABLE dbo.dashboard_client ADD nombre NVARCHAR(255) NULL;

    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.dashboard_client') AND name = 'fecha_creacion')
        ALTER TABLE dbo.dashboard_client ADD fecha_creacion DATETIME DEFAULT GETDATE();

    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.dashboard_client') AND name = 'activo')
        ALTER TABLE dbo.dashboard_client ADD activo BIT DEFAULT 1;

    IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('dbo.dashboard_client') AND name = 'es_principal')
        ALTER TABLE dbo.dashboard_client ADD es_principal BIT DEFAULT 0;
END
GO


