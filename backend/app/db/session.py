from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from app.core.config import settings

_connect_args: dict = {}
if settings.DB_TRUSTED_CONNECTION:
    _connect_args["trusted_connection"] = "yes"
elif settings.DB_USER and settings.DB_PASSWORD:
    _connect_args["uid"] = settings.DB_USER
    _connect_args["pwd"] = settings.DB_PASSWORD

engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=30,
    pool_recycle=1800,
    connect_args=_connect_args,
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    print("!!! get_db CALLED !!!", flush=True)
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()
