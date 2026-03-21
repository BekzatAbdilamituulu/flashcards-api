from tests.conftest import (
    add_card,
    admin_create_language,
    auth_headers,
    create_user_and_token,
    get_main_deck_id,
    set_default_languages,
)


def test_create_and_list_reading_sources_for_pair(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, user_token = create_user_and_token(client, "reader")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, user_token, en_id, ru_id)

    pair_resp = client.get("/api/v1/users/me/default-learning-pair", headers=auth_headers(user_token))
    assert pair_resp.status_code == 200, pair_resp.text
    pair_id = pair_resp.json()["id"]

    created = client.post(
        "/api/v1/reading-sources",
        json={
            "pair_id": pair_id,
            "title": "The Trial",
            "author": "Franz Kafka",
            "kind": "book",
            "reference": "Chapter 1",
        },
        headers=auth_headers(user_token),
    )
    assert created.status_code == 201, created.text
    source = created.json()
    assert source["title"] == "The Trial"
    assert source["author"] == "Franz Kafka"
    assert source["kind"] == "book"

    listed = client.get(
        f"/api/v1/reading-sources?pair_id={pair_id}&include_stats=true",
        headers=auth_headers(user_token),
    )
    assert listed.status_code == 200, listed.text
    body = listed.json()
    assert body["meta"]["total"] >= 1
    assert any(item["id"] == source["id"] for item in body["items"])


def test_creating_reading_source_does_not_create_new_deck(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, user_token = create_user_and_token(client, "reader_no_new_deck")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, user_token, en_id, ru_id)

    pair_id = client.get(
        "/api/v1/users/me/default-learning-pair",
        headers=auth_headers(user_token),
    ).json()["id"]

    decks_before = client.get("/api/v1/decks", headers=auth_headers(user_token))
    assert decks_before.status_code == 200, decks_before.text
    deck_ids_before = {item["id"] for item in decks_before.json().get("items", [])}

    created = client.post(
        "/api/v1/reading-sources",
        json={
            "pair_id": pair_id,
            "title": "Martin Eden",
            "author": "Jack London",
            "kind": "book",
        },
        headers=auth_headers(user_token),
    )
    assert created.status_code == 201, created.text

    decks_after = client.get("/api/v1/decks", headers=auth_headers(user_token))
    assert decks_after.status_code == 200, decks_after.text
    deck_ids_after = {item["id"] for item in decks_after.json().get("items", [])}

    assert deck_ids_after == deck_ids_before



def test_quick_add_with_existing_reading_source_id_validates_pair(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, user_token = create_user_and_token(client, "reader")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    es_id = admin_create_language(client, admin_token, "Spanish", "es")

    set_default_languages(client, user_token, en_id, ru_id)
    pair_ru = client.get("/api/v1/users/me/default-learning-pair", headers=auth_headers(user_token)).json()["id"]

    create_es_pair = client.post(
        "/api/v1/users/me/learning-pairs",
        json={
            "source_language_id": en_id,
            "target_language_id": es_id,
            "make_default": False,
        },
        headers=auth_headers(user_token),
    )
    assert create_es_pair.status_code in (200, 201), create_es_pair.text
    pair_es = create_es_pair.json()["id"]

    source_resp = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": pair_ru, "title": "1984"},
        headers=auth_headers(user_token),
    )
    assert source_resp.status_code == 201, source_resp.text
    source_id = source_resp.json()["id"]

    ok = client.post(
        "/api/v1/inbox/word",
        json={
            "front": "grim",
            "back": "мрачный",
            "source_language_id": en_id,
            "target_language_id": ru_id,
            "reading_source_id": source_id,
        },
        headers=auth_headers(user_token),
    )
    assert ok.status_code == 201, ok.text
    assert ok.json()["card"]["reading_source_id"] == source_id

    mismatch = client.post(
        "/api/v1/inbox/word",
        json={
            "front": "claro",
            "back": "ясный",
            "source_language_id": en_id,
            "target_language_id": es_id,
            "reading_source_id": source_id,
        },
        headers=auth_headers(user_token),
    )
    assert mismatch.status_code == 422, mismatch.text
    assert "pair" in mismatch.json()["detail"].lower()

    # Same user can still create for ES pair when source is created for ES.
    source_es_resp = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": pair_es, "title": "Don Quixote"},
        headers=auth_headers(user_token),
    )
    assert source_es_resp.status_code == 201, source_es_resp.text


def test_quick_add_rejects_other_users_reading_source(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, owner_token = create_user_and_token(client, "owner")
    _, other_token = create_user_and_token(client, "other")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, owner_token, en_id, ru_id)
    set_default_languages(client, other_token, en_id, ru_id)

    owner_pair = client.get(
        "/api/v1/users/me/default-learning-pair",
        headers=auth_headers(owner_token),
    ).json()["id"]

    source_resp = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": owner_pair, "title": "War and Peace"},
        headers=auth_headers(owner_token),
    )
    assert source_resp.status_code == 201, source_resp.text
    source_id = source_resp.json()["id"]

    forbidden = client.post(
        "/api/v1/inbox/word",
        json={
            "front": "legacy",
            "back": "наследие",
            "source_language_id": en_id,
            "target_language_id": ru_id,
            "reading_source_id": source_id,
        },
        headers=auth_headers(other_token),
    )
    assert forbidden.status_code == 404, forbidden.text


