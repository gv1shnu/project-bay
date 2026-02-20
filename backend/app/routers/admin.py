"""
routers/admin.py — Admin-only endpoints for viewing all users and bets.

Protected by a passphrase sent via the X-Admin-Passphrase header.

Endpoints:
  POST /admin/verify  — Verify the admin passphrase
  GET  /admin/users   — List all registered users
  GET  /admin/bets    — List all bets with creator username and challenges
"""
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session, joinedload
# from slowapi import Limiter
# from slowapi.util import get_remote_address
from app import models, schemas
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/admin", tags=["admin"])
# limiter = Limiter(key_func=get_remote_address)


def verify_admin_passphrase(x_admin_passphrase: str = Header(...)):
    """Dependency that checks the admin passphrase header on every admin request."""
    if x_admin_passphrase != settings.ADMIN_PASSPHRASE:
        raise HTTPException(status_code=403, detail="Invalid admin passphrase")


@router.post("/verify")
# @limiter.limit("10/minute")
def verify_passphrase(request: Request, _: None = Depends(verify_admin_passphrase)):
    """Verify the admin passphrase without fetching data. Used by the frontend gate."""
    return {"status": "ok"}


@router.get("/users")
# @limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_all_users(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_passphrase),
):
    """List all registered users with their points."""
    users = db.query(models.User).order_by(models.User.id).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "points": u.points,
            "created_at": u.created_at.isoformat() if u.created_at else None,
        }
        for u in users
    ]


@router.get("/bets")
# @limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_all_bets(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin_passphrase),
):
    """List all bets with creator username and associated challenges."""
    bets = (
        db.query(models.Bet)
        .options(joinedload(models.Bet.user), joinedload(models.Bet.challenges).joinedload(models.Challenge.challenger))
        .order_by(models.Bet.id)
        .all()
    )
    return [
        {
            "id": b.id,
            "title": b.title,
            "username": b.user.username,
            "amount": b.amount,
            "criteria": b.criteria,
            "status": b.status.value,
            "deadline": b.deadline.isoformat() if b.deadline else None,
            "created_at": b.created_at.isoformat() if b.created_at else None,
            "challenges": [
                {
                    "id": c.id,
                    "challenger_username": c.challenger.username,
                    "amount": c.amount,
                    "status": c.status.value,
                }
                for c in b.challenges
            ],
        }
        for b in bets
    ]
