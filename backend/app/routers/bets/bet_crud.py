"""Bet CRUD endpoints: create, list, and get bets."""
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
    # Validate creator has enough points
    validate_points(current_user, bet.amount)
    
    # Validate first person perspective using LLM with regex fallback
    if not await is_personal(bet.title):
        raise HTTPException(
            status_code=400,
            detail=(
                "Bets must be written as a personal commitment "
                "(e.g. 'I will win every Valorant match today')."
            )
        )
    
    # Create bet
    db_bet = create_bet(db, current_user, bet)
    
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
    current_user: models.User = Depends(get_current_user),
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
    """Get a specific bet by ID."""
    return get_bet_by_id(db, bet_id)
