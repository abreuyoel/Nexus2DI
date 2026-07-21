"""
media.py — Proxy de imágenes desde Azure Blob Storage.

Problema que resuelve:
  El service worker de Angular (ngsw-worker.js) intercepta TODOS los fetch
  de la página y los ejecuta con su propio fetch() desde el contexto del SW.
  Ese contexto hereda la CSP del documento, que incluye connect-src. Si la
  CSP no permite el dominio externo del blob storage, o si hay discrepancias
  entre versiones de ngsw cacheadas, las peticiones fallan con:
    "Refused to connect because it violates the document's Content Security Policy"

Solución:
  Las URLs de las imágenes se sustituyen por /api/media/foto?path=<blob_path>.
  El backend es el que realiza el fetch al blob storage (server-side), obtiene
  los bytes y los devuelve al cliente. Para el browser y el ngsw, la petición
  es a 'self' (mismo origen), siempre permitida por el CSP.

Seguridad:
  - Requiere JWT válido (get_current_user) → solo usuarios autenticados.
  - Solo se sirven blobs del contenedor configurado (AZURE_CONTAINER_NAME).
  - El blob_path es el path relativo dentro del contenedor; nunca puede
    escapar del contenedor porque se usa directamente en get_sas_url().
  - Respuesta con Content-Type correcto y Cache-Control de 1 hora.
"""

import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from app.core.auth import get_current_user
from app.models.user import Usuario
from app.services.azure_service import azure_service

router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("/foto")
async def proxy_foto(
    path: str = Query(..., description="Blob path relativo al contenedor"),
    current_user: Usuario = Depends(get_current_user),
) -> Response:
    """
    Sirve una imagen de Azure Blob Storage como respuesta HTTP directa.
    El cliente (browser/ngsw) la recibe como si viniera del mismo origen.
    """
    if not path or ".." in path:
        raise HTTPException(status_code=400, detail="path inválido")

    try:
        image_bytes = azure_service.download_blob(path)
    except Exception as exc:
        # El blob puede no existir o haber expirado — 404 claro para el cliente
        raise HTTPException(status_code=404, detail=f"Imagen no encontrada: {exc}") from exc

    # Detectar content-type básico por extensión
    ext = path.rsplit(".", 1)[-1].lower() if "." in path else "jpg"
    content_type_map = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "webp": "image/webp",
        "gif": "image/gif", "svg": "image/svg+xml",
    }
    content_type = content_type_map.get(ext, "image/jpeg")

    return Response(
        content=image_bytes,
        media_type=content_type,
        headers={
            # Cache 1 hora en el browser → reduce peticiones repetidas.
            # no-cache en CDN/proxy → siempre revalida desde el origen.
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )
