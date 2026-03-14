from tests.conftest import (
    add_card,
    admin_create_language,
    auth_headers,
    create_deck,
    create_user_and_token,
    get_main_deck_id,
)
from app import models
from app.services.srs import LEARNING_SUCCESS_INTERVALS, compute_next_review_state
from datetime import datetime


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
    create_deck(client, token, "D", en_id, ru_id)
    deck_id = get_main_deck_id(client, token, en_id, ru_id)

    c1 = add_card(client, token, deck_id, "hello", "привет")
    c2 = add_card(client, token, deck_id, "bye", "пока")

    # status before studying
    r = client.get(f"/api/v1/study/decks/{deck_id}/status", headers=auth_headers(token))
    assert r.status_code == 200, r.text
    status1 = r.json()
    assert status1["deck_id"] == deck_id
    assert status1["new_available_count"] >= 2

    # next batch
    r = client.get(
        f"/api/v1/study/decks/{deck_id}/next",
        params={"limit": 2, "new_ratio": 1.0},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    batch = r.json()
    assert batch["deck_id"] == deck_id
    assert batch["count"] in (1, 2)
    assert len(batch["cards"]) == batch["count"]

    # study card (body correct)
    r = client.post(
        f"/api/v1/study/{c1['id']}", json={"learned": True}, headers=auth_headers(token)
    )
    assert r.status_code == 200, r.text
    prog = r.json()
    assert prog["card_id"] == c1["id"]
    assert prog["times_seen"] >= 1

    # study card (quality)
    r = client.post(
        f"/api/v1/study/{c2['id']}", json={"learned": False}, headers=auth_headers(token)
    )
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
    create_deck(client, token, "D", en_id, ru_id)
    deck_id = get_main_deck_id(client, token, en_id, ru_id)
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
    assert p["stage"] == 1  # key: not 3


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


def test_stage_intervals_are_explicit_and_deterministic():
    now = datetime.utcnow()
    res = compute_next_review_state(
        status=models.ProgressStatus.LEARNING,
        stage=1,
        learned=True,
        now=now,
    )
    assert res.status == models.ProgressStatus.LEARNING
    assert res.stage == 2
    assert res.due_at == now + LEARNING_SUCCESS_INTERVALS[1]

    res2 = compute_next_review_state(
        status=models.ProgressStatus.LEARNING,
        stage=4,
        learned=True,
        now=now,
    )
    assert res2.stage == 5
    assert res2.due_at == now + LEARNING_SUCCESS_INTERVALS[4]


def test_next_batch_prioritizes_due_reviews_over_new(client, monkeypatch):
    monkeypatch.setattr("app.services.srs.FIRST_REVIEW_DELAY_SECONDS", 0)

    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "prio_user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    create_deck(client, token, "D", en_id, ru_id)
    deck_id = get_main_deck_id(client, token, en_id, ru_id)

    due_card = add_card(client, token, deck_id, "dueword", "перевод")
    new_card = add_card(client, token, deck_id, "newword", "новое")

    # Introduce first card: with delay=0 it becomes immediately due review.
    r = client.post(
        f"/api/v1/study/{due_card['id']}", json={"learned": True}, headers=auth_headers(token)
    )
    assert r.status_code == 200, r.text

    batch = client.get(
        f"/api/v1/study/decks/{deck_id}/next",
        params={"limit": 2, "new_ratio": 1.0},
        headers=auth_headers(token),
    )
    assert batch.status_code == 200, batch.text
    cards = batch.json()["cards"]
    ids = [c["id"] for c in cards]
    assert due_card["id"] in ids
    assert len(ids) == len(set(ids))
    # Reviews should come first in the queue ordering.
    assert ids[0] == due_card["id"]
    assert new_card["id"] in ids


def test_study_answer_updates_fields_consistently(client, token_headers, make_deck_with_cards):
    _, cards = make_deck_with_cards(n=1)
    card_id = cards[0]["id"]

    r1 = _post_learned(client, token_headers, card_id, True)
    assert r1.status_code == 200
    p1 = r1.json()
    assert p1["times_seen"] == 1
    assert p1["times_correct"] == 1
    assert p1["status"] == "learning"
    assert p1["stage"] == 1
    assert p1["due_at"] is not None
    assert p1["last_review"] is not None

    last_review_1 = datetime.fromisoformat(p1["last_review"])
    due_1 = datetime.fromisoformat(p1["due_at"])
    assert due_1 >= last_review_1

    r2 = _post_learned(client, token_headers, card_id, False)
    assert r2.status_code == 200
    p2 = r2.json()
    assert p2["times_seen"] == 2
    assert p2["times_correct"] == 1
    assert p2["status"] == "learning"
    assert p2["stage"] == 1
    assert p2["due_at"] is not None
    assert p2["last_review"] is not None
    last_review_2 = datetime.fromisoformat(p2["last_review"])
    due_2 = datetime.fromisoformat(p2["due_at"])
    assert last_review_2 >= last_review_1
    assert due_2 >= last_review_2
