"""Background LLM moderation queue (with the model call stubbed)."""
from datetime import datetime, timezone, timedelta

import pytest

from app import models
from app.models import BetStatus, QueueStatus
from app.utils import llm_validator
from tests.conftest import TestingSessionLocal


@pytest.fixture(autouse=True)
def _point_validator_at_test_db(monkeypatch):
    monkeypatch.setattr("app.utils.llm_validator.SessionLocal", TestingSessionLocal)


def _queued_bet(stake=7, leftover=3):
    s = TestingSessionLocal()
    u = models.User(username="c", email="c@gmail.com", hashed_password="h", points=leftover)
    s.add(u)
    s.flush()
    bet = models.Bet(
        user_id=u.id, title="I will run", amount=stake, criteria="c",
        deadline=datetime.now(timezone.utc) + timedelta(days=1), status=BetStatus.ACTIVE,
    )
    s.add(bet)
    s.flush()
    s.add(models.BetValidationQueue(bet_id=bet.id, status=QueueStatus.PENDING))
    s.commit()
    ids = (u.id, bet.id)
    s.close()
    return ids


def test_invalid_bet_is_cancelled_and_refunded(monkeypatch):
    uid, bet_id = _queued_bet(stake=7, leftover=3)
    monkeypatch.setattr(
        "app.utils.llm_validator.validate_bet_with_llm",
        lambda title, criteria, amount: {"is_valid": False, "reason": "not allowed", "raw_response": "{}", "error": ""},
    )
    llm_validator.process_validation_queue()

    s = TestingSessionLocal()
    assert s.get(models.Bet, bet_id).status == BetStatus.CANCELLED
    assert s.get(models.User, uid).points == 10  # stake refunded (3 + 7)
    s.close()


def test_valid_bet_stays_active(monkeypatch):
    uid, bet_id = _queued_bet(stake=7, leftover=3)
    monkeypatch.setattr(
        "app.utils.llm_validator.validate_bet_with_llm",
        lambda title, criteria, amount: {"is_valid": True, "reason": "ok", "raw_response": "{}", "error": ""},
    )
    llm_validator.process_validation_queue()

    s = TestingSessionLocal()
    assert s.get(models.Bet, bet_id).status == BetStatus.ACTIVE
    assert s.get(models.User, uid).points == 3  # unchanged
    q = s.query(models.BetValidationQueue).filter_by(bet_id=bet_id).first()
    assert q.status == QueueStatus.COMPLETED and q.is_valid == 1
    s.close()
