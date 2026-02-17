from tests.conftest import auth_headers

def test_admin_can_create_language_and_user_can_list(client, admin_token, user_token):
    # create language as admin
    r = client.post(
        "/admin/languages",
        json={"name": "English", "code": "en"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 201, r.text
    lang = r.json()
    assert lang["name"] == "English"
    assert lang["code"] == "en"

    # list as normal user (read-only)
    r = client.get("/languages", headers=auth_headers(user_token))
    assert r.status_code == 200, r.text
    items = r.json()
    assert any(x["code"] == "en" for x in items)


def test_non_admin_cannot_create_language(client, user_token):
    r = client.post(
        "/admin/languages",
        json={"name": "Spanish", "code": "es"},
        headers=auth_headers(user_token),
    )
    assert r.status_code == 403