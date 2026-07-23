-- =============================================================================
-- Script: verify_products_snowflake_prod_vs_qa.sql
-- EJECUTAR EN: epran (PRODUCCIÓN) — SOLO LECTURA
-- OBJETIVO: Verificar que todos los campos de referencia de PRODUCTS
--           coincidan entre QA y PROD por id_product:
--             - id_departamento  → DEPARTAMENTOS.nombre
--             - id_categoria     → CATEGORIAS.nombre
--             - id_subcategoria  → SUBCATEGORIAS.nombre
--             - id_marca         → MARCAS.nombre
--             - id_productora    → PRODUCTORAS.nombre
--             - id_presentacion  → PRESENTACIONES.nombre
-- =============================================================================

USE epran;
GO


-- ══════════════════════════════════════════════════════════════════════════════
-- RESUMEN EJECUTIVO: Rangos de IDs en dimensiones (QA vs PROD)
-- Esperado: todos iguales — si min/max/total difieren, hay problema.
-- ══════════════════════════════════════════════════════════════════════════════
SELECT
    'DEPARTAMENTOS'  AS tabla,
    (SELECT MIN(id_departamento) FROM DEPARTAMENTOS)      AS prod_min,
    (SELECT MAX(id_departamento) FROM DEPARTAMENTOS)      AS prod_max,
    (SELECT COUNT(*) FROM DEPARTAMENTOS)                  AS prod_total,
    (SELECT MIN(id_departamento) FROM [epran-qa].dbo.DEPARTAMENTOS) AS qa_min,
    (SELECT MAX(id_departamento) FROM [epran-qa].dbo.DEPARTAMENTOS) AS qa_max,
    (SELECT COUNT(*) FROM [epran-qa].dbo.DEPARTAMENTOS)             AS qa_total
UNION ALL SELECT
    'CATEGORIAS',
    (SELECT MIN(id_categoria) FROM CATEGORIAS),
    (SELECT MAX(id_categoria) FROM CATEGORIAS),
    (SELECT COUNT(*) FROM CATEGORIAS),
    (SELECT MIN(id_categoria) FROM [epran-qa].dbo.CATEGORIAS),
    (SELECT MAX(id_categoria) FROM [epran-qa].dbo.CATEGORIAS),
    (SELECT COUNT(*) FROM [epran-qa].dbo.CATEGORIAS)
UNION ALL SELECT
    'SUBCATEGORIAS',
    (SELECT MIN(id_subcategoria) FROM SUBCATEGORIAS),
    (SELECT MAX(id_subcategoria) FROM SUBCATEGORIAS),
    (SELECT COUNT(*) FROM SUBCATEGORIAS),
    (SELECT MIN(id_subcategoria) FROM [epran-qa].dbo.SUBCATEGORIAS),
    (SELECT MAX(id_subcategoria) FROM [epran-qa].dbo.SUBCATEGORIAS),
    (SELECT COUNT(*) FROM [epran-qa].dbo.SUBCATEGORIAS)
UNION ALL SELECT
    'MARCAS',
    (SELECT MIN(id_marca) FROM MARCAS),
    (SELECT MAX(id_marca) FROM MARCAS),
    (SELECT COUNT(*) FROM MARCAS),
    (SELECT MIN(id_marca) FROM [epran-qa].dbo.MARCAS),
    (SELECT MAX(id_marca) FROM [epran-qa].dbo.MARCAS),
    (SELECT COUNT(*) FROM [epran-qa].dbo.MARCAS)
UNION ALL SELECT
    'PRODUCTORAS',
    (SELECT MIN(id_productora) FROM PRODUCTORAS),
    (SELECT MAX(id_productora) FROM PRODUCTORAS),
    (SELECT COUNT(*) FROM PRODUCTORAS),
    (SELECT MIN(id_productora) FROM [epran-qa].dbo.PRODUCTORAS),
    (SELECT MAX(id_productora) FROM [epran-qa].dbo.PRODUCTORAS),
    (SELECT COUNT(*) FROM [epran-qa].dbo.PRODUCTORAS)
