"""Auth error paths, single-bet fetch, pagination shapes, public profiles + user count."""
from tests.conftest import register_and_login, create_bet, follow


# ── auth ───────────────────────────────────────────────────────────────────

def test_login_wrong_password_401(client):
    register_and_login(client, "bob")
    r = client.post("/auth/login", data={"username": "bob", "password": "nope"})
    assert r.status_code == 401


def test_login_unknown_user_401(client):
    r = client.post("/auth/login", data={"username": "ghost", "password": "whatever"})
    assert r.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/auth/me").status_code == 401


def test_me_with_bad_token_401(client):
    assert client.get("/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


def test_register_rejects_duplicate_email(client):
    register_and_login(client, "u1", email="dupe@gmail.com")
    r = client.post("/auth/register", json={"username": "u2", "email": "dupe@gmail.com", "password": "secret123"})
    assert r.status_code == 409


# ── public profile + count ─────────────────────────────────────────────────

def test_public_profile_and_404(client):
    register_and_login(client, "carol")
    r = client.get("/auth/user/carol")
    assert r.status_code == 200
    assert r.json()["username"] == "carol"
    assert client.get("/auth/user/nobody").status_code == 404


def test_user_count_grows(client):
    before = client.get("/auth/stats/count").json()
    before_n = before if isinstance(before, int) else before.get("count", list(before.values())[0])
    register_and_login(client, "newperson")
    after = client.get("/auth/stats/count").json()
    after_n = after if isinstance(after, int) else after.get("count", list(after.values())[0])
    assert after_n == before_n + 1


# ── single bet fetch ───────────────────────────────────────────────────────

def test_get_bet_by_id_and_404(client):
    ch = register_and_login(client, "creator")
    bet_id = create_bet(client, ch, amount=3).json()["id"]
    r = client.get(f"/bets/{bet_id}")
    assert r.status_code == 200
    assert r.json()["id"] == bet_id
    assert client.get("/bets/9999").status_code == 404


# ── pagination endpoints ───────────────────────────────────────────────────

def _assert_paginated(payload):
    assert {"items", "total", "page", "limit", "pages"} <= set(payload)
    assert isinstance(payload["items"], list)


def test_public_feed_pagination_shape(client):
    ch = register_and_login(client, "creator")
    create_bet(client, ch, amount=2)
    payload = client.get("/bets/public?limit=5").json()
    _assert_paginated(payload)
    assert payload["total"] >= 1


def test_my_bets_requires_auth_and_scopes_to_user(client):
    ch = register_and_login(client, "creator")
    other = register_and_login(client, "other")
    create_bet(client, ch, amount=2)
    assert client.get("/bets/").status_code == 401  # auth required
    payload = client.get("/bets/", headers=ch).json()
    _assert_paginated(payload)
    assert payload["total"] == 1  # only the creator's own bet
    assert client.get("/bets/", headers=other).json()["total"] == 0


def test_disputes_feed_shape(client):
    payload = client.get("/bets/disputes").json()
    _assert_paginated(payload)
