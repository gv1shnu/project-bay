"""
services/bet_service.py — Business logic for bet operations.

This is where the core bet logic lives (separated from HTTP concerns in routers).
Handles: point validation, bet creation, pagination, and bet resolution (point distribution).
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app import models, schemas
from app.models import BetStatus, ChallengeStatus
from app.exceptions import InsufficientFundsError, BetNotFoundError, InvalidBetAmountError
from app.logging_config import get_logger
from app.cache import feed_cache
from app.services.follow_service import notify_followers

logger = get_logger(__name__)

# Court fee taken from the pot when a dispute is settled by the public jury (Level 2).
COURT_FEE_PCT = 5  # percent

# Verification windows and thresholds (hours / vote counts).
PROOF_REVIEW_HOURS = 24   # Level 1: challengers have this long to review proof
DISPUTE_JURY_HOURS = 24   # Level 2: the public jury has this long to reach a verdict
JURY_MAJORITY = 3         # First side to reach this many jury votes wins the dispute


def apportion(total: int, weights: list[int]) -> list[int]:
    """
    Split an integer `total` across buckets in proportion to `weights`,
    guaranteeing the parts sum back to exactly `total` (no points burned).

    Uses the largest-remainder method: hand out the floor of each share,
    then give the leftover units to whoever was rounded down the most.
    """
    if total <= 0 or not weights:
        return [0 for _ in weights]

    weight_sum = sum(weights)
    if weight_sum <= 0:
        return [0 for _ in weights]

    # Exact (fractional) share for each bucket
    exact = [total * w / weight_sum for w in weights]
    floors = [int(x) for x in exact]
    remainder = total - sum(floors)  # leftover units to distribute

    # Rank buckets by the size of the fractional part they lost
    order = sorted(range(len(weights)), key=lambda i: exact[i] - floors[i], reverse=True)
    for i in range(remainder):
        floors[order[i % len(order)]] += 1
    return floors


def _active_challenges(bet: models.Bet) -> list[models.Challenge]:
    """Challenges still live on a bet (PENDING = accepted and in play)."""
    return [c for c in bet.challenges if c.status == ChallengeStatus.PENDING]


def validate_points(user: models.User, amount: int) -> bool:
    """
    Check that a user has enough points for a transaction.
    Raises specific exceptions if validation fails.
    """
    if amount <= 0:
        raise InvalidBetAmountError(amount)
    if int(user.points) < amount:
        raise InsufficientFundsError(int(user.points), amount)
    return True


def create_bet(
    db: Session,
    user: models.User,
    bet_data: schemas.BetCreate
) -> models.Bet:
    """
    Create a new bet and deduct the creator's stake.
    
    Flow:
      1. Deduct points from creator immediately
      2. Create the bet row with ACTIVE status
      3. Commit both changes in one transaction
    """
    # Deduct creator's stake from their point balance
    user.points = int(user.points) - bet_data.amount
    
    db_bet = models.Bet(
        user_id=user.id,
        title=bet_data.title,
        amount=bet_data.amount,     # Initial stake amount
        criteria=bet_data.criteria,
        deadline=bet_data.deadline,
        status=BetStatus.ACTIVE
    )
    db.add(db_bet)
    db.commit()
    db.refresh(db_bet)   # Get auto-generated id and timestamps
    
    # Enqueue LLM validation
    queue_item = models.BetValidationQueue(
        bet_id=db_bet.id,
        status=models.QueueStatus.PENDING
    )
    db.add(queue_item)

    # Nudge everyone who follows this creator that a new goal is up for grabs
    notify_followers(db, user.id, f'@{user.username} set a new goal: "{db_bet.title}"', db_bet.id)

    db.commit()
    
    db.refresh(user)     # Get updated points balance
    
    logger.info(f"User {user.username} created bet {db_bet.id} with {bet_data.amount} points stake")
    feed_cache.invalidate()  # New bet — clear feed cache
    return db_bet


def get_bet_by_id(db: Session, bet_id: int) -> models.Bet:
    """Fetch a bet by ID or raise 404 if not found."""
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    return bet


def get_bets_paginated(
    db: Session,
    user_id: int,
    page: int,
    limit: int
) -> tuple[list[models.Bet], int]:
    """
    Get a user's bets with pagination, newest first.
    Returns: (list_of_bets, total_count)
    """
    offset = (page - 1) * limit  # Convert page number to SQL offset
    total = db.query(models.Bet).filter(models.Bet.user_id == user_id).count()
    
    bets = db.query(models.Bet).filter(
        models.Bet.user_id == user_id
    ).order_by(models.Bet.created_at.desc()).offset(offset).limit(limit).all()
    
    return bets, total


def _serialize_bet_with_username(bet: models.Bet) -> schemas.BetWithUsername:
    """Build a public-feed BetWithUsername (challenges, proof votes, jury votes, stars)."""
    return schemas.BetWithUsername(
        id=bet.id, user_id=bet.user_id, title=bet.title, amount=bet.amount,
        criteria=bet.criteria, status=bet.status, stars=bet.stars, created_at=bet.created_at,
        updated_at=bet.updated_at, username=bet.user.username,
        challenges=[
            schemas.ChallengeResponse(
                id=c.id, bet_id=c.bet_id, challenger_id=c.challenger_id,
                challenger_username=c.challenger.username, amount=c.amount,
                status=c.status, created_at=c.created_at
            ) for c in bet.challenges
        ],
        deadline=bet.deadline, proof_comment=bet.proof_comment,
        proof_media_url=bet.proof_media_url, proof_submitted_at=bet.proof_submitted_at,
        proof_deadline=bet.proof_deadline, dispute_deadline=bet.dispute_deadline,
        proof_votes=[
            schemas.ProofVoteResponse(
                id=v.id, bet_id=v.bet_id, user_id=v.user_id,
                username=v.voter.username, vote=v.vote, created_at=v.created_at,
            ) for v in bet.proof_votes
        ],
        jury_votes=[
            schemas.JuryVoteResponse(
                id=v.id, bet_id=v.bet_id, user_id=v.user_id,
                username=v.voter.username, vote=v.vote, created_at=v.created_at,
            ) for v in bet.jury_votes
        ],
        starred_by_user_ids=[s.user_id for s in bet.starred_by],
    )


def get_public_bets_paginated(
    db: Session,
    page: int,
    limit: int
) -> tuple[list[schemas.BetWithUsername], int]:
    """
    Get all bets for the public feed, with usernames and non-rejected challenges.
    This is the main data source for the homepage feed.
    Returns: (list_of_bets_with_extra_data, total_count)

    Results are cached for 15 seconds to reduce DB load under high traffic.
    """
    cache_key = f"feed_p{page}_l{limit}"
    cached = feed_cache.get(cache_key)
    if cached:
        return cached

    offset = (page - 1) * limit
    total = db.query(models.Bet).count()

    # Fetch bets ordered by most stars first, then newest
    bets = db.query(models.Bet).order_by(
        models.Bet.stars.desc(),
        models.Bet.created_at.desc()
    ).offset(offset).limit(limit).all()

    bets_with_data = [_serialize_bet_with_username(bet) for bet in bets]

    result = (bets_with_data, total)
    feed_cache.set(cache_key, result)
    return result


def get_disputed_bets_paginated(
    db: Session,
    page: int,
    limit: int
) -> tuple[list[schemas.BetWithUsername], int]:
    """Get bets currently under jury review (status DISPUTED), newest dispute first."""
    offset = (page - 1) * limit
    query = db.query(models.Bet).filter(models.Bet.status == BetStatus.DISPUTED)
    total = query.count()
    bets = query.order_by(models.Bet.proof_submitted_at.desc()).offset(offset).limit(limit).all()
    return [_serialize_bet_with_username(bet) for bet in bets], total


# ──────────────────────────────────────────────────────────
# Payout helpers — pure point distribution, no auth/status checks.
# Each mutates points + challenge statuses but does NOT commit.
# The pot is always fully conserved (nothing is burned).
# ──────────────────────────────────────────────────────────

def _payout_won(db: Session, bet: models.Bet) -> None:
    """Creator wins: gets their own stake back plus the whole challenger pool."""
    challenges = _active_challenges(bet)
    pool = sum(c.amount for c in challenges)
    creator = db.query(models.User).filter(models.User.id == bet.user_id).first()
    creator.points = int(creator.points) + bet.amount + pool
    for c in challenges:
        c.status = ChallengeStatus.LOST
    logger.info("Bet %d WON by creator %s (+%d from pool)", bet.id, creator.username, pool)


def _payout_lost(db: Session, bet: models.Bet) -> None:
    """
    Creator loses: challengers split the creator's stake in proportion to their
    own stake (Proportional Risk Model). Largest-remainder split conserves points.
    """
    challenges = _active_challenges(bet)
    total_stake = sum(c.amount for c in challenges)
    if total_stake <= 0:
        # No challengers — creator's stake has nowhere to go; it is burned.
        logger.info("Bet %d LOST but no challengers. %d points burned.", bet.id, bet.amount)
        return

    shares = apportion(bet.amount, [c.amount for c in challenges])
    for c, share in zip(challenges, shares):
        challenger = db.query(models.User).filter(models.User.id == c.challenger_id).first()
        challenger.points = int(challenger.points) + c.amount + share
        c.status = ChallengeStatus.WON
        logger.info("Bet %d: challenger %s won %d (stake %d)", bet.id, challenger.username, share, c.amount)


def _payout_cancelled(db: Session, bet: models.Bet) -> None:
    """Cancelled: everyone gets a full refund."""
    challenges = _active_challenges(bet)
    creator = db.query(models.User).filter(models.User.id == bet.user_id).first()
    creator.points = int(creator.points) + bet.amount
    for c in challenges:
        challenger = db.query(models.User).filter(models.User.id == c.challenger_id).first()
        challenger.points = int(challenger.points) + c.amount
        c.status = ChallengeStatus.WITHDREW
    logger.info("Bet %d cancelled, all stakes refunded", bet.id)


def _payout_dispute(db: Session, bet: models.Bet, creator_wins: bool, majority_juror_ids: list[int]) -> None:
    """
    Settle a disputed bet by the public jury (Level 2).

    The winner pays a 5% court fee out of the pot, split among the jurors who
    voted with the majority. The remaining pot is distributed as a normal
    win/loss. Points are fully conserved.

    The fee is floored at 1 point whenever there are jurors to pay: 5% of a
    small integer pot (e.g. 5% of 8 = 0.4) would otherwise truncate to 0 and
    leave jurors unpaid, silently breaking the reward the UI promises. It is
    also capped at the pot so the winner's pool can never go negative.
    """
    challenges = _active_challenges(bet)
    pot = bet.amount + sum(c.amount for c in challenges)
    if majority_juror_ids and pot > 0:
        fee = min(pot, max(1, (pot * COURT_FEE_PCT) // 100))
    else:
        fee = 0  # no jurors to pay (or empty pot) — skip the fee entirely

    # Pay the court fee to the majority jurors (even split, remainder conserved)
    if fee > 0:
        juror_shares = apportion(fee, [1] * len(majority_juror_ids))
        for juror_id, share in zip(majority_juror_ids, juror_shares):
            juror = db.query(models.User).filter(models.User.id == juror_id).first()
            if juror:
                juror.points = int(juror.points) + share
        logger.info("Bet %d: %d court fee split among %d jurors", bet.id, fee, len(majority_juror_ids))

    winner_pool = pot - fee

    if creator_wins:
        creator = db.query(models.User).filter(models.User.id == bet.user_id).first()
        creator.points = int(creator.points) + winner_pool
        for c in challenges:
            c.status = ChallengeStatus.LOST
        logger.info("Bet %d dispute WON by creator (pool %d after fee)", bet.id, winner_pool)
    else:
        # Challengers collectively take the pot minus fee, split by their stake.
        total_stake = sum(c.amount for c in challenges)
        shares = apportion(winner_pool, [c.amount for c in challenges]) if total_stake > 0 else []
        for c, share in zip(challenges, shares):
            challenger = db.query(models.User).filter(models.User.id == c.challenger_id).first()
            challenger.points = int(challenger.points) + share
            c.status = ChallengeStatus.WON
        logger.info("Bet %d dispute LOST by creator (pool %d after fee)", bet.id, winner_pool)


def _notify_outcome(db: Session, bet: models.Bet) -> None:
    """Tell the creator's followers how a resolved bet turned out (WON/LOST only)."""
    if bet.status not in (BetStatus.WON, BetStatus.LOST):
        return
    creator = db.query(models.User).filter(models.User.id == bet.user_id).first()
    if not creator:
        return
    verb = "completed" if bet.status == BetStatus.WON else "failed"
    notify_followers(db, bet.user_id, f'@{creator.username} {verb} "{bet.title}"', bet.id)


