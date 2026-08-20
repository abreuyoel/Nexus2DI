-- ============================================================
-- CLIENTES.id_productora -- qué PRODUCTORA es "la propia" de cada cliente.
-- Usado por el filtro "Solo propios" de /productos-catalogos (Permisos >
-- módulo "Productos", can_see_all=False). Nullable: la mayoría de los
-- clientes no lo necesitan.
-- Ejecutar una sola vez, en cada ambiente (prod y qa por separado).
-- ============================================================

IF NOT EXISTS (
    SELECT 1 FROM sys.columns
    WHERE object_id = OBJECT_ID('CLIENTES') AND name = 'id_productora'
)
BEGIN
    ALTER TABLE CLIENTES ADD id_productora INT NULL;
    ALTER TABLE CLIENTES ADD CONSTRAINT FK_Clientes_Productora
        FOREIGN KEY (id_productora) REFERENCES PRODUCTORAS(id_productora);
END
GO

-- Configura Flora Foods -> productora "Flora Food" (el nombre real en
-- PRODUCTORAS, confirmado por captura de pantalla del catálogo -- si el
-- nombre exacto en la tabla difiere un poco, este UPDATE no hace nada,
-- ver el SELECT de verificación al final).
UPDATE c
SET c.id_productora = p.id_productora
FROM CLIENTES c
JOIN PRODUCTORAS p ON p.nombre = 'Flora Food'
WHERE c.cliente LIKE 'Flora Foods%'
  AND c.id_productora IS NULL;
GO

-- Verificación -- confirmar que sí quedó seteado antes de cerrar esto.
SELECT c.id_cliente, c.cliente, c.id_productora, p.nombre AS productora
FROM CLIENTES c
LEFT JOIN PRODUCTORAS p ON p.id_productora = c.id_productora
WHERE c.cliente LIKE 'Flora Foods%';

-- Si "productora" salió NULL arriba, buscar el nombre real así y repetir
-- el UPDATE de arriba con el nombre correcto:
-- SELECT id_productora, nombre FROM PRODUCTORAS WHERE nombre LIKE '%Flora%';
