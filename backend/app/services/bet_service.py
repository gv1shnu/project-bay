"""
services/bet_service.py — Business logic for bet operations.

This is where the core bet logic lives (separated from HTTP concerns in routers).
Handles: point validation, bet creation, pagination, and bet resolution (point distribution).
"""
import math
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app import models, schemas
from app.models import BetStatus, ChallengeStatus
from app.exceptions import InsufficientFundsError, BetNotFoundError, InvalidBetAmountError
from app.logging_config import get_logger
from app.cache import feed_cache

logger = get_logger(__name__)


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
    
    # Manually build response objects with username and filtered challenges
    bets_with_data = []
    for bet in bets:
        # Include all challenges except rejected ones (those are "hidden")
        challenges = [
            schemas.ChallengeResponse(
                id=c.id, bet_id=c.bet_id, challenger_id=c.challenger_id,
                challenger_username=c.challenger.username, amount=c.amount,
                status=c.status, created_at=c.created_at
            ) for c in bet.challenges if c.status != ChallengeStatus.REJECTED
        ]
        bets_with_data.append(schemas.BetWithUsername(
            id=bet.id, user_id=bet.user_id, title=bet.title, amount=bet.amount,
            criteria=bet.criteria, status=bet.status, stars=bet.stars, created_at=bet.created_at,
            updated_at=bet.updated_at, username=bet.user.username, challenges=challenges,
            deadline=bet.deadline, proof_comment=bet.proof_comment,
            proof_media_url=bet.proof_media_url, proof_submitted_at=bet.proof_submitted_at,
            proof_deadline=bet.proof_deadline,
            proof_votes=[
                schemas.ProofVoteResponse(
                    id=v.id, bet_id=v.bet_id, user_id=v.user_id,
                    username=v.voter.username, vote=v.vote, created_at=v.created_at,
                ) for v in bet.proof_votes
            ],
            starred_by_user_ids=[s.user_id for s in bet.starred_by],
        ))
    
    result = (bets_with_data, total)
    feed_cache.set(cache_key, result)
    return result


def resolve_bet(
    db: Session,
    user: models.User,
    bet_id: int,
    new_status: BetStatus
) -> models.Bet:
    """
    Resolve a bet and distribute points based on outcome.
    
    Only the bet CREATOR can resolve their own bet.
    Only ACTIVE bets can be resolved (prevents double-resolution).
    
    Point distribution:
      WON:       Creator gets their_stake + all_accepted_challenger_stakes
      LOST:      Each accepted challenger gets 2x their_stake (refund + winnings)
      CANCELLED: Everyone gets refunded — creator, all non-rejected challengers
    """
    # Find the bet — must belong to the current user
    bet = db.query(models.Bet).filter(
        models.Bet.id == bet_id,
        models.Bet.user_id == user.id  # Only creator can resolve
    ).first()
    
    if not bet:
        raise BetNotFoundError(bet_id)
    
    # Prevent resolving an already-resolved bet
    if bet.status != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Bet already resolved")
    
    bet.status = new_status
    
    # Get only ACCEPTED challenges — pending/rejected ones don't participate in resolution
    accepted_challenges = [c for c in bet.challenges if c.status == ChallengeStatus.ACCEPTED]
    total_challenger_stake = sum(c.amount for c in accepted_challenges)
    
    if new_status == BetStatus.WON:
        # Creator wins: gets back their own stake + takes all challenger stakes
        # [POOL UPDATE] Creator gets their stake (bet.amount) + all challenger stakes
        user.points = int(user.points) + bet.amount + total_challenger_stake
        logger.info(f"User {user.username} won bet {bet_id}, won {total_challenger_stake} points (Total: {bet.amount + total_challenger_stake})")
        
    elif new_status == BetStatus.LOST:
        # Creator loses: Challengers split the Creator's stake proportionally
        # [POOL UPDATE] Proportional Risk Model
        # Formula: Payout = ChallengerStake + (ChallengerStake / TotalChallengerStake) * CreatorStake
        
        if total_challenger_stake > 0:
            for challenge in accepted_challenges:
                challenger = db.query(models.User).filter(models.User.id == challenge.challenger_id).first()
                
                # Calculate share of the creator's stake
                share = (challenge.amount / total_challenger_stake) * bet.amount
                payout = challenge.amount + math.floor(share) # Floor to avoid fractional points
                
                challenger.points = int(challenger.points) + int(payout)
                logger.info(f"Challenger {challenger.username} won {payout - challenge.amount} points from bet {bet_id} (Stake: {challenge.amount}, Share: {share:.2f})")
        else:
            # Edge case: Creator lost but no challengers?
            # Creator loses stake. It disappears (burned).
            logger.info(f"Bet {bet_id} lost but no challengers. {bet.amount} points burned.")
            
    elif new_status == BetStatus.CANCELLED:
        # Cancelled: full refund to everyone
        
        # Refund the creator's stake
        user.points = int(user.points) + bet.amount
        logger.info(f"Refunded {bet.amount} points to creator {user.id}")
        
        # Refund all non-rejected challengers and mark their challenges as cancelled
        for challenge in bet.challenges:
            if challenge.status != ChallengeStatus.REJECTED:
                challenger = db.query(models.User).filter(models.User.id == challenge.challenger_id).first()
                challenger.points = int(challenger.points) + challenge.amount
                challenge.status = ChallengeStatus.CANCELLED
                logger.info(f"Refunded {challenge.amount} points to challenger {challenge.challenger_id}, challenge marked cancelled")
        
        bet.status = BetStatus.CANCELLED
        logger.info(f"Bet {bet_id} cancelled, all stakes refunded")
    
    # Commit all point changes and status updates in one transaction
    db.commit()
    db.refresh(bet)
    db.refresh(user)
    feed_cache.invalidate()  # Resolution changed bet status — clear feed cache
    
    return bet
