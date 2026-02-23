from tests.conftest import login, register


def test_register_and_login(client):
    token = register(client, "u1", "pass1234")
    assert isinstance(token, str) and token

    token2 = login(client, "u1", "pass1234")
    assert isinstance(token2, str) and token2

def test_refresh_rotates_tokens(client):
    client.post("/api/v1/auth/register", json={"username": "u_refresh", "password": "12345678"})
    login = client.post("/api/v1/auth/login", data={"username": "u_refresh", "password": "12345678"})
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


