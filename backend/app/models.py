"""
models.py — SQLAlchemy ORM models defining the database schema.

Three tables: users, bets, challenges.
Two enums: BetStatus, ChallengeStatus.

Relationships:
  User  →  many Bets (one user creates many bets)
  Bet   →  many Challenges (one bet can have many challengers)
  User  →  many Challenges (one user can challenge many bets)
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class BetStatus(str, enum.Enum):
    """Possible lifecycle states for a bet."""
    ACTIVE = "active"         # Bet is open — can receive challenges
    WON = "won"               # Creator completed their commitment
    LOST = "lost"             # Creator failed — challengers win
    CANCELLED = "cancelled"   # Creator cancelled — everyone gets refunded


class ChallengeStatus(str, enum.Enum):
    """Possible states for a challenge against a bet."""
    PENDING = "pending"       # Waiting for bet creator to accept/reject
    ACCEPTED = "accepted"     # Creator accepted — stakes are locked in
    REJECTED = "rejected"     # Creator rejected — challenger gets refund
    CANCELLED = "cancelled"   # Bet was cancelled — auto-refunded


class User(Base):
    """User account. New users start with 10 points."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)  # Login identifier
    email = Column(String, unique=True, index=True, nullable=False)     # Must be from allowed domains
    hashed_password = Column(String, nullable=False)                     # bcrypt hash, never store plaintext
    points = Column(Integer, default=10, nullable=False)                 # In-app currency, starts at 10
    created_at = Column(DateTime(timezone=True), server_default=func.now())  # Auto-set by DB
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())        # Auto-updated on any change

    # One user can create many bets
    bets = relationship("Bet", back_populates="user")


class Bet(Base):
    """A personal commitment that others can challenge with their points."""
    __tablename__ = "bets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)   # Who created this bet
    title = Column(String, nullable=False)                               # The commitment (e.g. "I will run 5km")
    amount = Column(Integer, nullable=False)                             # Creator's total matched stake (grows when challenges are accepted)
    criteria = Column(String, nullable=False)                            # How success will be measured
    deadline = Column(DateTime(timezone=True), nullable=False)           # When the bet expires
    status = Column(Enum(BetStatus), default=BetStatus.ACTIVE, nullable=False)  # Current lifecycle state
    stars = Column(Integer, default=0, nullable=False)                           # Number of stars (likes)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships — allows bet.user and bet.challenges in queries
    user = relationship("User", back_populates="bets")
    challenges = relationship("Challenge", back_populates="bet")


class Challenge(Base):
    """A user betting against someone's commitment. Points are deducted immediately on creation."""
    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    bet_id = Column(Integer, ForeignKey("bets.id"), nullable=False)       # Which bet is being challenged
    challenger_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who is challenging
    amount = Column(Integer, nullable=False)                               # Points staked by the challenger
    status = Column(Enum(ChallengeStatus), default=ChallengeStatus.PENDING, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships — allows challenge.bet and challenge.challenger in queries
    bet = relationship("Bet", back_populates="challenges")
    challenger = relationship("User")  # No back_populates — User doesn't need a .challenges list
