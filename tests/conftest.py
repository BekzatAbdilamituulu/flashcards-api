import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os


os.environ.setdefault("DATABASE_URL", "sqlite:///./data/test_flashcards.db")
os.environ.setdefault("SECRET_KEY", "test-secret")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
os.environ.setdefault("REFRESH_SECRET_KEY", "test-refresh-secret")
os.environ.setdefault("REFRESH_TOKEN_EXPIRE_DAYS", "30")



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
    r = client.post("/api/v1/auth/register", json={"username": username, "password": password})
    assert r.status_code == 201, r.text
    return r.json()["access_token"]


def login(client, username: str, password: str = "1234") -> str:
    r = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def create_user_and_token(client: TestClient, username: str, password: str = "pass1234") -> tuple[dict, str]:
    token = register(client, username, password)
    me = client.get("/api/v1/users/me", headers=auth_headers(token))
    assert me.status_code == 200, me.text
    return me.json(), token
    
def login_user_tokens(client, username: str, password: str = "1234") -> dict:
    r = client.post("/api/v1/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()


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
        "/api/v1/admin/languages",
        json={"name": name, "code": code},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def create_deck(client: TestClient, token: str, name: str, src_id: int, tgt_id: int) -> int:
    r = client.post(
        "/api/v1/decks",
        json={"name": name, "source_language_id": src_id, "target_language_id": tgt_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def add_card(client: TestClient, token: str, deck_id: int, front: str, back: str, example_sentence: str | None = None) -> dict:
    r = client.post(
        f"/api/v1/decks/{deck_id}/cards",
        json={"front": front, "back": back, "example_sentence": example_sentence},
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    return r.json()

@pytest.fixture()
def user_token(client):
    # one normal user for stage tests
    _, token = create_user_and_token(client, "user")
    return token
    
@pytest.fixture()
def token_headers(user_token):
    return auth_headers(user_token)

@pytest.fixture()
def make_deck_with_cards(client, user_token):
    def _make(n=1):
        # admin creates languages
        _, admin_token = create_user_and_token(client, "admin")

        en_id = admin_create_language(client, admin_token, "English", "en")
        ru_id = admin_create_language(client, admin_token, "Russian", "ru")

        # IMPORTANT: deck created by same user_token
        deck_id = create_deck(client, user_token, "Deck", en_id, ru_id)

        cards = []
        for i in range(n):
            c = add_card(client, user_token, deck_id, f"word{i}", f"слово{i}")
            cards.append(c)

        return deck_id, cards

    return _make