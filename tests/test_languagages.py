def test_create_language(client, user_token):
    res = client.post(
        "/languages",
        json={"name": "English", "code": "en"},
        headers={"Authorization": f"Bearer {user_token}"}
    )

    assert res.status_code == 200
    data = res.json()
    assert data["name"] == "English"


def test_languages_are_private(client, token_user1, token_user2):
    # user1 creates language
    client.post(
        "/languages",
        json={"name": "English", "code": "en"},
        headers={"Authorization": f"Bearer {token_user1}"}
    )

    # user2 list languages
    res = client.get(
        "/languages",
        headers={"Authorization": f"Bearer {token_user2}"}
    )

    assert res.status_code == 200
    assert res.json() == []   


def test_cannot_update_foreign_language(client, token_user1, token_user2):
    # user1 creates
    res = client.post(
        "/languages",
        json={"name": "English", "code": "en"},
        headers={"Authorization": f"Bearer {token_user1}"}
    )
    lang_id = res.json()["id"]

    # user2 tries update
    res = client.patch(
        f"/languages/{lang_id}",
        json={"name": "German"},
        headers={"Authorization": f"Bearer {token_user2}"}
    )

    assert res.status_code == 404
