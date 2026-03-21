from fastapi import HTTPException

from app import crud
from app.models import User
from app.services.google_auth import GoogleIdentity
from app.services.security import hash_password
from tests.conftest import register


def test_register_and_login(client):
    token = register(client, "u1", "pass1234")
    assert isinstance(token, str) and token


def test_refresh_rotates_tokens(client):
    client.post("/api/v1/auth/register", json={"username": "u_refresh", "password": "12345678"})
    login = client.post(
        "/api/v1/auth/login-json", json={"username": "u_refresh", "password": "12345678"}
    )
    assert login.status_code == 200, login.text
    tokens = login.json()

    r1 = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r1.status_code == 200, r1.text
    tokens2 = r1.json()
    assert tokens2["access_token"] != tokens["access_token"]
    assert tokens2["refresh_token"] != tokens["refresh_token"]

    # old refresh should fail (rotation)
    r2 = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert r2.status_code == 401


def test_register_duplicate_username(client):
    register(client, "u1", "pass1234")
    r = client.post("/api/v1/auth/register", json={"username": "u1", "password": "pass1234"})
    assert r.status_code == 400
    assert "exists" in r.json()["detail"].lower()


def test_login_json(client):
    client.post("/api/v1/auth/register", json={"username": "u1", "password": "12345678"})

    r = client.post("/api/v1/auth/login-json", json={"username": "u1", "password": "12345678"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_login_form(client):
    client.post("/api/v1/auth/register", json={"username": "u_form", "password": "12345678"})

    r = client.post("/api/v1/auth/login", data={"username": "u_form", "password": "12345678"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert "access_token" in body
    assert "refresh_token" in body


def test_google_login_creates_new_user(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda _: GoogleIdentity(
            sub="google-sub-1",
            email="alex.reader@gmail.com",
            email_verified=True,
            name="Alex Reader",
        ),
    )

    r = client.post("/api/v1/auth/google", json={"id_token": "good-token"})
    assert r.status_code == 200, r.text

    me = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {r.json()['access_token']}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["email"] == "alex.reader@gmail.com"
    assert me.json()["email_verified"] is True
    assert me.json()["username"] == "alex_reader"


def test_google_login_existing_linked_user(client, db_session, monkeypatch):
    user = crud.create_user(
        db_session,
        "linked_user",
        hash_password("not-used"),
        email="linked@gmail.com",
        google_sub="google-linked",
        email_verified=True,
    )
    db_session.commit()

    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda _: GoogleIdentity(
            sub="google-linked",
            email="linked@gmail.com",
            email_verified=True,
            name="Linked User",
        ),
    )

    r = client.post("/api/v1/auth/google", json={"id_token": "good-token"})
    assert r.status_code == 200, r.text

    me = client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {r.json()['access_token']}"},
    )
    assert me.status_code == 200, me.text
    assert me.json()["username"] == user.username


def test_google_login_rejects_existing_password_account_with_same_email(client, db_session, monkeypatch):
    register(client, "password_user", "pass1234")
    user = db_session.query(User).filter(User.username == "password_user").first()
    user.email = "existing@gmail.com"
    db_session.commit()

    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda _: GoogleIdentity(
            sub="new-google-sub",
            email="existing@gmail.com",
            email_verified=True,
            name="Existing User",
        ),
    )

    r = client.post("/api/v1/auth/google", json={"id_token": "good-token"})
    assert r.status_code == 409, r.text
    assert "existing method" in r.json()["detail"].lower()


def test_google_login_rejects_invalid_token(client, monkeypatch):
    def _raise(_):
        raise HTTPException(status_code=401, detail="Invalid Google token")

    monkeypatch.setattr("app.routers.auth.verify_google_id_token", _raise)

    r = client.post("/api/v1/auth/google", json={"id_token": "bad-token"})
    assert r.status_code == 401, r.text
    assert r.json()["detail"] == "Invalid Google token"


def test_google_login_rejects_unverified_email(client, monkeypatch):
    def _raise(_):
        raise HTTPException(status_code=400, detail="Google account email is not verified")

    monkeypatch.setattr("app.routers.auth.verify_google_id_token", _raise)

    r = client.post("/api/v1/auth/google", json={"id_token": "bad-token"})
    assert r.status_code == 400, r.text
    assert r.json()["detail"] == "Google account email is not verified"


def test_google_user_refresh_and_logout(client, monkeypatch):
    monkeypatch.setattr(
        "app.routers.auth.verify_google_id_token",
        lambda _: GoogleIdentity(
            sub="google-sub-refresh",
            email="refresh@gmail.com",
            email_verified=True,
            name="Refresh User",
        ),
    )

    login = client.post("/api/v1/auth/google", json={"id_token": "good-token"})
    assert login.status_code == 200, login.text
    tokens = login.json()

    refreshed = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refreshed.status_code == 200, refreshed.text

    logout = client.post("/api/v1/auth/logout", json={"refresh_token": refreshed.json()["refresh_token"]})
    assert logout.status_code == 200, logout.text

    after_logout = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refreshed.json()["refresh_token"]},
    )
    assert after_logout.status_code == 401, after_logout.text
