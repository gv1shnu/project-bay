"""
routers/notifications.py — Notification endpoints: list, unread count, mark as read.

Endpoints:
  GET  /notifications/         — Get all notifications for the current user
  GET  /notifications/unread   — Get unread notification count
  POST /notifications/{id}/read — Mark a notification as read
  POST /notifications/read-all  — Mark all notifications as read
"""
from fastapi import APIRouter, Depends, Request, HTTPException
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.config import settings

router = APIRouter(prefix="/notifications", tags=["notifications"])
limiter = Limiter(key_func=get_remote_address)


@router.get("/", response_model=list[schemas.NotificationResponse])
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_notifications(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get all notifications for the current user, newest first."""
    return (
        db.query(models.Notification)
        .filter(models.Notification.user_id == current_user.id)
        .order_by(models.Notification.created_at.desc())
        .limit(50)
        .all()
    )


@router.get("/unread", response_model=dict)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_unread_count(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Get the number of unread notifications (used for the badge dot)."""
    count = (
        db.query(models.Notification)
        .filter(
            models.Notification.user_id == current_user.id,
            models.Notification.is_read == 0,
        )
        .count()
    )
    return {"count": count}


@router.post("/{notification_id}/read")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def mark_as_read(
    request: Request,
    notification_id: int,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark a single notification as read."""
    notif = db.query(models.Notification).filter(
        models.Notification.id == notification_id,
        models.Notification.user_id == current_user.id,
    ).first()

    if not notif:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = 1
    db.commit()
    return {"id": notif.id, "is_read": 1}


@router.post("/read-all")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def mark_all_as_read(
    request: Request,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Mark all of the current user's notifications as read."""
    db.query(models.Notification).filter(
        models.Notification.user_id == current_user.id,
        models.Notification.is_read == 0,
    ).update({"is_read": 1})
    db.commit()
    return {"status": "ok"}
