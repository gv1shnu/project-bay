"""
routers/follows.py — Follow graph endpoints.

Endpoints:
  POST   /follows/{username}          — Follow a user (auth)
  DELETE /follows/{username}          — Unfollow a user (auth)
  GET    /follows/me/following        — Users I follow (auth)
  GET    /follows/me/followers        — Users who follow me (auth)
  GET    /follows/{username}/counts   — Follower / following counts (public)
  GET    /follows/{username}/status   — Whether I follow this user (auth)

The /me/* routes are declared before /{username}/* so the literal segment
isn't swallowed by the username matcher.
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app import models, schemas
from app.auth import get_current_user, get_user_by_username
from app.database import get_db
from app.config import settings
from app.services import follow_service

router = APIRouter(prefix="/follows", tags=["follows"])
limiter = Limiter(key_func=get_remote_address)


def _get_target(db: Session, username: str) -> models.User:
    user = get_user_by_username(db, username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/me/following", response_model=list[schemas.FollowUser])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def list_following(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the users the current user follows."""
    return follow_service.get_following(db, current_user.id)


@router.get("/me/followers", response_model=list[schemas.FollowUser])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def list_followers(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List the users who follow the current user."""
    return follow_service.get_followers(db, current_user.id)


@router.get("/{username}/counts", response_model=schemas.FollowCounts)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_counts(request: Request, username: str, db: Session = Depends(get_db)):
    """Public follower/following counts for a user."""
    target = _get_target(db, username)
    return follow_service.follow_counts(db, target.id)


@router.get("/{username}/status", response_model=schemas.FollowStatus)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_status(
    request: Request,
    username: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Whether the current user follows `username`."""
    target = _get_target(db, username)
    return {"following": follow_service.is_following(db, current_user.id, target.id)}


@router.post("/{username}", response_model=schemas.FollowStatus, status_code=201)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def follow(
    request: Request,
    username: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Follow a user — subscribes you to their activity and lets you challenge them."""
    target = _get_target(db, username)
    follow_service.follow_user(db, current_user, target)
    return {"following": True}


@router.delete("/{username}", response_model=schemas.FollowStatus)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def unfollow(
    request: Request,
    username: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Unfollow a user."""
    target = _get_target(db, username)
    follow_service.unfollow_user(db, current_user, target)
    return {"following": False}
