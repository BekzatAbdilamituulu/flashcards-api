from app.services import auto_content
from tests.conftest import (
    admin_create_language,
    auth_headers,
    create_user_and_token,
    set_default_languages,
)


def test_inbox_quick_add_autofills_back_and_example(client, monkeypatch):
    _, admin_token = create_user_and_token(client, "admin")
    _, user_token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    set_default_languages(client, user_token, en_id, ru_id)

    def fake_tr(*, text: str, src_code: str, tgt_code: str):
        return "кот"

    def fake_ex(*, query: str, src_code: str, tgt_code: str):
        return "The cat.\nКот."

    monkeypatch.setattr(auto_content, "fetch_mymemory_translation", fake_tr)
    monkeypatch.setattr(auto_content, "fetch_tatoeba_example", fake_ex)

    r = client.post(
        "/api/v1/inbox/word",
        json={"front": "cat", "back": "", "example_sentence": None},
        headers=auth_headers(user_token),
    )
    assert r.status_code in (200, 201), r.text
    data = r.json()
    card = data["card"]
    assert card["back"] == "кот"
    assert "The cat" in (card["example_sentence"] or "")
