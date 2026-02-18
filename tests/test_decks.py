from tests.conftest import auth_headers

def _create_language(client, admin_token, name, code):
    r = client.post("/admin/languages", json={"name": name, "code": code}, headers=auth_headers(admin_token))
    assert r.status_code == 201, r.text
    return r.json()["id"]

def test_create_deck_and_cards_flow(client, admin_token, user_token):
    en_id = _create_language(client, admin_token, "English", "en")
    ru_id = _create_language(client, admin_token, "Russian", "ru")

    # create deck
    r = client.post(
        "/decks",
        json={"name": "My Deck", "source_language_id": en_id, "target_language_id": ru_id},
        headers=auth_headers(user_token),
    )
    assert r.status_code == 201, r.text
    deck = r.json()
    deck_id = deck["id"]

    # add card
    r = client.post(
        f"/decks/{deck_id}/cards",
        json={"front": "hello", "back": "привет", "example_sentence": "hello world"},
        headers=auth_headers(user_token),
    )
    assert r.status_code == 201, r.text
    card = r.json()
    assert card["front"] == "hello"
    assert card["back"] == "привет"

    # list cards
    r = client.get(f"/decks/{deck_id}/cards", headers=auth_headers(user_token))
    assert r.status_code == 200, r.text
    cards = r.json()
    assert len(cards) == 1
    assert cards[0]["id"] == card["id"]

    # list my decks
    r = client.get("/decks", headers=auth_headers(user_token))
    assert r.status_code == 200
    assert any(d["id"] == deck_id for d in r.json())