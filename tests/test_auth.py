def test_register_success(client):
    r = client.post("/auth/register", json={"username": "u1", "password": "12345678"})
    assert r.status_code in (200, 201), r.text
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate_username(client):
    client.post("/auth/register", json={"username": "u2", "password": "12345678"})
    r = client.post("/auth/register", json={"username": "u2", "password": "12345678"})
    assert r.status_code in (400, 409), r.text


def test_login_success(client):
    client.post("/auth/register", json={"username": "u3", "password": "12345678"})
    # If your /auth/login uses OAuth2PasswordRequestForm, it expects form data:
    r = client.post("/auth/login", data={"username": "u3", "password": "12345678"})
    assert r.status_code == 200, r.text
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client):
    client.post("/auth/register", json={"username": "u4", "password": "12345678"})
    r = client.post("/auth/login", data={"username": "u4", "password": "WRONG"})
    assert r.status_code in (401, 400), r.text
