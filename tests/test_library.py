from tests.conftest import (
    admin_create_language,
    auth_headers,
    create_deck,
    create_user_and_token,
    set_default_languages,
)


def create_library_deck(client, admin_token: str, name: str, src_id: int, tgt_id: int) -> dict:
    r = client.post(
        "/api/v1/library/admin/decks",
        json={
            "name": name,
            "source_language_id": src_id,
            "target_language_id": tgt_id,
        },
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_admin_can_create_library_deck(client):
    _, admin_token = create_user_and_token(client, "admin")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    deck = create_library_deck(client, admin_token, "Top 100 words", en_id, ru_id)

    assert deck["name"] == "Top 100 words"
    assert deck["deck_type"] == "library"
    assert deck["source_language_id"] == en_id
    assert deck["target_language_id"] == ru_id


def test_normal_user_cannot_create_library_deck(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, user_token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    r = client.post(
        "/api/v1/library/admin/decks",
        json={
            "name": "Should fail",
            "source_language_id": en_id,
            "target_language_id": ru_id,
        },
        headers=auth_headers(user_token),
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"] == "Admin only"


def test_admin_can_add_card_to_library_deck(client):
    _, admin_token = create_user_and_token(client, "admin")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    deck = create_library_deck(client, admin_token, "A1", en_id, ru_id)

    r = client.post(
        f"/api/v1/decks/{deck['id']}/cards",
        json={
            "front": "hello",
            "back": "привет",
            "example_sentence": "hello world",
        },
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["front"] == "hello"
    assert body["back"] == "привет"
    assert body["deck_id"] == deck["id"]


def test_normal_user_cannot_add_card_to_library_deck(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, user_token = create_user_and_token(client, "alice")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    deck = create_library_deck(client, admin_token, "A1", en_id, ru_id)

    r = client.post(
        f"/api/v1/decks/{deck['id']}/cards",
        json={
            "front": "hello",
            "back": "привет",
        },
        headers=auth_headers(user_token),
    )
    assert r.status_code == 403, r.text
    assert r.json()["detail"] == "No access to deck"

def test_duplicate_import_is_skipped(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, user_token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    library_deck = create_library_deck(client, admin_token, "A1", en_id, ru_id)

    r = client.post(
        f"/api/v1/decks/{library_deck['id']}/cards",
        json={"front": "hello", "back": "привет"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 201, r.text
    library_card = r.json()

    set_default_languages(client, user_token, en_id, ru_id)
    user_deck_id = create_deck(client, user_token, "My Deck", en_id, ru_id)

    r1 = client.post(
        f"/api/v1/library/cards/{library_card['id']}/import",
        json={"target_deck_id": user_deck_id},
        headers=auth_headers(user_token),
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["imported"] is True

    r2 = client.post(
        f"/api/v1/library/cards/{library_card['id']}/import",
        json={"target_deck_id": user_deck_id},
        headers=auth_headers(user_token),
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["imported"] is False
    assert r2.json()["skipped"] is True
    assert r2.json()["reason"] == "duplicate"

def test_user_can_import_selected_library_cards(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, user_token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    library_deck = create_library_deck(client, admin_token, "A1", en_id, ru_id)

    r1 = client.post(
        f"/api/v1/decks/{library_deck['id']}/cards",
        json={"front": "hello", "back": "привет"},
        headers=auth_headers(admin_token),
    )
    card1 = r1.json()

    r2 = client.post(
        f"/api/v1/decks/{library_deck['id']}/cards",
        json={"front": "world", "back": "мир"},
        headers=auth_headers(admin_token),
    )
    card2 = r2.json()

    user_deck_id = create_deck(client, user_token, "My deck", en_id, ru_id)

    r = client.post(
        f"/api/v1/library/decks/{library_deck['id']}/import-selected",
        json={
            "target_deck_id": user_deck_id,
            "card_ids": [card1["id"], card2["id"]],
        },
        headers=auth_headers(user_token),
    )

    assert r.status_code == 200, r.text
    body = r.json()
    assert body["imported_count"] == 2
    assert body["skipped_count"] == 0
    assert len(body["results"]) == 2

def test_user_sees_only_library_decks_for_default_pair(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, user_token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    es_id = admin_create_language(client, admin_token, "Spanish", "es")

    create_library_deck(client, admin_token, "EN-RU Library", en_id, ru_id)
    create_library_deck(client, admin_token, "EN-ES Library", en_id, es_id)

    # make EN-RU the default pair for the user
    r = client.post(
        "/api/v1/users/me/learning-pairs",
        json={
            "source_language_id": en_id,
            "target_language_id": ru_id,
            "is_default": True,
        },
        headers=auth_headers(user_token),
    )
    assert r.status_code in (200, 201), r.text

    r = client.get("/api/v1/library/decks", headers=auth_headers(user_token))
    assert r.status_code == 200, r.text

    body = r.json()
    names = [item["name"] for item in body["items"]]

    assert "EN-RU Library" in names
    assert "EN-ES Library" not in names