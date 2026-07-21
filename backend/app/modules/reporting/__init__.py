"""
Módulo de Reporting - Centro de Mando.

Proporciona los endpoints del dashboard de Centro de Mando,
separados en sub-módulos para facilitar su mantenimiento:

- clientes.py:      GET /clientes
- resumen_dia.py:   GET /resumen-dia
- detalle_mercaderistas.py: GET /detalle-mercaderistas
- filtros_opciones.py:      GET /filtros-opciones
- fotos_visualizador.py:    GET /fotos-visualizador
- activaciones.py:          GET /activaciones
- utils.py:                 Utilidades compartidas (_dia_es, _clientes_de_analista)
- dto.py:                   Modelos Pydantic de respuesta
- entities.py:              Entidades SQLAlchemy
"""
