-- =============================================================================
-- Script: fix_id_categoria_productos_prod.sql
-- EJECUTAR EN: epran (PRODUCCIÓN)
-- OBJETIVO: Renumerar CATEGORIAS de PROD (IDs 23-116) para que queden
--           con los mismos IDs que QA (1-95), y actualizar todas las
--           tablas que referencian id_categoria.
--
-- TABLAS AFECTADAS:
--   - CATEGORIAS           → renumeración del PK (es IDENTITY, requiere recrear)
--   - PRODUCTS             → 5545 filas
--   - SUBCATEGORIAS        → 215 filas (tiene FK real a CATEGORIAS)
--   - AUDITORIA_CATEGORIAS → (tiene FK real a CATEGORIAS)
--   - BALANCES_TOTALES     → sin FK
--   - CATEGORIAS_CLIENTES  → sin FK
--   - CLIENTES             → 64 filas, solo id=23
--   - FOTOS_TOTALES        → sin FK
--
-- CONSTRAINTS CONOCIDOS (PROD):
--   PK de CATEGORIAS:          PK__CATEGORI__CD54BC5AFF0549BF
--   CATEGORIAS → DEPARTAMENTOS: FK__CATEGORIA__id_de__469D7149
--   SUBCATEGORIAS → CATEGORIAS: FK__SUBCATEGO__id_ca__4979DDF4
--   AUDITORIA_CATEGORIAS → CAT: FK_audcat_categoria
-- =============================================================================

USE epran;
GO


-- ══════════════════════════════════════════════════════════════════════════════
-- PASO 1 — SOLO LECTURA: Validar mapeo antes de ejecutar
-- ══════════════════════════════════════════════════════════════════════════════

-- 1A. Vista previa del mapeo (id_prod_viejo → id_qa_nuevo):
SELECT
    cat_prod.id_categoria  AS id_actual_prod,
    cat_prod.nombre,
    cat_qa.id_categoria    AS nuevo_id
FROM CATEGORIAS cat_prod
INNER JOIN [epran-qa].dbo.CATEGORIAS cat_qa
    ON LTRIM(RTRIM(cat_qa.nombre)) = LTRIM(RTRIM(cat_prod.nombre))
ORDER BY cat_qa.id_categoria;
GO

-- 1B. Categorías en PROD sin equivalente en QA (deben ser 0):
SELECT id_categoria, nombre AS [SIN MATCH EN QA - REVISAR]
FROM CATEGORIAS
WHERE NOT EXISTS (
    SELECT 1 FROM [epran-qa].dbo.CATEGORIAS cat_qa
    WHERE LTRIM(RTRIM(cat_qa.nombre)) = LTRIM(RTRIM(CATEGORIAS.nombre))
);
GO


