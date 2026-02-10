"""
routers/auth.py — Authentication API endpoints.

Endpoints:
  POST /auth/register  — Create a new user account (10 starting points)
  POST /auth/login     — Get a JWT access token
  GET  /auth/me        — Get current user's profile (requires auth)
  GET  /auth/user/{username} — Get any user's public profile
  GET  /auth/stats/count     — Get total registered user count
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address
from app import models, schemas
from app.auth import get_user_by_username, get_user_by_email, get_password_hash, authenticate_user, create_access_token, get_current_user
from app.database import get_db
from app.config import settings
from app.logging_config import get_logger
from app.exceptions import UserAlreadyExistsError, InvalidCredentialsError

logger = get_logger(__name__)
# All routes in this file are prefixed with /auth and tagged for OpenAPI docs
router = APIRouter(prefix="/auth", tags=["authentication"])
limiter = Limiter(key_func=get_remote_address)


@router.post("/register", response_model=schemas.UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def register(request: Request, user: schemas.UserCreate, db: Session = Depends(get_db)):
    """Register a new user with 10 starting points."""
    # Check if username or email already exists before creating
    if get_user_by_username(db, username=user.username):
        raise UserAlreadyExistsError("username", user.username)
    if get_user_by_email(db, email=user.email):
        raise UserAlreadyExistsError("email", user.email)
    
    # Create the user with hashed password — never store plaintext
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=get_password_hash(user.password),
        points=10  # Every new user starts with 10 points
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)  # Refresh to get the auto-generated id and timestamps
    
    logger.info(f"New user registered: {user.username}")
    return db_user


@router.post("/login", response_model=schemas.Token)
@limiter.limit(f"{settings.RATE_LIMIT_LOGIN_PER_MINUTE}/minute")  # Stricter limit to prevent brute force
def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """
    Login and get access token.
    NOTE: Uses OAuth2 form format (application/x-www-form-urlencoded), not JSON.
    The frontend sends username/password as form fields.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        logger.warning(f"Failed login attempt for: {form_data.username}")
        raise InvalidCredentialsError()
    
    # Create a JWT with the username as the subject ("sub" claim)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    logger.info(f"User logged in: {user.username}")
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=schemas.UserResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def read_users_me(request: Request, current_user: models.User = Depends(get_current_user)):
    """Get current user information. Requires a valid JWT in the Authorization header."""
    return current_user


@router.get("/user/{username}", response_model=schemas.UserResponse)
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_user_profile(request: Request, username: str, db: Session = Depends(get_db)):
    """Get public user profile by username. No auth required — used for profile pages."""
    user = get_user_by_username(db, username)
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("/stats/count")
@limiter.limit(f"{settings.RATE_LIMIT_PER_MINUTE}/minute")
def get_user_count(request: Request, db: Session = Depends(get_db)):
    """Get total registered user count. Shown in the footer of the homepage."""
    count = db.query(models.User).count()
    return {"count": count}
