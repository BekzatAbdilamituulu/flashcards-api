from tests.conftest import (
    admin_create_language,
    auth_headers,
    create_user_and_token,
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
    # default pair should be created and set
    r = client.get("/api/v1/users/me/learning-pairs", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    pairs = r.json()
    assert len(pairs) == 1
    assert pairs[0]["source_language_id"] == en_id
    assert pairs[0]["target_language_id"] == ru_id
    assert pairs[0]["is_default"] is True

    # invalid: same language
    r = client.put(
        "/api/v1/users/me/languages",
        json={"default_source_language_id": en_id, "default_target_language_id": en_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 422


def test_learning_pairs_endpoints(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    tr_id = admin_create_language(client, admin_token, "Turkish", "tr")

    # 1) set defaults -> should also create default learning pair
    r = client.put(
        "/api/v1/users/me/languages",
        json={"default_source_language_id": en_id, "default_target_language_id": ru_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text

    # 2) list pairs -> should contain en->ru default
    r = client.get("/api/v1/users/me/learning-pairs", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    pairs = r.json()
    assert isinstance(pairs, list)
    assert len(pairs) == 1
    assert pairs[0]["source_language_id"] == en_id
    assert pairs[0]["target_language_id"] == ru_id
    assert pairs[0]["is_default"] is True

    # 3) add second pair en->tr and make it default
    r = client.post(
        "/api/v1/users/me/learning-pairs",
        json={"source_language_id": en_id, "target_language_id": tr_id, "make_default": True},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    pair2 = r.json()
    assert pair2["source_language_id"] == en_id
    assert pair2["target_language_id"] == tr_id
    assert pair2["is_default"] is True
    pair2_id = pair2["id"]

    # 4) list pairs -> now should have 2 and only one default (en->tr)
    r = client.get("/api/v1/users/me/learning-pairs", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    pairs = r.json()
    assert len(pairs) == 2
    assert sum(1 for p in pairs if p["is_default"]) == 1
    assert any(p["target_language_id"] == tr_id and p["is_default"] for p in pairs)

    # 5) set default back to en->ru (find its id first)
    ru_pair_id = next(p["id"] for p in pairs if p["target_language_id"] == ru_id)

    r = client.put(
        f"/api/v1/users/me/learning-pairs/{ru_pair_id}/default",
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["id"] == ru_pair_id
    assert body["is_default"] is True

    # 6) confirm only one default again
    r = client.get("/api/v1/users/me/learning-pairs", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    pairs = r.json()
    assert sum(1 for p in pairs if p["is_default"]) == 1
    assert any(p["target_language_id"] == ru_id and p["is_default"] for p in pairs)


def test_learning_pairs_reject_same_language(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")

    r = client.post(
        "/api/v1/users/me/learning-pairs",
        json={"source_language_id": en_id, "target_language_id": en_id, "make_default": True},
        headers=auth_headers(token),
    )
    assert r.status_code == 422


def test_learning_pairs_flow(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    tr_id = admin_create_language(client, admin_token, "Turkish", "tr")

    # 1) set default languages (creates first pair)
    r = client.put(
        "/api/v1/users/me/languages",
        json={
            "default_source_language_id": en_id,
            "default_target_language_id": ru_id,
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text

    # 2) check pairs list
    r = client.get("/api/v1/users/me/learning-pairs", headers=auth_headers(token))
    assert r.status_code == 200
    pairs = r.json()
    assert len(pairs) == 1
    assert pairs[0]["is_default"] is True

    # 3) add second pair and make default
    r = client.post(
        "/api/v1/users/me/learning-pairs",
        json={
            "source_language_id": en_id,
            "target_language_id": tr_id,
            "make_default": True,
        },
        headers=auth_headers(token),
    )
    assert r.status_code == 200
    second_pair = r.json()
    assert second_pair["is_default"] is True

    # 4) confirm only one default
    r = client.get("/api/v1/users/me/learning-pairs", headers=auth_headers(token))
    pairs = r.json()
    assert sum(1 for p in pairs if p["is_default"]) == 1

    # 5) set default back to ru
    ru_pair_id = next(p["id"] for p in pairs if p["target_language_id"] == ru_id)

    r = client.put(
        f"/api/v1/users/me/learning-pairs/{ru_pair_id}/default",
        headers=auth_headers(token),
    )
    assert r.status_code == 200

    # confirm default switched
    r = client.get("/api/v1/users/me/learning-pairs", headers=auth_headers(token))
    pairs = r.json()
    assert sum(1 for p in pairs if p["is_default"]) == 1
    assert any(p["target_language_id"] == ru_id and p["is_default"] for p in pairs)
