import uuid
import io
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Optional
from azure.storage.blob import BlobServiceClient, ContentSettings, generate_blob_sas, BlobSasPermissions
from app.core.config import settings


def _extract_account_key(conn_str: str) -> Optional[str]:
    for part in conn_str.split(";"):
        if part.startswith("AccountKey="):
            return part[len("AccountKey="):]
    return None


class AzureStorageService:
    def __init__(self):
        self._client: Optional[BlobServiceClient] = None

    @property
    def client(self) -> BlobServiceClient:
        if self._client is None:
            self._client = BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            )
        return self._client

    def upload_photo(self, file_bytes: bytes, content_type: str = "image/jpeg", prefix: str = "fotos") -> str:
        blob_name = f"{prefix}/{uuid.uuid4()}.jpg"
        container = self.client.get_container_client(settings.AZURE_CONTAINER_NAME)
        container.upload_blob(
            name=blob_name,
            data=file_bytes,
            content_settings=ContentSettings(content_type=content_type),
            overwrite=True,
        )
        return blob_name

    def get_sas_url(self, blob_name: str, hours: int = 2) -> str:
        """Return a SAS-signed URL valid for `hours` hours. Handles private containers and special characters in paths."""
        account_key = _extract_account_key(settings.AZURE_STORAGE_CONNECTION_STRING)
        encoded = urllib.parse.quote(blob_name, safe="/")
        base = f"https://{settings.AZURE_ACCOUNT_NAME}.blob.core.windows.net/{settings.AZURE_CONTAINER_NAME}/{encoded}"
        if not account_key:
            return base
        # Expiry redondeado a ventana diaria (UTC) -> URL idéntica todo el día y cacheable.
        now = datetime.now(timezone.utc)
        min_days = max(1, (hours + 23) // 24)
        expiry = (now + timedelta(days=min_days + 1)).replace(hour=0, minute=0, second=0, microsecond=0)
        sas = generate_blob_sas(
            account_name=settings.AZURE_ACCOUNT_NAME,
            container_name=settings.AZURE_CONTAINER_NAME,
            blob_name=blob_name,
            account_key=account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry,
        )
        return f"{base}?{sas}"

    def get_blob_url(self, blob_name: str) -> str:
        encoded = urllib.parse.quote(blob_name, safe="/")
        return f"https://{settings.AZURE_ACCOUNT_NAME}.blob.core.windows.net/{settings.AZURE_CONTAINER_NAME}/{encoded}"

    def get_proxy_url(self, blob_name: str) -> Optional[str]:
        """Devuelve la URL del proxy interno para bypassear CSP/ngsw en el frontend."""
        if not blob_name:
            return None
        encoded = urllib.parse.quote(blob_name, safe="")
        return f"/api/media/foto?path={encoded}"

    def download_blob(self, blob_name: str) -> bytes:
        container = self.client.get_container_client(settings.AZURE_CONTAINER_NAME)
        blob = container.get_blob_client(blob_name)
        return blob.download_blob().readall()

    def delete_blob(self, blob_name: str) -> None:
        container = self.client.get_container_client(settings.AZURE_CONTAINER_NAME)
        blob = container.get_blob_client(blob_name)
        blob.delete_blob()


azure_service = AzureStorageService()
