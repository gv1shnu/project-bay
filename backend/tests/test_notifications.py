"""Notification endpoints: list, unread count, mark-read (single + all), auth + ownership."""
from tests.conftest import register_and_login, create_bet, follow


def _seed_one_notification(client):
    """Follower x follows creator c, then c posts a bet -> x receives a notification."""
    ch = register_and_login(client, "creator")
    xh = register_and_login(client, "watcher")
    follow(client, xh, "creator")
    create_bet(client, ch, amount=3)
    return ch, xh


def test_list_notifications_newest_first(client):
    ch, xh = _seed_one_notification(client)
    create_bet(client, ch, title="I will read 20 pages today", amount=2)
    r = client.get("/notifications/", headers=xh)
    assert r.status_code == 200
    items = r.json()
    assert len(items) >= 2
    times = [n["created_at"] for n in items]
    assert times == sorted(times, reverse=True)  # newest first


def test_unread_count(client):
    ch, xh = _seed_one_notification(client)
    r = client.get("/notifications/unread", headers=xh)
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_mark_one_read_decrements_count(client):
    ch, xh = _seed_one_notification(client)
    before = client.get("/notifications/unread", headers=xh).json()["count"]
    nid = client.get("/notifications/", headers=xh).json()[0]["id"]
    assert client.post(f"/notifications/{nid}/read", headers=xh).json()["is_read"] == 1
    after = client.get("/notifications/unread", headers=xh).json()["count"]
    assert after == before - 1


def test_mark_missing_notification_404(client):
    ch, xh = _seed_one_notification(client)
    assert client.post("/notifications/99999/read", headers=xh).status_code == 404


def test_mark_all_read_zeroes_count(client):
    ch, xh = _seed_one_notification(client)
    create_bet(client, ch, title="I will run 3km today", amount=1)
    assert client.post("/notifications/read-all", headers=xh).json()["status"] == "ok"
    assert client.get("/notifications/unread", headers=xh).json()["count"] == 0


def test_notifications_require_auth(client):
    assert client.get("/notifications/").status_code == 401


def test_cannot_mark_another_users_notification(client):
    ch, xh = _seed_one_notification(client)
    nid = client.get("/notifications/", headers=xh).json()[0]["id"]
    intruder = register_and_login(client, "intruder")
    # Notification belongs to watcher; intruder can't touch it (scoped by user_id -> 404)
    assert client.post(f"/notifications/{nid}/read", headers=intruder).status_code == 404
