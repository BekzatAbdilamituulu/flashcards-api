from tests.conftest import (
    admin_create_language,
    auth_headers,
    create_user_and_token,
    set_default_languages,
)


def test_update_my_goals(client):
    user, token = create_user_and_token(client, "goals_user_1")
    h = auth_headers(token)

    r = client.put(
        "/api/v1/users/me/goals",
        headers=h,
        json={"daily_card_target": 30, "daily_new_target": 10},
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["daily_card_target"] == 30
    assert data["daily_new_target"] == 10


def test_progress_summary_includes_goal_progress(client):
    user, token = create_user_and_token(client, "goals_user_2")
    h = auth_headers(token)

    # set goals
    r = client.put(
        "/api/v1/users/me/goals",
        headers=h,
        json={"daily_card_target": 20, "daily_new_target": 7},
    )
    assert r.status_code == 200, r.text

    # progress summary should include goal fields
    r = client.get("/api/v1/progress/summary", headers=h)
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["daily_card_target"] == 20
    assert data["daily_new_target"] == 7

    # If no study today, done should be 0
    assert data["cards_remaining"] == 20
    assert data["new_remaining"] == 7

    assert 0.0 <= data["cards_goal_pct"] <= 1.0
    assert 0.0 <= data["new_goal_pct"] <= 1.0