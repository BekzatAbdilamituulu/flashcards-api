from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import settings

DATABASE_URL = settings.resolved_database_url


def create_db_engine():
    if DATABASE_URL.startswith("sqlite"):
        return create_engine(
            DATABASE_URL,
            connect_args={"check_same_thread": False, "timeout": 5},
        )

    return create_engine(
        DATABASE_URL,
        pool_pre_ping=True,
    )


engine = create_db_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()