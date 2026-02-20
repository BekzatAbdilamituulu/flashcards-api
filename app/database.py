from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os 
from .config import settings

#BASE_DIR = Path(__file__).resolve().parent.parent

DATABASE_URL = settings.database_url


engine = create_engine(
    DATABASE_URL,
    # only for sqlite3
    connect_args={"check_same_thread": False, "timeout": 5}
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
