IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[dbo].[MERC_AUDITORIA_TIEMPO]') AND type in (N'U'))
BEGIN
    CREATE TABLE MERC_AUDITORIA_TIEMPO (
        id_auditoria_tiempo INT IDENTITY(1,1) PRIMARY KEY,
        id_visita INT NULL,
        identificador_punto_interes VARCHAR(50) NULL,
        id_mercaderista INT NOT NULL,
        evento VARCHAR(50) NOT NULL,
        detalle VARCHAR(500) NULL,
        tiempo_restante_segundos INT NOT NULL,
        fecha_registro DATETIME DEFAULT GETDATE()
    );
    PRINT 'Tabla MERC_AUDITORIA_TIEMPO creada con éxito.';
END
ELSE
BEGIN
    PRINT 'La tabla MERC_AUDITORIA_TIEMPO ya existe.';
END

==============================================================================


IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'VISITAS_MERCADERISTA'
      AND COLUMN_NAME = 'motivo_reabertura'
)
BEGIN
    ALTER TABLE VISITAS_MERCADERISTA
    ADD motivo_reabertura VARCHAR(500) NULL;
END


=================================================
INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete, can_see_all)
SELECT id_usuario, 'encuestador-configuracion', 1, 1, 0, 0
FROM USUARIOS
WHERE username = 'dev'
  AND NOT EXISTS (
      SELECT 1 
      FROM usuario_permisos 
      WHERE id_usuario = USUARIOS.id_usuario 
        AND module = 'encuestador-configuracion'
  );
====================================================


-- 1. Agregar columnas a la tabla encuestas_centro si no existen
IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = object_id('encuestas_centro') AND name = 'observacion_supervisor')
BEGIN
    ALTER TABLE encuestas_centro ADD observacion_supervisor NVARCHAR(MAX) NULL;
    PRINT 'Columna observacion_supervisor creada';
END
ELSE
BEGIN
    PRINT 'Columna observacion_supervisor ya existe';
END;

IF NOT EXISTS (SELECT * FROM sys.columns WHERE object_id = object_id('encuestas_centro') AND name = 'requiere_correccion')
BEGIN
    ALTER TABLE encuestas_centro ADD requiere_correccion BIT NOT NULL DEFAULT 0;
    PRINT 'Columna requiere_correccion creada';
END
ELSE
BEGIN
    PRINT 'Columna requiere_correccion ya existe';
END;

-- 2. Insertar módulo si no existe
IF NOT EXISTS (SELECT * FROM MODULOS WHERE clave = 'supervisor-encuestadores')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
    VALUES ('supervisor-encuestadores', 'Supervisor Encuestadores', NULL, 'modulo', '/supervisor-encuestadores', 'supervisor_account', 205, 1);
    PRINT 'Módulo supervisor-encuestadores insertado';
END
ELSE
BEGIN
    PRINT 'Módulo supervisor-encuestadores ya existe';
END;

-- 3. Dar permisos al usuario dev
DECLARE @IdUsuario INT;
SELECT @IdUsuario = id_usuario FROM USUARIOS WHERE username = 'dev';

IF @IdUsuario IS NOT NULL
BEGIN
    IF NOT EXISTS (SELECT * FROM usuario_permisos WHERE id_usuario = @IdUsuario AND module = 'supervisor-encuestadores')
    BEGIN
        INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete, can_see_all)
        VALUES (@IdUsuario, 'supervisor-encuestadores', 1, 1, 1, 0);
        PRINT 'Permisos para supervisor-encuestadores concedidos al usuario dev';
    END
    ELSE
    BEGIN
        PRINT 'El usuario dev ya tiene permisos para el módulo supervisor-encuestadores';
    END;
END
ELSE
BEGIN
    PRINT 'El usuario dev no existe en la tabla USUARIOS';
END;

===========================================================



-- 4. Insertar módulo portal-mercaderista si no existe
IF NOT EXISTS (SELECT * FROM MODULOS WHERE clave = 'portal-mercaderista')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
    VALUES ('portal-mercaderista', 'Portal Mercaderista', NULL, 'modulo', '/portal-mercaderista', 'storefront', 210, 1);
    PRINT 'Módulo portal-mercaderista insertado';
END
ELSE
BEGIN
    PRINT 'Módulo portal-mercaderista ya existe';
END;

-- 5. Dar permisos al usuario dev en portal-mercaderista
DECLARE @IdUsuarioDev2 INT;
SELECT @IdUsuarioDev2 = id_usuario FROM USUARIOS WHERE username = 'dev';

IF @IdUsuarioDev2 IS NOT NULL
BEGIN
    IF NOT EXISTS (SELECT * FROM usuario_permisos WHERE id_usuario = @IdUsuarioDev2 AND module = 'portal-mercaderista')
    BEGIN
        INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete, can_see_all)
        VALUES (@IdUsuarioDev2, 'portal-mercaderista', 1, 1, 1, 1);
        PRINT 'Permisos portal-mercaderista concedidos al usuario dev';
    END
    ELSE
    BEGIN
        PRINT 'El usuario dev ya tiene permisos para portal-mercaderista';
    END;
