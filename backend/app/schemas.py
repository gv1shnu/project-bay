"""
schemas.py — Pydantic models for request validation and response serialization.

Each schema defines the shape of data going in/out of the API.
- *Create schemas: what the client sends when creating something
- *Response schemas: what the API sends back
- PaginatedResponse: generic wrapper for paginated list endpoints
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Generic, TypeVar, List
from datetime import datetime
from app.models import BetStatus, ChallengeStatus

# Generic type var for PaginatedResponse — allows PaginatedResponse[BetResponse], etc.
T = TypeVar("T")


# ──────────────────────────────────────────────────────────
# User Schemas
# ──────────────────────────────────────────────────────────

class UserBase(BaseModel):
    """Shared fields for all user schemas."""
    username: str
    email: EmailStr  # Pydantic validates email format automatically


# Only these email providers are allowed for registration (abuse prevention)
ALLOWED_EMAIL_DOMAINS = [
    'tutamail.com', 'tutanota.com', 
    'protonmail.com', 'proton.me', 
    'gmail.com', 'icloud.com'
    ]


class UserCreate(UserBase):
    """Request body for POST /auth/register."""
    password: str = Field(..., min_length=6)  # Minimum 6 chars enforced
    
    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        """Reject emails from domains not in our whitelist."""
        domain = v.split('@')[-1].lower()
        if domain not in ALLOWED_EMAIL_DOMAINS:
            raise ValueError(f'Email domain not allowed.')
        return v


class UserResponse(UserBase):
    """Response body for user data — never includes password."""
    id: int
    points: int
    created_at: datetime

    model_config = {"from_attributes": True}  # Allows creating from SQLAlchemy model


class Token(BaseModel):
    """Response body for POST /auth/login — contains the JWT."""
    access_token: str
    token_type: str  # Always "bearer"


class TokenData(BaseModel):
    """Internal schema for decoded JWT payload."""
    username: Optional[str] = None


# ──────────────────────────────────────────────────────────
# Challenge Schemas
# ──────────────────────────────────────────────────────────

class ChallengeCreate(BaseModel):
    """Request body for POST /bets/{id}/challenge."""
    amount: int = Field(..., gt=0, description="Challenge amount in points")


class ChallengeResponse(BaseModel):
    """Response body for challenge data — includes challenger's username."""
    id: int
    bet_id: int
    challenger_id: int
    challenger_username: str  # Resolved from the User table, not stored in Challenge
    amount: int
    status: ChallengeStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ChallengeAction(BaseModel):
    """For accepting/rejecting challenges. Empty body — action is in the URL path."""
    pass


# ──────────────────────────────────────────────────────────
# Bet Schemas
# ──────────────────────────────────────────────────────────

class BetBase(BaseModel):
    """Shared fields for bet creation and response."""
    title: str = Field(..., min_length=1, max_length=200, description="Title of the bet")
    criteria: str = Field(..., min_length=1, description="Quantifiable success criteria")


class BetCreate(BetBase):
    """Request body for POST /bets/ — creating a new bet."""
    amount: int = Field(..., gt=0, description="Creator's stake amount in points")
    deadline: datetime = Field(..., description="Deadline for the bet completion")


class BetResponse(BetBase):
    """Response body for a single bet."""
    id: int
    user_id: int
    amount: int       # Total matched stake (increases when challenges are accepted)
    deadline: datetime
    status: BetStatus
    stars: int = 0    # Number of stars (likes)
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BetWithUsername(BetResponse):
    """Extended bet response for the public feed — includes creator's username and challenges."""
    username: str
    challenges: List[ChallengeResponse] = []  # All non-rejected challenges


class BetUpdate(BaseModel):
    """Request body for PATCH /bets/{id} — resolving a bet."""
    status: BetStatus  # Must be won, lost, or cancelled


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper. Used for list endpoints."""
    items: List[T]   # The actual data
    total: int       # Total items across all pages
    page: int        # Current page number (1-indexed)
    limit: int       # Items per page
    pages: int       # Total number of pages
