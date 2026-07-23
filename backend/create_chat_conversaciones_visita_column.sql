-- Ejecutar en SQL Server (epran-qa) para el sub-hilo de chat por visita
-- (solo equipo / equipo+cliente) dentro de una conversacion existente.
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.CHAT_CONVERSACIONES') AND name = 'id_visita'
)
BEGIN
    ALTER TABLE dbo.CHAT_CONVERSACIONES ADD id_visita INT NULL;
    ALTER TABLE dbo.CHAT_CONVERSACIONES ADD CONSTRAINT FK_CHAT_CONV_visita
        FOREIGN KEY (id_visita) REFERENCES dbo.VISITAS_MERCADERISTA (id_visita);
    PRINT 'Columna id_visita agregada a CHAT_CONVERSACIONES.';
END
ELSE
    PRINT 'Columna id_visita ya existe en CHAT_CONVERSACIONES.';
GO

IF NOT EXISTS (
    SELECT * FROM sys.indexes
    WHERE object_id = OBJECT_ID('dbo.CHAT_CONVERSACIONES') AND name = 'IX_CHAT_CONV_cliente_visita_tipo'
)
BEGIN
    CREATE NONCLUSTERED INDEX IX_CHAT_CONV_cliente_visita_tipo
        ON dbo.CHAT_CONVERSACIONES (id_cliente, id_visita, tipo);
    PRINT 'Indice IX_CHAT_CONV_cliente_visita_tipo creado.';
END
ELSE
    PRINT 'Indice IX_CHAT_CONV_cliente_visita_tipo ya existe.';
GO
