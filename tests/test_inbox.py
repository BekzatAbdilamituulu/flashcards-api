from tests.conftest import (
    auth_headers,
    create_user_and_token,
    admin_create_language,
)


def test_inbox_quick_add_creates_inbox_deck_and_card(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

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

    text = """
# comment
hello - привет
hello - ДУБЛЬ
world: мир
justfront
"""

    # dry_run: returns preview items and counts, no inserts
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
    assert out["created"] >= 2  # preview counts as created in your code
    assert out["skipped"] >= 1  # comment/blank/dupe

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
    assert out2["created"] >= 2
    assert out2["skipped"] >= 2  # duplicate + comment/blank

def test_inbox_is_per_language_pair(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    ky_id = admin_create_language(client, admin_token, "Kyrgyz", "ky")

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