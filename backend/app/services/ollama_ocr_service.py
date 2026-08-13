"""Lectura de notas de pedido en papel vía IA -- sin motor de OCR aparte.

En vez de un pipeline de 2 pasos (Tesseract -> texto -> LLM), se manda la
foto directo a un modelo de VISIÓN en Ollama (mismo servicio "ollama" que ya
usa epran_backend para leer precios en góndola con "llava" -- ver
epran_backend/src/infrastructure/ai/ollama.service.ts) con un prompt que pide
JSON estructurado. Un modelo de visión moderno lee manuscrito razonablemente
bien y evita instalar/mantener tesseract-ocr como dependencia de sistema.

Requiere que el servidor tenga el modelo de visión ya descargado
(`ollama pull llava`, o el que se configure en OLLAMA_MODEL) -- si no está,
Ollama responde 404/500 y esto se degrada a error controlado (nunca lanza
hacia arriba: el caller siempre puede ofrecer carga manual como respaldo).
"""
import base64
import json
import logging
from typing import Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("app")

PROMPT = """Estás viendo la foto de una nota de pedido manuscrita o impresa de un vendedor \
a un cliente (distribución de productos). Extrae la información en JSON con esta forma \
EXACTA, sin texto adicional antes o después:

{
  "cliente_texto": "nombre del cliente tal como aparece escrito, o null si no se ve",
  "fecha_texto": "fecha tal como aparece escrita, o null",
  "productos": [
    {"nombre_texto": "nombre del producto tal como está escrito", "cantidad": 3}
  ],
  "notas_texto": "cualquier observación adicional escrita en la nota, o null",
  "confianza": 0.0 a 1.0 según qué tan legible está la nota
}

Si un número de cantidad no es legible, usa 1 como valor por defecto para ese producto \
pero baja la confianza. Si la imagen no es una nota de pedido, devuelve productos: []."""


class OcrExtractionError(Exception):
    pass


async def leer_nota_pedido(image_bytes: bytes, content_type: str = "image/jpeg") -> dict:
    """Devuelve el JSON estructurado que propone la IA. Nunca None -- si algo
    falla, lanza OcrExtractionError con un mensaje entendible para mostrar al
    vendedor (que siempre puede cargar el pedido a mano como respaldo)."""
    b64 = base64.b64encode(image_bytes).decode("ascii")
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{settings.OLLAMA_API_URL}/api/generate",
                json={
                    "model": settings.OLLAMA_MODEL,
                    "prompt": PROMPT,
                    "images": [b64],
                    "stream": False,
                    "format": "json",
                },
            )
        resp.raise_for_status()
    except httpx.TimeoutException as e:
        raise OcrExtractionError("La IA tardó demasiado en responder (¿modelo de visión cargando por primera vez?)") from e
    except httpx.HTTPStatusError as e:
        logger.error(f"[OllamaOCR] HTTP {e.response.status_code}: {e.response.text[:300]}")
        raise OcrExtractionError(f"El servicio de IA respondió {e.response.status_code} -- ¿está el modelo '{settings.OLLAMA_MODEL}' descargado en el servidor?") from e
    except httpx.HTTPError as e:
        logger.error(f"[OllamaOCR] Error de conexión: {e!r}")
        raise OcrExtractionError("No se pudo conectar con el servicio de IA (Ollama)") from e

    data = resp.json()
    raw = data.get("response", "")
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"[OllamaOCR] Respuesta no es JSON válido: {raw[:300]!r}")
        raise OcrExtractionError("La IA no devolvió un formato reconocible -- intenta con una foto más clara") from e

    productos = parsed.get("productos") or []
    if not isinstance(productos, list):
        productos = []
    return {
        "cliente_texto": parsed.get("cliente_texto"),
        "fecha_texto": parsed.get("fecha_texto"),
        "productos": [
            {"nombre_texto": str(p.get("nombre_texto") or "").strip(), "cantidad": _to_int(p.get("cantidad"))}
            for p in productos if isinstance(p, dict) and (p.get("nombre_texto") or "").strip()
        ],
        "notas_texto": parsed.get("notas_texto"),
        "confianza": _to_float(parsed.get("confianza")),
    }


def _to_int(v) -> int:
    try:
        n = int(float(v))
        return n if n > 0 else 1
    except (TypeError, ValueError):
        return 1


def _to_float(v) -> float:
    try:
        return max(0.0, min(1.0, float(v)))
    except (TypeError, ValueError):
        return 0.0