END;

-- 6. Dar permisos genéricos de portal-mercaderista a todos los usuarios con rol mercaderista
-- (Opcional: ejecutar si quieres que todos los mercaderistas accedan también desde la web)
 INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete, can_see_all)
 SELECT u.id_usuario, 'portal-mercaderista', 1, 0, 0, 0
 FROM USUARIOS u
 INNER JOIN ROLES r ON u.id_rol = r.id_rol
 WHERE r.nombre_rol = 'mercaderista'
   AND NOT EXISTS (
       SELECT 1 FROM usuario_permisos up
       WHERE up.id_usuario = u.id_usuario AND up.module = 'portal-mercaderista'
   );

-- 7. Insertar sub-módulos del Centro de Mando en la tabla MODULOS
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.activaciones')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.activaciones', 'Activaciones', id_modulo, 'submodulo', 1, 1
    FROM MODULOS WHERE clave = 'centro-mando';
END;

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.visitas')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.visitas', 'Visitas', id_modulo, 'submodulo', 2, 1
    FROM MODULOS WHERE clave = 'centro-mando';
END;

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.activaciones.dashboard')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.activaciones.dashboard', 'Dashboard', id_modulo, 'accion', 1, 1
    FROM MODULOS WHERE clave = 'centro-mando.activaciones';
END;

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.activaciones.gestion_dia')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.activaciones.gestion_dia', 'Gestión del Día', id_modulo, 'accion', 2, 1
    FROM MODULOS WHERE clave = 'centro-mando.activaciones';
END;

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.activaciones.pendientes')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.activaciones.pendientes', 'Pendientes', id_modulo, 'accion', 3, 1
    FROM MODULOS WHERE clave = 'centro-mando.activaciones';
END;

IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'centro-mando.activaciones.horas_trabajadas')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, orden, activo)
    SELECT 'centro-mando.activaciones.horas_trabajadas', 'Horas Trabajadas', id_modulo, 'accion', 4, 1
    FROM MODULOS WHERE clave = 'centro-mando.activaciones';
END;

-- 8. Insertar módulo auditoria-usuarios en MODULOS si no existe
IF NOT EXISTS (SELECT 1 FROM MODULOS WHERE clave = 'auditoria-usuarios')
BEGIN
    INSERT INTO MODULOS (clave, nombre, id_padre, tipo, ruta, icono, orden, activo)
    VALUES ('auditoria-usuarios', 'Auditoría de Usuarios', NULL, 'modulo', '/auditoria-usuarios', 'admin_panel_settings', 215, 1);
    PRINT 'Módulo auditoria-usuarios insertado en MODULOS';
END;

-- 9. Conceder permisos de auditoria-usuarios al usuario dev y administradores
DECLARE @IdUsuarioDevAud INT;
SELECT @IdUsuarioDevAud = id_usuario FROM USUARIOS WHERE username = 'dev';

IF @IdUsuarioDevAud IS NOT NULL
BEGIN
    IF NOT EXISTS (SELECT 1 FROM usuario_permisos WHERE id_usuario = @IdUsuarioDevAud AND module = 'auditoria-usuarios')
    BEGIN
        INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete, can_see_all)
        VALUES (@IdUsuarioDevAud, 'auditoria-usuarios', 1, 1, 1, 1);
    END;
END;

INSERT INTO usuario_permisos (id_usuario, module, can_read, can_write, can_delete, can_see_all)
SELECT u.id_usuario, 'auditoria-usuarios', 1, 1, 1, 1
FROM USUARIOS u
WHERE u.id_rol = 8
  AND NOT EXISTS (
      SELECT 1 FROM usuario_permisos up
      WHERE up.id_usuario = u.id_usuario AND up.module = 'auditoria-usuarios'
  );

-- 10. Agregar columnas de fin de jornada en JORNADAS_ENCUESTADOR si faltan
IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('JORNADAS_ENCUESTADOR') AND name = 'latitud_fin')
    ALTER TABLE JORNADAS_ENCUESTADOR ADD latitud_fin FLOAT NULL;

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('JORNADAS_ENCUESTADOR') AND name = 'longitud_fin')
    ALTER TABLE JORNADAS_ENCUESTADOR ADD longitud_fin FLOAT NULL;

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('JORNADAS_ENCUESTADOR') AND name = 'ciudad_fin')
    ALTER TABLE JORNADAS_ENCUESTADOR ADD ciudad_fin VARCHAR(100) NULL;

IF NOT EXISTS (SELECT 1 FROM sys.columns WHERE object_id = OBJECT_ID('JORNADAS_ENCUESTADOR') AND name = 'estado_geo_fin')
    ALTER TABLE JORNADAS_ENCUESTADOR ADD estado_geo_fin VARCHAR(100) NULL;

