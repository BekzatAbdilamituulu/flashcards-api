import pytest

from app import models
from app.services import auto_content
from tests.conftest import (
    admin_create_language,
    auth_headers,
    create_user_and_token,
    set_default_languages,
)


@pytest.fixture()
def setup_user_pair(client):
    # admin username MUST be "admin" (your env config uses ADMIN_USERNAMES=admin)
    _, admin_token = create_user_and_token(client, "admin")
    _, user_token = create_user_and_token(client, "user")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")

    set_default_languages(client, user_token, en_id, ru_id)
    return en_id, ru_id, user_token


def test_auto_preview_returns_suggestions_and_saves_cache(
    client, db_session, monkeypatch, setup_user_pair
):
    en_id, ru_id, token = setup_user_pair

    async def fake_tr_async(*, text: str, src_code: str, tgt_code: str):
        assert text == "manager"
        assert src_code == "en"
        assert tgt_code == "ru"
        return "менеджер"

    async def fake_ex_async(*, query: str, src_code: str, tgt_code: str):
        assert query == "manager"
        assert src_code == "eng"
        assert tgt_code == "rus"
        return "I am a manager.\nЯ менеджер."

    monkeypatch.setattr(auto_content, "fetch_mymemory_translation_async", fake_tr_async)
    monkeypatch.setattr(auto_content, "fetch_tatoeba_example_async", fake_ex_async)

    r = client.post(
        "/api/v1/auto/preview",
        json={"front": "manager", "source_language_id": en_id, "target_language_id": ru_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["front"] == "manager"
    assert data["suggested_back"] == "менеджер"
    assert data["suggested_example_sentence"].startswith("I am a manager")

    tr_row = (
        db_session.query(models.TranslationCache)
        .filter(
            models.TranslationCache.src_language_id == en_id,
            models.TranslationCache.tgt_language_id == ru_id,
            models.TranslationCache.source_text_norm == "manager",
        )
        .first()
    )
    assert tr_row is not None
    assert tr_row.translated_text == "менеджер"


def test_auto_preview_uses_cache_second_call_no_http(client, monkeypatch, setup_user_pair):
    en_id, ru_id, token = setup_user_pair

    calls = {"tr": 0, "ex": 0}

    async def fake_tr_async(*, text: str, src_code: str, tgt_code: str):
        calls["tr"] += 1
        return "кот"

    async def fake_ex_async(*, query: str, src_code: str, tgt_code: str):
        calls["ex"] += 1
        return "The cat.\nКот."

    monkeypatch.setattr(auto_content, "fetch_mymemory_translation_async", fake_tr_async)
    monkeypatch.setattr(auto_content, "fetch_tatoeba_example_async", fake_ex_async)

    r1 = client.post(
        "/api/v1/auto/preview",
        json={"front": "cat", "source_language_id": en_id, "target_language_id": ru_id},
        headers=auth_headers(token),
    )
    assert r1.status_code == 200, r1.text
    assert calls["tr"] == 1
    assert calls["ex"] == 1

    async def boom(*args, **kwargs):
        raise AssertionError("HTTP should NOT be called on cached preview")

    monkeypatch.setattr(auto_content, "fetch_mymemory_translation_async", boom)
    monkeypatch.setattr(auto_content, "fetch_tatoeba_example_async", boom)

    r2 = client.post(
        "/api/v1/auto/preview",
        json={"front": "cat", "source_language_id": en_id, "target_language_id": ru_id},
        headers=auth_headers(token),
    )
    assert r2.status_code == 200, r2.text
    assert r2.json()["suggested_back"] == "кот"


def test_auto_preview_allows_missing_example(client, monkeypatch, setup_user_pair):
    en_id, ru_id, token = setup_user_pair

    async def fake_tr_async(*, text: str, src_code: str, tgt_code: str):
        return "перевод"

    async def fake_ex_async(*, query: str, src_code: str, tgt_code: str):
        return None

    monkeypatch.setattr(auto_content, "fetch_mymemory_translation_async", fake_tr_async)
    monkeypatch.setattr(auto_content, "fetch_tatoeba_example_async", fake_ex_async)

    r = client.post(
        "/api/v1/auto/preview",
        json={"front": "something", "source_language_id": en_id, "target_language_id": ru_id},
        headers=auth_headers(token),
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["suggested_back"] == "перевод"
    assert data["suggested_example_sentence"] is None
