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
    assert body["meta"]["total"] == 1
    assert body["items"][0]["id"] == deck_id

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


def test_share_link_and_join_as_viewer(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, owner_token = create_user_and_token(client, "owner")
    _, viewer_token = create_user_and_token(client, "viewer")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    deck_id = create_deck(client, owner_token, "Shared", en_id, ru_id)

    r = client.post(f"/api/v1/decks/{deck_id}/share-link", headers=auth_headers(owner_token))
    assert r.status_code == 200, r.text
    shared_code = r.json()["shared_code"]
    assert shared_code

    r = client.post(f"/api/v1/decks/join/{shared_code}", headers=auth_headers(viewer_token))
    assert r.status_code == 201, r.text
    assert r.json()["deck_id"] == deck_id
    assert r.json()["role"] in ("viewer", "VIEWER")  # depends on your enum serialization


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

    # share & join viewer
    r = client.post(f"/api/v1/decks/{deck_id}/share-link", headers=auth_headers(owner_token))
    assert r.status_code == 200
    code = r.json()["shared_code"]
    r = client.post(f"/api/v1/decks/join/{code}", headers=auth_headers(viewer_token))
    assert r.status_code == 201

    # viewer cannot update/delete
    r = client.patch(
        f"/api/v1/decks/{deck_id}/cards/{c1['id']}",
        json={"back": "nope"},
        headers=auth_headers(viewer_token),
    )
    assert r.status_code == 403, r.text

    r = client.delete(f"/api/v1/decks/{deck_id}/cards/{c2['id']}", headers=auth_headers(viewer_token))
    assert r.status_code == 403, r.text

    # owner delete
    r = client.delete(f"/api/v1/decks/{deck_id}/cards/{c2['id']}", headers=auth_headers(owner_token))
    assert r.status_code == 204, r.text

    # list doesn't include deleted
    r = client.get(f"/api/v1/decks/{deck_id}/cards", headers=auth_headers(owner_token))
    assert r.status_code == 200
    ids = {x["id"] for x in r.json()["items"]}
    assert c2["id"] not in ids

def test_deck_rename_publish_unpublish_unshare(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, owner_token = create_user_and_token(client, "owner")
    _, viewer_token = create_user_and_token(client, "viewer")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    deck_id = create_deck(client, owner_token, "Old", en_id, ru_id)

    # rename owner
    r = client.patch(f"/api/v1/decks/{deck_id}", json={"name": "New"}, headers=auth_headers(owner_token))
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "New"

    # publish owner (private)
    r = client.post(f"/api/v1/decks/{deck_id}/publish", headers=auth_headers(owner_token))
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["deck_id"] == deck_id
    assert out["status"] != "draft"
    assert out["shared_code"]  # generated
    assert out["is_public"] is False

    code = out["shared_code"]

    # viewer joins using shared code (join endpoint you already have)
    r = client.post(f"/api/v1/decks/join/{code}", headers=auth_headers(viewer_token))
    assert r.status_code == 201, r.text

    # viewer cannot publish/unpublish/unshare
    r = client.post(f"/api/v1/decks/{deck_id}/unpublish", headers=auth_headers(viewer_token))
    assert r.status_code == 403, r.text
    r = client.post(f"/api/v1/decks/{deck_id}/unshare", headers=auth_headers(viewer_token))
    assert r.status_code == 403, r.text

    # make public (owner)
    r = client.patch(f"/api/v1/decks/{deck_id}", json={"is_public": True}, headers=auth_headers(owner_token))
    assert r.status_code == 200, r.text
    assert r.json()["is_public"] is True

    # unshare (owner) -> shared_code cleared, but status stays published
    r = client.post(f"/api/v1/decks/{deck_id}/unshare", headers=auth_headers(owner_token))
    assert r.status_code == 200, r.text
    assert r.json()["shared_code"] is None

    # unpublish (owner) -> draft + private + no share
    r = client.post(f"/api/v1/decks/{deck_id}/unpublish", headers=auth_headers(owner_token))
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "draft"
    assert r.json()["is_public"] is False
    assert r.json()["shared_code"] is None


def test_cannot_make_draft_public(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, owner_token = create_user_and_token(client, "owner")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    deck_id = create_deck(client, owner_token, "D", en_id, ru_id)

    r = client.patch(f"/api/v1/decks/{deck_id}", json={"is_public": True}, headers=auth_headers(owner_token))
    assert r.status_code == 400, r.text
    assert "publish" in r.json()["detail"].lower()