def apply_resolution(db: Session, bet: models.Bet, new_status: BetStatus, commit: bool = True) -> models.Bet:
    """
    Internal resolver: set the bet's status and run the matching payout.

    Used by automated flows (proof voting, jury voting, deadline fail-safes).
    Does not enforce ownership — callers are trusted system paths.
    """
    bet.status = new_status
    if new_status == BetStatus.WON:
        _payout_won(db, bet)
    elif new_status == BetStatus.LOST:
        _payout_lost(db, bet)
    elif new_status == BetStatus.CANCELLED:
        _payout_cancelled(db, bet)

    _notify_outcome(db, bet)

    if commit:
        db.commit()
        db.refresh(bet)
        feed_cache.invalidate()
    return bet


def resolve_dispute(db: Session, bet: models.Bet, creator_wins: bool, majority_juror_ids: list[int]) -> models.Bet:
    """Settle a DISPUTED bet via the tribunal and mark it WON/LOST."""
    bet.status = BetStatus.WON if creator_wins else BetStatus.LOST
    _payout_dispute(db, bet, creator_wins, majority_juror_ids)
    _notify_outcome(db, bet)
    db.commit()
    db.refresh(bet)
    feed_cache.invalidate()
    return bet


def resolve_bet(
    db: Session,
    user: models.User,
    bet_id: int,
    new_status: BetStatus
) -> models.Bet:
    """
    Creator-initiated resolution (the PATCH /bets/{id} path and LLM auto-cancel).

    Only the bet CREATOR can resolve their own bet, and only while it is still
    ACTIVE — once proof is under review (PENDING) or DISPUTED, the outcome is
    decided by challengers / the jury, not the creator.

    Point distribution:
      WON:       Creator gets their stake + the whole challenger pool
      LOST:      Challengers split the creator's stake proportionally
      CANCELLED: Everyone gets refunded
    """
    bet = db.query(models.Bet).filter(
        models.Bet.id == bet_id,
        models.Bet.user_id == user.id  # Only creator can resolve
    ).first()

    if not bet:
        raise BetNotFoundError(bet_id)

    if bet.status != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Only active bets can be resolved by the creator")

    # A contested bet cannot be won/lost by creator fiat — that would let the
    # creator sweep the pot without the challengers ever reviewing proof. Once
    # anyone has staked against the bet, the outcome must go through the proof
    # review / jury flow. The creator may still CANCEL (which refunds everyone).
    has_active_challengers = any(
        c.status == ChallengeStatus.PENDING for c in bet.challenges
    )
    if new_status in (BetStatus.WON, BetStatus.LOST) and has_active_challengers:
        raise HTTPException(
            status_code=403,
            detail="A challenged bet can't be resolved by the creator — upload proof for the challengers to review.",
        )

    resolved = apply_resolution(db, bet, new_status)
    db.refresh(user)
    return resolved