def test_deck_cards_can_be_filtered_by_reading_source(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "reader_filter")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)
    deck_id = get_main_deck_id(client, token, en_id, ru_id)
    pair_id = client.get(
        "/api/v1/users/me/default-learning-pair",
        headers=auth_headers(token),
    ).json()["id"]

    source_1 = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": pair_id, "title": "Book One"},
        headers=auth_headers(token),
    ).json()
    source_2 = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": pair_id, "title": "Book Two"},
        headers=auth_headers(token),
    ).json()

    c1 = client.post(
        f"/api/v1/decks/{deck_id}/cards",
        json={"front": "abate", "back": "ослабевать", "reading_source_id": source_1["id"]},
        headers=auth_headers(token),
    )
    assert c1.status_code == 201, c1.text
    c2 = client.post(
        f"/api/v1/decks/{deck_id}/cards",
        json={"front": "brisk", "back": "бодрый", "reading_source_id": source_2["id"]},
        headers=auth_headers(token),
    )
    assert c2.status_code == 201, c2.text

    filtered = client.get(
        f"/api/v1/decks/{deck_id}/cards?reading_source_id={source_1['id']}",
        headers=auth_headers(token),
    )
    assert filtered.status_code == 200, filtered.text
    items = filtered.json()["items"]
    assert len(items) == 1
    assert items[0]["front"] == "abate"
    assert items[0]["reading_source_id"] == source_1["id"]


def test_reading_source_stats_include_totals_today_and_last_added(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "reader_stats")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)
    deck_id = get_main_deck_id(client, token, en_id, ru_id)
    pair_id = client.get(
        "/api/v1/users/me/default-learning-pair",
        headers=auth_headers(token),
    ).json()["id"]

    source = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": pair_id, "title": "The Castle", "author": "Kafka"},
        headers=auth_headers(token),
    ).json()

    card_1 = add_card(client, token, deck_id, "arcane", "тайный")
    card_2 = add_card(client, token, deck_id, "lucid", "ясный")
    update_1 = client.patch(
        f"/api/v1/decks/{deck_id}/cards/{card_1['id']}",
        json={"reading_source_id": source["id"]},
        headers=auth_headers(token),
    )
    assert update_1.status_code == 200, update_1.text
    update_2 = client.patch(
        f"/api/v1/decks/{deck_id}/cards/{card_2['id']}",
        json={"reading_source_id": source["id"]},
        headers=auth_headers(token),
    )
    assert update_2.status_code == 200, update_2.text

    listed = client.get(
        f"/api/v1/reading-sources?pair_id={pair_id}&include_stats=true",
        headers=auth_headers(token),
    )
    assert listed.status_code == 200, listed.text
    item = next(x for x in listed.json()["items"] if x["id"] == source["id"])
    assert item["total_cards"] == 2
    assert item["due_cards"] >= 0
    assert item["added_today"] >= 2
    assert item["last_added_at"] is not None


def test_reading_source_stats_count_only_main_deck_cards(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "reader_main_only_stats")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)
    main_deck_id = get_main_deck_id(client, token, en_id, ru_id)
    pair_id = client.get(
        "/api/v1/users/me/default-learning-pair",
        headers=auth_headers(token),
    ).json()["id"]

    users_deck_resp = client.post(
        "/api/v1/decks",
        json={
            "name": "Scratch",
            "source_language_id": en_id,
            "target_language_id": ru_id,
            "deck_type": "users",
        },
        headers=auth_headers(token),
    )
    assert users_deck_resp.status_code == 201, users_deck_resp.text
    users_deck_id = users_deck_resp.json()["id"]

    source = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": pair_id, "title": "Martin Eden"},
        headers=auth_headers(token),
    ).json()

    add_main = client.post(
        f"/api/v1/decks/{main_deck_id}/cards",
        json={"front": "stern", "back": "суровый", "reading_source_id": source["id"]},
        headers=auth_headers(token),
    )
    assert add_main.status_code == 201, add_main.text

    add_users = client.post(
        f"/api/v1/decks/{users_deck_id}/cards",
        json={"front": "harbor", "back": "гавань", "reading_source_id": source["id"]},
        headers=auth_headers(token),
    )
    assert add_users.status_code == 201, add_users.text

    listed = client.get(
        f"/api/v1/reading-sources?pair_id={pair_id}&include_stats=true",
        headers=auth_headers(token),
    )
    assert listed.status_code == 200, listed.text
    item = next(x for x in listed.json()["items"] if x["id"] == source["id"])
    assert item["total_cards"] == 1



