from tests.conftest import (
    auth_headers,
    create_user_and_token,
    admin_create_language,
    create_deck,
    add_card,
)

def test_stage1_wrong_stays_stage1(client, token_headers, make_deck_with_cards):
    deck, cards = make_deck_with_cards(n=1)
    card_id = cards[0]["id"]

    # enter stage1
    _post_learned(client, token_headers, card_id, True)

    # wrong at stage1 => still stage1
    p = _post_learned(client, token_headers, card_id, False).json()
    assert p["status"] == "learning"
    assert p["stage"] == 1

def _post_learned(client, token_headers, card_id: int, learned: bool):
    return client.post(
        f"/api/v1/study/{card_id}",
        json={"learned": learned},
        headers=token_headers,
    )

def _get_progress(client, token_headers, card_id: int):
    # You already have /users/me/progress endpoint in tests
    # but easiest: call it and filter by card_id
    r = client.get("/api/v1/users/me/progress", headers=token_headers)
    assert r.status_code == 200
    items = r.json().get("items", r.json())
    # items may be list or dict depending on your endpoint; adapt if needed
    for row in items:
        if row["card_id"] == card_id:
            return row
    return None

def test_study_next_and_status_and_review_flow(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    deck_id = create_deck(client, token, "D", en_id, ru_id)

    c1 = add_card(client, token, deck_id, "hello", "привет")
    c2 = add_card(client, token, deck_id, "bye", "пока")

    # status before studying
    r = client.get(f"/api/v1/study/decks/{deck_id}/status", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    status1 = r.json()
    assert status1["deck_id"] == deck_id
    assert status1["new_available_count"] >= 2

    # next batch
    r = client.get(f"/api/v1/study/decks/{deck_id}/next", params={"limit": 2, "new_ratio": 1.0}, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    batch = r.json()
    assert batch["deck_id"] == deck_id
    assert batch["count"] in (1, 2)
    assert len(batch["cards"]) == batch["count"]

    # study card (body correct)
    r = client.post(f"/api/v1/study/{c1['id']}", json={"learned": True}, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    prog = r.json()
    assert prog["card_id"] == c1["id"]
    assert prog["times_seen"] >= 1

    # study card (quality)
    r = client.post(f"/api/v1/study/{c2['id']}", json={"learned": False}, headers=auth_headers(token))
    assert r.status_code == 200, r.text

    # status after studying: reviewed_today/new_introduced_today change
    r = client.get(f"/api/v1/study/decks/{deck_id}/status", headers=auth_headers(token))
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

    r = client.post(f"/api/v1/study/{c1['id']}", headers=auth_headers(token))
    assert r.status_code == 422, r.text

def test_learning_stage2_fail_does_not_advance(client, token_headers, make_deck_with_cards):
    deck, cards = make_deck_with_cards(n=1)
    card_id = cards[0]["id"]

    # 1) NEW -> learned=True => enter LEARNING stage 1
    r = _post_learned(client, token_headers, card_id, True)
    assert r.status_code == 200
    p = r.json()
    assert p["status"] == "learning"
    assert p["stage"] == 1
    assert p["due_at"] is not None

    # 2) stage 1 -> learned=True => stage 2 (5 min)
    r = _post_learned(client, token_headers, card_id, True)
    assert r.status_code == 200
    p = r.json()
    assert p["status"] == "learning"
    assert p["stage"] == 2
    assert p["due_at"] is not None

    # 3) stage 2 -> learned=False => must NOT go to stage 3
    r = _post_learned(client, token_headers, card_id, False)
    assert r.status_code == 200
    p = r.json()

    # Depending on your rule: you currently drop back to stage 1
    assert p["status"] == "learning"
    assert p["stage"] == 1   # key: not 3

def test_learning_must_be_correct_to_advance(client, token_headers, make_deck_with_cards):
    deck, cards = make_deck_with_cards(n=1)
    card_id = cards[0]["id"]

    # NEW -> stage1
    _post_learned(client, token_headers, card_id, True)
    # stage1 -> stage2
    _post_learned(client, token_headers, card_id, True)

    # fail at stage2 => back to stage1
    r = _post_learned(client, token_headers, card_id, False)
    assert r.status_code == 200
    assert r.json()["stage"] == 1

    # now must re-pass stage1 -> stage2 again
    r = _post_learned(client, token_headers, card_id, True)
    assert r.json()["stage"] == 2

    # now pass stage2 => should go to stage3
    r = _post_learned(client, token_headers, card_id, True)
    assert r.json()["stage"] == 3

def test_learning_full_ladder_to_mastered(client, token_headers, make_deck_with_cards):
    deck, cards = make_deck_with_cards(n=1)
    card_id = cards[0]["id"]

    # NEW -> LEARNING 1
    p = _post_learned(client, token_headers, card_id, True).json()
    assert (p["status"], p["stage"]) == ("learning", 1)

    # 1 -> 2
    p = _post_learned(client, token_headers, card_id, True).json()
    assert p["stage"] == 2

    # 2 -> 3
    p = _post_learned(client, token_headers, card_id, True).json()
    assert p["stage"] == 3

    # 3 -> 4
    p = _post_learned(client, token_headers, card_id, True).json()
    assert p["stage"] == 4

    # 4 -> 5
    p = _post_learned(client, token_headers, card_id, True).json()
    assert p["stage"] == 5

    # 5 -> MASTERED
    p = _post_learned(client, token_headers, card_id, True).json()
    assert p["status"] == "mastered"
    assert p["due_at"] is None

def test_learning_wrong_drops_one_stage(client, token_headers, make_deck_with_cards):
    deck_id, cards = make_deck_with_cards(n=1)
    card_id = cards[0]["id"]

    # NEW -> stage1
    _post_learned(client, token_headers, card_id, True)
    # 1 -> 2
    _post_learned(client, token_headers, card_id, True)
    # 2 -> 3
    _post_learned(client, token_headers, card_id, True)
    # 3 -> 4
    _post_learned(client, token_headers, card_id, True)

    # wrong at stage 4 => stage 3 (drop one)
    r = _post_learned(client, token_headers, card_id, False)
    assert r.status_code == 200
    p = r.json()
    assert p["status"] == "learning"
    assert p["stage"] == 3