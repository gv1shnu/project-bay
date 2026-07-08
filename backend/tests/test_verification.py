"""Proof upload + Level 1 review + Level 2 tribunal."""
import pytest

from tests.conftest import register_and_login, create_bet, follow, points

PNG = b"\x89PNG\r\n\x1a\n"


def _proof(client, headers, bet_id):
    return client.post(
        f"/bets/{bet_id}/proof",
        data={"comment": "done, see photo"},
        files={"file": ("proof.png", PNG, "image/png")},
        headers=headers,
    )


def setup_pending(client, creator="c", challenger="x", cstake=5, xstake=3):
    ch = register_and_login(client, creator)
    xh = register_and_login(client, challenger)
    bet_id = create_bet(client, ch, amount=cstake).json()["id"]
    follow(client, xh, creator)
    assert client.post(f"/bets/{bet_id}/challenge", json={"amount": xstake}, headers=xh).status_code == 201
    assert _proof(client, ch, bet_id).status_code == 200
    return ch, xh, bet_id


def _bet(client, bet_id):
    items = client.get("/bets/public?limit=100").json()["items"]
    return next(b for b in items if b["id"] == bet_id)


def test_proof_requires_creator(client):
    ch, xh, bet_id = setup_pending(client)
    # already pending; make a fresh active bet to test the 403 path
    ch2, xh2, bet2 = setup_pending(client, "cc", "xx")
    # A challenger uploading proof on their target's bet is forbidden
    r = _proof(client, xh2, bet2)
    assert r.status_code in (400, 403)


def test_proof_requires_a_challenger(client):
    ch = register_and_login(client, "solo")
    bet_id = create_bet(client, ch, amount=4).json()["id"]
    r = _proof(client, ch, bet_id)
    assert r.status_code == 400  # no challengers yet


def test_proof_sets_pending_and_deadline(client):
    ch, xh, bet_id = setup_pending(client)
    b = _bet(client, bet_id)
    assert b["status"] == "pending"
    assert b["proof_deadline"] is not None


def test_level1_all_approve_creator_wins(client):
    ch, xh, bet_id = setup_pending(client, cstake=5, xstake=3)
    r = client.post(f"/bets/{bet_id}/vote?vote=cool", headers=xh)
    assert r.json()["bet_status"] == "won"
    assert points(client, ch) == 5 + 8  # 10-5 stake, then wins pot of 8
    assert points(client, xh) == 7      # 10-3, loses stake


def test_level1_flag_raises_dispute(client):
    ch, xh, bet_id = setup_pending(client)
    r = client.post(f"/bets/{bet_id}/vote?vote=not_cool", headers=xh)
    assert r.json()["bet_status"] == "disputed"
    assert _bet(client, bet_id)["status"] == "disputed"


def test_only_challenger_can_vote(client):
    ch, xh, bet_id = setup_pending(client)
    outsider = register_and_login(client, "nosy")
    assert client.post(f"/bets/{bet_id}/vote?vote=cool", headers=outsider).status_code == 403


def test_cannot_vote_twice(client):
    ch, xh, bet_id = setup_pending(client)
    # First vote must be COOL so the bet stays PENDING (NOT COOL would dispute it)
    ch2, xh2, bet2 = setup_pending(client, "c2", "x2", cstake=5, xstake=2)
    # add a second challenger so one COOL vote doesn't resolve the bet
    third = register_and_login(client, "x2b")
    follow(client, third, "c2")
    client.post(f"/bets/{bet2}/challenge", json={"amount": 2}, headers=third)
    # re-upload not needed; proof already pending. First challenger votes cool.
    assert client.post(f"/bets/{bet2}/vote?vote=cool", headers=xh2).status_code == 200
    assert client.post(f"/bets/{bet2}/vote?vote=cool", headers=xh2).status_code == 400


def _dispute(client, cstake, xstake):
    ch, xh, bet_id = setup_pending(client, "creatorD", "chalD", cstake, xstake)
    client.post(f"/bets/{bet_id}/vote?vote=not_cool", headers=xh)
    return ch, xh, bet_id


def test_tribunal_creator_wins_and_court_fee(client):
    # Big pot so 5% court fee is >= 1 point (creator 10 + challenger 10 = 20, fee = 1)
    ch, xh, bet_id = _dispute(client, cstake=10, xstake=10)
    jurors = [register_and_login(client, f"j{i}") for i in range(3)]
    for j in jurors[:2]:
        assert client.post(f"/bets/{bet_id}/jury-vote?vote=cool", headers=j).json()["bet_status"] == "disputed"
    res = client.post(f"/bets/{bet_id}/jury-vote?vote=cool", headers=jurors[2])
    assert res.json()["bet_status"] == "won"
    # creator had 0 (staked all 10); wins pot(20) - fee(1) = 19
    assert points(client, ch) == 19
    # exactly one juror received the 1-point fee
    juror_pts = sorted(points(client, j) for j in jurors)
    assert juror_pts == [10, 10, 11]


def test_tribunal_challengers_win(client):
    ch, xh, bet_id = _dispute(client, cstake=10, xstake=10)
    jurors = [register_and_login(client, f"k{i}") for i in range(3)]
    for j in jurors:
        client.post(f"/bets/{bet_id}/jury-vote?vote=not_cool", headers=j)
    assert _bet(client, bet_id)["status"] == "lost"
    assert points(client, xh) == 19  # challenger takes pot(20) - fee(1)


def test_jury_neutrality(client):
    ch, xh, bet_id = _dispute(client, cstake=5, xstake=3)
    assert client.post(f"/bets/{bet_id}/jury-vote?vote=cool", headers=ch).status_code == 403   # creator
    assert client.post(f"/bets/{bet_id}/jury-vote?vote=cool", headers=xh).status_code == 403   # challenger
    juror = register_and_login(client, "fair")
    assert client.post(f"/bets/{bet_id}/jury-vote?vote=cool", headers=juror).status_code == 200
    assert client.post(f"/bets/{bet_id}/jury-vote?vote=cool", headers=juror).status_code == 400  # no double vote


def test_jury_vote_requires_disputed_status(client):
    ch, xh, bet_id = setup_pending(client)  # still PENDING, not disputed
    juror = register_and_login(client, "early")
    assert client.post(f"/bets/{bet_id}/jury-vote?vote=cool", headers=juror).status_code == 400
