"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Generic, TypeVar, List
from datetime import datetime
from app.models import BetStatus, ChallengeStatus

T = TypeVar("T")


class UserBase(BaseModel):
    username: str
    email: EmailStr


ALLOWED_EMAIL_DOMAINS = ['tutamail.com', 'tutanota.com', 'protonmail.com', 'proton.me', 'gmail.com', 'icloud.com']


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)
    
    @field_validator('email')
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        domain = v.split('@')[-1].lower()
        if domain not in ALLOWED_EMAIL_DOMAINS:
            raise ValueError(f'Email domain not allowed.')
        return v


class UserResponse(UserBase):
    id: int
    points: int
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


# Challenge Schemas
class ChallengeCreate(BaseModel):
    amount: int = Field(..., gt=0, description="Challenge amount in points")


class ChallengeResponse(BaseModel):
    id: int
    bet_id: int
    challenger_id: int
    challenger_username: str
    amount: int
    status: ChallengeStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ChallengeAction(BaseModel):
    """For accepting/rejecting challenges."""
    pass


# Bet Schemas
class BetBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="Title of the bet")
    criteria: str = Field(..., min_length=1, description="Quantifiable success criteria")


class BetCreate(BetBase):
    amount: int = Field(..., gt=0, description="Creator's stake amount in points")


class BetResponse(BetBase):
    id: int
    user_id: int
    amount: int  # Total matched stake
    status: BetStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class BetWithUsername(BetResponse):
    """Public bet response with username included."""
    username: str
    challenges: List[ChallengeResponse] = []


class BetUpdate(BaseModel):
    status: BetStatus


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response schema."""
    items: List[T]
    total: int
    page: int
    limit: int
    pages: int
