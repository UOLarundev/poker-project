def create_game(client, username="arun"):
    body = client.post("/api/games", json={"username": username}).json()
    return body["game_id"], body["hand_id"]


def end_hand_by_folding(client, hand_id, action_id):
    return client.post(f"/api/hands/{hand_id}/actions", json={
        "action_id": action_id, "action_type": "fold",
    }).json()


def test_unknown_username_is_404(client):
    resp = client.get("/api/players/nobody/hands")
    assert resp.status_code == 404


def test_fresh_game_shows_one_in_progress_hand(client):
    create_game(client, "arun")
    resp = client.get("/api/players/arun/hands")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["hand_number"] == 1
    assert body[0]["ended_at"] is None
    assert body[0]["winners"] is None
    assert body[0]["hero_hole"] is not None  # dealt immediately, known regardless of hand outcome


def test_finished_hand_shows_full_result(client):
    _, hand_id = create_game(client, "arun")
    result = end_hand_by_folding(client, hand_id, "11111111-1111-1111-1111-111111111111")

    body = client.get("/api/players/arun/hands").json()
    assert len(body) == 1
    entry = body[0]
    assert entry["ended_at"] is not None
    assert entry["winners"] == result["winners"]
    assert entry["pot_total"] == sum(result["winners"].values())


def test_most_recent_hand_first_and_limit_respected(client):
    _, hand_id = create_game(client, "arun")
    for i in range(3):
        end_hand_by_folding(client, hand_id, f"2222222{i}-2222-2222-2222-222222222222")
        next_resp = client.post(f"/api/hands/{hand_id}/next", json={
            "action_id": f"3333333{i}-3333-3333-3333-333333333333",
        }).json()
        if next_resp.get("game_over"):
            break
        hand_id = next_resp["hand_id"]

    body = client.get("/api/players/arun/hands?limit=2").json()
    assert len(body) == 2
    # Most recent first: descending hand_number.
    assert body[0]["hand_number"] > body[1]["hand_number"]


def test_history_is_scoped_per_player(client):
    create_game(client, "arun")
    create_game(client, "someoneelse")

    assert len(client.get("/api/players/arun/hands").json()) == 1
    assert len(client.get("/api/players/someoneelse/hands").json()) == 1
