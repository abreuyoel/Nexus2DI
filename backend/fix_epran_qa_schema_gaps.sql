-- Corrige en epran-qa las columnas que ya existen en epran (produccion) y
-- que le faltan -- ver resultado.txt de compare_epran_vs_epran_qa.sql,
-- bloque 3, filas SOLO_EN_epran.
--
-- Solo se incluye lo que el codigo de Nexus2DI v2 realmente usa (verificado
-- por grep contra backend/app):
--   - CHAT_MENSAJES_GRUPO_VISITA.foto_adjunta: la tabla ya existia en
--     epran-qa (por eso no salio en el bloque 1/2), pero sin esta columna
--     -- ver app/models/chat_grupos.py::ChatMensajeGrupoVisita.foto_adjunta
--     (String(500)) y app/routes/chat_grupos.py, que la usa al mandar/leer
--     mensajes y al postear el rechazo de foto.
--
-- NO se toco RUTAS_ACTIVADAS.id_cliente / identificador_punto_interes
-- (tambien SOLO_EN_epran): no aparecen referenciadas en ningun INSERT/SELECT
-- de app/routes ni en app/models/ruta.py -- probablemente una columna de
-- v1 sin uso en v2. Avisar antes de agregarlas si hace falta.
--
-- Correr con: sqlcmd -S 172.174.41.110 -U <usuario> -P <password> -C -d epran-qa -i fix_epran_qa_schema_gaps.sql

SET NOCOUNT ON;

IF NOT EXISTS (
    SELECT 1 FROM INFORMATION_SCHEMA.COLUMNS
    WHERE TABLE_NAME = 'CHAT_MENSAJES_GRUPO_VISITA' AND COLUMN_NAME = 'foto_adjunta'
)
BEGIN
    ALTER TABLE CHAT_MENSAJES_GRUPO_VISITA ADD foto_adjunta NVARCHAR(500) NULL;
    PRINT 'Agregada CHAT_MENSAJES_GRUPO_VISITA.foto_adjunta';
END
ELSE
    PRINT 'CHAT_MENSAJES_GRUPO_VISITA.foto_adjunta ya existia, no se toco';