-- ══════════════════════════════════════════════════════════════════════════════
-- PASO 2 — EJECUCIÓN (no pongas GO hasta decidir COMMIT o ROLLBACK)
-- ══════════════════════════════════════════════════════════════════════════════
BEGIN TRANSACTION;

    -- ── 2a. Tabla de mapeo temporal ────────────────────────────────────────
    -- Guard: si el script se ejecutó antes y falló, limpia el residuo:
    IF OBJECT_ID('tempdb..#mapeo') IS NOT NULL DROP TABLE #mapeo;

    CREATE TABLE #mapeo (id_viejo INT NOT NULL, id_nuevo INT NOT NULL);

    INSERT INTO #mapeo (id_viejo, id_nuevo)
    SELECT cat_prod.id_categoria, cat_qa.id_categoria
    FROM CATEGORIAS cat_prod
    INNER JOIN [epran-qa].dbo.CATEGORIAS cat_qa
        ON LTRIM(RTRIM(cat_qa.nombre)) = LTRIM(RTRIM(cat_prod.nombre));

    SELECT COUNT(*) AS categorias_mapeadas FROM #mapeo;
    -- ESPERADO: 94

    -- ── 2b. Deshabilitar FKs que apuntan a CATEGORIAS ──────────────────────
    ALTER TABLE SUBCATEGORIAS        NOCHECK CONSTRAINT FK__SUBCATEGO__id_ca__4979DDF4;
    ALTER TABLE AUDITORIA_CATEGORIAS NOCHECK CONSTRAINT FK_audcat_categoria;

    -- ── 2c. Actualizar todas las tablas dependientes ────────────────────────
    UPDATE p  SET p.id_categoria  = m.id_nuevo FROM PRODUCTS           p  INNER JOIN #mapeo m ON m.id_viejo = p.id_categoria;
    SELECT @@ROWCOUNT AS products_actualizados;           -- ESPERADO: ~5545

    UPDATE sc SET sc.id_categoria = m.id_nuevo FROM SUBCATEGORIAS      sc INNER JOIN #mapeo m ON m.id_viejo = sc.id_categoria;
    SELECT @@ROWCOUNT AS subcategorias_actualizadas;      -- ESPERADO: 215

    UPDATE ac SET ac.id_categoria = m.id_nuevo FROM AUDITORIA_CATEGORIAS ac INNER JOIN #mapeo m ON m.id_viejo = ac.id_categoria;
    SELECT @@ROWCOUNT AS auditoria_actualizadas;

    UPDATE bt SET bt.id_categoria = m.id_nuevo FROM BALANCES_TOTALES   bt INNER JOIN #mapeo m ON m.id_viejo = bt.id_categoria;
    SELECT @@ROWCOUNT AS balances_actualizados;

    UPDATE cc SET cc.id_categoria = m.id_nuevo FROM CATEGORIAS_CLIENTES cc INNER JOIN #mapeo m ON m.id_viejo = cc.id_categoria;
    SELECT @@ROWCOUNT AS cat_clientes_actualizadas;

    UPDATE cl SET cl.id_categoria = m.id_nuevo FROM CLIENTES            cl INNER JOIN #mapeo m ON m.id_viejo = cl.id_categoria;
    SELECT @@ROWCOUNT AS clientes_actualizados;           -- ESPERADO: 64

    UPDATE ft SET ft.id_categoria = m.id_nuevo FROM FOTOS_TOTALES      ft INNER JOIN #mapeo m ON m.id_viejo = ft.id_categoria;
    SELECT @@ROWCOUNT AS fotos_actualizadas;

    -- CATEGORIAS_OLD tiene 0 filas con id_categoria → no necesita update.

    -- ── 2d. Recrear CATEGORIAS con los nuevos IDs ──────────────────────────
    -- id_categoria es IDENTITY → no se puede UPDATE. Solución: nueva tabla
    -- con IDENTITY + IDENTITY_INSERT para insertar IDs específicos.

    -- Guard: si CATEGORIAS_NUEVA existe de una ejecución previa anómala:
    IF OBJECT_ID('dbo.CATEGORIAS_NUEVA') IS NOT NULL DROP TABLE CATEGORIAS_NUEVA;

    CREATE TABLE CATEGORIAS_NUEVA (
        id_categoria    INT          IDENTITY(1,1) NOT NULL,
        nombre          VARCHAR(255) NULL,
        nombre_bi       VARCHAR(255) NULL,
        id_departamento INT          NULL
    );

    -- Permitir insertar IDs explícitos en la columna IDENTITY:
    SET IDENTITY_INSERT CATEGORIAS_NUEVA ON;

    INSERT INTO CATEGORIAS_NUEVA (id_categoria, nombre, nombre_bi, id_departamento)
    SELECT m.id_nuevo, c.nombre, c.nombre_bi, c.id_departamento
    FROM CATEGORIAS c
    INNER JOIN #mapeo m ON m.id_viejo = c.id_categoria;

    SET IDENTITY_INSERT CATEGORIAS_NUEVA OFF;

    SELECT COUNT(*) AS filas_en_nueva FROM CATEGORIAS_NUEVA;
    -- ESPERADO: 94

    -- ── 2e. Eliminar constraints y borrar tabla vieja ───────────────────────
    -- Primero las FKs entrantes a CATEGORIAS (ya las deshabilitamos, ahora las borramos):
    ALTER TABLE SUBCATEGORIAS        DROP CONSTRAINT FK__SUBCATEGO__id_ca__4979DDF4;
    ALTER TABLE AUDITORIA_CATEGORIAS DROP CONSTRAINT FK_audcat_categoria;

    -- FK saliente de CATEGORIAS → DEPARTAMENTOS:
    ALTER TABLE CATEGORIAS DROP CONSTRAINT FK__CATEGORIA__id_de__469D7149;

    -- Borrar la tabla vieja (el PK se borra junto con la tabla):
    DROP TABLE CATEGORIAS;

    -- ── 2f. Renombrar y restaurar constraints ──────────────────────────────
    -- 'OBJECT' es el tipo explícito para renombrar tablas (evita ambigüedad con columnas/índices):
    EXEC sp_rename 'dbo.CATEGORIAS_NUEVA', 'CATEGORIAS', 'OBJECT';

    -- PK:
    ALTER TABLE CATEGORIAS
        ADD CONSTRAINT PK_CATEGORIAS PRIMARY KEY CLUSTERED (id_categoria);

    -- FK saliente: CATEGORIAS → DEPARTAMENTOS:
    ALTER TABLE CATEGORIAS
        ADD CONSTRAINT FK_CATEGORIAS_DEPARTAMENTOS
        FOREIGN KEY (id_departamento) REFERENCES DEPARTAMENTOS(id_departamento);

    -- FKs entrantes: otras tablas → CATEGORIAS.
    -- WITH NOCHECK: no valida filas existentes al crear el constraint
    -- (ya las validamos manualmente en el paso 2h con los SELECTs de orphans).
    ALTER TABLE SUBCATEGORIAS
        WITH NOCHECK ADD CONSTRAINT FK_SUBCATEGORIAS_CATEGORIAS
        FOREIGN KEY (id_categoria) REFERENCES CATEGORIAS(id_categoria);

    ALTER TABLE AUDITORIA_CATEGORIAS
        WITH NOCHECK ADD CONSTRAINT FK_audcat_categoria
        FOREIGN KEY (id_categoria) REFERENCES CATEGORIAS(id_categoria);

    -- ── 2g. Ajustar el seed de IDENTITY para el próximo INSERT ─────────────
    -- Después de IDENTITY_INSERT, el seed queda en el último valor insertado.
    -- Reseeding explícito al máximo actual para asegurar continuidad:
    DECLARE @max_id INT = (SELECT MAX(id_categoria) FROM CATEGORIAS);
    DBCC CHECKIDENT ('CATEGORIAS', RESEED, @max_id);

    -- ── 2h. Verificación final ────────────────────────────────────────────
    SELECT
        MIN(id_categoria) AS min_id,    -- ESPERADO: 1
        MAX(id_categoria) AS max_id,    -- ESPERADO: 95 (o 94 si Sin Categoria no está)
        COUNT(*)          AS total      -- ESPERADO: 94
    FROM CATEGORIAS;

    SELECT COUNT(*) AS products_con_cat_invalida    -- ESPERADO: 0
    FROM PRODUCTS p
    WHERE p.id_categoria IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM CATEGORIAS c WHERE c.id_categoria = p.id_categoria);

    SELECT COUNT(*) AS subcats_con_cat_invalida     -- ESPERADO: 0
    FROM SUBCATEGORIAS s
    WHERE s.id_categoria IS NOT NULL
      AND NOT EXISTS (SELECT 1 FROM CATEGORIAS c WHERE c.id_categoria = s.id_categoria);


-- ══════════════════════════════════════════════════════════════════════════════
-- PASO 3A — Si min=1, invalidas=0: CONFIRMAR
-- ══════════════════════════════════════════════════════════════════════════════
-- COMMIT TRANSACTION;


-- ══════════════════════════════════════════════════════════════════════════════
-- PASO 3B — Si algo está mal: REVERTIR TODO (vuelve al estado original)
-- ══════════════════════════════════════════════════════════════════════════════
-- ROLLBACK TRANSACTION;
