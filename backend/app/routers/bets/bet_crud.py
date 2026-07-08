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
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, Request, Query, status, HTTPException, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app import models, schemas
from app.models import BetStatus, ChallengeStatus
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
    apply_resolution,
    resolve_dispute,
    PROOF_REVIEW_HOURS,
    DISPUTE_JURY_HOURS,
    JURY_MAJORITY,
)
from app.utils.validation import is_personal
from app.utils.llm_validator import process_validation_queue
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
    background_tasks: BackgroundTasks,
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
    
    # Step 4: Schedule background LLM validation
    background_tasks.add_task(process_validation_queue)
    
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


@router.get("/disputes", response_model=schemas.PaginatedResponse[schemas.BetWithUsername])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_disputes(
    request: Request,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Public feed of bets currently under jury review (Level 2 — no auth needed).

    Registered before /{bet_id} so the literal path isn't captured by the int matcher.
    """
    from app.services.bet_service import get_disputed_bets_paginated
    items, total = get_disputed_bets_paginated(db, page, limit)
    return schemas.PaginatedResponse(
        items=items, total=total, page=page, limit=limit,
        pages=math.ceil(total / limit) if total > 0 else 1,
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
def toggle_star(
    request: Request,
    bet_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Toggle star on a bet. Star if not starred, unstar if already starred."""
    bet = get_bet_by_id(db, bet_id)

    # Check if user already starred this bet
    existing = db.query(models.BetStar).filter_by(bet_id=bet_id, user_id=current_user.id).first()

    if existing:
        # Unstar — remove tracking record and decrement count
        db.delete(existing)
        bet.stars = max((bet.stars or 0) - 1, 0)
        starred = False
    else:
        # Star — create tracking record and increment count
        db.add(models.BetStar(bet_id=bet_id, user_id=current_user.id))
        bet.stars = (bet.stars or 0) + 1
        starred = True

    db.commit()
    db.refresh(bet)
    feed_cache.invalidate()
    return {"id": bet.id, "stars": bet.stars, "starred": starred}


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
    """Upload proof of bet completion (comment + media file). Creator only, before deadline."""
    bet = get_bet_by_id(db, bet_id)

    # Only the bet creator can upload proof
    if bet.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Only the bet creator can upload proof")

    # Must have active challengers (pending or accepted) to upload proof
    has_active_challengers = any(
        c.status == models.ChallengeStatus.PENDING
        for c in bet.challenges
    )
    if not has_active_challengers:
        raise HTTPException(status_code=400, detail="Cannot upload proof without any challengers")

    # Bet must be ACTIVE (proof can be uploaded anytime before deadline)
    if bet.status != BetStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Proof can only be uploaded for active bets")

    # Check deadline hasn't passed. Normalize to aware-UTC so a tz-naive value
    # coming back from the DB never raises on comparison.
    now = datetime.now(timezone.utc)
    deadline = bet.deadline if bet.deadline.tzinfo else bet.deadline.replace(tzinfo=timezone.utc)
    if now > deadline:
        raise HTTPException(status_code=400, detail="Deadline has passed — proof can no longer be uploaded")

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
    # __file__ = backend/app/routers/bets/bet_crud.py → 4 dirname calls → backend/
    uploads_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads")
    os.makedirs(uploads_dir, exist_ok=True)
    file_path = os.path.join(uploads_dir, unique_name)

    with open(file_path, "wb") as f:
        f.write(contents)

    # Update bet with proof data. Challengers now have a fixed review window (Level 1).
    bet.proof_comment = comment
    bet.proof_media_url = f"/uploads/{unique_name}"
    bet.proof_submitted_at = now
    bet.proof_deadline = now + timedelta(hours=PROOF_REVIEW_HOURS)
    bet.status = BetStatus.PENDING

    # Notify all active challengers (accepted + pending) that proof has been submitted
    active_challengers_to_notify = [
        c for c in bet.challenges
        if c.status == models.ChallengeStatus.PENDING
    ]
    for challenge in active_challengers_to_notify:
        notif = models.Notification(
            user_id=challenge.challenger_id,
            message=f'@{current_user.username} uploaded proof for "{bet.title}"',
            bet_id=bet.id,
        )
        db.add(notif)

    db.commit()
    db.refresh(bet)

    feed_cache.invalidate()  # Status change affects feed
    logger.info("Bet %d: proof uploaded by %s, status -> PENDING", bet_id, current_user.username)

    return {
        "id": bet.id,
        "status": bet.status.value,
        "proof_comment": bet.proof_comment,
        "proof_media_url": bet.proof_media_url,
    }


@router.post("/{bet_id}/vote")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def vote_on_proof(
    request: Request,
    bet_id: int,
    vote: str = Query(..., pattern="^(cool|not_cool)$"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Level 1 (Trust Check) — challengers review the creator's proof.

      • Every eligible challenger votes COOL  -> creator WINS immediately.
      • Any challenger votes NOT COOL         -> dispute raised, escalates to the
                                                 public jury (status DISPUTED).

    (If challengers simply ignore the proof, the deadline checker awards the
    creator the win when the review window lapses — funds are never trapped.)
    """
    bet = get_bet_by_id(db, bet_id)

    if bet.status != BetStatus.PENDING:
        raise HTTPException(status_code=400, detail="Bet is not under proof review")

    active_challenges = [c for c in bet.challenges if c.status == ChallengeStatus.PENDING]
    eligible_voter_ids = {c.challenger_id for c in active_challenges}
    if current_user.id not in eligible_voter_ids:
        raise HTTPException(status_code=403, detail="Only active challengers can vote on proof")

    existing_vote = db.query(models.ProofVote).filter(
        models.ProofVote.bet_id == bet_id,
        models.ProofVote.user_id == current_user.id,
    ).first()
    if existing_vote:
        raise HTTPException(status_code=400, detail="You have already voted on this proof")

    proof_vote = models.ProofVote(bet_id=bet_id, user_id=current_user.id, vote=vote)
    db.add(proof_vote)
    db.flush()

    total_voters = len(eligible_voter_ids)

    # ── Any NOT COOL vote raises a dispute → Level 2 tribunal ──
    if vote == "not_cool":
        bet.status = BetStatus.DISPUTED
        bet.dispute_deadline = datetime.now(timezone.utc) + timedelta(hours=DISPUTE_JURY_HOURS)
        # Notify the creator that their proof is contested
        db.add(models.Notification(
            user_id=bet.user_id,
            message=f'@{current_user.username} disputed your proof for "{bet.title}" — sent to the jury',
            bet_id=bet.id,
        ))
        db.commit()
        feed_cache.invalidate()
        logger.info("Bet %d DISPUTED by challenger %s -> jury", bet_id, current_user.username)
        return {
            "id": proof_vote.id, "bet_id": bet_id, "vote": vote,
            "cool_count": 0, "total_voters": total_voters,
            "votes_cast": db.query(models.ProofVote).filter(models.ProofVote.bet_id == bet_id).count(),
            "bet_status": bet.status.value,
        }

    # ── COOL vote: creator wins only once every challenger has approved ──
    all_votes = db.query(models.ProofVote).filter(models.ProofVote.bet_id == bet_id).all()
    cool_count = sum(1 for v in all_votes if v.vote == "cool")
    votes_cast = len(all_votes)

    if cool_count >= total_voters:
        apply_resolution(db, bet, BetStatus.WON)
        logger.info("Bet %d -> WON (all %d challengers approved)", bet_id, total_voters)
    else:
        db.commit()

    return {
        "id": proof_vote.id, "bet_id": bet_id, "vote": vote,
        "cool_count": cool_count, "total_voters": total_voters,
        "votes_cast": votes_cast, "bet_status": bet.status.value,
    }


@router.post("/{bet_id}/jury-vote")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def vote_on_dispute(
    request: Request,
    bet_id: int,
    vote: str = Query(..., pattern="^(cool|not_cool)$"),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Level 2 (The Tribunal) — a neutral juror votes on disputed proof.

    Jurors must be neither the creator nor a challenger. The first side to reach
    a 3-vote majority wins. The winner pays a 5% court fee out of the pot, split
    among the jurors who voted with the majority.
    """
    bet = get_bet_by_id(db, bet_id)

    if bet.status != BetStatus.DISPUTED:
        raise HTTPException(status_code=400, detail="This bet is not under jury review")

    # Neutrality checks — can't judge your own bet or one you have a stake in
    if bet.user_id == current_user.id:
        raise HTTPException(status_code=403, detail="You cannot judge your own bet")
    challenger_ids = {c.challenger_id for c in bet.challenges if c.status == ChallengeStatus.PENDING}
    if current_user.id in challenger_ids:
        raise HTTPException(status_code=403, detail="Challengers cannot serve on the jury for their own bet")

    existing = db.query(models.JuryVote).filter(
        models.JuryVote.bet_id == bet_id,
        models.JuryVote.user_id == current_user.id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already voted as a juror on this bet")

    db.add(models.JuryVote(bet_id=bet_id, user_id=current_user.id, vote=vote))
    db.flush()

    jury_votes = db.query(models.JuryVote).filter(models.JuryVote.bet_id == bet_id).all()
    cool = [v for v in jury_votes if v.vote == "cool"]
    not_cool = [v for v in jury_votes if v.vote == "not_cool"]

    if len(cool) >= JURY_MAJORITY:
        resolve_dispute(db, bet, creator_wins=True, majority_juror_ids=[v.user_id for v in cool])
        logger.info("Bet %d jury verdict -> WON (creator)", bet_id)
    elif len(not_cool) >= JURY_MAJORITY:
        resolve_dispute(db, bet, creator_wins=False, majority_juror_ids=[v.user_id for v in not_cool])
        logger.info("Bet %d jury verdict -> LOST (challengers)", bet_id)
    else:
        db.commit()

    return {
        "id": bet_id, "vote": vote,
        "cool_count": len(cool), "not_cool_count": len(not_cool),
        "majority_needed": JURY_MAJORITY, "bet_status": bet.status.value,
    }
