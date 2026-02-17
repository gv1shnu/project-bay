"""
routers/bets/bet_crud.py — Bet CRUD endpoints: create, list, get, star, and proof upload.

Endpoints:
  POST /bets/              — Create a new bet (requires auth + regex validation)
  GET  /bets/public        — List all bets with usernames and challenges (public feed)
  GET  /bets/              — List current user's bets (requires auth)
  GET  /bets/{bet_id}      — Get a single bet by ID
  POST /bets/{bet_id}/star — Increment star count
  POST /bets/{bet_id}/proof — Upload proof of completion (requires auth)
"""
import os
import math
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, Request, Query, status, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app import models, schemas
from app.models import BetStatus
from app.auth import get_current_user
from app.database import get_db
from app.config import settings
from app.cache import feed_cache
from app.services.bet_service import (
    validate_points,
    create_bet,
    get_bet_by_id,
    get_bets_paginated,
    get_public_bets_paginated,
)
from app.utils.validation import is_personal
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# Allowed file types for proof upload
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp4", ".mov", ".webm"}
# Max file size: 10 MB
MAX_FILE_SIZE = 10 * 1024 * 1024


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


@router.post("/{bet_id}/star")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def star_bet(
    request: Request,
    bet_id: int,
    db: Session = Depends(get_db)
):
    """Increment a bet's star count. No auth required."""
    bet = get_bet_by_id(db, bet_id)
    bet.stars = (bet.stars or 0) + 1
    db.commit()
    db.refresh(bet)
    feed_cache.invalidate()  # Star count affects feed sort order
    return {"id": bet.id, "stars": bet.stars}


@router.post("/{bet_id}/proof")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
async def upload_proof(
    request: Request,
    bet_id: int,
    comment: str = Form(..., min_length=1, max_length=1000),
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload proof of bet completion (comment + media file). Creator only, during proof window."""
    bet = get_bet_by_id(db, bet_id)

    # Only the bet creator can upload proof
    if bet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the bet creator can upload proof")

    # Bet must be in AWAITING_PROOF status
    if bet.status != BetStatus.AWAITING_PROOF:
        raise HTTPException(status_code=400, detail="Bet is not awaiting proof")

    # Check proof window hasn't expired
    now = datetime.now(timezone.utc)
    if bet.proof_deadline and now > bet.proof_deadline:
        raise HTTPException(status_code=400, detail="Proof upload window has expired")

    # Validate file extension
    _, ext = os.path.splitext(file.filename or "")
    ext = ext.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Accepted: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read and validate file size
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File too large (max 10 MB)")

    # Save file with unique name to prevent collisions
    unique_name = f"{bet_id}_{uuid.uuid4().hex[:8]}{ext}"
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(contents)

    # Update bet with proof data
    bet.proof_comment = comment
    bet.proof_media_url = f"/uploads/{unique_name}"
    bet.proof_submitted_at = now
    bet.status = BetStatus.PROOF_UNDER_REVIEW
    db.commit()
    db.refresh(bet)

    feed_cache.invalidate()  # Status change affects feed
    logger.info("Bet %d: proof uploaded by %s, status → PROOF_UNDER_REVIEW", bet_id, current_user.username)

    return {
        "id": bet.id,
        "status": bet.status.value,
        "proof_comment": bet.proof_comment,
        "proof_media_url": bet.proof_media_url,
    }
