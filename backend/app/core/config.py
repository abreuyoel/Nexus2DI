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

    DB_DRIVER: str = "ODBC Driver 18 for SQL Server"
    DB_SERVER: str = "172.174.41.110"
    DB_NAME: str = "epran-qa"
    # Opcionales cuando se usa Trusted_Connection (Windows Auth)
    DB_USER: Optional[str] = None
    DB_PASSWORD: Optional[str] = None
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10
    # True → usa Windows Authentication (Trusted_Connection=yes) sin user/pass
    DB_TRUSTED_CONNECTION: bool = False

    ENVIRONMENT: str = "development"

    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379

    AZURE_STORAGE_CONNECTION_STRING: str = ""
    AZURE_CONTAINER_NAME: str = "epran"
    AZURE_ACCOUNT_NAME: str = "saeprandat001"

    VAPID_PRIVATE_KEY: str = ""
    VAPID_PUBLIC_KEY: str = ""
    VAPID_EMAIL: str = "mailto:admin@epran.com"

    SCHEDULER_INTERVAL_MINUTES: int = 60
    SCHEDULER_TIMEZONE: str = "America/Caracas"

    FRONTEND_URL: str = "http://localhost:4200"

    @property
    def DATABASE_URL(self) -> str:
        driver = self.DB_DRIVER.replace(" ", "+")
        if self.DB_TRUSTED_CONNECTION:
            # Windows Authentication — no user/password en la URL
            return (
                f"mssql+pyodbc://@{self.DB_SERVER}/{self.DB_NAME}"
                f"?driver={driver}"
                f"&Trusted_Connection=yes"
                f"&TrustServerCertificate=yes"
            )
        # SQL Server Authentication (producción / Azure)
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