def test_update_reading_source_is_owner_scoped(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, owner_token = create_user_and_token(client, "reader_update_owner")
    _, other_token = create_user_and_token(client, "reader_update_other")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, owner_token, en_id, ru_id)
    set_default_languages(client, other_token, en_id, ru_id)

    owner_pair = client.get(
        "/api/v1/users/me/default-learning-pair",
        headers=auth_headers(owner_token),
    ).json()["id"]

    source_resp = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": owner_pair, "title": "The Trial", "author": "Kafka"},
        headers=auth_headers(owner_token),
    )
    assert source_resp.status_code == 201, source_resp.text
    source_id = source_resp.json()["id"]

    updated = client.patch(
        f"/api/v1/reading-sources/{source_id}",
        json={
            "title": "The Castle",
            "author": "Franz Kafka",
            "kind": "book",
            "reference": "Chapter 2",
        },
        headers=auth_headers(owner_token),
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["title"] == "The Castle"
    assert body["author"] == "Franz Kafka"
    assert body["kind"] == "book"
    assert body["reference"] == "Chapter 2"

    forbidden = client.patch(
        f"/api/v1/reading-sources/{source_id}",
        json={"title": "Nope"},
        headers=auth_headers(other_token),
    )
    assert forbidden.status_code == 404, forbidden.text


def test_delete_reading_source_blocks_when_cards_reference_it(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "reader_delete_blocked")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)
    deck_id = get_main_deck_id(client, token, en_id, ru_id)
    pair_id = client.get(
        "/api/v1/users/me/default-learning-pair",
        headers=auth_headers(token),
    ).json()["id"]

    source = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": pair_id, "title": "Book In Use"},
        headers=auth_headers(token),
    ).json()

    card_resp = client.post(
        f"/api/v1/decks/{deck_id}/cards",
        json={"front": "abate", "back": "ослабевать", "reading_source_id": source["id"]},
        headers=auth_headers(token),
    )
    assert card_resp.status_code == 201, card_resp.text

    deleted = client.delete(
        f"/api/v1/reading-sources/{source['id']}",
        headers=auth_headers(token),
    )
    assert deleted.status_code == 409, deleted.text
    assert "reference" in deleted.json()["detail"].lower()


def test_delete_reading_source_succeeds_when_unused(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "reader_delete_unused")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    set_default_languages(client, token, en_id, ru_id)
    pair_id = client.get(
        "/api/v1/users/me/default-learning-pair",
        headers=auth_headers(token),
    ).json()["id"]

    source_resp = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": pair_id, "title": "Disposable Source"},
        headers=auth_headers(token),
    )
    assert source_resp.status_code == 201, source_resp.text
    source_id = source_resp.json()["id"]

    deleted = client.delete(
        f"/api/v1/reading-sources/{source_id}",
        headers=auth_headers(token),
    )
    assert deleted.status_code == 204, deleted.text

    missing = client.get(
        f"/api/v1/reading-sources/{source_id}",
        headers=auth_headers(token),
    )
    assert missing.status_code == 404, missing.text


def test_reading_source_stats_are_pair_scoped(client):
    _, admin_token = create_user_and_token(client, "admin")
    _, token = create_user_and_token(client, "reader_pair_stats")

    en_id = admin_create_language(client, admin_token, "English", "en")
    ru_id = admin_create_language(client, admin_token, "Russian", "ru")
    es_id = admin_create_language(client, admin_token, "Spanish", "es")
    set_default_languages(client, token, en_id, ru_id)

    pair_ru = client.get(
        "/api/v1/users/me/default-learning-pair",
        headers=auth_headers(token),
    ).json()["id"]
    deck_ru = get_main_deck_id(client, token, en_id, ru_id)

    pair_es_resp = client.post(
        "/api/v1/users/me/learning-pairs",
        json={
            "source_language_id": en_id,
            "target_language_id": es_id,
            "make_default": False,
        },
        headers=auth_headers(token),
    )
    assert pair_es_resp.status_code in (200, 201), pair_es_resp.text
    pair_es = pair_es_resp.json()["id"]
    deck_es = get_main_deck_id(client, token, en_id, es_id)

    source_ru = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": pair_ru, "title": "RU Source"},
        headers=auth_headers(token),
    ).json()
    source_es = client.post(
        "/api/v1/reading-sources",
        json={"pair_id": pair_es, "title": "ES Source"},
        headers=auth_headers(token),
    ).json()

    add_ru = client.post(
        f"/api/v1/decks/{deck_ru}/cards",
        json={"front": "stoic", "back": "стойкий", "reading_source_id": source_ru["id"]},
        headers=auth_headers(token),
    )
    assert add_ru.status_code == 201, add_ru.text
    add_es = client.post(
        f"/api/v1/decks/{deck_es}/cards",
        json={"front": "claro", "back": "ясный", "reading_source_id": source_es["id"]},
        headers=auth_headers(token),
    )
    assert add_es.status_code == 201, add_es.text

    listed_ru = client.get(
        f"/api/v1/reading-sources?pair_id={pair_ru}&include_stats=true",
        headers=auth_headers(token),
    )
    assert listed_ru.status_code == 200, listed_ru.text
    items_ru = listed_ru.json()["items"]
    assert len(items_ru) == 1
    assert items_ru[0]["id"] == source_ru["id"]
    assert items_ru[0]["total_cards"] == 1
