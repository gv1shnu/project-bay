from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from app.models import BetStatus


class UserBase(BaseModel):
    username: str
    email: EmailStr


class UserCreate(UserBase):
    password: str = Field(..., min_length=6)


class UserResponse(UserBase):
    id: int
    points: float
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class BetBase(BaseModel):
    amount: float = Field(..., gt=0, description="Bet amount must be greater than 0")
    description: Optional[str] = None


class BetCreate(BetBase):
    pass


class BetResponse(BetBase):
    id: int
    user_id: int
    status: BetStatus
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class BetUpdate(BaseModel):
    status: BetStatus

