from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from app.core.config import settings

# Motor Síncrono (Original - No tocar para mantener retrocompatibilidad)
engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Motor Asíncrono (Nuevo - Para endpoints de alta carga)
# Se reemplaza `mssql+pyodbc` por `mssql+aioodbc` dinámicamente
ASYNC_DATABASE_URL = settings.DATABASE_URL.replace("mssql+pyodbc", "mssql+aioodbc")
if "MultipleActiveResultSets" not in ASYNC_DATABASE_URL and "MARS_Connection" not in ASYNC_DATABASE_URL:
    sep = "&" if "?" in ASYNC_DATABASE_URL else "?"
    ASYNC_DATABASE_URL += f"{sep}MultipleActiveResultSets=True"

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    pool_pre_ping=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=30,
    pool_recycle=1800,
    echo=False,
)

AsyncSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=async_engine, class_=AsyncSession, expire_on_commit=False)

async def get_async_db():
    async with AsyncSessionLocal() as db:
        yield db
