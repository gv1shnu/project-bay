"""Admin endpoints: passphrase gate + users/bets listings.

conftest sets ADMIN_PASSPHRASE=secret.
"""
from tests.conftest import register_and_login, create_bet, follow

OK = {"X-Admin-Passphrase": "secret"}
BAD = {"X-Admin-Passphrase": "wrong"}


def test_verify_correct_passphrase(client):
    r = client.post("/admin/verify", headers=OK)
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_verify_wrong_passphrase_403(client):
    assert client.post("/admin/verify", headers=BAD).status_code == 403


def test_verify_missing_header_422(client):
    # Header(...) is required, so its absence is a validation error, not a 403.
    assert client.post("/admin/verify").status_code == 422


def test_users_listing_requires_passphrase(client):
    register_and_login(client, "alice")
    assert client.get("/admin/users", headers=BAD).status_code == 403
    r = client.get("/admin/users", headers=OK)
    assert r.status_code == 200
    users = r.json()
    assert any(u["username"] == "alice" for u in users)
    assert all({"id", "username", "email", "points"} <= set(u) for u in users)


def test_bets_listing_includes_challenges(client):
    ch = register_and_login(client, "creator")
    xh = register_and_login(client, "chal")
    bet_id = create_bet(client, ch, amount=5).json()["id"]
    follow(client, xh, "creator")
    client.post(f"/bets/{bet_id}/challenge", json={"amount": 3}, headers=xh)

    r = client.get("/admin/bets", headers=OK)
    assert r.status_code == 200
    bet = next(b for b in r.json() if b["id"] == bet_id)
    assert bet["username"] == "creator"
    assert bet["status"] == "active"
    assert len(bet["challenges"]) == 1
    assert bet["challenges"][0]["challenger_username"] == "chal"


def test_bets_listing_requires_passphrase(client):
    assert client.get("/admin/bets", headers=BAD).status_code == 403
