"""Follow graph + challenge gating."""
from tests.conftest import register_and_login, create_bet, follow, points


def test_follow_unfollow_and_counts(client):
    a = register_and_login(client, "amy")
    register_and_login(client, "ben")

    assert follow(client, a, "ben").status_code == 201
    assert client.get("/follows/ben/counts").json() == {"followers": 1, "following": 0}
    assert client.get("/follows/amy/counts").json() == {"followers": 0, "following": 1}
    assert client.get("/follows/ben/status", headers=a).json() == {"following": True}

    # Idempotent: following again is a no-op, still 1 follower
    assert follow(client, a, "ben").status_code == 201
    assert client.get("/follows/ben/counts").json()["followers"] == 1

    # Unfollow
    assert client.delete("/follows/ben", headers=a).status_code == 200
    assert client.get("/follows/ben/counts").json()["followers"] == 0


def test_cannot_follow_self(client):
    a = register_and_login(client, "sam")
    assert client.post("/follows/sam", headers=a).status_code == 400


def test_follow_unknown_user_404(client):
    a = register_and_login(client, "kim")
    assert client.post("/follows/ghost", headers=a).status_code == 404


def test_following_and_followers_lists(client):
    a = register_and_login(client, "lea")
    register_and_login(client, "max")
    follow(client, a, "max")
    following = client.get("/follows/me/following", headers=a).json()
    assert [u["username"] for u in following] == ["max"]


def test_challenge_requires_following(client):
    creator = register_and_login(client, "creator1")
    challenger = register_and_login(client, "chal1")
    bet_id = create_bet(client, creator, amount=5).json()["id"]

    # Not following → blocked
    r = client.post(f"/bets/{bet_id}/challenge", json={"amount": 3}, headers=challenger)
    assert r.status_code == 403

    # Follow, then challenge succeeds
    follow(client, challenger, "creator1")
    r = client.post(f"/bets/{bet_id}/challenge", json={"amount": 3}, headers=challenger)
    assert r.status_code == 201, r.text
    assert points(client, challenger) == 7  # 10 - 3 staked


def test_cannot_challenge_own_bet(client):
    creator = register_and_login(client, "creator2")
    bet_id = create_bet(client, creator, amount=5).json()["id"]
    r = client.post(f"/bets/{bet_id}/challenge", json={"amount": 2}, headers=creator)
    assert r.status_code == 400


def test_follower_gets_new_bet_notification(client):
    creator = register_and_login(client, "star")
    fan = register_and_login(client, "fan")
    follow(client, fan, "star")
    create_bet(client, creator, title="I will meditate 10 minutes", amount=2)
    notes = client.get("/notifications/", headers=fan).json()
    assert any("set a new goal" in n["message"] for n in notes)
