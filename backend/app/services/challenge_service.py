"""
services/challenge_service.py — Business logic for challenge operations.

Handles: creating challenges, listing them, and accepting/rejecting them.
Challenge lifecycle: PENDING → ACCEPTED or REJECTED (or CANCELLED if bet is cancelled)
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app import models, schemas
from app.models import BetStatus, ChallengeStatus
from app.exceptions import BetNotFoundError
from app.services.bet_service import validate_points
from app.logging_config import get_logger

logger = get_logger(__name__)


def create_challenge(
    db: Session,
    user: models.User,
    bet_id: int,
    challenge_data: schemas.ChallengeCreate
) -> schemas.ChallengeResponse:
    """
    Create a challenge against a bet (bet against the creator's success).
    
    Flow:
      1. Verify bet exists and is still active
      2. Prevent self-challenge (can't challenge your own bet)
      3. Validate challenger has enough points
      4. Deduct points immediately
      5. Create challenge with PENDING status
    
    Points are deducted NOW, not when the challenge is accepted.
    If rejected, points are refunded by reject_challenge().
    """
    # Verify the bet exists
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    
    # Can only challenge active bets
    if bet.status != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot challenge a resolved bet")
    
    # Can't challenge your own bet — that would be free money!
    if bet.user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot challenge your own bet")

    # Check if user already has an active challenge (pending or accepted)
    existing_challenge = db.query(models.Challenge).filter(
        models.Challenge.bet_id == bet_id,
        models.Challenge.challenger_id == user.id,
        models.Challenge.status.in_([ChallengeStatus.PENDING, ChallengeStatus.ACCEPTED])
    ).first()

    if existing_challenge:
        raise HTTPException(status_code=400, detail="You have already challenged this bet")
    
    # Check challenger has enough points
    validate_points(user, challenge_data.amount)
    
    # Deduct points from challenger immediately (refunded if rejected/cancelled)
    user.points = int(user.points) - challenge_data.amount
    
    # Create the challenge record
    db_challenge = models.Challenge(
        bet_id=bet_id,
        challenger_id=user.id,
        amount=challenge_data.amount,
        status=ChallengeStatus.PENDING  # Waiting for bet creator to accept/reject
    )
    db.add(db_challenge)
    db.commit()
    db.refresh(db_challenge)
    
    logger.info(f"User {user.username} challenged bet {bet_id} with {challenge_data.amount} points")
    
    # Build and return the response (includes username, not just ID)
    return schemas.ChallengeResponse(
        id=db_challenge.id, bet_id=db_challenge.bet_id,
        challenger_id=db_challenge.challenger_id,
        challenger_username=user.username,
        amount=db_challenge.amount, status=db_challenge.status,
        created_at=db_challenge.created_at
    )


def get_challenges_for_bet(db: Session, bet_id: int) -> list[schemas.ChallengeResponse]:
    """Get all challenges for a bet, including the challenger's username."""
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    
    # Convert ORM objects to response schemas (resolves challenger username via relationship)
    return [
        schemas.ChallengeResponse(
            id=c.id, bet_id=c.bet_id, challenger_id=c.challenger_id,
            challenger_username=c.challenger.username, amount=c.amount,
            status=c.status, created_at=c.created_at
        ) for c in bet.challenges
    ]


def accept_challenge(
    db: Session,
    user: models.User,
    bet_id: int,
    challenge_id: int
) -> schemas.ChallengeResponse:
    """
    Accept a challenge — only the bet creator can do this.
    
    Flow:
      1. Verify bet exists and user is the creator
      2. Find the challenge and verify it's still PENDING
      3. Deduct matching stake from creator (must have enough points)
      4. Increase bet.amount (tracks total matched amount)
      5. Mark challenge as ACCEPTED
    
    After accepting, the creator has matched the challenger's stake.
    Both sides now have "skin in the game".
    """
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    
    # Only the bet creator can accept challenges on their bet
    if bet.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only bet creator can accept challenges")
    
    # Find the specific challenge
    challenge = db.query(models.Challenge).filter(
        models.Challenge.id == challenge_id,
        models.Challenge.bet_id == bet_id
    ).first()
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    # Can only accept PENDING challenges
    if challenge.status != ChallengeStatus.PENDING:
        raise HTTPException(status_code=400, detail="Challenge already processed")
    
    # Creator must have enough points to match the challenger's stake
    validate_points(user, challenge.amount)
    
    # Deduct matching stake from the bet creator
    user.points = int(user.points) - challenge.amount
    
    # Increase the bet's total matched amount
    bet.amount = int(bet.amount) + challenge.amount
    
    # Mark the challenge as accepted — now both sides are committed
    challenge.status = ChallengeStatus.ACCEPTED
    
    db.commit()
    db.refresh(challenge)
    
    logger.info(f"User {user.username} accepted challenge {challenge_id} for bet {bet_id}")
    
    return schemas.ChallengeResponse(
        id=challenge.id, bet_id=challenge.bet_id,
        challenger_id=challenge.challenger_id,
        challenger_username=challenge.challenger.username,
        amount=challenge.amount, status=challenge.status,
        created_at=challenge.created_at
    )


def reject_challenge(
    db: Session,
    user: models.User,
    bet_id: int,
    challenge_id: int
) -> schemas.ChallengeResponse:
    """
    Reject a challenge — only the bet creator can do this.
    
    Flow:
      1. Verify bet exists and user is the creator
      2. Find the challenge and verify it's still PENDING
      3. Refund the challenger's staked points
      4. Mark challenge as REJECTED
    """
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    
    # Only the bet creator can reject challenges
    if bet.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only bet creator can reject challenges")
    
    challenge = db.query(models.Challenge).filter(
        models.Challenge.id == challenge_id,
        models.Challenge.bet_id == bet_id
    ).first()
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    if challenge.status != ChallengeStatus.PENDING:
        raise HTTPException(status_code=400, detail="Challenge already processed")
    
    # Refund the challenger — they get their staked points back
    challenger = db.query(models.User).filter(models.User.id == challenge.challenger_id).first()
    challenger.points = int(challenger.points) + challenge.amount
    
    # Mark as rejected
    challenge.status = ChallengeStatus.REJECTED
    
    db.commit()
    db.refresh(challenge)
    
    logger.info(f"User {user.username} rejected challenge {challenge_id} for bet {bet_id}")
    
    return schemas.ChallengeResponse(
        id=challenge.id, bet_id=challenge.bet_id,
        challenger_id=challenge.challenger_id,
        challenger_username=challenge.challenger.username,
        amount=challenge.amount, status=challenge.status,
        created_at=challenge.created_at
    )
