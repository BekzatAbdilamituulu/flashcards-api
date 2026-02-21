import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


from app.database import Base, get_db

# IMPORTANT: ensure models are imported before create_all
import app.models  # noqa: F401
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from app.main import app



def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register(client: TestClient, username: str, password: str = "pass1234") -> str:
    r = client.post("/auth/register", json={"username": username, "password": password})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def login(client: TestClient, username: str, password: str = "pass1234") -> str:
    # OAuth2PasswordRequestForm => form fields
    r = client.post(
        "/auth/login",
        data={"username": username, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def create_user_and_token(client: TestClient, username: str, password: str = "pass1234") -> tuple[dict, str]:
    token = register(client, username, password)
    me = client.get("/users/me", headers=auth_headers(token))
    assert me.status_code == 200, me.text
    return me.json(), token


@pytest.fixture(autouse=True)
def _admin_env(monkeypatch):
    # Your admin gate is env-based (deps.require_admin)
    monkeypatch.setenv("ADMIN_USERNAMES", "admin")
    yield


@pytest.fixture()
def db_session(tmp_path):
    # Fresh SQLite file DB per test
    db_file = tmp_path / "test.sqlite"
    url = f"sqlite:///{db_file}"

    engine = create_engine(url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    Base.metadata.create_all(bind=engine)

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


# --------- small helpers used by many tests ---------

def admin_create_language(client: TestClient, admin_token: str, name: str, code: str) -> int:
    r = client.post(
        "/admin/languages",
        json={"name": name, "code": code},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def create_deck(client: TestClient, token: str, name: str, src_id: int, tgt_id: int) -> int:
    r = client.post(
        "/decks",
        json={"name": name, "source_language_id": src_id, "target_language_id": tgt_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def add_card(client: TestClient, token: str, deck_id: int, front: str, back: str, example_sentence: str | None = None) -> dict:
    r = client.post(
        f"/decks/{deck_id}/cards",
        json={"front": front, "back": back, "example_sentence": example_sentence},
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    return r.json()
