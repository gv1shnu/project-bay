"""Service-level payout maths: apportionment + point conservation (no burning)."""
from datetime import datetime, timezone, timedelta

import pytest

from app import models
from app.models import BetStatus, ChallengeStatus
from app.services import bet_service as bs


# ── apportion() ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("total,weights", [
    (7, [4, 5]),
    (10, [1, 1, 1]),
    (100, [1, 1, 1]),
    (5, [3]),
    (1, [1, 1, 1]),
    (0, [1, 2]),
    (13, [2, 3, 5, 1]),
])
def test_apportion_conserves_total(total, weights):
    parts = bs.apportion(total, weights)
    assert sum(parts) == total
    assert all(p >= 0 for p in parts)


def test_apportion_matches_spec_scenario():
    # Spec Scenario 2: creator stake 7, challengers 4 & 5 -> +3 and +4
    assert bs.apportion(7, [4, 5]) == [3, 4]


# ── Helpers to build a bet in the DB ─────────────────────────────────────

def _user(db, name, pts):
    u = models.User(username=name, email=f"{name}@gmail.com", hashed_password="h", points=pts)
    db.add(u)
    db.flush()
    return u


def _bet_with_challengers(db, creator_leftover, stake, challenger_specs, status=BetStatus.PENDING):
    """challenger_specs: list of (leftover_points, stake). Stakes are already 'locked'."""
    creator = _user(db, "creator", creator_leftover)
    bet = models.Bet(
        user_id=creator.id, title="I will run", amount=stake, criteria="c",
        deadline=datetime.now(timezone.utc) + timedelta(days=1), status=status,
    )
    db.add(bet)
    db.flush()
    challengers = []
    for i, (left, s) in enumerate(challenger_specs):
        cu = _user(db, f"ch{i}", left)
        db.add(models.Challenge(bet_id=bet.id, challenger_id=cu.id, amount=s, status=ChallengeStatus.PENDING))
        challengers.append(cu)
    db.flush()
    return creator, bet, challengers


def _total(db):
    return sum(int(u.points) for u in db.query(models.User).all())


def test_won_creator_takes_pot(db):
    creator, bet, chs = _bet_with_challengers(db, 3, 7, [(6, 4), (5, 5)])
    before, pot = _total(db), 7 + 4 + 5
    bs.apply_resolution(db, bet, BetStatus.WON)
    assert _total(db) == before + pot
    assert db.get(models.User, creator.id).points == 3 + pot
    assert all(c.status == ChallengeStatus.LOST for c in bet.challenges)


def test_lost_proportional_split_no_burn(db):
    creator, bet, chs = _bet_with_challengers(db, 3, 7, [(6, 4), (5, 5)])
    before, pot = _total(db), 7 + 4 + 5
    bs.apply_resolution(db, bet, BetStatus.LOST)
    assert _total(db) == before + pot
    pts = sorted(db.get(models.User, c.id).points for c in chs)
    assert pts == [6 + 4 + 3, 5 + 5 + 4]  # stake back + proportional share of 7
    assert all(c.status == ChallengeStatus.WON for c in bet.challenges)


def test_cancelled_refunds_everyone(db):
    creator, bet, chs = _bet_with_challengers(db, 3, 7, [(6, 4), (5, 5)])
    before, pot = _total(db), 7 + 4 + 5
    bs.apply_resolution(db, bet, BetStatus.CANCELLED)
    assert _total(db) == before + pot
    assert db.get(models.User, creator.id).points == 3 + 7
    assert all(c.status == ChallengeStatus.WITHDREW for c in bet.challenges)


def test_dispute_creator_wins_with_court_fee(db):
    creator, bet, chs = _bet_with_challengers(db, 0, 10, [(0, 10)], status=BetStatus.DISPUTED)
    j1, j2, j3 = _user(db, "j1", 0), _user(db, "j2", 0), _user(db, "j3", 0)
    before, pot = _total(db), 20
    fee = pot * bs.COURT_FEE_PCT // 100  # = 1
    bs.resolve_dispute(db, bet, creator_wins=True, majority_juror_ids=[j1.id, j2.id, j3.id])
    assert _total(db) == before + pot                    # fully conserved
    assert db.get(models.User, creator.id).points == pot - fee
    assert sum(db.get(models.User, j).points for j in (j1.id, j2.id, j3.id)) == fee


def test_dispute_challengers_win(db):
    creator, bet, chs = _bet_with_challengers(db, 0, 10, [(0, 10)], status=BetStatus.DISPUTED)
    j1, j2, j3 = _user(db, "j1", 0), _user(db, "j2", 0), _user(db, "j3", 0)
    before, pot = _total(db), 20
    fee = pot * bs.COURT_FEE_PCT // 100
    bs.resolve_dispute(db, bet, creator_wins=False, majority_juror_ids=[j1.id, j2.id, j3.id])
    assert _total(db) == before + pot
    assert db.get(models.User, chs[0].id).points == pot - fee
