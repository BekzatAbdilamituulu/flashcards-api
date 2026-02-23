from tests.conftest import (
    auth_headers,
    create_user_and_token,
    admin_create_language,
)


def test_admin_languages_crud_and_user_list(client):
    # admin user must be username 'admin' because env ADMIN_USERNAMES="admin"
    _, admin_token = create_user_and_token(client, "admin")
    _, user_token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    # user can list languages
    r = client.get("/api/v1/languages", headers=auth_headers(user_token))
    assert r.status_code == 200, r.text
    codes = {x["code"] for x in r.json()}
    assert "en" in codes and "ru" in codes

    # admin update
    r = client.patch(
        f"/api/v1/admin/languages/{ru_id}",
        json={"name": "Русский", "code": "ru"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200, r.text
    assert r.json()["name"] == "Русский"

    # duplicate code should 409
    r = client.post(
        "/api/v1/admin/languages",
        json={"name": "English 2", "code": "en"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 409

    # non-admin cannot create
    r = client.post(
        "/api/v1/admin/languages",
        json={"name": "German", "code": "de"},
        headers=auth_headers(user_token),
    )
    assert r.status_code == 403

    # delete
    r = client.delete(f"/api/v1/admin/languages/{en_id}", headers=auth_headers(admin_token))
    assert r.status_code == 204

    # deleted not found
    r = client.patch(
        f"/api/v1/admin/languages/{en_id}",
        json={"name": "English", "code": "en"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 404
