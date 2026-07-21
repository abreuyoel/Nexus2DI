"""add_performance_indexes_for_activaciones

Revision ID: 1c8d4f3e7b2a
Revises: df332ad7f2f5
Create Date: 2026-07-20 14:30:00.000000

Índices para optimizar las consultas del endpoint /activaciones:

1. VISITAS_MERCADERISTA  → cubre WHERE fecha + JOINs
2. FOTOS_TOTALES         → cubre window functions (ROW_NUMBER)
3. RUTA_PROGRAMACION     → cubre subquery ruta_pre + pending
4. CHAT_MENSAJES_CLIENTE → cubre subquery chat_pre
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1c8d4f3e7b2a'
down_revision: Union[str, None] = 'df332ad7f2f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── VISITAS_MERCADERISTA ──────────────────────────────────
    # WHERE fecha_visita BETWEEN ... ORDER BY fecha_visita DESC
    # JOIN con CLIENTES, PUNTOS_INTERES1, MERCADERISTAS
    op.create_index(
        'ix_visitas_fecha',
        'VISITAS_MERCADERISTA',
        ['fecha_visita'],
        mssql_include=['id_visita', 'id_mercaderista',
                       'identificador_punto_interes', 'id_cliente']
    )
    # JOIN columns individuales (útil cuando hay filtro por cliente)
    op.create_index(
        'ix_visitas_id_mercaderista',
        'VISITAS_MERCADERISTA',
        ['id_mercaderista']
    )
    op.create_index(
        'ix_visitas_id_cliente',
        'VISITAS_MERCADERISTA',
        ['id_cliente']
    )
    op.create_index(
        'ix_visitas_identificador_punto',
        'VISITAS_MERCADERISTA',
        ['identificador_punto_interes']
    )

    # ── FOTOS_TOTALES ─────────────────────────────────────────
    # Subconsultas con ROW_NUMBER() OVER(PARTITION BY id_visita ORDER BY fecha_registro DESC)
    # WHERE id_tipo_foto IN (5, 6)
    op.create_index(
        'ix_fotos_visita_tipo_fecha',
        'FOTOS_TOTALES',
        ['id_visita', 'id_tipo_foto', 'fecha_registro'],
        mssql_include=['id_foto', 'file_path', 'Estado']
    )
    op.create_index(
        'ix_fotos_id_tipo_foto',
        'FOTOS_TOTALES',
        ['id_tipo_foto']
    )

    # ── RUTA_PROGRAMACION ─────────────────────────────────────
    # Subquery ruta_pre: WHERE activa = 1 GROUP BY id_punto_interes
    # Pending query: WHERE activa = 1 AND dia IN (...)
    op.create_index(
        'ix_ruta_prog_punto_activo',
        'RUTA_PROGRAMACION',
        ['id_punto_interes', 'activa'],
        mssql_include=['id_ruta', 'prioridad']
    )
    op.create_index(
        'ix_ruta_prog_dia_activo',
        'RUTA_PROGRAMACION',
        ['dia', 'activa'],
        mssql_include=['id_ruta', 'id_punto_interes', 'id_cliente', 'prioridad']
    )

    # ── CHAT_MENSAJES_CLIENTE ─────────────────────────────────
    # Subquery chat_pre: WHERE id_visita = X GROUP BY id_visita
    op.create_index(
        'ix_chat_msgs_visita',
        'CHAT_MENSAJES_CLIENTE',
        ['id_visita'],
        mssql_include=['visto', 'tipo_mensaje']
    )

    # ── MERCADERISTAS ─────────────────────────────────────────
    # Pending query: WHERE activo = 1
    op.create_index(
        'ix_mercaderistas_activo',
        'MERCADERISTAS',
        ['activo'],
        mssql_include=['id_mercaderista', 'nombre']
    )


def downgrade() -> None:
    op.drop_index('ix_visitas_fecha', table_name='VISITAS_MERCADERISTA')
    op.drop_index('ix_visitas_id_mercaderista', table_name='VISITAS_MERCADERISTA')
    op.drop_index('ix_visitas_id_cliente', table_name='VISITAS_MERCADERISTA')
    op.drop_index('ix_visitas_identificador_punto', table_name='VISITAS_MERCADERISTA')
    op.drop_index('ix_fotos_visita_tipo_fecha', table_name='FOTOS_TOTALES')
    op.drop_index('ix_fotos_id_tipo_foto', table_name='FOTOS_TOTALES')
    op.drop_index('ix_ruta_prog_punto_activo', table_name='RUTA_PROGRAMACION')
    op.drop_index('ix_ruta_prog_dia_activo', table_name='RUTA_PROGRAMACION')
    op.drop_index('ix_chat_msgs_visita', table_name='CHAT_MENSAJES_CLIENTE')
    op.drop_index('ix_mercaderistas_activo', table_name='MERCADERISTAS')
