"""
auth.py — Authentication utilities: password hashing, JWT tokens, and user lookup.

This module provides:
  - Password hashing/verification (bcrypt)
  - JWT token creation/decoding
  - FastAPI dependency (get_current_user) for protected endpoints
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app import models, schemas
from app.config import settings
from app.database import get_db

# Password hashing context — uses bcrypt algorithm
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme — tells FastAPI to look for "Authorization: Bearer <token>" header
# tokenUrl is the login endpoint path (used for Swagger UI's "Authorize" button)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Check if a plaintext password matches the stored bcrypt hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a plaintext password using bcrypt. Store this in the DB, never the plaintext."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    """
    Create a signed JWT token.
    
    The token payload contains:
      - "sub": username (subject of the token)
      - "exp": expiration timestamp
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        # Default expiration from settings (30 minutes)
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    # Sign the token with our secret key
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def get_user_by_username(db: Session, username: str) -> Optional[models.User]:
    """Look up a user by username. Returns None if not found."""
    return db.query(models.User).filter(models.User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    """Look up a user by email. Returns None if not found."""
    return db.query(models.User).filter(models.User.email == email).first()


def authenticate_user(db: Session, username: str, password: str) -> Optional[models.User]:
    """
    Verify username + password combo. Returns the User if valid, None if not.
    Used by the login endpoint.
    """
    user = get_user_by_username(db, username)
    if not user:
        return None  # Username doesn't exist
    if not verify_password(password, user.hashed_password):
        return None  # Password doesn't match
    return user


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> models.User:
    """
    FastAPI dependency — extracts and validates the JWT from the request header.
    
    Usage in any route:
        current_user: models.User = Depends(get_current_user)
    
    Raises 401 if the token is missing, expired, or the user doesn't exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # Decode the JWT and extract the username from the "sub" claim
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        # Token is invalid, expired, or tampered with
        raise credentials_exception
    
    # Fetch the actual user from the database
    user = get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception  # User was deleted but token still valid
    return user

