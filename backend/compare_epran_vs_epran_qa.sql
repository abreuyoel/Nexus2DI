-- Comparacion de esquema entre epran (produccion) y epran-qa, en el mismo
-- servidor (172.174.41.110). Asume que el login usado tiene permisos de
-- lectura sobre INFORMATION_SCHEMA en ambas bases.
--
-- Diagnostico puntual para planear el paso de Nexus2DI de epran-qa a
-- epran (produccion) -- no es parte del esquema de la app, no se ejecuta
-- como parte de ningun deploy.
--
-- Produce 3 resultados (bloques) por separado:
--   1) Tablas que existen en epran pero NO en epran-qa
--   2) Tablas que existen en epran-qa pero NO en epran
--   3) Para las tablas que existen en AMBAS: columnas que solo estan en una,
--      o que existen en las dos pero con tipo de dato / longitud / nullable
--      distintos.
--
-- Correr con: sqlcmd -S 172.174.41.110 -U <usuario> -P <password> -C -i compare_epran_vs_epran_qa.sql -o resultado.txt
-- (el -o vuelca todo a un archivo de texto, mas facil de revisar que la consola.
--  el -C es necesario con ODBC Driver 18 por el certificado autofirmado.)

SET NOCOUNT ON;

PRINT '=== 1) TABLAS SOLO EN epran (produccion) ===';
SELECT
    CAST(t1.TABLE_SCHEMA AS VARCHAR(8))  AS esquema,
    CAST(t1.TABLE_NAME   AS VARCHAR(45)) AS tabla
FROM epran.INFORMATION_SCHEMA.TABLES t1
WHERE t1.TABLE_TYPE = 'BASE TABLE'
  AND NOT EXISTS (
      SELECT 1 FROM [epran-qa].INFORMATION_SCHEMA.TABLES t2
      WHERE t2.TABLE_TYPE = 'BASE TABLE'
        AND t2.TABLE_SCHEMA = t1.TABLE_SCHEMA AND t2.TABLE_NAME = t1.TABLE_NAME
  )
ORDER BY t1.TABLE_SCHEMA, t1.TABLE_NAME;

PRINT '=== 2) TABLAS SOLO EN epran-qa ===';
SELECT
    CAST(t2.TABLE_SCHEMA AS VARCHAR(8))  AS esquema,
    CAST(t2.TABLE_NAME   AS VARCHAR(45)) AS tabla
FROM [epran-qa].INFORMATION_SCHEMA.TABLES t2
WHERE t2.TABLE_TYPE = 'BASE TABLE'
  AND NOT EXISTS (
      SELECT 1 FROM epran.INFORMATION_SCHEMA.TABLES t1
      WHERE t1.TABLE_TYPE = 'BASE TABLE'
        AND t1.TABLE_SCHEMA = t2.TABLE_SCHEMA AND t1.TABLE_NAME = t2.TABLE_NAME
  )
ORDER BY t2.TABLE_SCHEMA, t2.TABLE_NAME;

