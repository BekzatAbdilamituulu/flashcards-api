from tests.conftest import (
    auth_headers,
    create_user_and_token,
    admin_create_language,
    create_deck,
    add_card,
)


def test_users_me_and_set_default_languages(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    r = client.get("/users/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["username"] == "user"

    # set defaults
    r = client.put(
        "/users/me/languages",
        json={"default_source_language_id": en_id, "default_target_language_id": ru_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["default_source_language_id"] == en_id
    assert body["default_target_language_id"] == ru_id

    # invalid: same language
    r = client.put(
        "/users/me/languages",
        json={"default_source_language_id": en_id, "default_target_language_id": en_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 422


def test_users_progress_endpoints(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    deck_id = create_deck(client, token, "D", en_id, ru_id)

    c1 = add_card(client, token, deck_id, "hello", "привет")
    c2 = add_card(client, token, deck_id, "bye", "пока")

    # progress starts empty
    r = client.get("/users/me/progress", params={"deck_id": deck_id}, headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json() == []

    # study one card -> progress should exist
    r = client.post(f"/study/{c1['id']}", json={"learned": True}, headers=auth_headers(token))
    assert r.status_code == 200, r.text

    r = client.get("/users/me/progress", params={"deck_id": deck_id}, headers=auth_headers(token))
    assert r.status_code == 200
    assert len(r.json()) == 1

    # stats
    r = client.get("/users/me/progress/stats", params={"deck_id": deck_id}, headers=auth_headers(token))
    assert r.status_code == 200
    stats = r.json()
    assert stats["deck_id"] == deck_id
    assert "due_count" in stats
    assert "new_available_count" in stats

    # reset progress
    r = client.delete("/users/me/progress", params={"deck_id": deck_id}, headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["deleted"] >= 1

    r = client.get("/users/me/progress", params={"deck_id": deck_id}, headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json() == []
