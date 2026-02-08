def test_study_flow(client):
    # 1) Register + login
    client.post("/auth/register", json={"username": "u1", "password": "12345678"})
    login = client.post("/auth/login", data={"username": "u1", "password": "12345678"})
    assert login.status_code == 200, login.text
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2) Create language
    r = client.post("/languages", json={"name": "TestLang", "code": "tl"})
    assert r.status_code == 200, r.text
    language_id = r.json()["id"]

    # 3) Create word
    r = client.post("/words", json={
        "text": "kopek",
        "translation": "dog",
        "example_sentence": "little dog",
        "language_id": language_id
    })
    assert r.status_code == 200, r.text
    word_id = r.json()["id"]

    # 4) Get next study item (new endpoint)
    r = client.get(
        "/study/next",
        params={"language_id": language_id, "limit": 10, "random_top": 5},
        headers=headers
    )
    assert r.status_code == 200, r.text

    # 5) Submit answer (new endpoint)
    r = client.post(f"/study/{word_id}", json={"correct": True}, headers=headers)
    assert r.status_code == 200, r.text
