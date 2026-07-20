-- Genera (via PRINT, no ejecuta nada) el ALTER TABLE ... ADD <columna> para
-- las columnas de resultado.txt (bloque 3, filas SOLO_EN_x) que le faltan
-- al otro lado, introspectando el tipo REAL desde la base contra la que se
-- corre este script (no se adivina longitud/precision a mano).
--
-- Correr DOS VECES, una por cada base -- el script solo emite DDL para las
-- columnas que SI existen en la base contra la que corre:
--
--   1) Contra epran (produccion) -- RUTAS_ACTIVADAS.id_cliente /
--      identificador_punto_interes existen ahi y faltan en epran-qa:
--      sqlcmd -S 172.174.41.110 -d epran -U <usuario> -P <password> -C -i generate_ddl_missing_columns.sql -o ddl_para_epran_qa.sql
--      (revisar ddl_para_epran_qa.sql y correrlo contra epran-qa)
--
--   2) Contra epran-qa -- FOTOS_TOTALES/PRECIOS_COMPETENCIA existen ahi y
--      faltan en epran:
--      sqlcmd -S 172.174.41.110 -d epran-qa -U <usuario> -P <password> -C -i generate_ddl_missing_columns.sql -o ddl_para_epran.sql
--      (revisar ddl_para_epran.sql y correrlo contra epran)
--
-- Cada corrida solo genera DDL para las columnas que existen en ESA base
-- (las que faltan del otro lado se ignoran silenciosamente ahi).

SET NOCOUNT ON;

DECLARE @pares TABLE (tabla sysname, columna sysname);
INSERT INTO @pares (tabla, columna) VALUES
    ('RUTAS_ACTIVADAS', 'id_cliente'),
    ('RUTAS_ACTIVADAS', 'identificador_punto_interes'),
    ('FOTOS_TOTALES', 'motivo_rechazo'),
    ('FOTOS_TOTALES', 'ultima_fecha_rechazo_paso1'),
    ('FOTOS_TOTALES', 'ultimo_rechazo_por_paso1'),
    ('FOTOS_TOTALES', 'veces_reemplazada'),
    ('PRECIOS_COMPETENCIA', 'cadena_oficial'),
    ('PRECIOS_COMPETENCIA', 'capacidad_normalizada'),
    ('PRECIOS_COMPETENCIA', 'categoria_fisa'),
    ('PRECIOS_COMPETENCIA', 'establecimiento_oficial'),
    ('PRECIOS_COMPETENCIA', 'precio_limpio'),
    ('PRECIOS_COMPETENCIA', 'producto_normalizado'),
    ('PRECIOS_COMPETENCIA', 'region_oficial');

PRINT '-- DDL generado desde ' + DB_NAME() + ' el ' + CONVERT(VARCHAR(30), GETDATE(), 120);
PRINT '';

DECLARE @tabla sysname, @columna sysname;
DECLARE cur CURSOR FAST_FORWARD FOR SELECT tabla, columna FROM @pares ORDER BY tabla, columna;
OPEN cur;
FETCH NEXT FROM cur INTO @tabla, @columna;
WHILE @@FETCH_STATUS = 0
BEGIN
    IF EXISTS (SELECT 1 FROM sys.columns c WHERE c.object_id = OBJECT_ID('dbo.' + @tabla) AND c.name = @columna)
    BEGIN
        DECLARE @coldef NVARCHAR(200);
        SELECT @coldef =
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
            + CASE WHEN c.is_nullable = 0 THEN ' NOT NULL' ELSE ' NULL' END
        FROM sys.columns c
        JOIN sys.types ty ON ty.user_type_id = c.user_type_id
        WHERE c.object_id = OBJECT_ID('dbo.' + @tabla) AND c.name = @columna;

        PRINT 'IF NOT EXISTS (SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_NAME = ''' + @tabla + ''' AND COLUMN_NAME = ''' + @columna + ''')';
        PRINT '    ALTER TABLE dbo.' + QUOTENAME(@tabla) + ' ADD ' + QUOTENAME(@columna) + ' ' + @coldef + ';';
        PRINT 'GO';
        PRINT '';
    END
    FETCH NEXT FROM cur INTO @tabla, @columna;
END
CLOSE cur;
DEALLOCATE cur;
