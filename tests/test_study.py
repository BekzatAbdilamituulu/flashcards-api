from datetime import datetime, timedelta
from tests.conftest import auth_headers

def _create_language(client, admin_token, name, code):
    r = client.post("/admin/languages", json={"name": name, "code": code}, headers=auth_headers(admin_token))
    assert r.status_code == 201, r.text
    return r.json()["id"]

def _create_deck_with_cards(client, admin_token, user_token, n=5):
    en_id = _create_language(client, admin_token, "English", "en")
    kg_id = _create_language(client, admin_token, "Kyrgyz", "ky")
    r = client.post(
        "/decks",
        json={"name": "Study Deck", "source_language_id": en_id, "target_language_id": kg_id},
        headers=auth_headers(user_token),
    )
    assert r.status_code == 201, r.text
    deck_id = r.json()["id"]

    card_ids = []
    for i in range(n):
        r = client.post(
            f"/decks/{deck_id}/cards",
            json={"front": f"w{i}", "back": f"t{i}"},
            headers=auth_headers(user_token),
        )
        assert r.status_code == 201, r.text
        card_ids.append(r.json()["id"])
    return deck_id, card_ids

def test_study_next_returns_cards_and_review_updates_progress(client, admin_token, user_token):
    deck_id, card_ids = _create_deck_with_cards(client, admin_token, user_token, n=6)

    # initial status: all new available, no due reviews
    r = client.get("/study/status", params={"deck_id": deck_id}, headers=auth_headers(user_token))
    assert r.status_code == 200, r.text
    status = r.json()
    assert status["deck_id"] == deck_id
    assert status["reviewed_today"] == 0
    assert status["new_introduced_today"] == 0
    assert status["due_count"] == 0
    assert status["new_available_count"] >= 6

    # get next batch (should contain some cards)
    r = client.get("/study/next", params={"deck_id": deck_id, "limit": 4, "new_ratio": 1.0}, headers=auth_headers(user_token))
    assert r.status_code == 200, r.text
    batch = r.json()
    assert batch["deck_id"] == deck_id
    assert batch["count"] == 4
    assert len(batch["cards"]) == 4

    first_card_id = batch["cards"][0]["id"]

    # answer study (use body with 'correct')
    r = client.post(f"/study/{first_card_id}", json={"correct": True}, headers=auth_headers(user_token))
    assert r.status_code == 200, r.text
    rec = r.json()
    assert rec["card_id"] == first_card_id
    assert rec["times_seen"] >= 1
    assert rec["last_review"] is not None
    assert rec["next_review"] is not None

    # status should reflect counts (cards_done increment is in daily_progress)
    r = client.get("/study/status", params={"deck_id": deck_id}, headers=auth_headers(user_token))
    assert r.status_code == 200, r.text
    status2 = r.json()
    assert status2["reviewed_today"] in (0, 1)  # first time is treated as "new" not a review
    assert status2["new_introduced_today"] >= 1