def test_create_game_deals_a_hand_to_the_new_player(client):
    resp = client.post("/api/games", json={"username": "arun"})
    assert resp.status_code == 201

    body = resp.json()
    assert body["viewer_id"] == "arun"
    assert body["street"] == "PRE_FLOP"
    assert body["pot_total"] == 15  # 5 SB + 10 BB

    seats = {p["player_id"]: p for p in body["players"]}
    assert set(seats) == {"arun", "Bot A", "Bot B"}
    assert len(seats["arun"]["hole_cards"]) == 2
    # Bots' cards must never appear in the response.
    assert seats["Bot A"]["hole_cards"] is None
    assert seats["Bot B"]["hole_cards"] is None


def test_same_username_reuses_the_player_row_but_creates_a_new_game(client):
    first = client.post("/api/games", json={"username": "arun"}).json()
    second = client.post("/api/games", json={"username": "arun"}).json()
    assert first["game_id"] != second["game_id"]


def test_get_game_returns_what_was_just_created(client):
    created = client.post("/api/games", json={"username": "arun"}).json()
    fetched = client.get(f"/api/games/{created['game_id']}").json()

    # your_equity is a fresh Monte Carlo estimate on every single call —
    # even for the same unchanged game state, two independent samples
    # won't be bit-for-bit equal. Check it separately for presence/range;
    # everything else should still match exactly.
    created_equity = created.pop("your_equity")
    fetched_equity = fetched.pop("your_equity")
    assert fetched == created
    assert created_equity is not None and 0.0 <= created_equity <= 1.0
    assert fetched_equity is not None and 0.0 <= fetched_equity <= 1.0


def test_get_unknown_game_is_404(client):
    resp = client.get("/api/games/00000000-0000-0000-0000-000000000000")
    assert resp.status_code == 404


def test_rejects_empty_username(client):
    resp = client.post("/api/games", json={"username": ""})
    assert resp.status_code == 422  # Pydantic validation, not application code
