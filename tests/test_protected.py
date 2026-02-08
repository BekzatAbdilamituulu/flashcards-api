def test_protected_requires_token(client):
    r = client.get("/users/me/progress", params={"language_id": 1})
    assert r.status_code in (401, 403), r.text


def test_protected_works_with_token(client):
    client.post("/auth/register", json={"username": "u5", "password": "12345678"})
    login = client.post("/auth/login", data={"username": "u5", "password": "12345678"})
    token = login.json()["access_token"]

    r = client.get(
        "/users/me/progress",
        params={"language_id": 1},
        headers={"Authorization": f"Bearer {token}"},
    )
    # Might be 200 or 404 depending on whether your app has words/language seeded.
    assert r.status_code in (200, 404), r.text
