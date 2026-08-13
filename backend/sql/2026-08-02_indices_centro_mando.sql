-- Índices recomendados para acelerar Centro de Mando (Activaciones + Visitas)
-- y Revisión de Fotos/Visitas.
--
-- Por qué: casi todas las queries de este módulo filtran por fecha
-- (VISITAS_MERCADERISTA.fecha_visita, FOTOS_TOTALES.fecha_registro,
-- RUTAS_ACTIVADAS.fecha_hora_activacion) y cruzan por las mismas columnas
-- una y otra vez (id_visita, id_mercaderista, id_ruta, identificador_punto_interes).
-- Sin índices sobre esas columnas, SQL Server tiene que escanear la tabla
-- entera en cada llamada -- coincide con lo que se ve en el Network tab del
-- navegador (7+ segundos por endpoint).
--
-- CÓMO CORRERLO: revisar cada CREATE INDEX antes de ejecutar. Todas usan
-- "IF NOT EXISTS" así que el script es seguro de re-correr si se corta a
-- mitad. En FOTOS_TOTALES / VISITAS_MERCADERISTA (las tablas más grandes),
-- crear un índice nuevo escanea toda la tabla una vez y puede tardar minutos
-- y bloquear escrituras mientras corre -- mejor en horario de bajo tráfico.
-- Si la edición de SQL Server lo soporta, agregar WITH (ONLINE = ON) a cada
-- CREATE INDEX para no bloquear escrituras durante la creación (Enterprise /
-- Azure SQL; no disponible en Standard).

-- ── VISITAS_MERCADERISTA: la tabla más consultada de todo el módulo ──
-- fecha_visita es EL filtro principal de resumen-dia, activaciones,
-- review-list, gestión por día. id_cliente/id_mercaderista/identificador_
-- punto_interes son las columnas de JOIN más usadas.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_VisitasMercaderista_FechaVisita' AND object_id = OBJECT_ID('VISITAS_MERCADERISTA'))
    CREATE INDEX IX_VisitasMercaderista_FechaVisita
    ON VISITAS_MERCADERISTA (fecha_visita)
    INCLUDE (id_mercaderista, id_cliente, identificador_punto_interes, estado);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_VisitasMercaderista_Mercaderista_Fecha' AND object_id = OBJECT_ID('VISITAS_MERCADERISTA'))
    CREATE INDEX IX_VisitasMercaderista_Mercaderista_Fecha
    ON VISITAS_MERCADERISTA (id_mercaderista, fecha_visita);

-- ── FOTOS_TOTALES: tabla histórica de solo-inserción, la más grande ──
-- fecha_registro se usa para "horas trabajadas"/"tiempo de traslado" y para
-- acotar el join en gestión por día. id_visita es la columna de JOIN más
-- repetida de todo el archivo (OUTER APPLY por fila en activaciones).
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_FotosTotales_Visita_Tipo' AND object_id = OBJECT_ID('FOTOS_TOTALES'))
    CREATE INDEX IX_FotosTotales_Visita_Tipo
    ON FOTOS_TOTALES (id_visita, id_tipo_foto)
    INCLUDE (fecha_registro, Estado, id_foto, file_path);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_FotosTotales_FechaRegistro' AND object_id = OBJECT_ID('FOTOS_TOTALES'))
    CREATE INDEX IX_FotosTotales_FechaRegistro
    ON FOTOS_TOTALES (fecha_registro)
    INCLUDE (id_visita, id_tipo_foto);

-- ── RUTAS_ACTIVADAS: usada por resumen-dia para "quién activó hoy" ──
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_RutasActivadas_Fecha' AND object_id = OBJECT_ID('RUTAS_ACTIVADAS'))
    CREATE INDEX IX_RutasActivadas_Fecha
    ON RUTAS_ACTIVADAS (fecha_hora_activacion)
    INCLUDE (id_mercaderista, id_ruta, estado);

-- ── RUTA_PROGRAMACION: se cruza en CASI todos los EXISTS de scoping ──
-- (analista, cliente, roster de mercaderistas) -- prácticamente cada query
-- de este módulo la toca al menos una vez.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_RutaProgramacion_Ruta_Activa' AND object_id = OBJECT_ID('RUTA_PROGRAMACION'))
    CREATE INDEX IX_RutaProgramacion_Ruta_Activa
    ON RUTA_PROGRAMACION (id_ruta, activa)
    INCLUDE (id_cliente, id_punto_interes, dia);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_RutaProgramacion_Punto_Cliente' AND object_id = OBJECT_ID('RUTA_PROGRAMACION'))
    CREATE INDEX IX_RutaProgramacion_Punto_Cliente
    ON RUTA_PROGRAMACION (id_punto_interes, id_cliente)
    WHERE activa = 1;

-- ── MERCADERISTAS_RUTAS / analistas_rutas: tablas puente pequeñas pero ──
-- consultadas en casi cada EXISTS de scoping por analista.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_MercaderistasRutas_Ruta_Merc' AND object_id = OBJECT_ID('MERCADERISTAS_RUTAS'))
    CREATE INDEX IX_MercaderistasRutas_Ruta_Merc
    ON MERCADERISTAS_RUTAS (id_ruta, id_mercaderista);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_AnalistasRutas_Ruta_Analista' AND object_id = OBJECT_ID('analistas_rutas'))
    CREATE INDEX IX_AnalistasRutas_Ruta_Analista
    ON analistas_rutas (id_ruta, id_analista);

-- ── BALANCES_TOTALES: pantalla "Data de Clientes" (balances/productos) ──
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_BalancesTotales_Cliente_Fecha' AND object_id = OBJECT_ID('BALANCES_TOTALES'))
    CREATE INDEX IX_BalancesTotales_Cliente_Fecha
    ON BALANCES_TOTALES (id_cliente, fecha_balance)
    INCLUDE (identificador_pdv, id_visita, producto, categoria);

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = 'IX_BalancesTotales_Pdv' AND object_id = OBJECT_ID('BALANCES_TOTALES'))
    CREATE INDEX IX_BalancesTotales_Pdv
    ON BALANCES_TOTALES (identificador_pdv);
