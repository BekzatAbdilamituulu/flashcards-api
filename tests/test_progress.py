from datetime import date

from tests.conftest import (
    add_card,
    admin_create_language,
    auth_headers,
    create_user_and_token,
)


def set_default_pair(client, token, src_id, tgt_id) -> int:
    r = client.put(
        "/api/v1/users/me/languages",
        json={"default_source_language_id": src_id, "default_target_language_id": tgt_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text

    r = client.get("/api/v1/users/me/learning-pairs", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    pairs = r.json()
    default = next(p for p in pairs if p["is_default"] is True)
    return default["id"]


def get_main_deck_id(client, token: str) -> int:
    r = client.get("/api/v1/decks", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    main_deck = next(x for x in r.json()["items"] if x.get("deck_type") == "main")
    return main_deck["id"]


def test_progress_month_returns_full_calendar(client):
    # setup
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    pair_id = set_default_pair(client, token, en_id, ru_id)

    # Study is only allowed from MAIN deck.
    d = client.get("/api/v1/decks", headers=auth_headers(token))
    assert d.status_code == 200, d.text
    main_deck = next(x for x in d.json()["items"] if x.get("deck_type") == "main")
    c1 = add_card(client, token, main_deck["id"], "hello", "привет")

    # Study 1 card once (still below streak threshold, but will create daily progress row)
    r = client.post(
        f"/api/v1/study/{c1['id']}", json={"learned": True}, headers=auth_headers(token)
    )
    assert r.status_code == 200, r.text

    # Ask month view for the current month (use server date assumptions)
    # We cannot easily know exact month here; so just request a fixed month like 2026-02 if your tests run on that date.
    # Better: request month of "today" returned by /progress/today-added.
    t = client.get("/api/v1/progress/today-added", headers=auth_headers(token))
    assert t.status_code == 200, t.text
    today = date.fromisoformat(t.json()["date"])
    year = today.year
    month = today.month

    r = client.get(
        "/api/v1/progress/month",
        params={"year": year, "month": month, "pair_id": pair_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert "items" in data
    items = data["items"]
    # at least 28 days, at most 31
    assert 28 <= len(items) <= 31

    # ensure every item has required fields
    for it in items:
        assert "date" in it
        assert "cards_done" in it
        assert "reviews_done" in it
        assert "new_done" in it


def test_streak_threshold_10_cards(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    pair_id = set_default_pair(client, token, en_id, ru_id)
    main_deck_id = get_main_deck_id(client, token)

    # add 10 cards
    cards = []
    for i in range(10):
        cards.append(add_card(client, token, main_deck_id, f"w{i}", f"b{i}"))

    # study 9 cards -> streak should be 0 (threshold=10)
    for i in range(9):
        r = client.post(
            f"/api/v1/study/{cards[i]['id']}", json={"learned": True}, headers=auth_headers(token)
        )
        assert r.status_code == 200, r.text

    r = client.get(
        "/api/v1/progress/streak", params={"pair_id": pair_id}, headers=auth_headers(token)
    )
    assert r.status_code == 200, r.text
    assert r.json()["threshold"] == 10
    assert r.json()["current_streak"] == 0

    # study 10th card -> now cards_done=10 today -> streak becomes 1
    r = client.post(
        f"/api/v1/study/{cards[9]['id']}", json={"learned": True}, headers=auth_headers(token)
    )
    assert r.status_code == 200, r.text

    r = client.get("/api/v1/progress/streak", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    assert r.json()["current_streak"] == 1


def test_today_added_cards_count(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    pair_id = set_default_pair(client, token, en_id, ru_id)
    main_deck_id = get_main_deck_id(client, token)

    r = client.get(
        "/api/v1/progress/today-added", params={"pair_id": pair_id}, headers=auth_headers(token)
    )
    assert r.status_code == 200, r.text
    before = r.json()["count"]

    add_card(client, token, main_deck_id, "hello", "привет")

    r = client.get("/api/v1/progress/today-added", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    after = r.json()["count"]

    assert after == before + 1


def test_progress_summary_basic(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    pair_id = set_default_pair(client, token, en_id, ru_id)
    main_deck_id = get_main_deck_id(client, token)

    add_card(client, token, main_deck_id, "hello", "привет")

    r = client.get(
        "/api/v1/progress/summary",
        params={"pair_id": pair_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert "date" in data
    assert data["today_added_cards"] >= 1
    assert data["streak_threshold"] == 10
    assert "total_cards" in data
    assert data["total_cards"] >= 1
