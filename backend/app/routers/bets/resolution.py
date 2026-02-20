"""
routers/bets/resolution.py — Bet resolution endpoint.

Endpoint:
  PATCH /bets/{bet_id}  — Resolve a bet as won, lost, or cancelled

Only the bet creator can resolve their own bet.
Point distribution is handled by the service layer (bet_service.resolve_bet).
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
# from slowapi import Limiter
# from slowapi.util import get_remote_address
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.config import settings
from app.services.bet_service import resolve_bet

router = APIRouter()
# limiter = Limiter(key_func=get_remote_address)


@router.patch("/{bet_id}", response_model=schemas.BetResponse)
# @limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def update_bet_status(
    request: Request,
    bet_id: int,
    bet_update: schemas.BetUpdate,  # Contains the new status (won/lost/cancelled)
    current_user: models.User = Depends(get_current_user),  # Must be the bet creator
    db: Session = Depends(get_db)
):
    """
    Resolve a bet and distribute points:
      - WON: creator gets their stake + all accepted challenger stakes
      - LOST: each accepted challenger gets 2x their stake
      - CANCELLED: everyone gets their stakes refunded
    """
    return resolve_bet(db, current_user, bet_id, bet_update.status)
