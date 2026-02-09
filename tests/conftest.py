import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db


SQLALCHEMY_DATABASE_URL = "sqlite:///./test_flashcards.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="session", autouse=True)
def create_test_db():
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db():
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db):
    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()

from uuid import uuid4

def create_user_and_login(client, prefix="user"):
    username = f"{prefix}_{uuid4().hex[:6]}"
    password = "1234"

    # register
    r = client.post("/auth/register", json={
        "username": username,
        "password": password,
    })
    assert r.status_code in (200, 201), r.text

    # login MUST be form-data
    r = client.post(
        "/auth/login",
        data={"username": username, "password": password}
    )
    assert r.status_code == 200, r.text

    body = r.json()
    assert "access_token" in body, body
    return body["access_token"]


import pytest

@pytest.fixture()
def token_user1(client):
    return create_user_and_login(client, "user1")


@pytest.fixture()
def token_user2(client):
    return create_user_and_login(client, "user2")