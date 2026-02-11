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


def test_study_review_increments_progress(client):
    token = create_user_and_login(client, "u1")
    lang_id = create_language(client, token)
    word_id = create_word(client, token, lang_id)

    # 1st review correct
    r = client.post(
        f"/study/{word_id}",
        json={"correct": True},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["word_id"] == word_id
    assert data["times_seen"] == 1
    assert data["times_correct"] == 1

    # 2nd review incorrect
    r = client.post(
        f"/study/{word_id}",
        json={"correct": False},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["times_seen"] == 2
    assert data["times_correct"] == 1  # unchanged


def test_study_cannot_review_foreign_word(client):
    token1 = create_user_and_login(client, "u1")
    token2 = create_user_and_login(client, "u2")

    lang1 = create_language(client, token1, name="English_u1", code="en")
    word_id = create_word(client, token1, lang1)

    r = client.post(
        f"/study/{word_id}",
        json={"correct": True},
        headers=auth_headers(token2),
    )
    assert r.status_code == 404, r.text


def test_study_next_returns_deckout_and_only_my_words(client):
    token1 = create_user_and_login(client, "u1")
    token2 = create_user_and_login(client, "u2")

    # user1 creates language+word
    lang1 = create_language(client, token1, name="English_u1", code="en")
    create_word(client, token1, lang1, text="hello", translation="привет")

    # user2 creates their own language but no words
    lang2 = create_language(client, token2, name="English_u2", code="en")

    # user2 asks next -> current app returns 200 with empty deck
    r = client.get(
        f"/study/next?language_id={lang2}&limit=20",
        headers=auth_headers(token2),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["language_id"] == lang2
    assert data["count"] == 0
    assert data["words"] == []

    # user1 asks next -> should return 1 word in DeckOut
    r = client.get(
        f"/study/next?language_id={lang1}&limit=20",
        headers=auth_headers(token1),
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["language_id"] == lang1
    assert data["count"] == 1
    assert isinstance(data["words"], list)
    assert data["words"][0]["language_id"] == lang1
