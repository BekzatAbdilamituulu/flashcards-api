from tests.conftest import login, register


def test_register_and_login(client):
    token = register(client, "u1", "pass1234")
    assert isinstance(token, str) and token

    token2 = login(client, "u1", "pass1234")
    assert isinstance(token2, str) and token2


def test_register_duplicate_username(client):
    register(client, "u1", "pass1234")
    r = client.post("/auth/register", json={"username": "u1", "password": "pass1234"})
    assert r.status_code == 400
    assert "exists" in r.json()["detail"].lower()


def test_login_invalid_credentials(client):
    register(client, "u1", "pass1234")
    r = client.post(
        "/auth/login",
        data={"username": "u1", "password": "wrong"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert r.status_code == 401
