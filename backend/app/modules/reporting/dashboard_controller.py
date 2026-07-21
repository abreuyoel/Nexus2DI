"""
Hub central del módulo Centro de Mando.

Importa y combina todos los sub-módulos de reporting para exponerlos
bajo un único router con el prefijo /api/centro-mando.

La funcionalidad se encuentra separada en los siguientes archivos:
- clientes.py:              GET /clientes
- resumen_dia.py:           GET /resumen-dia
- detalle_mercaderistas.py: GET /detalle-mercaderistas
- filtros_opciones.py:      GET /filtros-opciones
- fotos_visualizador.py:    GET /fotos-visualizador
- activaciones.py:          GET /activaciones
- utils.py:                 Utilidades compartidas (_dia_es, _clientes_de_analista)
- dto.py:                   Modelos Pydantic de respuesta
"""
from fastapi import APIRouter

from app.modules.reporting.clientes import router as clientes_router
from app.modules.reporting.resumen_dia import router as resumen_dia_router
from app.modules.reporting.detalle_mercaderistas import router as detalle_mercaderistas_router
from app.modules.reporting.filtros_opciones import router as filtros_opciones_router
from app.modules.reporting.fotos_visualizador import router as fotos_visualizador_router
from app.modules.reporting.activaciones import router as activaciones_router

router = APIRouter(prefix="/api/centro-mando", tags=["Centro de Mando"])

router.include_router(clientes_router)
router.include_router(resumen_dia_router)
router.include_router(detalle_mercaderistas_router)
router.include_router(filtros_opciones_router)
router.include_router(fotos_visualizador_router)
router.include_router(activaciones_router)
