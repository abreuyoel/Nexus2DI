-- ================================================
-- REPARAR SECUENCIA (IDENTITY RESEED)
-- Ambiente: QA
-- Fecha: 2026-07-21
-- ================================================

-- 1. CATEGORIAS: reseed al MAX actual (95)
DBCC CHECKIDENT ('dbo.CATEGORIAS', RESEED, 95);

-- 2. PRODUCTS: está OK, pero si quieres normalizarlo también:
-- DBCC CHECKIDENT ('dbo.PRODUCTS', RESEED, 5546);

-- Verificación post-fix:
SELECT 
    'PRODUCTS'   AS tabla, IDENT_CURRENT('PRODUCTS')   AS identity_actual, (SELECT MAX(id_product)  FROM PRODUCTS)   AS max_id
UNION ALL
SELECT 
    'CATEGORIAS' AS tabla, IDENT_CURRENT('CATEGORIAS') AS identity_actual, (SELECT MAX(id_categoria) FROM CATEGORIAS) AS max_id;
