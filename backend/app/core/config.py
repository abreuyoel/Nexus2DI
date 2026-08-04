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

    FRONTEND_URL: str = "http://localhost:4200"

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
