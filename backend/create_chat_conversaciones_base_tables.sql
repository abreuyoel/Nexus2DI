-- Ejecutar en SQL Server (epran-qa) ANTES que
-- create_chat_conversaciones_visita_column.sql y
-- create_chat_mensaje_lecturas_table.sql.
--
-- Crea las tablas base del sistema de "conversaciones" (chats directos y
-- de grupo no atados a una visita puntual: direct/group_team/group_region/
-- group_pdv, y ahora tambien visit_team/visit_team_client) que el codigo
-- de AppWeb v2 (backend/app/models/chat.py: ChatConversacion,
-- ChatParticipante) ya asume que existen desde antes de esta sesion, pero
-- que nunca se crearon en epran-qa.

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'CHAT_CONVERSACIONES')
BEGIN
    CREATE TABLE dbo.CHAT_CONVERSACIONES (
        id_conversacion   INT IDENTITY(1,1) NOT NULL,
        id_cliente        INT NOT NULL,
        tipo              NVARCHAR(20) NOT NULL,
        titulo            NVARCHAR(200) NULL,
        region            NVARCHAR(100) NULL,
        id_punto_interes  NVARCHAR(50) NULL,
        creado_por        INT NOT NULL,
        fecha_creacion    DATETIME NULL,
        CONSTRAINT PK_CHAT_CONVERSACIONES PRIMARY KEY CLUSTERED (id_conversacion),
        CONSTRAINT FK_CHAT_CONV_cliente FOREIGN KEY (id_cliente) REFERENCES dbo.CLIENTES (id_cliente),
        CONSTRAINT FK_CHAT_CONV_creador FOREIGN KEY (creado_por) REFERENCES dbo.USUARIOS (id_usuario)
    );
    CREATE NONCLUSTERED INDEX IX_CHAT_CONV_cliente ON dbo.CHAT_CONVERSACIONES (id_cliente);
    CREATE NONCLUSTERED INDEX IX_CHAT_CONV_tipo ON dbo.CHAT_CONVERSACIONES (tipo);
    PRINT 'Tabla CHAT_CONVERSACIONES creada.';
END
ELSE
    PRINT 'CHAT_CONVERSACIONES ya existe.';
GO

IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'CHAT_PARTICIPANTES')
BEGIN
    CREATE TABLE dbo.CHAT_PARTICIPANTES (
        id_conversacion  INT NOT NULL,
        id_usuario       INT NOT NULL,
        fecha_union      DATETIME NULL,
        CONSTRAINT PK_CHAT_PARTICIPANTES PRIMARY KEY CLUSTERED (id_conversacion, id_usuario),
        CONSTRAINT FK_CHAT_PART_conversacion FOREIGN KEY (id_conversacion) REFERENCES dbo.CHAT_CONVERSACIONES (id_conversacion),
        CONSTRAINT FK_CHAT_PART_usuario FOREIGN KEY (id_usuario) REFERENCES dbo.USUARIOS (id_usuario)
    );
    CREATE NONCLUSTERED INDEX IX_CHAT_PART_usuario ON dbo.CHAT_PARTICIPANTES (id_usuario);
    PRINT 'Tabla CHAT_PARTICIPANTES creada.';
END
ELSE
    PRINT 'CHAT_PARTICIPANTES ya existe.';
GO

-- CHAT_MENSAJES_CLIENTE ya existe (chat legacy cliente<->staff por visita),
-- pero le falta la columna que liga un mensaje a una conversacion nueva.
IF NOT EXISTS (
    SELECT * FROM sys.columns
    WHERE object_id = OBJECT_ID('dbo.CHAT_MENSAJES_CLIENTE') AND name = 'id_conversacion'
)
BEGIN
    ALTER TABLE dbo.CHAT_MENSAJES_CLIENTE ADD id_conversacion INT NULL;
    ALTER TABLE dbo.CHAT_MENSAJES_CLIENTE ADD CONSTRAINT FK_CMC_conversacion
        FOREIGN KEY (id_conversacion) REFERENCES dbo.CHAT_CONVERSACIONES (id_conversacion);
    CREATE NONCLUSTERED INDEX IX_CMC_conversacion ON dbo.CHAT_MENSAJES_CLIENTE (id_conversacion);
    PRINT 'Columna id_conversacion agregada a CHAT_MENSAJES_CLIENTE.';
END
ELSE
    PRINT 'Columna id_conversacion ya existe en CHAT_MENSAJES_CLIENTE.';
GO
