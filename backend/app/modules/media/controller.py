import urllib.parse
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from app.core.auth import get_current_user
from app.modules.auth.entities import Usuario
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
        raise HTTPException(status_code=404, detail=f"Imagen no encontrada: {exc}") from exc

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