UNION ALL SELECT
    'PRESENTACIONES',
    (SELECT MIN(id_presentacion) FROM PRESENTACIONES),
    (SELECT MAX(id_presentacion) FROM PRESENTACIONES),
    (SELECT COUNT(*) FROM PRESENTACIONES),
    (SELECT MIN(id_presentacion) FROM [epran-qa].dbo.PRESENTACIONES),
    (SELECT MAX(id_presentacion) FROM [epran-qa].dbo.PRESENTACIONES),
    (SELECT COUNT(*) FROM [epran-qa].dbo.PRESENTACIONES);
GO


-- ══════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN POR CAMPO: Cuántos productos difieren en cada campo
-- Si todos son 0, PROD y QA están perfectamente sincronizados.
-- ══════════════════════════════════════════════════════════════════════════════
SELECT
    SUM(CASE WHEN ISNULL(p.id_departamento,-1) <> ISNULL(q.id_departamento,-1) THEN 1 ELSE 0 END) AS diff_departamento,
    SUM(CASE WHEN ISNULL(p.id_categoria,-1)    <> ISNULL(q.id_categoria,-1)    THEN 1 ELSE 0 END) AS diff_categoria,
    SUM(CASE WHEN ISNULL(p.id_subcategoria,-1) <> ISNULL(q.id_subcategoria,-1) THEN 1 ELSE 0 END) AS diff_subcategoria,
    SUM(CASE WHEN ISNULL(p.id_marca,-1)        <> ISNULL(q.id_marca,-1)        THEN 1 ELSE 0 END) AS diff_marca,
    SUM(CASE WHEN ISNULL(p.id_productora,-1)   <> ISNULL(q.id_productora,-1)   THEN 1 ELSE 0 END) AS diff_productora,
    SUM(CASE WHEN ISNULL(p.id_presentacion,-1) <> ISNULL(q.id_presentacion,-1) THEN 1 ELSE 0 END) AS diff_presentacion
FROM PRODUCTS p
INNER JOIN [epran-qa].dbo.PRODUCTS q ON q.id_product = p.id_product;
GO


-- ══════════════════════════════════════════════════════════════════════════════
-- DETALLE: Productos que tienen ALGUNA diferencia entre QA y PROD
-- Muestra el nombre resuelto en cada DB para comparación visual.
-- (Cambia TOP 50 por TOP 200 si quieres ver más registros)
-- ══════════════════════════════════════════════════════════════════════════════
SELECT TOP 50
    p.id_product,
    p.producto_gutrade,

    -- DEPARTAMENTO
    p.id_departamento       AS dept_id_prod,
    dp.nombre               AS dept_prod,
    q.id_departamento       AS dept_id_qa,
    dq.nombre               AS dept_qa,

    -- CATEGORIA
    p.id_categoria          AS cat_id_prod,
    cp.nombre               AS cat_prod,
    q.id_categoria          AS cat_id_qa,
    cq.nombre               AS cat_qa,

    -- SUBCATEGORIA
    p.id_subcategoria       AS subcat_id_prod,
    sp.nombre               AS subcat_prod,
    q.id_subcategoria       AS subcat_id_qa,
    sq.nombre               AS subcat_qa,

    -- MARCA
    p.id_marca              AS marca_id_prod,
    mp.nombre               AS marca_prod,
    q.id_marca              AS marca_id_qa,
    mq.nombre               AS marca_qa,

    -- PRODUCTORA
    p.id_productora         AS prod_id_prod,
    pp.nombre               AS productora_prod,
    q.id_productora         AS prod_id_qa,
    pq.nombre               AS productora_qa,

    -- PRESENTACION
    p.id_presentacion       AS pres_id_prod,
    prp.nombre              AS presentacion_prod,
    q.id_presentacion       AS pres_id_qa,
    prq.nombre              AS presentacion_qa

FROM PRODUCTS p
INNER JOIN [epran-qa].dbo.PRODUCTS q ON q.id_product = p.id_product

-- Dimensiones PROD
LEFT JOIN DEPARTAMENTOS       dp  ON dp.id_departamento  = p.id_departamento
LEFT JOIN CATEGORIAS          cp  ON cp.id_categoria     = p.id_categoria
LEFT JOIN SUBCATEGORIAS       sp  ON sp.id_subcategoria  = p.id_subcategoria
LEFT JOIN MARCAS              mp  ON mp.id_marca          = p.id_marca
LEFT JOIN PRODUCTORAS         pp  ON pp.id_productora    = p.id_productora
LEFT JOIN PRESENTACIONES      prp ON prp.id_presentacion = p.id_presentacion

