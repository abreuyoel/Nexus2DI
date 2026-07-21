-- Ejecutar en SQL Server para crear la tabla de permisos
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='usuario_permisos' AND xtype='U')
BEGIN
    CREATE TABLE usuario_permisos (
        id          INT IDENTITY(1,1) PRIMARY KEY,
        id_usuario  INT NOT NULL,
        module      VARCHAR(50) NOT NULL,
        can_read    BIT NOT NULL DEFAULT 1,
        can_write   BIT NOT NULL DEFAULT 0,
        can_delete  BIT NOT NULL DEFAULT 0,
        can_see_all BIT NOT NULL DEFAULT 0,
        CONSTRAINT FK_permisos_usuario FOREIGN KEY (id_usuario)
            REFERENCES USUARIOS(id_usuario) ON DELETE CASCADE,
        CONSTRAINT UQ_permisos_usuario_module UNIQUE (id_usuario, module)
    );
    PRINT 'Tabla usuario_permisos creada correctamente.';
END
ELSE
    PRINT 'Tabla usuario_permisos ya existe.';
