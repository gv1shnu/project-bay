"""
models.py — SQLAlchemy ORM models defining the database schema.

Three tables: users, bets, challenges.
Two enums: BetStatus, ChallengeStatus.

Relationships:
  User  →  many Bets (one user creates many bets)
  Bet   →  many Challenges (one bet can have many challengers)
  User  →  many Challenges (one user can challenge many bets)
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base


class BetStatus(str, enum.Enum):
    """Possible lifecycle states for a bet."""
    ACTIVE = "active"                       # Bet is open — can receive challenges and proof
    PROOF_UNDER_REVIEW = "proof_under_review"  # Proof uploaded — waiting for review
    WON = "won"                             # Creator completed their commitment
    LOST = "lost"                           # Creator failed — challengers win
    CANCELLED = "cancelled"                 # Creator cancelled — everyone gets refunded


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
    notifications = relationship("Notification", back_populates="user")


class Notification(Base):
    """In-app notification for a user (e.g. 'Proof uploaded for a bet you challenged')."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # Who receives this
    message = Column(String, nullable=False)                            # Human-readable message
    bet_id = Column(Integer, ForeignKey("bets.id"), nullable=True)     # Related bet, if any
    is_read = Column(Integer, default=0, nullable=False)               # 0 = unread, 1 = read
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="notifications")
    bet = relationship("Bet")

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
    proof_comment = Column(String, nullable=True)                # Creator's proof description
    proof_media_url = Column(String, nullable=True)              # Path to uploaded proof file
    proof_submitted_at = Column(DateTime(timezone=True), nullable=True)  # When proof was uploaded
    proof_deadline = Column(DateTime(timezone=True), nullable=True)      # Deadline + 1hr for proof upload
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships — allows bet.user and bet.challenges in queries
    user = relationship("User", back_populates="bets")
    challenges = relationship("Challenge", back_populates="bet")
    proof_votes = relationship("ProofVote", back_populates="bet")
    starred_by = relationship("BetStar", back_populates="bet")


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


class ProofVote(Base):
    """A challenger's vote on uploaded proof: 'cool' (approve) or 'not_cool' (reject)."""
    __tablename__ = "proof_votes"

    id = Column(Integer, primary_key=True, index=True)
    bet_id = Column(Integer, ForeignKey("bets.id"), nullable=False)       # Which bet's proof is being voted on
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)     # Who is voting (must be accepted challenger)
    vote = Column(String, nullable=False)                                  # "cool" or "not_cool"
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bet = relationship("Bet", back_populates="proof_votes")
    voter = relationship("User")


class BetStar(Base):
    """Tracks which users have starred which bets (for toggle behavior)."""
    __tablename__ = "bet_stars"
    __table_args__ = (UniqueConstraint("bet_id", "user_id", name="uq_bet_star"),)

    id = Column(Integer, primary_key=True, index=True)
    bet_id = Column(Integer, ForeignKey("bets.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    bet = relationship("Bet", back_populates="starred_by")
    user = relationship("User")
