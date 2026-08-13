-- Tabla nueva para el módulo "SKU vs SKU": por cada cliente, qué SKU propio
-- se enfrenta contra qué SKU(s) de la competencia. Por ahora es solo la
-- definición (pantalla de administración) -- todavía no cambia lo que ve
-- el mercaderista en la APK (GET /api/merc/productos sigue mostrando toda
-- la categoría hasta que se confirme ese paso siguiente).
--
-- Referencia PRODUCTS(id_product): es la misma tabla del catálogo Productos
-- (Departamento -> Categoría -> Subcategoría -> Marca -> Productora), no una
-- tabla nueva de SKUs.

IF NOT EXISTS (SELECT 1 FROM sys.tables WHERE name = 'SKU_COMPETENCIA')
BEGIN
    CREATE TABLE SKU_COMPETENCIA (
        id_sku_competencia      INT IDENTITY(1,1) PRIMARY KEY,
        id_cliente              INT NOT NULL,
        id_producto_cliente     INT NOT NULL,
        id_producto_competencia INT NOT NULL,
        activo                  BIT NOT NULL DEFAULT 1,
        fecha_creacion          DATETIME NOT NULL DEFAULT GETDATE(),
        CONSTRAINT FK_SkuCompetencia_Cliente FOREIGN KEY (id_cliente) REFERENCES CLIENTES(id_cliente),
        CONSTRAINT FK_SkuCompetencia_ProductoCliente FOREIGN KEY (id_producto_cliente) REFERENCES PRODUCTS(id_product),
        CONSTRAINT FK_SkuCompetencia_ProductoCompetencia FOREIGN KEY (id_producto_competencia) REFERENCES PRODUCTS(id_product),
        CONSTRAINT UQ_SkuCompetencia UNIQUE (id_cliente, id_producto_cliente, id_producto_competencia)
    );

    CREATE INDEX IX_SkuCompetencia_Cliente_Producto ON SKU_COMPETENCIA (id_cliente, id_producto_cliente);
END
