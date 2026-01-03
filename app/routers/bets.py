from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app import models, schemas, auth
from app.database import get_db
from app.models import BetStatus

router = APIRouter(prefix="/bets", tags=["bets"])


def validate_bet_transaction(db: Session, user: models.User, bet_amount: float) -> bool:
    """
    Validate if a bet transaction can be made.
    Returns True if valid, raises HTTPException if invalid.
    """
    # Check if user has sufficient points
    if user.points < bet_amount:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient points. You have {user.points} points, but need {bet_amount}"
        )
    
    # Check if bet amount is positive
    if bet_amount <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Bet amount must be greater than 0"
        )
    
    return True


@router.post("/", response_model=schemas.BetResponse, status_code=status.HTTP_201_CREATED)
def create_bet(
    bet: schemas.BetCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new bet (deducts points from user)"""
    # Validate the transaction
    validate_bet_transaction(db, current_user, bet.amount)
    
    # Deduct points from user
    current_user.points -= bet.amount
    db.commit()
    db.refresh(current_user)
    
    # Create the bet
    db_bet = models.Bet(
        user_id=current_user.id,
        amount=bet.amount,
        description=bet.description,
        status=BetStatus.PENDING
    )
    db.add(db_bet)
    db.commit()
    db.refresh(db_bet)
    
    return db_bet


@router.get("/public", response_model=list[schemas.BetResponse])
def get_public_bets(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all bets (public endpoint, no authentication required)"""
    bets = db.query(models.Bet).order_by(
        models.Bet.created_at.desc()
    ).offset(skip).limit(limit).all()
    return bets


@router.get("/", response_model=list[schemas.BetResponse])
def get_bets(
    skip: int = 0,
    limit: int = 100,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bets for the current user"""
    bets = db.query(models.Bet).filter(
        models.Bet.user_id == current_user.id
    ).offset(skip).limit(limit).all()
    return bets


@router.get("/{bet_id}", response_model=schemas.BetResponse)
def get_bet(
    bet_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific bet by ID"""
    bet = db.query(models.Bet).filter(
        models.Bet.id == bet_id,
        models.Bet.user_id == current_user.id
    ).first()
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found"
        )
    return bet


@router.patch("/{bet_id}", response_model=schemas.BetResponse)
def update_bet_status(
    bet_id: int,
    bet_update: schemas.BetUpdate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    """Update bet status (e.g., mark as won/lost)"""
    bet = db.query(models.Bet).filter(
        models.Bet.id == bet_id,
        models.Bet.user_id == current_user.id
    ).first()
    
    if not bet:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bet not found"
        )
    
    old_status = bet.status
    bet.status = bet_update.status
    
    # If bet is won, add points back plus winnings (assuming 1:1 payout for simplicity)
    # You can adjust this logic based on your betting rules
    if bet_update.status == BetStatus.WON and old_status == BetStatus.PENDING:
        current_user.points += bet.amount * 2  # Return bet amount + winnings
    elif bet_update.status == BetStatus.LOST and old_status == BetStatus.PENDING:
        # Points already deducted, no need to do anything
        pass
    elif bet_update.status == BetStatus.CANCELLED and old_status == BetStatus.PENDING:
        # Return the bet amount if cancelled
        current_user.points += bet.amount
    
    db.commit()
    db.refresh(bet)
    db.refresh(current_user)
    
    return bet

