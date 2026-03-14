from tests.conftest import (
    admin_create_language,
    auth_headers,
    create_user_and_token,
    set_default_languages,
)


def test_create_deck_accepts_reader_fields(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)

    r = client.post(
        "/api/v1/decks",
        json={
            "name": "Reader Deck",
            "source_language_id": en_id,
            "target_language_id": ru_id,
            "source_type": "book",
            "author_name": "Leo Tolstoy",
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_type"] == "book"
    assert body["author_name"] == "Leo Tolstoy"


def test_update_deck_accepts_reader_fields(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)

    create = client.post(
        "/api/v1/decks",
        json={
            "name": "Deck",
            "source_language_id": en_id,
            "target_language_id": ru_id,
        },
        headers=auth_headers(token),
    )
    assert create.status_code == 201, create.text
    deck_id = create.json()["id"]

    r = client.patch(
        f"/api/v1/decks/{deck_id}",
        json={
            "source_type": "article",
            "author_name": "Unknown",
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source_type"] == "article"
    assert body["author_name"] == "Unknown"


def test_create_card_accepts_reader_fields(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)

    deck_resp = client.post(
        "/api/v1/decks",
        json={
            "name": "Deck",
            "source_language_id": en_id,
            "target_language_id": ru_id,
        },
        headers=auth_headers(token),
    )
    assert deck_resp.status_code == 201, deck_resp.text
    deck_id = deck_resp.json()["id"]

    r = client.post(
        f"/api/v1/decks/{deck_id}/cards",
        json={
            "front": "serendipity",
            "back": "счастливая случайность",
            "content_kind": "word",
            "source_title": "Anna Karenina",
            "source_author": "Leo Tolstoy",
            "source_reference": "Part 1, Chapter 3",
            "source_sentence": "It was pure serendipity.",
            "source_page": "p. 14",
            "context_note": "Found in chapter 2.",
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["content_kind"] == "word"
    assert body["source_title"] == "Anna Karenina"
    assert body["source_author"] == "Leo Tolstoy"
    assert body["source_reference"] == "Part 1, Chapter 3"
    assert body["source_sentence"] == "It was pure serendipity."
    assert body["source_page"] == "p. 14"
    assert body["context_note"] == "Found in chapter 2."
    assert body["reading_source_id"] is not None


def test_update_card_accepts_reader_fields(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)

    deck_resp = client.post(
        "/api/v1/decks",
        json={
            "name": "Deck",
            "source_language_id": en_id,
            "target_language_id": ru_id,
        },
        headers=auth_headers(token),
    )
    assert deck_resp.status_code == 201, deck_resp.text
    deck_id = deck_resp.json()["id"]

    card_resp = client.post(
        f"/api/v1/decks/{deck_id}/cards",
        json={"front": "insight", "back": "озарение"},
        headers=auth_headers(token),
    )
    assert card_resp.status_code == 201, card_resp.text
    card_id = card_resp.json()["id"]

    r = client.patch(
        f"/api/v1/decks/{deck_id}/cards/{card_id}",
        json={
            "content_kind": "idea",
            "source_title": "Collected Essays",
            "source_author": "M. Proust",
            "source_reference": "Essay II",
            "source_sentence": "That paragraph gave me insight.",
            "source_page": "12",
            "context_note": "Key idea for this text.",
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["content_kind"] == "idea"
    assert body["source_title"] == "Collected Essays"
    assert body["source_author"] == "M. Proust"
    assert body["source_reference"] == "Essay II"
    assert body["source_sentence"] == "That paragraph gave me insight."
    assert body["source_page"] == "12"
    assert body["context_note"] == "Key idea for this text."
    assert body["reading_source_id"] is not None


def test_old_card_payload_without_source_metadata_still_works(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)

    deck_resp = client.post(
        "/api/v1/decks",
        json={
            "name": "Deck",
            "source_language_id": en_id,
            "target_language_id": ru_id,
        },
        headers=auth_headers(token),
    )
    assert deck_resp.status_code == 201, deck_resp.text
    deck_id = deck_resp.json()["id"]

    r = client.post(
        f"/api/v1/decks/{deck_id}/cards",
        json={"front": "legacy", "back": "устаревший"},
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["source_title"] is None
    assert body["source_author"] is None
    assert body["source_reference"] is None
