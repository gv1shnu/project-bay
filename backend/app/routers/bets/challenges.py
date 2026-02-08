"""Challenge endpoints: create, list, accept, and reject challenges."""
from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.config import settings
from app.services.challenge_service import (
    create_challenge,
    get_challenges_for_bet,
    accept_challenge,
    reject_challenge,
)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/{bet_id}/challenge", response_model=schemas.ChallengeResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def create_challenge_endpoint(
    request: Request,
    bet_id: int,
    challenge: schemas.ChallengeCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Challenge a bet (stakes points betting against the creator)."""
    return create_challenge(db, current_user, bet_id, challenge)


@router.get("/{bet_id}/challenges", response_model=list[schemas.ChallengeResponse])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_challenges(
    request: Request,
    bet_id: int,
    db: Session = Depends(get_db)
):
    """Get all challenges for a bet."""
    return get_challenges_for_bet(db, bet_id)


@router.post("/{bet_id}/challenges/{challenge_id}/accept", response_model=schemas.ChallengeResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def accept_challenge_endpoint(
    request: Request,
    bet_id: int,
    challenge_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Accept a challenge (bet creator matches the stake)."""
    return accept_challenge(db, current_user, bet_id, challenge_id)


@router.post("/{bet_id}/challenges/{challenge_id}/reject", response_model=schemas.ChallengeResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def reject_challenge_endpoint(
    request: Request,
    bet_id: int,
    challenge_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Reject a challenge (refunds challenger's stake)."""
    return reject_challenge(db, current_user, bet_id, challenge_id)
