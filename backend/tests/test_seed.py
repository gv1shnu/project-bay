"""Demo seed — initial build and auto-refresh of expired demo bets."""
from datetime import datetime, timezone, timedelta

import pytest

from app import models, seed
from app.models import BetStatus
from tests.conftest import TestingSessionLocal

PAST = datetime.now(timezone.utc) - timedelta(days=1)


@pytest.fixture(autouse=True)
def _point_seed_at_test_db(monkeypatch):
    monkeypatch.setattr("app.seed.SessionLocal", TestingSessionLocal)


def _statuses(db):
    return sorted(b.status.value for b in db.query(models.Bet))


def _open_count(db):
    return db.query(models.Bet).filter(models.Bet.status.in_(seed.OPEN_STATUSES)).count()


def _expire_open_bets(db):
    for b in db.query(models.Bet).filter(models.Bet.status.in_(seed.OPEN_STATUSES)):
        b.status = BetStatus.WON
    db.commit()


def test_seed_if_empty_builds_every_state(db):
    assert seed.seed_if_empty() is True
    assert _statuses(db) == ["active", "active", "cancelled", "disputed", "lost", "pending", "won"]
    assert db.query(models.User).count() == len(seed.DEMO_USERNAMES)


def test_refresh_is_noop_while_demo_bets_are_open(db):
    seed.seed_if_empty()
    assert seed.refresh_demo_bets_if_stale() is False
    assert db.query(models.Bet).count() == 7


def test_refresh_rebuilds_open_bets_once_all_expired(db):
    seed.seed_if_empty()
    _expire_open_bets(db)
    assert _open_count(db) == 0

    assert seed.refresh_demo_bets_if_stale() is True
    db.expire_all()
    # The 4 open bets come back; the old history (7 bets) is kept, resolved ones aren't duplicated.
    assert db.query(models.Bet).count() == 11
    open_statuses = sorted(b.status.value for b in db.query(models.Bet)
                           .filter(models.Bet.status.in_(seed.OPEN_STATUSES)))
    assert open_statuses == ["active", "active", "disputed", "pending"]
    # No duplicate users or follow edges.
    assert db.query(models.User).count() == len(seed.DEMO_USERNAMES)
    assert db.query(models.Follow).count() == 13

    # Second call right after is a no-op.
    assert seed.refresh_demo_bets_if_stale() is False


def test_refresh_tops_up_drained_demo_wallets(db):
    seed.seed_if_empty()
    _expire_open_bets(db)
    for u in db.query(models.User):
        u.points = 0
    db.commit()

    assert seed.refresh_demo_bets_if_stale() is True
    db.expire_all()
    assert all(u.points >= 0 for u in db.query(models.User))


def test_refresh_never_touches_a_db_without_demo_users(db):
    real = models.User(username="realuser", email="r@gmail.com", hashed_password="h", points=10)
    db.add(real)
    db.flush()
    db.add(models.Bet(user_id=real.id, title="I will run", amount=5, criteria="c",
                      deadline=PAST, status=BetStatus.LOST))
    db.commit()

    assert seed.refresh_demo_bets_if_stale() is False
    assert db.query(models.Bet).count() == 1
    assert db.query(models.User).count() == 1


def test_refresh_ignores_real_users_open_bets(db):
    """A real user's active bet doesn't stop the demo from refreshing."""
    seed.seed_if_empty()
    _expire_open_bets(db)
    real = models.User(username="realuser", email="r@gmail.com", hashed_password="h", points=10)
    db.add(real)
    db.flush()
    db.add(models.Bet(user_id=real.id, title="I will run", amount=5, criteria="c",
                      deadline=datetime.now(timezone.utc) + timedelta(days=1), status=BetStatus.ACTIVE))
    db.commit()

    assert seed.refresh_demo_bets_if_stale() is True
