"""
seed.py — Populates the database with sample users, bets, and challenges on first run.

Creates 3 demo users, 10 personal commitment bets across all statuses
(active, won, lost, cancelled), and challenges in varied states
(pending, accepted, rejected, cancelled).

Only runs if the users table is empty — safe to call on every startup.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.models import User, Bet, Challenge, BetStatus, ChallengeStatus
from app.auth import get_password_hash
from app.logging_config import get_logger

logger = get_logger(__name__)

# Default password for all seed users (for demo/dev purposes only)
SEED_PASSWORD = "password123"

# 3 demo users with enough points to cover all stakes
SEED_USERS = [
    {"username": "alex",   "email": "alex@gmail.com",   "points": 50},
    {"username": "jordan", "email": "jordan@gmail.com", "points": 50},
    {"username": "sam",    "email": "sam@gmail.com",     "points": 50},
]

# 10 bets with varied statuses
# (user_index, title, criteria, amount, days_offset, status)
#   days_offset: positive = future deadline, negative = past deadline
SEED_BETS = [
    # ── Active bets (open for challenges) ──
    (0, "I will read 30 pages every day this week",
     "Photo of book with page number", 3, 7, BetStatus.ACTIVE),

    (1, "I will cook homemade meals every day this week",
     "Photo of each meal before eating", 3, 7, BetStatus.ACTIVE),

    (2, "I will practice guitar for 30 minutes daily",
     "Short daily video clip of practice session", 3, 21, BetStatus.ACTIVE),

    # ── Won bets (creator completed their commitment) ──
    (0, "I will complete a 5K run this weekend",
     "Screenshot from fitness tracking app", 4, -3, BetStatus.WON),

    (1, "I will finish my online course by month end",
     "Certificate of completion screenshot", 4, -5, BetStatus.WON),

    # ── Lost bets (creator failed) ──
    (2, "I will do 50 push-ups every morning for two weeks",
     "Video proof of daily push-ups", 5, -14, BetStatus.LOST),

    (0, "I will wake up before 6 AM for 5 days straight",
     "Screenshot of alarm log from phone", 5, -7, BetStatus.LOST),

    # ── Cancelled bets (creator cancelled, everyone refunded) ──
    (1, "I will meditate for 15 minutes daily for 10 days",
     "Screenshot from meditation app streak", 5, -2, BetStatus.CANCELLED),

    (2, "I will not spend money on junk food for a month",
     "Bank statement showing no fast food charges", 4, -1, BetStatus.CANCELLED),

    (0, "I will write 500 words in my journal every day",
     "Photo of journal page with date", 3, 14, BetStatus.ACTIVE),
]

# Challenges linking users to other users' bets
# (challenger_user_index, bet_index, amount, status)
SEED_CHALLENGES = [
    # Challenges on active bets
    (1, 0, 3, ChallengeStatus.ACCEPTED),    # jordan accepted on alex's reading bet
    (2, 0, 2, ChallengeStatus.PENDING),      # sam pending on alex's reading bet
    (0, 1, 4, ChallengeStatus.PENDING),      # alex pending on jordan's cooking bet
    (2, 2, 3, ChallengeStatus.REJECTED),     # sam rejected on sam's guitar bet (will fix user)
    (0, 2, 2, ChallengeStatus.ACCEPTED),     # alex accepted on sam's guitar bet

    # Challenges on won bets
    (1, 3, 4, ChallengeStatus.ACCEPTED),     # jordan challenged alex's 5K — alex won, jordan lost stake
    (2, 4, 3, ChallengeStatus.ACCEPTED),     # sam challenged jordan's course — jordan won

    # Challenges on lost bets
    (1, 5, 5, ChallengeStatus.ACCEPTED),     # jordan challenged sam's push-ups — sam lost, jordan wins
    (2, 6, 4, ChallengeStatus.ACCEPTED),     # sam challenged alex's wake-up — alex lost, sam wins

    # Challenges on cancelled bets (auto-cancelled)
    (0, 7, 3, ChallengeStatus.CANCELLED),    # alex's challenge on jordan's meditation — cancelled
    (1, 8, 2, ChallengeStatus.CANCELLED),    # jordan's challenge on sam's junk food — cancelled
]


def run_seed(db: Session) -> None:
    """
    Seed the database with demo users, bets, and challenges.
    Skips entirely if any users already exist (idempotent).
    """
    existing_users = db.query(User).first()
    if existing_users:
        logger.info("Database already has data — skipping seed")
        return

    logger.info("Seeding database with demo data...")

    # ── Create users ──
    hashed_pw = get_password_hash(SEED_PASSWORD)
    users = []
    for user_data in SEED_USERS:
        user = User(
            username=user_data["username"],
            email=user_data["email"],
            hashed_password=hashed_pw,
            points=user_data["points"],
        )
        db.add(user)
        users.append(user)

    db.flush()  # Assign user IDs

    # ── Create bets ──
    now = datetime.now(timezone.utc)
    bets = []
    for user_idx, title, criteria, amount, days_offset, bet_status in SEED_BETS:
        bet = Bet(
            user_id=users[user_idx].id,
            title=title,
            criteria=criteria,
            amount=amount,
            deadline=now + timedelta(days=days_offset),
            status=bet_status,
        )
        db.add(bet)
        bets.append(bet)
        # Deduct stake from creator (skip for cancelled — points were refunded)
        if bet_status != BetStatus.CANCELLED:
            users[user_idx].points -= amount

    db.flush()  # Assign bet IDs

    # ── Create challenges ──
    for challenger_idx, bet_idx, amount, challenge_status in SEED_CHALLENGES:
        challenge = Challenge(
            bet_id=bets[bet_idx].id,
            challenger_id=users[challenger_idx].id,
            amount=amount,
            status=challenge_status,
        )
        db.add(challenge)
        # Deduct points from challenger (skip cancelled/rejected — refunded)
        if challenge_status not in (ChallengeStatus.CANCELLED, ChallengeStatus.REJECTED):
            users[challenger_idx].points -= amount

    db.commit()
    logger.info(
        "Seeded %d users, %d bets, and %d challenges",
        len(SEED_USERS), len(SEED_BETS), len(SEED_CHALLENGES),
    )
