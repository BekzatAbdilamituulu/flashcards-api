def test_register_returns_token(client):
    r = client.post("/auth/register", json={"username": "u1", "password": "12345678"})
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"


def test_register_duplicate_username(client):
    client.post("/auth/register", json={"username": "u2", "password": "12345678"})
    r = client.post("/auth/register", json={"username": "u2", "password": "12345678"})
    assert r.status_code == 400
    assert r.json()["detail"] == "Username already exists"


def test_login_invalid_credentials(client):
    client.post("/auth/register", json={"username": "u3", "password": "12345678"})
    r = client.post("/auth/login", data={"username": "u3", "password": "wrong"})
    assert r.status_code == 401