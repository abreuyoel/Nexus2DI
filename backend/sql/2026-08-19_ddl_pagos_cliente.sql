-- Vendedor: falta #4 de la lista de gaps -- CREDITO_CLIENTE ya mostraba
-- saldo y mora, pero /api/vendedor/credito/{id} solo permitía SOBRESCRIBIR
-- el saldo entero (set_credito, para el admin) -- no había forma de
-- registrar UN pago puntual ni ver el historial de abonos de un cliente.
--
-- PAGOS_CLIENTE es el libro de pagos; CREDITO_CLIENTE.saldo_actual sigue
-- siendo el saldo vigente (se decrementa en cada INSERT acá, dentro de la
-- misma transacción -- ver POST /api/vendedor/credito/{id}/pago).

CREATE TABLE PAGOS_CLIENTE (
    id_pago INT IDENTITY(1,1) PRIMARY KEY,
    id_cliente INT NOT NULL,
    monto DECIMAL(14,2) NOT NULL,
    metodo_pago NVARCHAR(50) NOT NULL,       -- Transferencia / Efectivo / Zelle / Pago Móvil / Otro
    referencia NVARCHAR(100) NULL,           -- nro de referencia/comprobante, si aplica
    notas NVARCHAR(500) NULL,
    id_usuario_registro INT NOT NULL,        -- quién lo cargó (vendedor/admin)
    fecha_pago DATETIME NOT NULL DEFAULT GETDATE(),
    saldo_antes DECIMAL(14,2) NOT NULL,      -- saldo_actual de CREDITO_CLIENTE justo antes de este pago
    saldo_despues DECIMAL(14,2) NOT NULL,    -- ... y justo después -- auditoría sin tener que recalcular
    CONSTRAINT FK_pagos_cliente_cliente FOREIGN KEY (id_cliente) REFERENCES CLIENTES(id_cliente),
    CONSTRAINT FK_pagos_cliente_usuario FOREIGN KEY (id_usuario_registro) REFERENCES USUARIOS(id_usuario)
);

CREATE INDEX IX_pagos_cliente_cliente_fecha ON PAGOS_CLIENTE (id_cliente, fecha_pago DESC);
