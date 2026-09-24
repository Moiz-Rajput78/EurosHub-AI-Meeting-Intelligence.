from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models.base import Base


def get_connect_args() -> dict:
    if settings.database_url.startswith("sqlite"):
        return {
            "check_same_thread": False
        }

    return {}


engine = create_engine(
    settings.database_url,
    connect_args=get_connect_args(),
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


def create_database_tables() -> None:
    Base.metadata.create_all(bind=engine)