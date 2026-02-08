"""Bet service layer containing business logic for bet operations."""
import math
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app import models, schemas
from app.models import BetStatus, ChallengeStatus
from app.exceptions import InsufficientFundsError, BetNotFoundError, InvalidBetAmountError
from app.logging_config import get_logger

logger = get_logger(__name__)


def validate_points(user: models.User, amount: int) -> bool:
    """Validate if user has sufficient points."""
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
    """Create a new bet with creator's initial stake."""
    # Deduct creator's stake
    user.points = int(user.points) - bet_data.amount
    
    db_bet = models.Bet(
        user_id=user.id,
        title=bet_data.title,
        amount=bet_data.amount,
        criteria=bet_data.criteria,
        deadline=bet_data.deadline,
        status=BetStatus.ACTIVE
    )
    db.add(db_bet)
    db.commit()
    db.refresh(db_bet)
    db.refresh(user)
    
    logger.info(f"User {user.username} created bet {db_bet.id} with {bet_data.amount} points stake")
    return db_bet


def get_bet_by_id(db: Session, bet_id: int) -> models.Bet:
    """Get a specific bet by ID."""
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
    """Get user's bets with pagination. Returns (bets, total_count)."""
    offset = (page - 1) * limit
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
    """Get all public bets with pagination. Returns (bets_with_data, total_count)."""
    offset = (page - 1) * limit
    total = db.query(models.Bet).count()
    
    bets = db.query(models.Bet).order_by(
        models.Bet.created_at.desc()
    ).offset(offset).limit(limit).all()
    
    bets_with_data = []
    for bet in bets:
        # Get all challenges (pending and accepted)
        challenges = [
            schemas.ChallengeResponse(
                id=c.id, bet_id=c.bet_id, challenger_id=c.challenger_id,
                challenger_username=c.challenger.username, amount=c.amount,
                status=c.status, created_at=c.created_at
            ) for c in bet.challenges if c.status != ChallengeStatus.REJECTED
        ]
        bets_with_data.append(schemas.BetWithUsername(
            id=bet.id, user_id=bet.user_id, title=bet.title, amount=bet.amount,
            criteria=bet.criteria, status=bet.status, created_at=bet.created_at,
            updated_at=bet.updated_at, username=bet.user.username, challenges=challenges, deadline=bet.deadline
        ))
    
    return bets_with_data, total


def resolve_bet(
    db: Session,
    user: models.User,
    bet_id: int,
    new_status: BetStatus
) -> models.Bet:
    """Resolve bet (won/lost/cancelled) and distribute winnings."""
    bet = db.query(models.Bet).filter(
        models.Bet.id == bet_id,
        models.Bet.user_id == user.id
    ).first()
    
    if not bet:
        raise BetNotFoundError(bet_id)
    
    if bet.status != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Bet already resolved")
    
    bet.status = new_status
    
    # Get accepted challenges
    accepted_challenges = [c for c in bet.challenges if c.status == ChallengeStatus.ACCEPTED]
    total_challenger_stake = sum(c.amount for c in accepted_challenges)
    
    if new_status == BetStatus.WON:
        # Creator wins: gets their stake back + all challenger stakes
        user.points = int(user.points) + bet.amount + total_challenger_stake
        logger.info(f"User {user.username} won bet {bet_id}, won {total_challenger_stake} points")
        
    elif new_status == BetStatus.LOST:
        # Challengers win: each gets 2x their stake
        for challenge in accepted_challenges:
            challenger = db.query(models.User).filter(models.User.id == challenge.challenger_id).first()
            challenger.points = int(challenger.points) + (challenge.amount * 2)
            logger.info(f"Challenger {challenger.username} won {challenge.amount * 2} points from bet {bet_id}")
            
    elif new_status == BetStatus.CANCELLED:
        # Refund creator
        user.points = int(user.points) + bet.amount
        logger.info(f"Refunded {bet.amount} points to creator {user.id}")
        
        # Refund and cancel all non-rejected challenges
        for challenge in bet.challenges:
            if challenge.status != ChallengeStatus.REJECTED:
                challenger = db.query(models.User).filter(models.User.id == challenge.challenger_id).first()
                challenger.points = int(challenger.points) + challenge.amount
                challenge.status = ChallengeStatus.CANCELLED
                logger.info(f"Refunded {challenge.amount} points to challenger {challenge.challenger_id}, challenge marked cancelled")
        
        bet.status = BetStatus.CANCELLED
        logger.info(f"Bet {bet_id} cancelled, all stakes refunded")
    
    db.commit()
    db.refresh(bet)
    db.refresh(user)
    
    return bet
