from uuid import uuid4
from datetime import datetime, timedelta, timezone
from app import models

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
    r = client.post(
        "/languages",
        json={"name": name, "code": code},
        headers=auth_headers(token),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def create_word(client, token: str, language_id: int, text="hello", translation="привет") -> int:
    r = client.post(
        "/words",
        json={
            "text": text,
            "translation": translation,
            "example_sentence": "",
            "language_id": language_id,
        },
        headers=auth_headers(token),
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


# -------------------------
# Tests
# -------------------------

def test_deck_requires_auth(client):
    r = client.get("/deck?language_id=1&limit=10")
    assert r.status_code in (401, 403), r.text


def test_deck_for_new_user_returns_new_items(client):
    token = create_user_and_login(client, "u1")
    lang_id = create_language(client, token)

    for i in range(20):
        create_word(client, token, lang_id, text=f"w{i}", translation=f"t{i}")

    r = client.get(
        f"/deck?language_id={lang_id}&limit=10",
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text

    data = r.json()
    assert len(data) <= 10
    assert len(data) > 0

    assert "word" in data[0]
    assert "status" in data[0]

    assert all(item["status"] == "new" for item in data)


def test_deck_respects_limit(client):
    token = create_user_and_login(client, "u1")
    lang_id = create_language(client, token)

    for i in range(50):
        create_word(client, token, lang_id, text=f"w{i}", translation=f"t{i}")

    r = client.get(
        f"/deck?language_id={lang_id}&limit=5",
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    assert len(r.json()) <= 5


def test_deck_has_no_duplicates(client):
    token = create_user_and_login(client, "u1")
    lang_id = create_language(client, token)

    for i in range(30):
        create_word(client, token, lang_id, text=f"w{i}", translation=f"t{i}")

    r = client.get(
        f"/deck?language_id={lang_id}&limit=20",
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text

    ids = [item["word"]["id"] for item in r.json()]
    assert len(ids) == len(set(ids))


def test_deck_is_user_specific(client):
    token1 = create_user_and_login(client, "u1")
    token2 = create_user_and_login(client, "u2")

    lang1 = create_language(client, token1, "English_u1", "en")
    create_word(client, token1, lang1, "hello", "привет")

    # user2 should not receive user1 data
    r = client.get(
        f"/deck?language_id={lang1}&limit=10",
        headers=auth_headers(token2),
    )

    # depending on your design → 404 OR empty list
    assert r.status_code == 404, r.text
    if r.status_code == 200:
        assert r.json() == []


def test_deck_includes_overdue_items(client, db):
    token = create_user_and_login(client, "u1")
    lang_id = create_language(client, token)

    # create a word
    word_id = create_word(client, token, lang_id)

    from app import models
    user = db.query(models.User).filter(models.User.username.like("u1_%")).first()
    uw = (
        db.query(models.UserWord)
        .filter_by(word_id=word_id, user_id=user.id)
        .first()
    )
    if not uw:
        uw = models.UserWord(user_id=user.id, word_id=word_id, times_seen=1, times_correct=1)
        db.add(uw)

    uw.times_seen = 5
    uw.times_correct = 1
    uw.last_review = datetime.utcnow() - timedelta(days=10)
    db.commit()

    r = client.get(
        f"/deck?language_id={lang_id}&limit=10",
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    ids = [item["word"]["id"] for item in data]
    assert word_id in ids
