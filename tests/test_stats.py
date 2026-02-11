from datetime import datetime, timedelta

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


def study(client, token: str, word_id: int, correct: bool):
    r = client.post(f"/study/{word_id}", json={"correct": correct}, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    return r.json()


def test_stats_requires_auth(client):
    r = client.get("/stats?language_id=1")
    assert r.status_code in (401, 403), r.text


def test_stats_counts_new_learning_mastered_and_overdue(client, db):
    token = create_user_and_login(client, "u1")
    lang_id = create_language(client, token)

    # total 3 words
    w1 = create_word(client, token, lang_id, "w1", "t1")
    w2 = create_word(client, token, lang_id, "w2", "t2")
    w3 = create_word(client, token, lang_id, "w3", "t3")

    # w1: learning (1 correct)
    study(client, token, w1, True)

    # w2: mastered (3 correct)
    study(client, token, w2, True)
    study(client, token, w2, True)
    study(client, token, w2, True)

    # w3: untouched => new

    # make w1 overdue by forcing last_review far in past
    from app import models
    uw1 = db.query(models.UserWord).filter(models.UserWord.word_id == w1).first()
    uw1.last_review = datetime.utcnow() - timedelta(days=10)
    db.commit()

    r = client.get(f"/stats?language_id={lang_id}", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["language_id"] == lang_id
    assert data["total_words"] == 3
    assert data["learned_words"] == 2
    assert data["new_words"] == 1
    assert data["learning_words"] == 1
    assert data["mastered_words"] == 1
    assert data["overdue_words"] >= 1  # w1 should be overdue
