from uuid import uuid4

def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}

def create_user_and_login(client, prefix="user") -> str:
    username = f"{prefix}_{uuid4().hex[:6]}"
    password = "1234"
    r = client.post("/auth/register", json={"username": username, "password": password})
    assert r.status_code in (200, 201), r.text
    r = client.post("/auth/login", data={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]

def create_language(client, token: str, name="English", code="en") -> int:
    r = client.post("/languages", json={"name": name, "code": code}, headers=auth_headers(token))
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]

def create_word(client, token: str, language_id: int, text="hello", translation="привет") -> int:
    r = client.post(
        "/words",
        json={"text": text, "translation": translation, "example_sentence": "", "language_id": language_id},
        headers=auth_headers(token),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]

def test_study_status_basic_counts(client):
    token = create_user_and_login(client, "u1")
    lang_id = create_language(client, token)
    w1 = create_word(client, token, lang_id, text="hello", translation="привет")
    create_word(client, token, lang_id, text="bye", translation="пока")

    r = client.get(f"/study/status?language_id={lang_id}", headers=auth_headers(token))
    assert r.status_code == 200
    data = r.json()
    assert data["due_count"] == 0
    assert data["new_available_count"] == 2
    assert data["next_due_at"] is None

    r = client.post(f"/study/{w1}", json={"quality": 4}, headers=auth_headers(token))
    assert r.status_code == 200

    r = client.get(f"/study/status?language_id={lang_id}", headers=auth_headers(token))
    data = r.json()
    assert data["reviewed_today"] == 1
    assert data["new_introduced_today"] == 1
    assert data["new_available_count"] == 1
    assert data["next_due_at"] is not None
