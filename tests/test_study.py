from tests.conftest import (
    auth_headers,
    create_user_and_token,
    admin_create_language,
    create_deck,
    add_card,
)


def test_study_next_and_status_and_review_flow(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    deck_id = create_deck(client, token, "D", en_id, ru_id)

    c1 = add_card(client, token, deck_id, "hello", "привет")
    c2 = add_card(client, token, deck_id, "bye", "пока")

    # status before studying
    r = client.get("/study/status", params={"deck_id": deck_id}, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    status1 = r.json()
    assert status1["deck_id"] == deck_id
    assert status1["new_available_count"] >= 2

    # next batch
    r = client.get("/study/next", params={"deck_id": deck_id, "limit": 2, "new_ratio": 1.0}, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    batch = r.json()
    assert batch["deck_id"] == deck_id
    assert batch["count"] in (1, 2)
    assert len(batch["cards"]) == batch["count"]

    # study card (body correct)
    r = client.post(f"/study/{c1['id']}", json={"correct": True}, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    prog = r.json()
    assert prog["card_id"] == c1["id"]
    assert prog["times_seen"] >= 1

    # study card (quality)
    r = client.post(f"/study/{c2['id']}", json={"quality": 2}, headers=auth_headers(token))
    assert r.status_code == 200, r.text

    # status after studying: reviewed_today/new_introduced_today change
    r = client.get("/study/status", params={"deck_id": deck_id}, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    status2 = r.json()
    assert status2["reviewed_today"] >= 0
    assert status2["new_introduced_today"] >= 1


def test_study_requires_input(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    deck_id = create_deck(client, token, "D", en_id, ru_id)
    c1 = add_card(client, token, deck_id, "hello", "привет")

    r = client.post(f"/study/{c1['id']}", headers=auth_headers(token))
    assert r.status_code == 422, r.text
