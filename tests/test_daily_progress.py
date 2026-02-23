from datetime import date, timedelta
from tests.conftest import (
    auth_headers,
    create_user_and_token,
    admin_create_language,
    create_deck,
    add_card,
)

def test_daily_progress_range_returns_rows(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    deck_id = create_deck(client, token, "D", en_id, ru_id)

    c1 = add_card(client, token, deck_id, "hello", "привет")
    c2 = add_card(client, token, deck_id, "bye", "пока")

    # Do some study to create DailyProgress rows
    r = client.post(f"/api/v1/study/{c1['id']}", json={"learned": True}, headers=auth_headers(token))
    assert r.status_code == 200, r.text
    r = client.post(f"/api/v1/study/{c2['id']}", json={"learned": False}, headers=auth_headers(token))
    assert r.status_code == 200, r.text

    today = date.today()
    r = client.get(
        "/api/v1/users/me/daily-progress",
        params={"from_date": today.isoformat(), "to_date": today.isoformat()},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    body = r.json()

    assert body["from_date"] == today.isoformat()
    assert body["to_date"] == today.isoformat()

    assert isinstance(body["items"], list)
    assert len(body["items"]) >= 1
    assert body["items"][0]["date"] == today.isoformat()
    assert body["items"][0]["cards_done"] >= 1

def test_daily_progress_invalid_range(client):
    _, token = create_user_and_token(client, "user")
    d1 = date.today()
    d2 = d1 - timedelta(days=1)

    r = client.get(
        "/api/v1/users/me/daily-progress",
        params={"from_date": d1.isoformat(), "to_date": d2.isoformat()},
        headers=auth_headers(token),
    )
    assert r.status_code == 400, r.text