PRINT '=== 3) DIFERENCIAS DE COLUMNAS EN TABLAS QUE EXISTEN EN AMBAS ===';
;WITH cols_prod AS (
    SELECT c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE,
           c.CHARACTER_MAXIMUM_LENGTH, c.NUMERIC_PRECISION, c.NUMERIC_SCALE, c.IS_NULLABLE
    FROM epran.INFORMATION_SCHEMA.COLUMNS c
    JOIN epran.INFORMATION_SCHEMA.TABLES t
      ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_TYPE = 'BASE TABLE'
),
cols_qa AS (
    SELECT c.TABLE_SCHEMA, c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE,
           c.CHARACTER_MAXIMUM_LENGTH, c.NUMERIC_PRECISION, c.NUMERIC_SCALE, c.IS_NULLABLE
    FROM [epran-qa].INFORMATION_SCHEMA.COLUMNS c
    JOIN [epran-qa].INFORMATION_SCHEMA.TABLES t
      ON t.TABLE_SCHEMA = c.TABLE_SCHEMA AND t.TABLE_NAME = c.TABLE_NAME AND t.TABLE_TYPE = 'BASE TABLE'
),
tablas_comunes AS (
    SELECT DISTINCT p.TABLE_SCHEMA, p.TABLE_NAME
    FROM cols_prod p
    JOIN cols_qa q ON q.TABLE_SCHEMA = p.TABLE_SCHEMA AND q.TABLE_NAME = p.TABLE_NAME
),
diffs AS (
    SELECT 'SOLO_EN_epran' AS diferencia,
           p.TABLE_SCHEMA, p.TABLE_NAME, p.COLUMN_NAME,
           p.DATA_TYPE AS tipo_epran, CAST(NULL AS NVARCHAR(100)) AS tipo_epran_qa
    FROM cols_prod p
    JOIN tablas_comunes tc ON tc.TABLE_SCHEMA = p.TABLE_SCHEMA AND tc.TABLE_NAME = p.TABLE_NAME
    WHERE NOT EXISTS (
        SELECT 1 FROM cols_qa q
        WHERE q.TABLE_SCHEMA = p.TABLE_SCHEMA AND q.TABLE_NAME = p.TABLE_NAME AND q.COLUMN_NAME = p.COLUMN_NAME
    )

    UNION ALL

    SELECT 'SOLO_EN_epran-qa' AS diferencia,
           q.TABLE_SCHEMA, q.TABLE_NAME, q.COLUMN_NAME,
           CAST(NULL AS NVARCHAR(100)) AS tipo_epran, q.DATA_TYPE AS tipo_epran_qa
    FROM cols_qa q
    JOIN tablas_comunes tc ON tc.TABLE_SCHEMA = q.TABLE_SCHEMA AND tc.TABLE_NAME = q.TABLE_NAME
    WHERE NOT EXISTS (
        SELECT 1 FROM cols_prod p
        WHERE p.TABLE_SCHEMA = q.TABLE_SCHEMA AND p.TABLE_NAME = q.TABLE_NAME AND p.COLUMN_NAME = q.COLUMN_NAME
    )

    UNION ALL

    SELECT 'TIPO_O_NULLABLE_DISTINTO' AS diferencia,
           p.TABLE_SCHEMA, p.TABLE_NAME, p.COLUMN_NAME,
           p.DATA_TYPE
             + ISNULL('(' + CAST(p.CHARACTER_MAXIMUM_LENGTH AS VARCHAR(10)) + ')', '')
             + ISNULL('[' + CAST(p.NUMERIC_PRECISION AS VARCHAR(10)) + ',' + CAST(p.NUMERIC_SCALE AS VARCHAR(10)) + ']', '')
             + ' NULL=' + p.IS_NULLABLE AS tipo_epran,
           q.DATA_TYPE
             + ISNULL('(' + CAST(q.CHARACTER_MAXIMUM_LENGTH AS VARCHAR(10)) + ')', '')
             + ISNULL('[' + CAST(q.NUMERIC_PRECISION AS VARCHAR(10)) + ',' + CAST(q.NUMERIC_SCALE AS VARCHAR(10)) + ']', '')
             + ' NULL=' + q.IS_NULLABLE AS tipo_epran_qa
    FROM cols_prod p
    JOIN cols_qa q ON q.TABLE_SCHEMA = p.TABLE_SCHEMA AND q.TABLE_NAME = p.TABLE_NAME AND q.COLUMN_NAME = p.COLUMN_NAME
    WHERE p.DATA_TYPE <> q.DATA_TYPE
       OR ISNULL(p.CHARACTER_MAXIMUM_LENGTH, -1) <> ISNULL(q.CHARACTER_MAXIMUM_LENGTH, -1)
       OR ISNULL(CAST(p.NUMERIC_PRECISION AS INT), -1) <> ISNULL(CAST(q.NUMERIC_PRECISION AS INT), -1)
       OR ISNULL(CAST(p.NUMERIC_SCALE AS INT), -1) <> ISNULL(CAST(q.NUMERIC_SCALE AS INT), -1)
       OR p.IS_NULLABLE <> q.IS_NULLABLE
)
SELECT
    CAST(diferencia   AS VARCHAR(26)) AS diferencia,
    CAST(TABLE_NAME    AS VARCHAR(30)) AS tabla,
    CAST(COLUMN_NAME   AS VARCHAR(28)) AS columna,
    CAST(tipo_epran    AS VARCHAR(28)) AS tipo_epran,
    CAST(tipo_epran_qa AS VARCHAR(28)) AS tipo_epran_qa
FROM diffs
ORDER BY diferencia, TABLE_NAME, COLUMN_NAME;
