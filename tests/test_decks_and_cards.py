from tests.conftest import (
    auth_headers,
    create_user_and_token,
    admin_create_language,
    create_deck,
    add_card,
)


def test_decks_create_list_get_delete(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    deck_id = create_deck(client, token, "My Deck", en_id, ru_id)

    r = client.get("/api/v1/decks", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    body = r.json()
    # Setting default languages auto-creates the user's MAIN deck for this pair.
    # Then we create an extra USERS deck.
    assert body["meta"]["total"] >= 2
    users_decks = [d for d in body["items"] if d.get("deck_type") == "users"]
    assert any(d["id"] == deck_id for d in users_decks)

    r = client.get(f"/api/v1/decks/{deck_id}", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["name"] == "My Deck"

    # delete
    r = client.delete(f"/api/v1/decks/{deck_id}", headers=auth_headers(token))
    assert r.status_code == 204

    r = client.get(f"/api/v1/decks/{deck_id}", headers=auth_headers(token))
    assert r.status_code == 404


def test_cards_create_list_duplicate(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    deck_id = create_deck(client, token, "D", en_id, ru_id)

    c1 = add_card(client, token, deck_id, "Hello", "привет", "hello world")
    assert c1["front"] == "Hello"

    r = client.get(f"/api/v1/decks/{deck_id}/cards", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["meta"]["total"] == 1

    # front_norm duplicates should fail (Hello == hello)
    r = client.post(
        f"/api/v1/decks/{deck_id}/cards",
        json={"front": "hello", "back": "x", "example_sentence": None},
        headers=auth_headers(token),
    )
    assert r.status_code in (400, 422, 403), r.text  # your API raises ValueError -> may map to 500 if not caught
    # recommended: after you refactor, expect 400 with "Duplicate word..."
def test_card_update_and_delete_requires_endpoints(client):
    """
    This test assumes you added:
      PATCH /decks/{deck_id}/cards/{card_id}
      DELETE /decks/{deck_id}/cards/{card_id}

    If you haven't implemented them yet, this will fail (expected).
    """
    _, admin_token = create_user_and_token(client, "admin")
    _, owner_token = create_user_and_token(client, "owner")
    _, viewer_token = create_user_and_token(client, "viewer")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    deck_id = create_deck(client, owner_token, "D", en_id, ru_id)

    c1 = add_card(client, owner_token, deck_id, "hello", "привет", "ex1")
    c2 = add_card(client, owner_token, deck_id, "bye", "пока", None)

    # update back + example
    r = client.patch(
        f"/api/v1/decks/{deck_id}/cards/{c1['id']}",
        json={"back": "привет!!!", "example_sentence": "ex2"},
        headers=auth_headers(owner_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["back"] == "привет!!!"
    assert r.json()["example_sentence"] == "ex2"

    # duplicate front should fail
    r = client.patch(
        f"/api/v1/decks/{deck_id}/cards/{c1['id']}",
        json={"front": "bye"},
        headers=auth_headers(owner_token),
    )
    assert r.status_code == 400, r.text
    assert "duplicate" in r.json()["detail"].lower()

    # Note: shared-deck collaboration endpoints were removed in the current app.

    # owner delete
    r = client.delete(f"/api/v1/decks/{deck_id}/cards/{c2['id']}", headers=auth_headers(owner_token))
    assert r.status_code == 204, r.text

    # list doesn't include deleted
    r = client.get(f"/api/v1/decks/{deck_id}/cards", headers=auth_headers(owner_token))
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()["items"]}
    assert c2["id"] not in ids
