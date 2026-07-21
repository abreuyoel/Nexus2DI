-- ============================================================
-- Índices de rendimiento para consultas de Centro de Mando
-- Generado desde: alembic/versions/1c8d4f3e7b2a_add_performance_indexes.py
-- Ejecutar directamente en SQL Server Management Studio (SSMS)
-- ============================================================

-- ── VISITAS_MERCADERISTA ──────────────────────────────────
-- WHERE fecha_visita BETWEEN ... ORDER BY fecha_visita DESC
-- JOIN con CLIENTES, PUNTOS_INTERES1, MERCADERISTAS
CREATE INDEX ix_visitas_fecha ON VISITAS_MERCADERISTA (fecha_visita DESC)
    INCLUDE (id_visita, id_mercaderista, identificador_punto_interes, id_cliente);

CREATE INDEX ix_visitas_id_mercaderista ON VISITAS_MERCADERISTA (id_mercaderista);
CREATE INDEX ix_visitas_id_cliente ON VISITAS_MERCADERISTA (id_cliente);
CREATE INDEX ix_visitas_identificador_punto ON VISITAS_MERCADERISTA (identificador_punto_interes);

-- ── FOTOS_TOTALES ─────────────────────────────────────────
-- Subconsultas con ROW_NUMBER() OVER(PARTITION BY id_visita ORDER BY fecha_registro DESC)
-- WHERE id_tipo_foto IN (5, 6)
CREATE INDEX ix_fotos_visita_tipo_fecha ON FOTOS_TOTALES (id_visita, id_tipo_foto, fecha_registro DESC)
    INCLUDE (id_foto, file_path, Estado);

CREATE INDEX ix_fotos_id_tipo_foto ON FOTOS_TOTALES (id_tipo_foto);

-- ── RUTA_PROGRAMACION ─────────────────────────────────────
-- Subquery ruta_pre: WHERE activa = 1 GROUP BY id_punto_interes
-- Pending query: WHERE activa = 1 AND dia IN (...)
CREATE INDEX ix_ruta_prog_punto_activo ON RUTA_PROGRAMACION (id_punto_interes, activa)
    INCLUDE (id_ruta, prioridad);

CREATE INDEX ix_ruta_prog_dia_activo ON RUTA_PROGRAMACION (dia, activa)
    INCLUDE (id_ruta, id_punto_interes, id_cliente, prioridad);

-- ── CHAT_MENSAJES_CLIENTE ─────────────────────────────────
-- Subquery chat_pre: WHERE id_visita = X GROUP BY id_visita
CREATE INDEX ix_chat_msgs_visita ON CHAT_MENSAJES_CLIENTE (id_visita)
    INCLUDE (visto, tipo_mensaje);

-- ── MERCADERISTAS ─────────────────────────────────────────
-- Pending query: WHERE activo = 1
CREATE INDEX ix_mercaderistas_activo ON MERCADERISTAS (activo)
    INCLUDE (id_mercaderista, nombre);
