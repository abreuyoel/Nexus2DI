-- ============================================================
-- Rol Cliente: Módulos y permisos por defecto
-- Ejecutar una sola vez en la base de datos de praoducción.
-- ============================================================

-- 1. Sub-módulo Power BI como hijo del Dashboard (id_padre = 1)
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'dashboard-powerbi')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
    VALUES ('dashboard-powerbi', 'Power BI', 1, 'modulo', '/dashboard?view=powerbi', 'bar_chart', 11, 1);
ENDa
GO

-- ============================================================
-- 2. Permisos por defecto para el rol Cliente (id_rol = 1).
--    Se insertan en usuario_permisos solo si no existen ya.
--    Módulos: dashboard, dashboard-powerbi, centro-mando,
--             points, products, data, chat, users,
--             client-categories
--    Acciones: solo can_read = 1 (no write, no delete)
-- ============================================================
DECLARE @modulos TABLE (clave NVARCHAR(100));
INSERT INTO @modulos VALUES
    ('dashboard'),
    ('dashboard-powerbi'),
    ('centro-mando'),
    ('points'),
    ('products'),
    ('data'),
    ('data.exportar'),
    ('chat'),
    ('users'),
    ('client-categories');

INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete)
SELECT u.id_usuario, m.clave, 1, 0, 0
FROM USUARIOS u
CROSS JOIN @modulos m
WHERE u.id_rol = 1
  AND NOT EXISTS (
      SELECT 1 FROM usuario_permisos up
      WHERE up.id_usuario = u.id_usuario AND up.module = m.clave
  );
GO

-- ============================================================
-- 3. Asegura que el cliente NO tenga can_read en módulos
--    que deben quedar ocultos para él.
-- ============================================================
DECLARE @ocultos TABLE (clave NVARCHAR(100));
INSERT INTO @ocultos VALUES
    ('client'),
    ('client-visits'),
    ('routes'),
    ('permissions'),
    ('atencion-cliente'),
    ('audit'),
    ('admin/chat-grupos'),
    ('auditor-campo'),
    ('auditoria-data'),
    ('supervisor'),
    ('clientes-rutas'),
    ('frecuencias-pdvs-cliente'),
    ('horas-promedio-ejecucion'),
    ('sku-competencia'),
    ('plan-accion'),
    ('centro-mando-auditoria'),
    ('encuestador'),
    ('cliente-encuestador'),
    ('ventas');

-- Actualizar permisos existentes a can_read=0
UPDATE up
SET up.can_read = 0, up.can_write = 0, up.can_delete = 0
FROM usuario_permisos up
JOIN USUARIOS u ON u.id_usuario = up.id_usuario
JOIN @ocultos o ON o.clave = up.module
WHERE u.id_rol = 1;

-- Insertar restricciones donde no existían aún
INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete)
SELECT u.id_usuario, o.clave, 0, 0, 0
FROM USUARIOS u
CROSS JOIN @ocultos o
WHERE u.id_rol = 1
  AND NOT EXISTS (
      SELECT 1 FROM usuario_permisos up
      WHERE up.id_usuario = u.id_usuario AND up.module = o.clave
  );
GO