-- Dimensiones QA
LEFT JOIN [epran-qa].dbo.DEPARTAMENTOS  dq  ON dq.id_departamento  = q.id_departamento
LEFT JOIN [epran-qa].dbo.CATEGORIAS     cq  ON cq.id_categoria     = q.id_categoria
LEFT JOIN [epran-qa].dbo.SUBCATEGORIAS  sq  ON sq.id_subcategoria  = q.id_subcategoria
LEFT JOIN [epran-qa].dbo.MARCAS         mq  ON mq.id_marca         = q.id_marca
LEFT JOIN [epran-qa].dbo.PRODUCTORAS    pq  ON pq.id_productora    = q.id_productora
LEFT JOIN [epran-qa].dbo.PRESENTACIONES prq ON prq.id_presentacion = q.id_presentacion

-- Solo los que tienen al menos una diferencia:
WHERE
    ISNULL(p.id_departamento,-1) <> ISNULL(q.id_departamento,-1) OR
    ISNULL(p.id_categoria,-1)    <> ISNULL(q.id_categoria,-1)    OR
    ISNULL(p.id_subcategoria,-1) <> ISNULL(q.id_subcategoria,-1) OR
    ISNULL(p.id_marca,-1)        <> ISNULL(q.id_marca,-1)        OR
    ISNULL(p.id_productora,-1)   <> ISNULL(q.id_productora,-1)   OR
    ISNULL(p.id_presentacion,-1) <> ISNULL(q.id_presentacion,-1)

ORDER BY p.id_product;
GO


-- ══════════════════════════════════════════════════════════════════════════════
-- VERIFICACIÓN DE NOMBRES: Dimensiones con mismo ID pero diferente nombre
-- Esto detecta si el mapeo de IDs en PROD es internamente inconsistente
-- respecto a QA (mismo número = distinto significado).
-- ══════════════════════════════════════════════════════════════════════════════

-- Marcas con mismo id_marca pero distinto nombre:
SELECT 'MARCAS' AS tabla, m_prod.id_marca, m_prod.nombre AS nombre_prod, m_qa.nombre AS nombre_qa
FROM MARCAS m_prod
INNER JOIN [epran-qa].dbo.MARCAS m_qa ON m_qa.id_marca = m_prod.id_marca
WHERE LTRIM(RTRIM(m_prod.nombre)) <> LTRIM(RTRIM(m_qa.nombre));

-- Productoras:
SELECT 'PRODUCTORAS' AS tabla, pp.id_productora, pp.nombre AS nombre_prod, pq.nombre AS nombre_qa
FROM PRODUCTORAS pp
INNER JOIN [epran-qa].dbo.PRODUCTORAS pq ON pq.id_productora = pp.id_productora
WHERE LTRIM(RTRIM(pp.nombre)) <> LTRIM(RTRIM(pq.nombre));

-- Presentaciones:
SELECT 'PRESENTACIONES' AS tabla, prp.id_presentacion, prp.nombre AS nombre_prod, prq.nombre AS nombre_qa
FROM PRESENTACIONES prp
INNER JOIN [epran-qa].dbo.PRESENTACIONES prq ON prq.id_presentacion = prp.id_presentacion
WHERE LTRIM(RTRIM(prp.nombre)) <> LTRIM(RTRIM(prq.nombre));

-- Subcategorias:
SELECT 'SUBCATEGORIAS' AS tabla, sp.id_subcategoria, sp.nombre AS nombre_prod, sq.nombre AS nombre_qa
FROM SUBCATEGORIAS sp
INNER JOIN [epran-qa].dbo.SUBCATEGORIAS sq ON sq.id_subcategoria = sp.id_subcategoria
WHERE LTRIM(RTRIM(sp.nombre)) <> LTRIM(RTRIM(sq.nombre));

-- Departamentos:
SELECT 'DEPARTAMENTOS' AS tabla, dp.id_departamento, dp.nombre AS nombre_prod, dq.nombre AS nombre_qa
FROM DEPARTAMENTOS dp
INNER JOIN [epran-qa].dbo.DEPARTAMENTOS dq ON dq.id_departamento = dp.id_departamento
WHERE LTRIM(RTRIM(dp.nombre)) <> LTRIM(RTRIM(dq.nombre));
GO
