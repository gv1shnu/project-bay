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
    """
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
            updated_at=bet.updated_at, username=bet.user.username, challenges=challenges, deadline=bet.deadline
        ))
    
    return bets_with_data, total


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
        # ✅ Creator wins: gets back their own stake + takes all challenger stakes
        user.points = int(user.points) + bet.amount + total_challenger_stake
        logger.info(f"User {user.username} won bet {bet_id}, won {total_challenger_stake} points")
        
    elif new_status == BetStatus.LOST:
        # ❌ Creator loses: each accepted challenger gets their stake back + matches the winnings (2x)
        for challenge in accepted_challenges:
            challenger = db.query(models.User).filter(models.User.id == challenge.challenger_id).first()
            # Challenger gets 2x: their original stake (refund) + creator's matching amount (winnings)
            challenger.points = int(challenger.points) + (challenge.amount * 2)
            logger.info(f"Challenger {challenger.username} won {challenge.amount * 2} points from bet {bet_id}")
            
    elif new_status == BetStatus.CANCELLED:
        # 🔄 Cancelled: full refund to everyone
        
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
    
    return bet
