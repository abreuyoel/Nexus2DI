"""
Router principal del Portal Mercaderista.
Agrega todos los sub-routers bajo /api/merc.
"""

from fastapi import APIRouter

from app.mercaderista.endpoints.auth import router as auth_router
from app.mercaderista.endpoints.rutas import router as rutas_router
from app.mercaderista.endpoints.visitas import router as visitas_router
from app.mercaderista.endpoints.pdv import router as pdv_router
from app.mercaderista.endpoints.chat import router as chat_router

# Router principal — los prefijos ya están definidos en cada endpoint
router = APIRouter()

router.include_router(auth_router)
router.include_router(rutas_router)
router.include_router(visitas_router)
router.include_router(pdv_router)
router.include_router(chat_router)
