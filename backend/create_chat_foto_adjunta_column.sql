-- Ejecutar en SQL Server (epran-qa) para que el aviso automatico de foto
-- rechazada pueda adjuntar la foto en el mensaje del chat.
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.CHAT_MENSAJES_CLIENTE') AND name = 'foto_adjunta'
)
BEGIN
    ALTER TABLE dbo.CHAT_MENSAJES_CLIENTE ADD foto_adjunta NVARCHAR(500) NULL;
    PRINT 'Columna foto_adjunta agregada a CHAT_MENSAJES_CLIENTE.';
END
ELSE
    PRINT 'Columna foto_adjunta ya existe en CHAT_MENSAJES_CLIENTE.';
GO
