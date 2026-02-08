"""Bet resolution endpoint: update bet status and distribute winnings."""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.config import settings
from app.services.bet_service import resolve_bet

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


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
    return resolve_bet(db, current_user, bet_id, bet_update.status)
