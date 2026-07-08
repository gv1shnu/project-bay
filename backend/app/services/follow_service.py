"""
services/follow_service.py — Business logic for the follow graph.

Follows are one-way: A follows B. Following B means you see B's activity in your
notifications and you're allowed to challenge B's bets. Nothing here commits —
callers own the transaction — except follow/unfollow which are self-contained.
"""
from sqlalchemy.orm import Session
from fastapi import HTTPException
from app import models
from app.logging_config import get_logger

logger = get_logger(__name__)


def is_following(db: Session, follower_id: int, followed_id: int) -> bool:
    """True if `follower_id` currently follows `followed_id`."""
    return db.query(models.Follow).filter(
        models.Follow.follower_id == follower_id,
        models.Follow.followed_id == followed_id,
    ).first() is not None


def follow_user(db: Session, follower: models.User, target: models.User) -> models.Follow:
    """Create a follow edge follower -> target. Idempotent per (follower, target)."""
    if follower.id == target.id:
        raise HTTPException(status_code=400, detail="You cannot follow yourself")

    existing = db.query(models.Follow).filter(
        models.Follow.follower_id == follower.id,
        models.Follow.followed_id == target.id,
    ).first()
    if existing:
        return existing  # Already following — no-op

    edge = models.Follow(follower_id=follower.id, followed_id=target.id)
    db.add(edge)
    # Let the target know they have a new follower
    db.add(models.Notification(
        user_id=target.id,
        message=f"@{follower.username} started following you",
    ))
    db.commit()
    db.refresh(edge)
    logger.info("%s now follows %s", follower.username, target.username)
    return edge


def unfollow_user(db: Session, follower: models.User, target: models.User) -> None:
    """Remove the follow edge follower -> target, if it exists."""
    edge = db.query(models.Follow).filter(
        models.Follow.follower_id == follower.id,
        models.Follow.followed_id == target.id,
    ).first()
    if edge:
        db.delete(edge)
        db.commit()
        logger.info("%s unfollowed %s", follower.username, target.username)


def get_following(db: Session, user_id: int) -> list[models.User]:
    """Users that `user_id` follows."""
    edges = db.query(models.Follow).filter(models.Follow.follower_id == user_id).all()
    return [e.followed for e in edges]


def get_followers(db: Session, user_id: int) -> list[models.User]:
    """Users that follow `user_id`."""
    edges = db.query(models.Follow).filter(models.Follow.followed_id == user_id).all()
    return [e.follower for e in edges]


def follow_counts(db: Session, user_id: int) -> dict:
    """{'followers': N, 'following': M} for a user."""
    followers = db.query(models.Follow).filter(models.Follow.followed_id == user_id).count()
    following = db.query(models.Follow).filter(models.Follow.follower_id == user_id).count()
    return {"followers": followers, "following": following}


def notify_followers(db: Session, creator_id: int, message: str, bet_id: int | None = None) -> None:
    """Queue a notification for every follower of `creator_id` (caller commits)."""
    follower_ids = [
        f.follower_id
        for f in db.query(models.Follow).filter(models.Follow.followed_id == creator_id).all()
    ]
    for fid in follower_ids:
        db.add(models.Notification(user_id=fid, message=message, bet_id=bet_id))
