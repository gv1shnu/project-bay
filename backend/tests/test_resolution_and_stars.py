"""Creator resolution (PATCH), star toggle, and contested-bet authorization."""
from tests.conftest import register_and_login, create_bet, follow, points


def _bet_with_challenger(client, cstake=5, xstake=3):
    ch = register_and_login(client, "creator")
    xh = register_and_login(client, "chal")
    bet_id = create_bet(client, ch, amount=cstake).json()["id"]
    follow(client, xh, "creator")
    client.post(f"/bets/{bet_id}/challenge", json={"amount": xstake}, headers=xh)
    return ch, xh, bet_id


# ── PATCH /bets/{id} resolution ────────────────────────────────────────────

def test_creator_cancel_refunds_everyone(client):
    ch, xh, bet_id = _bet_with_challenger(client, cstake=5, xstake=3)
    assert points(client, ch) == 5 and points(client, xh) == 7
    r = client.patch(f"/bets/{bet_id}", json={"status": "cancelled"}, headers=ch)
    assert r.status_code == 200
    assert r.json()["status"] == "cancelled"
    assert points(client, ch) == 10  # creator refunded
    assert points(client, xh) == 10  # challenger refunded


def test_non_creator_cannot_resolve(client):
    ch, xh, bet_id = _bet_with_challenger(client)
    # resolve_bet scopes by creator id -> a stranger's PATCH looks like a missing bet
    r = client.patch(f"/bets/{bet_id}", json={"status": "cancelled"}, headers=xh)
    assert r.status_code == 404


def test_cannot_resolve_already_resolved_bet(client):
    ch, xh, bet_id = _bet_with_challenger(client)
    assert client.patch(f"/bets/{bet_id}", json={"status": "cancelled"}, headers=ch).status_code == 200
    r = client.patch(f"/bets/{bet_id}", json={"status": "cancelled"}, headers=ch)
    assert r.status_code == 400
    assert "active" in r.json()["detail"].lower()


def test_resolve_requires_auth(client):
    ch, xh, bet_id = _bet_with_challenger(client)
    assert client.patch(f"/bets/{bet_id}", json={"status": "cancelled"}).status_code == 401


def test_creator_cannot_self_declare_won_with_active_challengers(client):
    """A contested bet can't be won by creator fiat — it must go through review."""
    ch, xh, bet_id = _bet_with_challenger(client, cstake=5, xstake=3)
    r = client.patch(f"/bets/{bet_id}", json={"status": "won"}, headers=ch)
    assert r.status_code == 403
    assert points(client, ch) == 5  # creator did NOT sweep the 8-pt pot (still just their leftover)
    assert points(client, xh) == 7  # challenger's stake is untouched


def test_creator_can_self_resolve_uncontested_bet(client):
    """With no challengers, the creator may still settle their own bet (gets their stake back)."""
    ch = register_and_login(client, "solo")
    bet_id = create_bet(client, ch, amount=4).json()["id"]
    r = client.patch(f"/bets/{bet_id}", json={"status": "won"}, headers=ch)
    assert r.status_code == 200
    assert points(client, ch) == 10  # 10 - 4 stake, + 4 pot back


# ── POST /bets/{id}/star ───────────────────────────────────────────────────

def test_star_then_unstar_toggles(client):
    ch = register_and_login(client, "creator")
    bet_id = create_bet(client, ch, amount=2).json()["id"]
    viewer = register_and_login(client, "viewer")

    r1 = client.post(f"/bets/{bet_id}/star", headers=viewer).json()
    assert r1["starred"] is True and r1["stars"] == 1
    r2 = client.post(f"/bets/{bet_id}/star", headers=viewer).json()
    assert r2["starred"] is False and r2["stars"] == 0


def test_star_requires_auth(client):
    ch = register_and_login(client, "creator")
    bet_id = create_bet(client, ch, amount=2).json()["id"]
    assert client.post(f"/bets/{bet_id}/star").status_code == 401


def test_star_nonexistent_bet_404(client):
    viewer = register_and_login(client, "viewer")
    assert client.post("/bets/9999/star", headers=viewer).status_code == 404
