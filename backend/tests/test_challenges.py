"""Challenge creation guards + withdrawal lifecycle (refunds, permissions, status gates)."""
from tests.conftest import register_and_login, create_bet, follow, points

PNG = b"\x89PNG\r\n\x1a\n"


def _proof(client, headers, bet_id):
    return client.post(
        f"/bets/{bet_id}/proof",
        data={"comment": "done"},
        files={"file": ("proof.png", PNG, "image/png")},
        headers=headers,
    )


def _setup(client, cstake=5):
    """Creator c with a live bet; challenger x already following c. Returns (ch, xh, bet_id)."""
    ch = register_and_login(client, "creator")
    xh = register_and_login(client, "chal")
    bet_id = create_bet(client, ch, amount=cstake).json()["id"]
    follow(client, xh, "creator")
    return ch, xh, bet_id


# ── create_challenge ───────────────────────────────────────────────────────

def test_challenge_deducts_points_and_lists(client):
    ch, xh, bet_id = _setup(client)
    assert client.post(f"/bets/{bet_id}/challenge", json={"amount": 4}, headers=xh).status_code == 201
    assert points(client, xh) == 6  # 10 - 4 staked immediately
    lst = client.get(f"/bets/{bet_id}/challenges").json()
    assert len(lst) == 1
    assert lst[0]["challenger_username"] == "chal"
    assert lst[0]["status"] == "pending"
    assert lst[0]["amount"] == 4


def test_challenge_nonexistent_bet_404(client):
    xh = register_and_login(client, "x")
    assert client.post("/bets/9999/challenge", json={"amount": 2}, headers=xh).status_code == 404


def test_cannot_challenge_same_bet_twice(client):
    ch, xh, bet_id = _setup(client)
    assert client.post(f"/bets/{bet_id}/challenge", json={"amount": 2}, headers=xh).status_code == 201
    r = client.post(f"/bets/{bet_id}/challenge", json={"amount": 2}, headers=xh)
    assert r.status_code == 400
    assert "already challenged" in r.json()["detail"].lower()


def test_cannot_challenge_resolved_bet(client):
    ch, xh, bet_id = _setup(client)
    # Creator cancels the bet -> no longer ACTIVE
    assert client.patch(f"/bets/{bet_id}", json={"status": "cancelled"}, headers=ch).status_code == 200
    r = client.post(f"/bets/{bet_id}/challenge", json={"amount": 2}, headers=xh)
    assert r.status_code == 400
    assert "resolved" in r.json()["detail"].lower()


def test_challenge_insufficient_points(client):
    ch, xh, bet_id = _setup(client)
    r = client.post(f"/bets/{bet_id}/challenge", json={"amount": 999}, headers=xh)
    assert r.status_code == 400
    assert "insufficient" in r.json()["detail"].lower()


def test_challenge_nonpositive_amount_rejected(client):
    ch, xh, bet_id = _setup(client)
    # amount has gt=0 at the schema layer, so zero is a validation error (422).
    assert client.post(f"/bets/{bet_id}/challenge", json={"amount": 0}, headers=xh).status_code == 422


def test_get_challenges_nonexistent_bet_404(client):
    assert client.get("/bets/9999/challenges").status_code == 404


# ── withdraw_challenge ─────────────────────────────────────────────────────

def _challenge(client, xh, bet_id, amount=4):
    return client.post(f"/bets/{bet_id}/challenge", json={"amount": amount}, headers=xh).json()["id"]


def test_withdraw_refunds_and_marks_withdrew(client):
    ch, xh, bet_id = _setup(client)
    cid = _challenge(client, xh, bet_id, 4)
    assert points(client, xh) == 6
    r = client.post(f"/bets/{bet_id}/challenges/{cid}/withdraw", headers=xh)
    assert r.status_code == 200
    assert r.json()["status"] == "withdrew"
    assert points(client, xh) == 10  # fully refunded


def test_only_challenger_can_withdraw(client):
    ch, xh, bet_id = _setup(client)
    cid = _challenge(client, xh, bet_id, 3)
    outsider = register_and_login(client, "outsider")
    r = client.post(f"/bets/{bet_id}/challenges/{cid}/withdraw", headers=outsider)
    assert r.status_code == 403


def test_cannot_withdraw_once_bet_left_active(client):
    ch, xh, bet_id = _setup(client)
    cid = _challenge(client, xh, bet_id, 3)
    assert _proof(client, ch, bet_id).status_code == 200  # bet -> PENDING
    r = client.post(f"/bets/{bet_id}/challenges/{cid}/withdraw", headers=xh)
    assert r.status_code == 400
    assert "no longer active" in r.json()["detail"].lower()


def test_withdraw_nonexistent_challenge_404(client):
    ch, xh, bet_id = _setup(client)
    assert client.post(f"/bets/{bet_id}/challenges/9999/withdraw", headers=xh).status_code == 404
