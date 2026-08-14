-- ── Módulo Auditoría de Usuarios en la tabla MODULOS y permisos por defecto ──

-- 1. Insertar el módulo auditoria-usuarios en MODULOS
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'auditoria-usuarios')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
    VALUES ('auditoria-usuarios', 'Auditoría de Usuarios', NULL, 'modulo', '/auditoria-usuarios', 'admin_panel_settings', 215, 1);
    PRINT 'Módulo auditoria-usuarios insertado en MODULOS';
END
ELSE
BEGIN
    PRINT 'Módulo auditoria-usuarios ya existe en MODULOS';
END;

-- 2. Conceder permisos de auditoria-usuarios al usuario 'dev'
DECLARE @IdUsuarioDevAud INT;
SELECT @IdUsuarioDevAud = id_usuario FROM USUARIOS WHERE username = 'dev';

IF @IdUsuarioDevAud IS NOT NULL
BEGIN
    IF NOT EXISTS (SELECT 1 FROM usuario_permisos WHERE id_usuario = @IdUsuarioDevAud AND module = 'auditoria-usuarios')
    BEGIN
        INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete, can_see_all)
        VALUES (@IdUsuarioDevAud, 'auditoria-usuarios', 1, 1, 1, 1);
        PRINT 'Permiso auditoria-usuarios concedido a usuario dev';
    END;
END;

-- 3. Conceder permisos de auditoria-usuarios a todos los administradores (id_rol = 8)
INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete, can_see_all)
SELECT u.id_usuario, 'auditoria-usuarios', 1, 1, 1, 1
FROM USUARIOS u
WHERE u.id_rol = 8
  AND NOT EXISTS (
      SELECT 1 FROM usuario_permisos up
      WHERE up.id_usuario = u.id_usuario AND up.module = 'auditoria-usuarios'
  );
