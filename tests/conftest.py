import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# IMPORTANT: ensure models are imported so Base.metadata is populated
from app import models  # noqa: F401
from app.main import app
from app.database import Base, get_db

SQLALCHEMY_DATABASE_URL = "sqlite:///./test_flashcards.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 5},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def _create_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    # keep tests isolated using a nested transaction pattern
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


from uuid import uuid4

def register_user(client, username: str, password: str = "1234") -> None:
    r = client.post("/auth/register", json={"username": username, "password": password})
    assert r.status_code in (200, 201), r.text

def login_user(client, username: str, password: str = "1234") -> str:
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

def create_user_and_token(client, prefix="user") -> tuple[str, str]:
    username = f"{prefix}_{uuid4().hex[:8]}"
    password = "1234"
    register_user(client, username, password)
    token = login_user(client, username, password)
    return username, token

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture()
def user_token(client):
    return create_user_and_token(client, "user")[1]

@pytest.fixture()
def admin_token(client):
    # admin gate defaults to username "admin" (see deps.require_admin)
    # We create it per-test (transactional DB makes it isolated).
    register_user(client, "admin", "1234")
    return login_user(client, "admin", "1234")