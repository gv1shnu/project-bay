"""
routers/bets/bet_crud.py — Bet CRUD endpoints: create, list, and get bets.

Endpoints:
  POST /bets/          — Create a new bet (requires auth + regex validation)
  GET  /bets/public    — List all bets with usernames and challenges (public feed)
  GET  /bets/          — List current user's bets (requires auth)
  GET  /bets/{bet_id}  — Get a single bet by ID
"""
import math
from fastapi import APIRouter, Depends, Request, Query, status, HTTPException
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.config import settings
from app.services.bet_service import (
    validate_points,
    create_bet,
    get_bet_by_id,
    get_bets_paginated,
    get_public_bets_paginated,
)
from app.utils.validation import is_personal

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.post("/", response_model=schemas.BetResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def create_bet_endpoint(
    request: Request,
    bet: schemas.BetCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new bet with creator's initial stake."""
    # Step 1: Check the creator has enough points to stake
    validate_points(current_user, bet.amount)
    
    # Step 2: Validate the title is a personal commitment using regex pattern matching
    # This prevents bets like "Team A will win" — only allows "I will..." style commitments
    if not is_personal(bet.title):
        raise HTTPException(
            status_code=400,
            detail=(
                "Bets must be written as a personal commitment "
                "(e.g. 'I will win every Valorant match today')."
            )
        )
    
    # Step 3: Create the bet and deduct creator's stake
    db_bet = create_bet(db, current_user, bet)
    
    return db_bet


@router.get("/public", response_model=schemas.PaginatedResponse[schemas.BetWithUsername])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_public_bets(
    request: Request,
    page: int = Query(1, ge=1),           # Page number, starts at 1
    limit: int = Query(20, ge=1, le=100), # Items per page, max 100
    db: Session = Depends(get_db)
):
    """Get all bets with pagination and challenges (public feed — no auth needed)."""
    bets_with_data, total = get_public_bets_paginated(db, page, limit)
    
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
    current_user: models.User = Depends(get_current_user),  # Auth required
    db: Session = Depends(get_db)
):
    """Get all bets for the current user with pagination."""
    bets, total = get_bets_paginated(db, current_user.id, page, limit)
    
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
    """Get a specific bet by ID. No auth required."""
    return get_bet_by_id(db, bet_id)
