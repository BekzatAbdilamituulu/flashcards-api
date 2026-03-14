from tests.conftest import (
    admin_create_language,
    auth_headers,
    create_user_and_token,
    set_default_languages,
)


def test_inbox_quick_add_creates_inbox_deck_and_card(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    # Ensure main deck/access exists for this pair
    set_default_languages(client, token, en_id, ru_id)

    r = client.post(
        "/api/v1/inbox/word",
        json={
            "front": "apple",
            "back": "яблоко",
            "example_sentence": "an apple a day",
            "source_language_id": en_id,
            "target_language_id": ru_id,
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert "deck_id" in body and "card" in body
    assert body["card"]["front"] == "apple"


def test_inbox_bulk_import_dry_run_and_dedupe(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    set_default_languages(client, token, en_id, ru_id)

    text = """
# comment
hello - привет
hello - ДУБЛЬ
world: мир
justfront
"""

    # dry_run: returns preview items/counts, no inserts
    r = client.post(
        "/api/v1/inbox/bulk",
        json={
            "text": text,
            "delimiter": None,
            "dry_run": True,
            "source_language_id": en_id,
            "target_language_id": ru_id,
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["created_count"] == 0
    assert out["preview_count"] >= 2
    assert out["duplicate_count"] >= 1
    assert out["invalid_count"] >= 1
    assert out["failed_count"] == 0
    assert all(item["status"] in {"preview", "duplicate", "invalid"} for item in out["results"])

    # real insert
    r = client.post(
        "/api/v1/inbox/bulk",
        json={
            "text": text,
            "delimiter": None,
            "dry_run": False,
            "source_language_id": en_id,
            "target_language_id": ru_id,
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    out2 = r.json()
    assert out2["created_count"] >= 2
    assert out2["preview_count"] == 0
    assert out2["duplicate_count"] >= 1
    assert out2["invalid_count"] >= 1
    assert out2["failed_count"] == 0
    assert any(item["status"] == "created" for item in out2["results"])
    assert all(
        item["status"] in {"created", "duplicate", "invalid", "failed"} for item in out2["results"]
    )


def test_inbox_bulk_dry_run_does_not_persist_rows(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "preview_user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)

    decks = client.get("/api/v1/decks", headers=auth_headers(token))
    assert decks.status_code == 200, decks.text
    main_deck = next(d for d in decks.json()["items"] if d.get("deck_type") == "main")
    before_cards = client.get(
        f"/api/v1/decks/{main_deck['id']}/cards",
        headers=auth_headers(token),
    )
    assert before_cards.status_code == 200, before_cards.text
    before_total = before_cards.json()["meta"]["total"]

    preview = client.post(
        "/api/v1/inbox/bulk",
        json={
            "text": "novelty - новизна\nlucid - ясный",
            "dry_run": True,
            "source_language_id": en_id,
            "target_language_id": ru_id,
        },
        headers=auth_headers(token),
    )
    assert preview.status_code == 201, preview.text
    body = preview.json()
    assert body["preview_count"] == 2
    assert body["created_count"] == 0

    after_cards = client.get(
        f"/api/v1/decks/{main_deck['id']}/cards",
        headers=auth_headers(token),
    )
    assert after_cards.status_code == 200, after_cards.text
    assert after_cards.json()["meta"]["total"] == before_total


def test_inbox_is_per_language_pair(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    ky_id = admin_create_language(client, admin_token, "Kyrgyz", "ky")

    # Pre-create main decks/access for each pair (SQLite + flush behavior)
    set_default_languages(client, token, en_id, ru_id)

    r1 = client.post(
        "/api/v1/inbox/word",
        json={
            "front": "apple",
            "back": "яблоко",
            "source_language_id": en_id,
            "target_language_id": ru_id,
        },
        headers=auth_headers(token),
    )
    assert r1.status_code == 201, r1.text
    deck1 = r1.json()["deck_id"]

    set_default_languages(client, token, en_id, ky_id)

    r2 = client.post(
        "/api/v1/inbox/word",
        json={
            "front": "alma",
            "back": "алма",
            "source_language_id": en_id,
            "target_language_id": ky_id,
        },
        headers=auth_headers(token),
    )
    assert r2.status_code == 201, r2.text
    deck2 = r2.json()["deck_id"]

    assert deck1 != deck2  # different inbox decks per pair


def test_inbox_without_payload_languages_uses_default_pair(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    # Set default pair
    r = client.put(
        "/api/v1/users/me/languages",
        json={
            "default_source_language_id": en_id,
            "default_target_language_id": ru_id,
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 200

    # Now create inbox word WITHOUT specifying languages
    r = client.post(
        "/api/v1/inbox/word",
        json={
            "front": "hello",
            "back": "привет",
        },
        headers=auth_headers(token),
    )

    assert r.status_code == 201, r.text
    body = r.json()
    assert "deck_id" in body


def test_inbox_requires_languages_if_no_default_pair(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    r = client.post(
        "/api/v1/inbox/word",
        json={
            "front": "hello",
            "back": "привет",
        },
        headers=auth_headers(token),
    )

    assert r.status_code == 422


def test_inbox_quick_add_accepts_source_metadata(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "reader")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)

    r = client.post(
        "/api/v1/inbox/word",
        json={
            "front": "subtle",
            "back": "тонкий",
            "source_title": "The Trial",
            "source_author": "Franz Kafka",
            "source_reference": "Chapter 1",
            "source_sentence": "He noticed a subtle change in tone.",
            "source_page": "p. 9",
            "context_note": "First appearance in opening scene",
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 201, r.text
    card = r.json()["card"]
    assert card["source_title"] == "The Trial"
    assert card["source_author"] == "Franz Kafka"
    assert card["source_reference"] == "Chapter 1"
    assert card["source_sentence"] == "He noticed a subtle change in tone."
    assert card["source_page"] == "p. 9"
    assert card["context_note"] == "First appearance in opening scene"
    assert card["reading_source_id"] is not None
