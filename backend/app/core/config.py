from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Sin default a propósito: si falta la env var, pydantic-settings debe
    # fallar fuerte al arrancar en vez de caer en un secreto débil conocido
    # (los valores viejos de este archivo quedaron expuestos en git).
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480

    DB_DRIVER: str = "ODBC Driver 17 for SQL Server"
    DB_SERVER: str = "172.174.41.110"
    DB_NAME: str = "epran-qa"
    DB_USER: str
    DB_PASSWORD: str
    # Con --workers 1 (ver Dockerfile) todo el tráfico de ~400 mercaderistas +
    # usuarios web pasa por un solo proceso -- 5+10=15 conexiones máximo se
    # agotaban rápido bajo carga real, dejando requests en cola hasta 30s
    # (pool_timeout) antes de fallar: eso es lo que se percibía como "el
    # servidor está lento" y, si superaba el timeout del proxy/Cloudflare, un
    # 502 directo. Puede sobreescribirse por env var si hace falta ajustar
    # más sin tocar código.
    DB_POOL_SIZE: int = 20
    DB_MAX_OVERFLOW: int = 30

    ENVIRONMENT: str = "development"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: Optional[str] = None
    # DB lógica separada de epran_backend (usa la 0 para socket.io/BullMQ en
    # la misma instancia) -- aísla el canal de pub/sub de este backend.
    REDIS_DB: int = 1

    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_CONTAINER_NAME: str = "epran"
    AZURE_ACCOUNT_NAME: str = "saeprandat001"

    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_EMAIL: str = "mailto:admin@epran.com"

    SCHEDULER_INTERVAL_MINUTES: int = 60
    SCHEDULER_TIMEZONE: str = "America/Caracas"
    PLAN_ACCION_INTERVAL_HOURS: int = 4
    # Quiebre dinámico (N2): Capa 1 (línea base de percentiles) es cara --
    # agrega sobre 90 días de balances -- y cambia poco día a día, así que
    # corre una vez al día. Capa 2 (alertas) es barata y depende de balances
    # frescos; correrla más seguido que Capa 1 tiene sentido. El diseño
    # original decía "en cada sync de balance", pero enganchar esto al
    # endpoint de sync de cada mercaderista es justo el patrón que ya tumbó
    # el sitio una vez con Plan de Acción (N1) -- se usa el mismo intervalo
    # que Plan de Acción como aproximación segura en vez de eso.
    QUIEBRE_LINEA_BASE_INTERVAL_HOURS: int = 24
    QUIEBRE_ALERTAS_INTERVAL_HOURS: int = 4
    # Cobertura de encuestas médicas (S4): pocos cientos de médicos en
    # total, cambia poco en el día -- una vez al día alcanza de sobra.
    COBERTURA_ENCUESTAS_INTERVAL_HOURS: int = 24

    FRONTEND_URL: str = "http://localhost:4200"

    # IA (Ollama) -- mismo servicio "ollama" (namespace default) que ya usa
    # epran_backend para analizar fotos de precios con el modelo "llava"
    # (ver epran_backend/src/infrastructure/ai/ollama.service.ts). Reusado
    # acá para leer notas de pedido en papel: se manda la foto directo al
    # modelo de visión (sin motor de OCR aparte) y se le pide texto
    # estructurado en JSON.
    OLLAMA_API_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llava"

    # Notificaciones por correo del módulo de Ventas (confirmación de pedido,
    # alertas de pedido grande, etc.) -- sin valores reales por defecto:
    # mientras no se configuren, EmailService.enviar() hace no-op y loguea en
    # vez de fallar, para no bloquear el flujo de ventas por esto.
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "ventas@epran.com"

    @property
    def DATABASE_URL(self) -> str:
        driver = self.DB_DRIVER.replace(" ", "+")
        return (
            f"mssql+pyodbc://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_SERVER}/{self.DB_NAME}"
            f"?driver={driver}&TrustServerCertificate=yes"
        )

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
