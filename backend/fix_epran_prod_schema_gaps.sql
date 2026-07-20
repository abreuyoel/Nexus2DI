-- Corrige en epran (produccion) las columnas que ya existen en epran-qa y
-- que le faltan, o que tienen un tipo/longitud mas chico del que el codigo
-- de Nexus2DI v2 realmente necesita -- ver resultado.txt de
-- compare_epran_vs_epran_qa.sql, bloque 3.
--
-- Diagnostico columna por columna (por que se elige esta direccion y no la
-- otra -- confirmado leyendo app/models y app/routes, no es un volcado
-- automatico de epran-qa a epran):
--
--   1) CHAT_MENSAJES_CLIENTE.id_conversacion / foto_adjunta
--      SOLO existen en epran-qa. app/models/chat.py::ChatMensaje ya las
--      mapea (conversacion_id -> id_conversacion FK a CHAT_CONVERSACIONES,
--      foto_adjunta NVARCHAR(500)) -- si v2 apuntara a epran hoy, cualquier
--      insert/select de mensajes con foto adjunta o de conversaciones
--      rompe. CHAT_CONVERSACIONES ya existe en epran (se creo en la
--      migracion de las 22 tablas de esta sesion), asi que el FK es valido.
--
--   2) SESIONES_ACTIVAS.session_id: NVARCHAR(200) NOT NULL en epran vs
--      VARCHAR(1000) en epran-qa. app/models/sesion.py::SesionActiva.
--      session_token mapea a String(1000) -- los tokens de sesion (JWT)
--      normalmente superan los 200 caracteres, con 200 se trunca o falla el
--      insert. Se ensancha a VARCHAR(1000) (el contenido es ASCII, no hace
--      falta NVARCHAR) y se mantiene NOT NULL (la app siempre lo manda).
--
--   3) VENDEDOR_VISITAS.id_punto_interes: VARCHAR(50) en epran vs
--      VARCHAR(100) en epran-qa. create_vendedor_tables.py (script fuente
--      de la tabla) la define como VARCHAR(100) -- identificadores de PDV
--      mas largos que 50 caracteres se truncarian silenciosamente.
--
--   4) RUTAS_ACTIVADAS.motivo_no_activacion: VARCHAR(50) en epran vs
--      NVARCHAR(500) en epran-qa. app/routes/auditor_campo.py::no_activar_ruta
--      inserta un texto libre (`razon`) sin limite de longitud en el
--      backend -- con VARCHAR(50) cualquier razon un poco larga falla el
--      insert (truncation error).
--
--   5) VENDEDOR_JORNADAS.estado: VARCHAR(20) en epran vs VARCHAR(50) en
--      epran-qa. Se ensancha por consistencia con el script fuente
--      (create_vendedor_tables.py) -- sin evidencia de que ya se haya roto,
--      pero ambos deben coincidir.
--
-- NO incluido aqui (falta info o no corresponde a esta direccion, ver
-- mensaje al final del chat):
--   - RUTAS_ACTIVADAS.id_ruta (nullable distinto): requiere confirmar que
--     no haya filas con id_ruta NULL en epran antes de poner NOT NULL.
--   - VENDEDOR_VISITAS.monto (DECIMAL en epran vs FLOAT en epran-qa): el
--     lado de PRODUCCION es el mas correcto (decimal evita error de
--     redondeo en montos) -- si se homogeniza, es epran-qa el que deberia
--     cambiar a DECIMAL(18,2), no al reves. No se toca en este script.
--   - FOTOS_TOTALES (motivo_rechazo, veces_reemplazada, etc.) y
--     PRECIOS_COMPETENCIA: cero referencias en el codigo de Nexus2DI v2
--     (backend/app) -- probablemente tablas/columnas de otro proceso, no
--     de esta app. No se tocan sin confirmar con el usuario.
--
-- Correr con: sqlcmd -S 172.174.41.110 -U <usuario> -P <password> -C -d epran -i fix_epran_prod_schema_gaps.sql

SET NOCOUNT ON;

