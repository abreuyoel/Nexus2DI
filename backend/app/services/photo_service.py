import io
import exifread
from typing import Optional
from datetime import datetime
from PIL import Image
from app.services.azure_service import azure_service


def extract_exif_data(file_bytes: bytes) -> dict:
    result = {"latitud": None, "longitud": None, "timestamp": None, "camera_model": None}
    try:
        tags = exifread.process_file(io.BytesIO(file_bytes), details=False)

        if "GPS GPSLatitude" in tags and "GPS GPSLongitude" in tags:
            lat = _dms_to_decimal(tags["GPS GPSLatitude"].values, str(tags.get("GPS GPSLatitudeRef", "N")))
            lon = _dms_to_decimal(tags["GPS GPSLongitude"].values, str(tags.get("GPS GPSLongitudeRef", "E")))
            result["latitud"] = lat
            result["longitud"] = lon

        if "EXIF DateTimeOriginal" in tags:
            dt_str = str(tags["EXIF DateTimeOriginal"])
            result["timestamp"] = datetime.strptime(dt_str, "%Y:%m:%d %H:%M:%S")

        if "Image Model" in tags:
            result["camera_model"] = str(tags["Image Model"])
    except Exception:
        pass
    return result


def _dms_to_decimal(dms_values, ref: str) -> float:
    d = float(dms_values[0].num) / float(dms_values[0].den)
    m = float(dms_values[1].num) / float(dms_values[1].den)
    s = float(dms_values[2].num) / float(dms_values[2].den)
    decimal = d + m / 60 + s / 3600
    if ref in ("S", "W"):
        decimal = -decimal
    return decimal


def process_and_upload_photo(file_bytes: bytes, content_type: str = "image/jpeg", prefix: str = "fotos") -> dict:
    exif = extract_exif_data(file_bytes)
    compressed = compress_image(file_bytes)
    blob_path = azure_service.upload_photo(compressed, content_type, prefix)
    url = azure_service.get_proxy_url(blob_path)
    return {
        "blob_path": blob_path,
        "url": url,
        "tamano_bytes": len(file_bytes),
        **exif,
    }


def compress_image(file_bytes: bytes, max_size: int = 1920, quality: int = 85) -> bytes:
    try:
        img = Image.open(io.BytesIO(file_bytes))
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        img.thumbnail((max_size, max_size), Image.LANCZOS)
        output = io.BytesIO()
        img.save(output, format="JPEG", quality=quality, optimize=True)
        return output.getvalue()
    except Exception:
        return file_bytes
