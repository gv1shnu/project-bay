"""Deadline-checker fail-safes — funds are never trapped."""
from datetime import datetime, timezone, timedelta

import pytest

from app import models, deadline_checker
from app.models import BetStatus, ChallengeStatus
from tests.conftest import TestingSessionLocal

PAST = datetime.now(timezone.utc) - timedelta(days=1)
FUTURE = datetime.now(timezone.utc) + timedelta(days=1)


@pytest.fixture(autouse=True)
def _point_checker_at_test_db(monkeypatch):
    monkeypatch.setattr("app.deadline_checker.SessionLocal", TestingSessionLocal)


def _seed(status, deadline=None, proof_deadline=None, dispute_deadline=None):
    """Create a creator + bet + one challenger; return bet_id."""
    s = TestingSessionLocal()
    creator = models.User(username="c", email="c@gmail.com", hashed_password="h", points=0)
    chal = models.User(username="x", email="x@gmail.com", hashed_password="h", points=0)
    s.add_all([creator, chal])
    s.flush()
    bet = models.Bet(
        user_id=creator.id, title="I will run", amount=5, criteria="c",
        deadline=deadline or FUTURE, status=status,
        proof_deadline=proof_deadline, dispute_deadline=dispute_deadline,
    )
    s.add(bet)
    s.flush()
    s.add(models.Challenge(bet_id=bet.id, challenger_id=chal.id, amount=3, status=ChallengeStatus.PENDING))
    s.commit()
    bet_id = bet.id
    s.close()
    return bet_id


def _status(bet_id):
    s = TestingSessionLocal()
    st = s.get(models.Bet, bet_id).status
    s.close()
    return st


def test_active_past_deadline_becomes_lost(db):
    bet_id = _seed(BetStatus.ACTIVE, deadline=PAST)
    deadline_checker.deadline_checker._check_deadlines()
    assert _status(bet_id) == BetStatus.LOST


def test_pending_past_review_window_becomes_won(db):
    bet_id = _seed(BetStatus.PENDING, deadline=PAST, proof_deadline=PAST)
    deadline_checker.deadline_checker._check_deadlines()
    assert _status(bet_id) == BetStatus.WON


def test_disputed_past_jury_window_becomes_won(db):
    bet_id = _seed(BetStatus.DISPUTED, deadline=PAST, proof_deadline=PAST, dispute_deadline=PAST)
    deadline_checker.deadline_checker._check_deadlines()
    assert _status(bet_id) == BetStatus.WON


def test_pending_within_window_is_untouched(db):
    bet_id = _seed(BetStatus.PENDING, deadline=PAST, proof_deadline=FUTURE)
    deadline_checker.deadline_checker._check_deadlines()
    assert _status(bet_id) == BetStatus.PENDING
