-- Ejecutar en SQL Server (epran-qa) para crear la tabla de recibos de
-- lectura por mensaje (estilo WhatsApp) del chat de AppWeb v2.
IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='CHAT_MENSAJE_LECTURAS' AND xtype='U')
BEGIN
    CREATE TABLE dbo.CHAT_MENSAJE_LECTURAS (
        id_lectura     INT IDENTITY(1,1) NOT NULL,
        id_mensaje     INT NOT NULL,
        id_usuario     INT NOT NULL,
        username       NVARCHAR(150) NULL,
        fecha_lectura  DATETIME NOT NULL DEFAULT (GETDATE()),
        CONSTRAINT PK_CHAT_MENSAJE_LECTURAS PRIMARY KEY CLUSTERED (id_lectura),
        CONSTRAINT UQ_CML_mensaje_usuario UNIQUE (id_mensaje, id_usuario),
        CONSTRAINT FK_CML_mensaje FOREIGN KEY (id_mensaje) REFERENCES dbo.CHAT_MENSAJES_CLIENTE (id_mensaje)
    );
    PRINT 'Tabla CHAT_MENSAJE_LECTURAS creada correctamente.';
END
ELSE
    PRINT 'Tabla CHAT_MENSAJE_LECTURAS ya existe.';
