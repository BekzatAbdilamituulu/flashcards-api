from uuid import uuid4

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def create_user_and_login(client, prefix="user") -> str:
    username = f"{prefix}_{uuid4().hex[:6]}"
    password = "1234"

    r = client.post("/auth/register", json={"username": username, "password": password})
    assert r.status_code in (200, 201), r.text

    # OAuth2PasswordRequestForm -> must be form data
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]




def test_languages_are_private(client, token_user1, token_user2):
    # user1 creates language
    client.post(
        "/languages",
        json={"name": "English", "code": "en"},
        headers={"Authorization": f"Bearer {token_user1}"}
    )

    # user2 list languages
    res = client.get(
        "/languages",
        headers={"Authorization": f"Bearer {token_user2}"}
    )

    assert res.status_code == 200
    assert res.json() == []   


def test_cannot_update_foreign_language(client, token_user1, token_user2):
    # user1 creates
    res = client.post(
        "/languages",
        json={"name": "English", "code": "en"},
        headers={"Authorization": f"Bearer {token_user1}"}
    )
    lang_id = res.json()["id"]

    # user2 tries update
    res = client.patch(
        f"/languages/{lang_id}",
        json={"name": "German"},
        headers={"Authorization": f"Bearer {token_user2}"}
    )

    assert res.status_code == 404
