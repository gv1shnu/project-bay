"""Bets router with CRUD operations and challenge system."""
import math
from fastapi import APIRouter, Depends, Request, Query, status, HTTPException
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.models import BetStatus, ChallengeStatus
from app.config import settings
from app.logging_config import get_logger
from app.exceptions import InsufficientFundsError, BetNotFoundError, InvalidBetAmountError
from app.utils.validation import is_personal

logger = get_logger(__name__)
router = APIRouter(prefix="/bets", tags=["bets"])
limiter = Limiter(key_func=get_remote_address)


def validate_points(user: models.User, amount: int) -> bool:
    """Validate if user has sufficient points."""
    if amount <= 0:
        raise InvalidBetAmountError(amount)
    if int(user.points) < amount:
        raise InsufficientFundsError(int(user.points), amount)
    return True


@router.post("/", response_model=schemas.BetResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_bet(
    request: Request,
    bet: schemas.BetCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new bet with creator's initial stake."""
    # Validate creator has enough points
    validate_points(current_user, bet.amount)
    
    # validate first person perspective
    if not await is_personal(bet.title):
        raise HTTPException(
            status_code=400,
            detail=(
                "Bets must be written as a personal commitment "
                "(e.g. 'I will win every Valorant match today')."
            )
        )

    # Deduct creator's stake
    current_user.points = int(current_user.points) - bet.amount
    
    db_bet = models.Bet(
        user_id=current_user.id,
        title=bet.title,
        amount=bet.amount, 
        criteria=bet.criteria,
        status=BetStatus.ACTIVE
    )
    db.add(db_bet)
    db.commit()
    db.refresh(db_bet)
    db.refresh(current_user)
    
    logger.info(f"User {current_user.username} created bet {db_bet.id} with {bet.amount} points stake")
    return db_bet


@router.get("/public", response_model=schemas.PaginatedResponse[schemas.BetWithUsername])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_public_bets(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Get all bets with pagination and challenges (public endpoint)."""
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
            updated_at=bet.updated_at, username=bet.user.username, challenges=challenges
        ))
    
    return schemas.PaginatedResponse(
        items=bets_with_data, total=total, page=page, limit=limit,
        pages=math.ceil(total / limit) if total > 0 else 1
    )


@router.get("/", response_model=schemas.PaginatedResponse[schemas.BetResponse])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_bets(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bets for the current user with pagination."""
    offset = (page - 1) * limit
    total = db.query(models.Bet).filter(models.Bet.user_id == current_user.id).count()
    
    bets = db.query(models.Bet).filter(
        models.Bet.user_id == current_user.id
    ).order_by(models.Bet.created_at.desc()).offset(offset).limit(limit).all()
    
    return schemas.PaginatedResponse(
        items=bets, total=total, page=page, limit=limit,
        pages=math.ceil(total / limit) if total > 0 else 1
    )


@router.get("/{bet_id}", response_model=schemas.BetResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_bet(
    request: Request,
    bet_id: int,
    db: Session = Depends(get_db)
):
    """Get a specific bet by ID."""
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    return bet


# ============ CHALLENGE ENDPOINTS ============

@router.post("/{bet_id}/challenge", response_model=schemas.ChallengeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def create_challenge(
    request: Request,
    bet_id: int,
    challenge: schemas.ChallengeCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Challenge a bet (stakes points betting against the creator)."""
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    
    if bet.status != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Cannot challenge a resolved bet")
    
    if bet.user_id == current_user.id:
        raise HTTPException(status_code=400, detail="Cannot challenge your own bet")
    
    validate_points(current_user, challenge.amount)
    
    # Deduct points from challenger
    current_user.points = int(current_user.points) - challenge.amount
    
    db_challenge = models.Challenge(
        bet_id=bet_id,
        challenger_id=current_user.id,
        amount=challenge.amount,
        status=ChallengeStatus.PENDING
    )
    db.add(db_challenge)
    db.commit()
    db.refresh(db_challenge)
    
    logger.info(f"User {current_user.username} challenged bet {bet_id} with {challenge.amount} points")
    
    return schemas.ChallengeResponse(
        id=db_challenge.id, bet_id=db_challenge.bet_id,
        challenger_id=db_challenge.challenger_id,
        challenger_username=current_user.username,
        amount=db_challenge.amount, status=db_challenge.status,
        created_at=db_challenge.created_at
    )


@router.get("/{bet_id}/challenges", response_model=list[schemas.ChallengeResponse])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_challenges(
    request: Request,
    bet_id: int,
    db: Session = Depends(get_db)
):
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


@router.post("/{bet_id}/challenges/{challenge_id}/accept", response_model=schemas.ChallengeResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def accept_challenge(
    request: Request,
    bet_id: int,
    challenge_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept a challenge (bet creator matches the stake)."""
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    
    if bet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only bet creator can accept challenges")
    
    challenge = db.query(models.Challenge).filter(
        models.Challenge.id == challenge_id,
        models.Challenge.bet_id == bet_id
    ).first()
    
    if not challenge:
        raise HTTPException(status_code=404, detail="Challenge not found")
    
    if challenge.status != ChallengeStatus.PENDING:
        raise HTTPException(status_code=400, detail="Challenge already processed")
    
    validate_points(current_user, challenge.amount)
    
    # Deduct matching stake from bet creator
    current_user.points = int(current_user.points) - challenge.amount
    
    # Update bet's total matched amount
    bet.amount = int(bet.amount) + challenge.amount
    
    # Accept the challenge
    challenge.status = ChallengeStatus.ACCEPTED
    
    db.commit()
    db.refresh(challenge)
    
    logger.info(f"User {current_user.username} accepted challenge {challenge_id} for bet {bet_id}")
    
    return schemas.ChallengeResponse(
        id=challenge.id, bet_id=challenge.bet_id,
        challenger_id=challenge.challenger_id,
        challenger_username=challenge.challenger.username,
        amount=challenge.amount, status=challenge.status,
        created_at=challenge.created_at
    )


@router.post("/{bet_id}/challenges/{challenge_id}/reject", response_model=schemas.ChallengeResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def reject_challenge(
    request: Request,
    bet_id: int,
    challenge_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject a challenge (refunds challenger's stake)."""
    bet = db.query(models.Bet).filter(models.Bet.id == bet_id).first()
    if not bet:
        raise BetNotFoundError(bet_id)
    
    if bet.user_id != current_user.id:
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
    
    logger.info(f"User {current_user.username} rejected challenge {challenge_id} for bet {bet_id}")
    
    return schemas.ChallengeResponse(
        id=challenge.id, bet_id=challenge.bet_id,
        challenger_id=challenge.challenger_id,
        challenger_username=challenge.challenger.username,
        amount=challenge.amount, status=challenge.status,
        created_at=challenge.created_at
    )


# ============ BET RESOLUTION ============

@router.patch("/{bet_id}", response_model=schemas.BetResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def update_bet_status(
    request: Request,
    bet_id: int,
    bet_update: schemas.BetUpdate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Resolve bet (won/lost/cancelled) and distribute winnings."""
    bet = db.query(models.Bet).filter(
        models.Bet.id == bet_id,
        models.Bet.user_id == current_user.id
    ).first()
    
    if not bet:
        raise BetNotFoundError(bet_id)
    
    if bet.status != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Bet already resolved")
    
    old_status = bet.status
    bet.status = bet_update.status
    
    # Get accepted challenges
    accepted_challenges = [c for c in bet.challenges if c.status == ChallengeStatus.ACCEPTED]
    total_challenger_stake = sum(c.amount for c in accepted_challenges)
    
    if bet_update.status == BetStatus.WON:
        # Creator wins: gets their stake back + all challenger stakes
        current_user.points = int(current_user.points) + bet.amount + total_challenger_stake
        logger.info(f"User {current_user.username} won bet {bet_id}, won {total_challenger_stake} points")
        
    elif bet_update.status == BetStatus.LOST:
        # Challengers win: each gets 2x their stake
        for challenge in accepted_challenges:
            challenger = db.query(models.User).filter(models.User.id == challenge.challenger_id).first()
            challenger.points = int(challenger.points) + (challenge.amount * 2)
            logger.info(f"Challenger {challenger.username} won {challenge.amount * 2} points from bet {bet_id}")
            
    elif bet_update.status == BetStatus.CANCELLED:
        # Refund everyone
        current_user.points = int(current_user.points) + bet.amount
        for challenge in accepted_challenges:
            challenger = db.query(models.User).filter(models.User.id == challenge.challenger_id).first()
            challenger.points = int(challenger.points) + challenge.amount
        logger.info(f"Bet {bet_id} cancelled, all stakes refunded")
    
    db.commit()
    db.refresh(bet)
    db.refresh(current_user)
    
    return bet
