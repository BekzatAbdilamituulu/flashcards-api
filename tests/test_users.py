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

    r = client.get("/api/v1/users/me", headers=auth_headers(token))
    assert r.status_code == 200
    assert r.json()["username"] == "user"

    # set defaults
    r = client.put(
        "/api/v1/users/me/languages",
        json={"default_source_language_id": en_id, "default_target_language_id": ru_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["default_source_language_id"] == en_id
    assert body["default_target_language_id"] == ru_id

    # invalid: same language
    r = client.put(
        "/api/v1/users/me/languages",
        json={"default_source_language_id": en_id, "default_target_language_id": en_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 422



