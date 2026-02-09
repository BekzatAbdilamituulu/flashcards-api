def create_language(client, token):
    res = client.post(
        "/languages",
        json={"name": "English", "code": "en"},
        headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code in (200, 201), res.text
    return res.json()["id"]

def test_create_word(client, token_user1):
    lang_id = create_language(client, token_user1)

    res = client.post(
        "/words",
        json={
            "text": "hello",
            "translation": "привет",
            "example_sentence": "",
            "language_id": lang_id
        },
        headers={"Authorization": f"Bearer {token_user1}"}
    )

    assert res.status_code == 200, res.text
    assert res.json()["text"] == "hello"


def test_words_private(client, token_user1, token_user2):
    lang1 = create_language(client, token_user1)

    client.post(
        "/words",
        json={
            "text": "hello",
            "translation": "привет",
            "example_sentence": "",
            "language_id": lang1
        },
        headers={"Authorization": f"Bearer {token_user1}"}
    )

    # user2 creates their own language
    lang2 = create_language(client, token_user2)

    res = client.get(
        f"/words?language_id={lang2}",
        headers={"Authorization": f"Bearer {token_user2}"}
    )

    assert res.status_code == 200
    assert res.json() == []


def test_cannot_update_foreign_word(client, token_user1, token_user2):
    lang1 = create_language(client, token_user1)
    res = client.post(
        "/words",
        json={
            "text": "hello",
            "translation": "привет",
            "example_sentence": "",
            "language_id": lang1
        },
        headers={"Authorization": f"Bearer {token_user1}"}
    )
    word_id = res.json()["id"]

    lang2 = create_language(client, token_user2)

    res = client.put(
        f"/words/{word_id}",
        json={
            "text": "bye",
            "translation": "пока",
            "example_sentence": "",
            "language_id": lang2
        },
        headers={"Authorization": f"Bearer {token_user2}"}
    )

    assert res.status_code == 404

def test_cannot_delete_foreign_word(client, token_user1, token_user2):
    lang1 = create_language(client, token_user1)
    res = client.post(
        "/words",
        json={
            "text": "hello",
            "translation": "привет",
            "example_sentence": "",
            "language_id": lang1
        },
        headers={"Authorization": f"Bearer {token_user1}"}
    )
    word_id = res.json()["id"]

    lang2 = create_language(client, token_user2)

    res = client.delete(
        f"/words/{word_id}",
        headers={"Authorization": f"Bearer {token_user2}"}
    )

    assert res.status_code == 404