-- 1) CHAT_MENSAJES_CLIENTE.id_conversacion + foto_adjunta
IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'CHAT_MENSAJES_CLIENTE' AND COLUMN_NAME = 'id_conversacion')
BEGIN
    ALTER TABLE CHAT_MENSAJES_CLIENTE ADD id_conversacion INT NULL;
    ALTER TABLE CHAT_MENSAJES_CLIENTE ADD CONSTRAINT FK_CHAT_MENSAJES_CLIENTE_conversacion
        FOREIGN KEY (id_conversacion) REFERENCES CHAT_CONVERSACIONES(id_conversacion);
    PRINT 'Agregada CHAT_MENSAJES_CLIENTE.id_conversacion (+ FK)';
END
ELSE PRINT 'CHAT_MENSAJES_CLIENTE.id_conversacion ya existia, no se toco';

IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = 'CHAT_MENSAJES_CLIENTE' AND COLUMN_NAME = 'foto_adjunta')
BEGIN
    ALTER TABLE CHAT_MENSAJES_CLIENTE ADD foto_adjunta NVARCHAR(500) NULL;
    PRINT 'Agregada CHAT_MENSAJES_CLIENTE.foto_adjunta';
END
ELSE PRINT 'CHAT_MENSAJES_CLIENTE.foto_adjunta ya existia, no se toco';
GO

-- 2) SESIONES_ACTIVAS.session_id: ensanchar a VARCHAR(1000).
-- Tiene un indice (IX_SESIONES_SESSION_ID, probablemente UNIQUE por el
-- unique=True del modelo) que depende de la columna -- SQL Server no deja
-- alterar una columna indexada directamente. Se guarda si el indice era
-- unique, se elimina, se altera la columna, y se recrea igual que estaba.
DECLARE @is_unique BIT, @index_exists BIT = 0;
SELECT @is_unique = is_unique, @index_exists = 1
FROM sys.indexes
WHERE object_id = OBJECT_ID('SESIONES_ACTIVAS') AND name = 'IX_SESIONES_SESSION_ID';

IF @index_exists = 1
BEGIN
    DROP INDEX IX_SESIONES_SESSION_ID ON SESIONES_ACTIVAS;
    PRINT 'Indice IX_SESIONES_SESSION_ID eliminado temporalmente';
END

ALTER TABLE SESIONES_ACTIVAS ALTER COLUMN session_id VARCHAR(1000) NOT NULL;
PRINT 'SESIONES_ACTIVAS.session_id ensanchado a VARCHAR(1000)';

IF @index_exists = 1
BEGIN
    IF @is_unique = 1
        CREATE UNIQUE NONCLUSTERED INDEX IX_SESIONES_SESSION_ID ON SESIONES_ACTIVAS(session_id);
    ELSE
        CREATE NONCLUSTERED INDEX IX_SESIONES_SESSION_ID ON SESIONES_ACTIVAS(session_id);
    PRINT 'Indice IX_SESIONES_SESSION_ID recreado';
END
GO

-- 3) VENDEDOR_VISITAS.id_punto_interes: ensanchar a VARCHAR(100)
ALTER TABLE VENDEDOR_VISITAS ALTER COLUMN id_punto_interes VARCHAR(100) NOT NULL;
PRINT 'VENDEDOR_VISITAS.id_punto_interes ensanchado a VARCHAR(100)';
GO

-- 4) RUTAS_ACTIVADAS.motivo_no_activacion: ensanchar a NVARCHAR(500)
ALTER TABLE RUTAS_ACTIVADAS ALTER COLUMN motivo_no_activacion NVARCHAR(500) NULL;
PRINT 'RUTAS_ACTIVADAS.motivo_no_activacion ensanchado a NVARCHAR(500)';
GO

-- 5) VENDEDOR_JORNADAS.estado: ensanchar a VARCHAR(50)
ALTER TABLE VENDEDOR_JORNADAS ALTER COLUMN estado VARCHAR(50) NOT NULL;
PRINT 'VENDEDOR_JORNADAS.estado ensanchado a VARCHAR(50)';
GO
