-- Genera (via PRINT, no ejecuta nada por si mismo) los INSERT para copiar
-- TODAS las filas de los 10 catalogos de epran-qa hacia epran (produccion).
-- Solo tiene sentido correr esto DESPUES de crear las tablas en epran con
-- generate_ddl_qa_only_tables.sql (deben existir y estar vacias).
--
-- Correr CONTRA epran-qa (introspecta columnas/PK, no escribe nada ahi):
--   sqlcmd -S 172.174.41.110 -d epran-qa -U <usuario> -P <password> -C -i generate_dml_catalogos_qa_to_prod.sql -o dml_catalogos_para_produccion.sql
--
-- El archivo de salida es el que se REVISA y luego se corre CONTRA epran
-- (produccion) como paso separado. Usa IDENTITY_INSERT para preservar los
-- mismos IDs que en epran-qa (importante: tablas nuevas como
-- HORAS_PROMEDIO_EJECUCION tienen FKs a CAT_TIPO_NEGOCIO.id por id, no por
-- nombre -- si los IDs no coincidieran entre ambientes esas referencias
-- quedarian rotas). Cada INSERT tiene guarda NOT EXISTS por PK, asi que es
-- re-corrible sin duplicar filas si se corre mas de una vez.

SET NOCOUNT ON;

-- Orden explicito (no alfabetico): CAT_DEPARTAMENTOS debe insertarse ANTES
-- que CAT_CIUDADES porque esta ultima tiene FK a CAT_DEPARTAMENTOS -- en
-- orden alfabetico CAT_CIUDADES queda primero y el INSERT fallaria por
-- violacion de FK (los departamentos todavia no existirian en destino).
DECLARE @tablas TABLE (orden INT IDENTITY(1,1), nombre sysname);
INSERT INTO @tablas (nombre) VALUES
    ('CAT_DEPARTAMENTOS'), ('CAT_CIUDADES'),
    ('CAT_ALCANCE'), ('CAT_CANAL_VENTA'),
    ('CAT_ESTADOS'), ('CAT_SUBTIPO_NEGOCIO'), ('CAT_TIPO_NEGOCIO'),
    ('MODULOS'), ('SERVICIOS'), ('CUADRANTES');

PRINT '-- ═══════════════════════════════════════════════════════════════════════';
PRINT '-- DML (copia de datos) generado desde epran-qa el ' + CONVERT(VARCHAR(30), GETDATE(), 120);
PRINT '-- REVISAR ANTES DE CORRER CONTRA epran (produccion).';
PRINT '-- Requiere que las 10 tablas ya existan en epran (correr primero';
PRINT '-- generate_ddl_qa_only_tables.sql y su resultado contra produccion).';
PRINT '-- ═══════════════════════════════════════════════════════════════════════';
PRINT '';

DECLARE @tabla sysname;
DECLARE cur CURSOR FAST_FORWARD FOR SELECT nombre FROM @tablas ORDER BY orden;
OPEN cur;
FETCH NEXT FROM cur INTO @tabla;

WHILE @@FETCH_STATUS = 0
BEGIN
    IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = @tabla)
    BEGIN
        PRINT '-- ADVERTENCIA: tabla ' + @tabla + ' no encontrada en epran-qa, se omite.';
        PRINT '';
        FETCH NEXT FROM cur INTO @tabla;
        CONTINUE;
    END

    DECLARE @collist NVARCHAR(MAX);
    SELECT @collist = STRING_AGG(CAST(QUOTENAME(c.name) AS NVARCHAR(MAX)), ', ') WITHIN GROUP (ORDER BY c.column_id)
    FROM sys.columns c
    WHERE c.object_id = OBJECT_ID('dbo.' + @tabla);

    DECLARE @has_identity BIT = CASE WHEN EXISTS (
        SELECT 1 FROM sys.identity_columns WHERE object_id = OBJECT_ID('dbo.' + @tabla)
    ) THEN 1 ELSE 0 END;

    -- "dst.[col1] = src.[col1] AND dst.[col2] = src.[col2] ..." listo para
    -- usar tal cual dentro del WHERE NOT EXISTS, sin post-procesar strings.
    DECLARE @pk_join NVARCHAR(MAX) = NULL;
    SELECT @pk_join = STRING_AGG(
        CAST('dst.' + QUOTENAME(col.name) + ' = src.' + QUOTENAME(col.name) AS NVARCHAR(MAX)),
        ' AND '
    ) WITHIN GROUP (ORDER BY ic.key_ordinal)
    FROM sys.key_constraints kc
    JOIN sys.index_columns ic ON ic.object_id = kc.parent_object_id AND ic.index_id = kc.unique_index_id
    JOIN sys.columns col ON col.object_id = ic.object_id AND col.column_id = ic.column_id
    WHERE kc.parent_object_id = OBJECT_ID('dbo.' + @tabla) AND kc.type = 'PK';

    DECLARE @sql NVARCHAR(MAX) = '';

    IF @has_identity = 1
        SET @sql = @sql + 'SET IDENTITY_INSERT epran.dbo.' + QUOTENAME(@tabla) + ' ON;' + CHAR(10);

    SET @sql = @sql
        + 'INSERT INTO epran.dbo.' + QUOTENAME(@tabla) + ' (' + @collist + ')' + CHAR(10)
        + 'SELECT ' + @collist + CHAR(10)
        + 'FROM [epran-qa].dbo.' + QUOTENAME(@tabla) + ' src';

    IF @pk_join IS NOT NULL
        SET @sql = @sql + CHAR(10)
            + 'WHERE NOT EXISTS (' + CHAR(10)
            + '    SELECT 1 FROM epran.dbo.' + QUOTENAME(@tabla) + ' dst WHERE ' + @pk_join + CHAR(10)
            + ');';
    ELSE
        SET @sql = @sql + ';';

    IF @has_identity = 1
        SET @sql = @sql + CHAR(10) + 'SET IDENTITY_INSERT epran.dbo.' + QUOTENAME(@tabla) + ' OFF;';

    PRINT @sql;
    PRINT 'GO';
    PRINT '';

    FETCH NEXT FROM cur INTO @tabla;
END
CLOSE cur;
DEALLOCATE cur;
