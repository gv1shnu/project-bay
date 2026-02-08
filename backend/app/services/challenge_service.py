"""Challenge service layer containing business logic for challenge operations."""
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
    """Challenge a bet (stakes points betting against the creator)."""
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    
    if bet.status != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot challenge a resolved bet")
    
    if bet.user_id == user.id:
        raise HTTPException(status_code=400, detail="Cannot challenge your own bet")
    
    validate_points(user, challenge_data.amount)
    
    # Deduct points from challenger
    user.points = int(user.points) - challenge_data.amount
    
    db_challenge = models.Challenge(
        bet_id=bet_id,
        challenger_id=user.id,
        amount=challenge_data.amount,
        status=ChallengeStatus.PENDING
    )
    db.add(db_challenge)
    db.commit()
    db.refresh(db_challenge)
    
    logger.info(f"User {user.username} challenged bet {bet_id} with {challenge_data.amount} points")
    
    return schemas.ChallengeResponse(
        id=db_challenge.id, bet_id=db_challenge.bet_id,
        challenger_id=db_challenge.challenger_id,
        challenger_username=user.username,
        amount=db_challenge.amount, status=db_challenge.status,
        created_at=db_challenge.created_at
    )


def get_challenges_for_bet(db: Session, bet_id: int) -> list[schemas.ChallengeResponse]:
    """Get all challenges for a bet."""
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    
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
    """Accept a challenge (bet creator matches the stake)."""
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    
    if bet.user_id != user.id:
        raise HTTPException(status_code=403, detail="Only bet creator can accept challenges")
    
    challenge = db.query(models.Challenge).filter(
        models.Challenge.id == challenge_id,
        models.Challenge.bet_id == bet_id
    ).first()
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    if challenge.status != ChallengeStatus.PENDING:
        raise HTTPException(status_code=400, detail="Challenge already processed")
    
    validate_points(user, challenge.amount)
    
    # Deduct matching stake from bet creator
    user.points = int(user.points) - challenge.amount
    
    # Update bet's total matched amount
    bet.amount = int(bet.amount) + challenge.amount
    
    # Accept the challenge
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
    """Reject a challenge (refunds challenger's stake)."""
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    
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
    
    # Refund challenger
    challenger = db.query(models.User).filter(models.User.id == challenge.challenger_id).first()
    challenger.points = int(challenger.points) + challenge.amount
    
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
