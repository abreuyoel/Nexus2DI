-- ============================================================
-- Script: insertar_permiso_admin.sql
-- Descripción: Inserta el permiso "merc_rutas" con can_see_all=1
--              para el usuario administrador "Dev" (id_usuario=1).
-- Ejecutar en SQL Server Management Studio o Azure Data Studio.
-- ============================================================

IF NOT EXISTS (
    SELECT 1 FROM usuario_permisos
    WHERE id_usuario = 1 AND module = 'merc_rutas'
)
BEGIN
    INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete, can_see_all)
    VALUES (1, 'merc_rutas', 1, 0, 0, 1);
    PRINT 'Permiso merc_rutas insertado correctamente para el admin.';
END
ELSE
BEGIN
    PRINT 'El permiso merc_rutas ya existe para el admin.';
END;
