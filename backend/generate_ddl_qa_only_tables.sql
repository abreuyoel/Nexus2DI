-- Genera (via PRINT, no ejecuta nada) el DDL de CREATE TABLE + FOREIGN KEYs
-- para las 22 tablas que existen en epran-qa y NO en epran (produccion),
-- introspectando el esquema REAL de epran-qa (sys.columns/sys.types/etc.)
-- en vez de adivinarlo a mano.
--
-- Correr esto CONTRA epran-qa (no hace ningun cambio, solo lee catalogo):
--   sqlcmd -S 172.174.41.110 -d epran-qa -U <usuario> -P <password> -C -i generate_ddl_qa_only_tables.sql -o ddl_para_produccion.sql
--
-- El archivo de salida (ddl_para_produccion.sql) es el que se REVISA y
-- luego se corre CONTRA epran (produccion) como paso separado.
--
-- Cobertura: columnas (tipo, longitud/precision/escala, IDENTITY, NULL/NOT
-- NULL, DEFAULT), PRIMARY KEY, y FOREIGN KEYs (en un segundo bloque, para
-- que el orden de creacion entre estas 22 tablas no importe).
-- NO cubre: constraints UNIQUE fuera de la PK, CHECK constraints, indices
-- no-PK, columnas calculadas, triggers. Si alguna de estas 22 tablas tiene
-- algo de eso, revisar con la funcion "Generate Scripts" de SSMS/Azure
-- Data Studio antes de correr en produccion.

SET NOCOUNT ON;

DECLARE @tablas TABLE (nombre sysname);
INSERT INTO @tablas (nombre) VALUES
    ('AUDIT_LOG'), ('CAT_ALCANCE'), ('CAT_CANAL_VENTA'), ('CAT_CIUDADES'),
    ('CAT_DEPARTAMENTOS'), ('CAT_ESTADOS'), ('CAT_SUBTIPO_NEGOCIO'), ('CAT_TIPO_NEGOCIO'),
    ('CATEGORIAS_OLD'), ('CHAT_CONVERSACIONES'), ('CHAT_MENSAJE_LECTURAS'), ('CHAT_PARTICIPANTES'),
    ('CLIENTES_RUTAS'), ('CUADRANTES'), ('FOTOS_MERCADERISTA'), ('FOTOS_RAZONES_RECHAZOS'),
    ('FRECUENCIAS_PDVS_CLIENTE'), ('HORAS_PROMEDIO_EJECUCION'), ('MODULOS'), ('SERVICIOS'),
    ('SUPERVISORES_CLIENTES'), ('usuario_permisos');

PRINT '-- ═══════════════════════════════════════════════════════════════════════';
PRINT '-- DDL generado desde epran-qa el ' + CONVERT(VARCHAR(30), GETDATE(), 120);
PRINT '-- REVISAR ANTES DE CORRER CONTRA epran (produccion).';
PRINT '-- Bloque 1: CREATE TABLE (columnas + PK, sin FKs)';
PRINT '-- Bloque 2: ALTER TABLE ... ADD CONSTRAINT FK (al final, cuando las 22 ya existen)';
PRINT '-- ═══════════════════════════════════════════════════════════════════════';
PRINT '';

DECLARE @tabla sysname;
DECLARE cur CURSOR FAST_FORWARD FOR SELECT nombre FROM @tablas ORDER BY nombre;
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

    DECLARE @sql NVARCHAR(MAX) = 'CREATE TABLE dbo.' + QUOTENAME(@tabla) + ' (' + CHAR(10);
    DECLARE @cols NVARCHAR(MAX) = '';

    -- STRING_AGG (no el truco de "SELECT @v = @v + expr", que no está
    -- garantizado por SQL Server y se rompe si el optimizador elige un
    -- plan en paralelo -- se quedaba con una sola fila en vez de todas).
    SELECT @cols = STRING_AGG(
        CAST(
            '    ' + QUOTENAME(c.name) + ' ' +
            CASE
                WHEN ty.name IN ('varchar', 'char', 'varbinary', 'binary')
                    THEN ty.name + '(' + CASE WHEN c.max_length = -1 THEN 'MAX' ELSE CAST(c.max_length AS VARCHAR(10)) END + ')'
                WHEN ty.name IN ('nvarchar', 'nchar')
                    THEN ty.name + '(' + CASE WHEN c.max_length = -1 THEN 'MAX' ELSE CAST(c.max_length / 2 AS VARCHAR(10)) END + ')'
                WHEN ty.name IN ('decimal', 'numeric')
                    THEN ty.name + '(' + CAST(c.precision AS VARCHAR(10)) + ',' + CAST(c.scale AS VARCHAR(10)) + ')'
                WHEN ty.name IN ('datetime2', 'datetimeoffset', 'time')
                    THEN ty.name + '(' + CAST(c.scale AS VARCHAR(10)) + ')'
                WHEN ty.name = 'float' AND c.precision <> 53
                    THEN ty.name + '(' + CAST(c.precision AS VARCHAR(10)) + ')'
                ELSE ty.name
            END
            + CASE WHEN c.is_identity = 1
                   THEN ' IDENTITY(' + CAST(ISNULL(ic.seed_value, 1) AS VARCHAR(20)) + ',' + CAST(ISNULL(ic.increment_value, 1) AS VARCHAR(20)) + ')'
                   ELSE '' END
            + CASE WHEN c.is_nullable = 0 THEN ' NOT NULL' ELSE ' NULL' END
            + CASE WHEN dc.definition IS NOT NULL THEN ' DEFAULT ' + dc.definition ELSE '' END
        AS NVARCHAR(MAX)),
        ',' + CHAR(10)
    ) WITHIN GROUP (ORDER BY c.column_id) + ',' + CHAR(10)
    FROM sys.columns c
    JOIN sys.types ty ON ty.user_type_id = c.user_type_id
    LEFT JOIN sys.identity_columns ic ON ic.object_id = c.object_id AND ic.column_id = c.column_id
    LEFT JOIN sys.default_constraints dc ON dc.parent_object_id = c.object_id AND dc.parent_column_id = c.column_id
    WHERE c.object_id = OBJECT_ID('dbo.' + @tabla);

    SET @sql = @sql + @cols;

    DECLARE @pkcols NVARCHAR(MAX) = NULL;
    SELECT @pkcols = STRING_AGG(CAST(QUOTENAME(col.name) AS NVARCHAR(MAX)), ', ') WITHIN GROUP (ORDER BY ic.key_ordinal)
    FROM sys.key_constraints kc
    JOIN sys.index_columns ic ON ic.object_id = kc.parent_object_id AND ic.index_id = kc.unique_index_id
    JOIN sys.columns col ON col.object_id = ic.object_id AND col.column_id = ic.column_id
    WHERE kc.parent_object_id = OBJECT_ID('dbo.' + @tabla) AND kc.type = 'PK';

    IF @pkcols IS NOT NULL
        SET @sql = @sql + '    CONSTRAINT PK_' + @tabla + ' PRIMARY KEY CLUSTERED (' + @pkcols + ')' + CHAR(10);
    ELSE
        SET @sql = LEFT(@sql, LEN(@sql) - 2) + CHAR(10); -- quita la ultima coma+LF si no hay PK

    SET @sql = @sql + ');';
    PRINT @sql;
    PRINT 'GO';
    PRINT '';

    FETCH NEXT FROM cur INTO @tabla;
END
CLOSE cur;
DEALLOCATE cur;

PRINT '-- ═══════════════════════════════════════════════════════════════════════';
PRINT '-- Bloque 2: Foreign Keys de estas 22 tablas';
PRINT '-- ═══════════════════════════════════════════════════════════════════════';
PRINT '';

DECLARE @fk_ddl TABLE (id INT IDENTITY(1,1), ddl NVARCHAR(MAX));
INSERT INTO @fk_ddl (ddl)
SELECT
    'ALTER TABLE dbo.' + QUOTENAME(tp.name) + ' ADD CONSTRAINT ' + QUOTENAME(fk.name) +
    ' FOREIGN KEY (' + STRING_AGG(CAST(QUOTENAME(cp.name) AS NVARCHAR(MAX)), ', ') WITHIN GROUP (ORDER BY fkc.constraint_column_id) + ')' +
    ' REFERENCES dbo.' + QUOTENAME(tr.name) + ' (' + STRING_AGG(CAST(QUOTENAME(cr.name) AS NVARCHAR(MAX)), ', ') WITHIN GROUP (ORDER BY fkc.constraint_column_id) + ');'
FROM sys.foreign_keys fk
JOIN sys.tables tp ON tp.object_id = fk.parent_object_id
JOIN sys.tables tr ON tr.object_id = fk.referenced_object_id
JOIN sys.foreign_key_columns fkc ON fkc.constraint_object_id = fk.object_id
JOIN sys.columns cp ON cp.object_id = fkc.parent_object_id AND cp.column_id = fkc.parent_column_id
JOIN sys.columns cr ON cr.object_id = fkc.referenced_object_id AND cr.column_id = fkc.referenced_column_id
WHERE tp.name IN (SELECT nombre FROM @tablas)
GROUP BY tp.name, fk.name, tr.name;

DECLARE @fk_ddl_text NVARCHAR(MAX);
DECLARE fkcur CURSOR FAST_FORWARD FOR SELECT ddl FROM @fk_ddl ORDER BY id;
OPEN fkcur;
FETCH NEXT FROM fkcur INTO @fk_ddl_text;
IF @@FETCH_STATUS <> 0
    PRINT '-- (Ninguna de estas 22 tablas tiene FKs declaradas en epran-qa.)';
WHILE @@FETCH_STATUS = 0
BEGIN
    PRINT @fk_ddl_text;
    PRINT 'GO';
    FETCH NEXT FROM fkcur INTO @fk_ddl_text;
END
CLOSE fkcur;
DEALLOCATE fkcur;
