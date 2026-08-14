"""
media.py — Proxy de imágenes desde Azure Blob Storage o disco local.

Autenticación:
  Las URLs incluyen ?token=<JWT> generado por el servidor en _foto_url().
  Así las etiquetas <img> pueden autenticarse sin enviar header Authorization.
  El token es válido 24h y está firmado con SECRET_KEY.

Seguridad:
  - Token JWT en query param (type=media, exp=24h).
  - Validación de path sin path traversal (..).
  - Respuesta con Content-Type correcto y Cache-Control de 1 hora.
"""

import urllib.parse
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from app.core.security import decode_media_token
from jwt.exceptions import InvalidTokenError
from app.services.azure_service import azure_service

router = APIRouter(prefix="/api/media", tags=["media"])


@router.get("/foto")
async def proxy_foto(
    path: str = Query(..., description="Blob path relativo al contenedor o path local /static/..."),
    token: str = Query(..., description="Token JWT de media generado por el servidor"),
) -> Response:
    """
    Sirve una imagen desde Azure Blob Storage o del disco local.
    Autenticación vía token JWT en query param (para tags <img> que
    no pueden enviar header Authorization).
    """
    # Validar token
    try:
        decode_media_token(token)
    except InvalidTokenError:
        raise HTTPException(status_code=403, detail="Token inválido o expirado")

    if not path or ".." in path:
        raise HTTPException(status_code=400, detail="path inválido")

    # --- Path local (fallback guardado en disco durante desarrollo) ---
    if path.startswith("/static/fotos_mercaderista/"):
        import os
        local_base = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "static", "fotos_mercaderista",
        )
        filename = os.path.basename(path)
        local_path = os.path.join(local_base, filename)
        if not os.path.isfile(local_path):
            raise HTTPException(status_code=404, detail=f"Imagen local no encontrada: {filename}")
        try:
            with open(local_path, "rb") as f:
                image_bytes = f.read()
        except Exception as exc:
            raise HTTPException(status_code=404, detail=f"Error leyendo archivo local: {exc}") from exc
    else:
        # --- Azure Blob ---
        try:
            image_bytes = azure_service.download_blob(path)
        except Exception as exc:
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
            "Cache-Control": "private, max-age=3600",
            "X-Content-Type-Options": "nosniff",
        },
    )
