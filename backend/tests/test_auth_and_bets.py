"""Auth + bet-creation rules."""
from datetime import datetime, timezone, timedelta

from tests.conftest import register_and_login, create_bet, points


def test_register_login_me(client):
    headers = register_and_login(client, "alice")
    me = client.get("/auth/me", headers=headers).json()
    assert me["username"] == "alice"
    assert me["points"] == 10  # new users start with 10


def test_register_rejects_disallowed_email_domain(client):
    r = client.post("/auth/register", json={"username": "bob", "email": "bob@evil.xyz", "password": "secret123"})
    assert r.status_code == 422  # domain not in allowlist


def test_register_rejects_duplicate_username(client):
    register_and_login(client, "carol")
    r = client.post("/auth/register", json={"username": "carol", "email": "carol2@gmail.com", "password": "secret123"})
    assert r.status_code == 409  # UserAlreadyExistsError -> Conflict


def test_create_bet_deducts_stake(client):
    headers = register_and_login(client, "dave")
    r = create_bet(client, headers, amount=7)
    assert r.status_code == 201, r.text
    assert points(client, headers) == 3  # 10 - 7


def test_create_bet_rejects_non_personal_title(client):
    headers = register_and_login(client, "erin")
    r = create_bet(client, headers, title="Team A will win the cup", amount=3)
    assert r.status_code == 400  # regex gate: must be a personal commitment


def test_create_bet_insufficient_points(client):
    headers = register_and_login(client, "frank")
    r = create_bet(client, headers, amount=50)  # only has 10
    assert r.status_code == 400


def test_create_bet_rejects_nonpositive_amount(client):
    headers = register_and_login(client, "grace")
    deadline = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    r = client.post("/bets/", json={"title": "I will read 20 pages", "criteria": "photo", "amount": 0, "deadline": deadline}, headers=headers)
    assert r.status_code == 422  # amount must be > 0
