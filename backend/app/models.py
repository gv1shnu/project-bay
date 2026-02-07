"""Database models for the betting API."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class BetStatus(str, enum.Enum):
    """Possible statuses for a bet."""
    ACTIVE = "active"
    WON = "won"
    LOST = "lost"
    CANCELLED = "cancelled"


class ChallengeStatus(str, enum.Enum):
    """Possible statuses for a challenge."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class User(Base):
    """User model representing registered users."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    points = Column(Integer, default=10, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    bets = relationship("Bet", back_populates="user")


class Bet(Base):
    """Bet model representing individual bets placed by users."""
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)  # Creator's total matched stake
    criteria = Column(String, nullable=False)
    deadline = Column(DateTime(timezone=True), nullable=False)
    status = Column(Enum(BetStatus), default=BetStatus.ACTIVE, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="bets")
    challenges = relationship("Challenge", back_populates="bet")


class Challenge(Base):
    """Challenge model - users betting against a bet creator."""
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    bet_id = Column(Integer, ForeignKey("bets.id"), nullable=False)
    challenger_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    status = Column(Enum(ChallengeStatus), default=ChallengeStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bet = relationship("Bet", back_populates="challenges")
    challenger = relationship("User")
