-- Módulo de Ventas 2.0 -- catálogo real, pedidos con líneas, OCR/IA, workflow,
-- crédito, caché de inventario externo. Aditivo: no toca VENDEDOR_JORNADAS ni
-- ninguna tabla existente salvo agregar una columna nullable a VENDEDOR_VISITAS.

-- 1. Catálogo de venta: qué producto (de la tabla PRODUCTS ya existente, 6072
-- filas, BI/snowflake) se le vende a qué cliente, a qué precio, con qué
-- metadata comercial (foto, presentación, código de barras propio si el de
-- PRODUCTS viene vacío). Un producto puede tener precios distintos por cliente.
CREATE TABLE CATALOGO_VENTA (
    id_catalogo INT IDENTITY(1,1) PRIMARY KEY,
    id_producto INT NOT NULL,
    id_cliente INT NOT NULL,
    precio_unitario DECIMAL(12,2) NOT NULL,
    unidades_por_caja INT NULL,
    presentacion_venta VARCHAR(20) NOT NULL DEFAULT 'Unidad',
    foto_url VARCHAR(500) NULL,
    codigo_barras VARCHAR(100) NULL,
    descuento_max_pct DECIMAL(5,2) NOT NULL DEFAULT 0,
    activo BIT NOT NULL DEFAULT 1,
    created_at DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_catalogo_venta_producto_cliente UNIQUE (id_producto, id_cliente)
);
CREATE INDEX IX_catalogo_venta_cliente ON CATALOGO_VENTA(id_cliente, activo);

-- 2. Pedido formal (la "nota de pedido" real -- reemplaza el monto suelto de
-- VENDEDOR_VISITAS como fuente de verdad de una venta).
CREATE TABLE PEDIDOS (
    id_pedido INT IDENTITY(1,1) PRIMARY KEY,
    numero_pedido VARCHAR(30) NOT NULL UNIQUE,
    id_cliente INT NOT NULL,
    id_usuario_vendedor INT NOT NULL,
    identificador_punto_interes VARCHAR(50) NULL,
    fecha DATETIME NOT NULL DEFAULT GETDATE(),
    estado VARCHAR(20) NOT NULL DEFAULT 'Borrador',
    subtotal DECIMAL(14,2) NOT NULL DEFAULT 0,
    descuento_total DECIMAL(14,2) NOT NULL DEFAULT 0,
    impuestos DECIMAL(14,2) NOT NULL DEFAULT 0,
    total DECIMAL(14,2) NOT NULL DEFAULT 0,
    latitud FLOAT NULL,
    longitud FLOAT NULL,
    notas NVARCHAR(1000) NULL,
    origen VARCHAR(20) NOT NULL DEFAULT 'app',
    firma_cliente_url VARCHAR(500) NULL,
    aprobado_por INT NULL,
    fecha_aprobacion DATETIME NULL,
    id_visita INT NULL,
    created_at DATETIME NOT NULL DEFAULT GETDATE()
);
CREATE INDEX IX_pedidos_cliente ON PEDIDOS(id_cliente, fecha);
CREATE INDEX IX_pedidos_vendedor ON PEDIDOS(id_usuario_vendedor, fecha);
CREATE INDEX IX_pedidos_estado ON PEDIDOS(estado);

-- 3. Líneas del pedido.
CREATE TABLE PEDIDO_LINEAS (
    id_linea INT IDENTITY(1,1) PRIMARY KEY,
    id_pedido INT NOT NULL,
    id_producto INT NOT NULL,
    nombre_producto VARCHAR(255) NULL,
    cantidad INT NOT NULL,
    precio_unitario DECIMAL(12,2) NOT NULL,
    descuento_pct DECIMAL(5,2) NOT NULL DEFAULT 0,
    subtotal_linea DECIMAL(14,2) NOT NULL,
    CONSTRAINT FK_pedido_lineas_pedido FOREIGN KEY (id_pedido) REFERENCES PEDIDOS(id_pedido)
);
CREATE INDEX IX_pedido_lineas_pedido ON PEDIDO_LINEAS(id_pedido);

-- 4. Notas de pedido en papel: foto -> OCR -> IA (Ollama) -> revisión humana.
CREATE TABLE PEDIDO_NOTAS_OCR (
    id INT IDENTITY(1,1) PRIMARY KEY,
    id_pedido INT NULL,
    id_usuario INT NOT NULL,
    foto_url VARCHAR(500) NOT NULL,
    texto_ocr NVARCHAR(MAX) NULL,
    json_ia NVARCHAR(MAX) NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente_revision',
    error_mensaje NVARCHAR(500) NULL,
    created_at DATETIME NOT NULL DEFAULT GETDATE()
);

-- 5. Caché de inventario externo -- diseñada para ser alimentada por la
-- futura API de DUSA (o cualquier cliente). Por ahora se llena manual/seed.
CREATE TABLE INVENTARIO_CACHE_EXTERNO (
    id INT IDENTITY(1,1) PRIMARY KEY,
    id_producto INT NOT NULL,
    id_cliente INT NOT NULL,
    cantidad_disponible INT NOT NULL DEFAULT 0,
    fuente VARCHAR(50) NOT NULL DEFAULT 'MANUAL',
    ultima_actualizacion DATETIME NOT NULL DEFAULT GETDATE(),
    CONSTRAINT UQ_inventario_cache_producto_cliente UNIQUE (id_producto, id_cliente)
);

-- 6. Crédito del cliente -- workflow de aprobación de pedidos.
CREATE TABLE CREDITO_CLIENTE (
    id_cliente INT NOT NULL PRIMARY KEY,
    limite_credito DECIMAL(14,2) NOT NULL DEFAULT 0,
    saldo_actual DECIMAL(14,2) NOT NULL DEFAULT 0,
    dias_mora INT NOT NULL DEFAULT 0,
    bloqueado BIT NOT NULL DEFAULT 0,
    actualizado_en DATETIME NOT NULL DEFAULT GETDATE()
);

-- 7. Enlace opcional: una visita de vendedor puede resultar en un pedido formal.
ALTER TABLE VENDEDOR_VISITAS ADD id_pedido INT NULL;
