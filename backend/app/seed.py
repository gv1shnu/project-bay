"""
seed.py — Populate the database with realistic demo data.

Gives a first-time visitor an instantly-alive app: a populated feed, user
profiles with wins/losses, a bet under Level-1 review, a live dispute in the
Tribunal, and already-resolved wins/losses/cancellations — plus a follow graph
so challenges and notifications make sense.

Run manually:
    python -m app.seed            # seed only if the DB has no users
    python -m app.seed --reset    # DROP all tables, recreate, then seed

Or let it run automatically: when SEED_DEMO_DATA=true (default), the app seeds
an empty database on startup.

Every demo user shares the password:  demo1234
"""
import base64
import os
import sys
from datetime import datetime, timezone, timedelta

from app.database import SessionLocal, Base, engine
from app import models
from app.models import BetStatus, ChallengeStatus
from app.auth import get_password_hash
from app.services.bet_service import apply_resolution
from app.logging_config import get_logger

logger = get_logger(__name__)

DEMO_PASSWORD = "demo1234"
START_POINTS = 20  # demo users start richer than the live default (10) for fuller activity

# A tiny valid 1x1 PNG, written to /uploads so proof images actually render.
_PNG_1x1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
)


def _now():
    return datetime.now(timezone.utc)


def _write_demo_proof() -> str:
    """Drop a placeholder proof image into the uploads dir and return its URL."""
    uploads = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
    os.makedirs(uploads, exist_ok=True)
    path = os.path.join(uploads, "demo_proof.png")
    with open(path, "wb") as f:
        f.write(_PNG_1x1)
    return "/uploads/demo_proof.png"


def _build(db):
    """Insert the whole demo world in one session."""
    proof_url = _write_demo_proof()

    # ── Users ────────────────────────────────────────────────────────────
    names = ["alex", "bella", "chris", "dana", "evan", "fiona", "gina", "hugo"]
    users = {}
    for n in names:
        u = models.User(
            username=n,
            email=f"{n}@gmail.com",
            hashed_password=get_password_hash(DEMO_PASSWORD),
            points=START_POINTS,
        )
        db.add(u)
        users[n] = u
    db.flush()

    # ── Follow graph (follower -> followed) ──────────────────────────────
    edges = [
        ("chris", "bella"), ("dana", "bella"), ("alex", "bella"),
        ("chris", "evan"), ("dana", "evan"), ("fiona", "evan"),
        ("gina", "chris"), ("hugo", "chris"),
        ("bella", "alex"), ("dana", "alex"),
        ("evan", "bella"), ("fiona", "bella"),
        ("chris", "dana"),
    ]
    for a, b in edges:
        db.add(models.Follow(follower_id=users[a].id, followed_id=users[b].id))
    db.flush()

    # ── Helpers ──────────────────────────────────────────────────────────
    def make_bet(creator, title, criteria, stake, deadline_days, created_hours_ago,
                 status=BetStatus.ACTIVE, stars=0):
        creator.points = int(creator.points) - stake
        bet = models.Bet(
            user_id=creator.id, title=title, criteria=criteria, amount=stake,
            deadline=_now() + timedelta(days=deadline_days), status=status, stars=stars,
            created_at=_now() - timedelta(hours=created_hours_ago),
        )
        db.add(bet)
        db.flush()
        return bet

    def add_challenge(bet, challenger, amount):
        challenger.points = int(challenger.points) - amount
        c = models.Challenge(bet_id=bet.id, challenger_id=challenger.id,
                             amount=amount, status=ChallengeStatus.PENDING)
        db.add(c)
        db.flush()
        return c

    def add_proof(bet, comment):
        bet.proof_comment = comment
        bet.proof_media_url = proof_url
        bet.proof_submitted_at = _now() - timedelta(hours=2)

    def star(bet, *starrers):
        for s in starrers:
            db.add(models.BetStar(bet_id=bet.id, user_id=users[s].id))
        bet.stars = (bet.stars or 0) + len(starrers)

    U = users

    # 1) ACTIVE — no challengers yet
    b1 = make_bet(U["alex"], "I will run 5km before Friday", "Timestamped Strava screenshot", 3, 3, 30)
    star(b1, "bella", "chris")

    # 2) ACTIVE — with challengers
    b2 = make_bet(U["bella"], "I will finish reading Dune this week", "Photo of the last page", 4, 5, 26)
    add_challenge(b2, U["chris"], 2)
    add_challenge(b2, U["dana"], 2)
    star(b2, "alex", "evan", "gina")

    # 3) PENDING — proof uploaded, Level-1 review open (no votes yet)
    b3 = make_bet(U["evan"], "I will do 100 pushups today", "Video of the full set", 3, 1, 20,
                  status=BetStatus.PENDING)
    add_challenge(b3, U["chris"], 2)
    add_challenge(b3, U["dana"], 2)
    add_proof(b3, "Knocked out all 100 — clip attached.")
    b3.proof_deadline = _now() + timedelta(hours=20)
    star(b3, "fiona")

    # 4) DISPUTED — a challenger flagged the proof; now in the Tribunal
    b4 = make_bet(U["chris"], "I will wake up at 5am for 5 days", "Daily alarm-off screenshots", 5, 2, 40,
                  status=BetStatus.DISPUTED)
    ch_g = add_challenge(b4, U["gina"], 3)
    add_challenge(b4, U["hugo"], 2)
    add_proof(b4, "Five mornings, five screenshots in the collage.")
    b4.proof_deadline = _now() - timedelta(hours=1)
    b4.dispute_deadline = _now() + timedelta(hours=18)
    db.add(models.ProofVote(bet_id=b4.id, user_id=U["gina"].id, vote="not_cool"))  # the flag
    db.add(models.JuryVote(bet_id=b4.id, user_id=U["alex"].id, vote="cool"))       # neutral juror so far
    star(b4, "dana", "evan")

    # 5) WON — resolved, creator took the pot
    b5 = make_bet(U["alex"], "I will meditate 10 minutes", "Calm app session log", 2, -1, 60)
    add_challenge(b5, U["bella"], 2)
    add_proof(b5, "10-minute session done, log attached.")
    apply_resolution(db, b5, BetStatus.WON, commit=False)
    star(b5, "chris", "dana", "fiona")

    # 6) LOST — resolved, challengers split the pot
    b6 = make_bet(U["bella"], "I will write 1000 words today", "Word-count screenshot", 4, -1, 72)
    add_challenge(b6, U["evan"], 3)
    add_challenge(b6, U["fiona"], 2)
    apply_resolution(db, b6, BetStatus.LOST, commit=False)
    star(b6, "gina")

    # 7) CANCELLED — pulled before the deadline, everyone refunded
    b7 = make_bet(U["dana"], "I will bike 20km this weekend", "GPS route export", 3, 2, 18)
    add_challenge(b7, U["chris"], 2)
    apply_resolution(db, b7, BetStatus.CANCELLED, commit=False)

    # A couple of standalone notifications for flavor
    db.add(models.Notification(user_id=U["chris"].id,
                               message='@evan uploaded proof for "I will do 100 pushups today"',
                               bet_id=b3.id))
    db.add(models.Notification(user_id=U["hugo"].id,
                               message='@gina disputed the proof for "I will wake up at 5am for 5 days" — sent to the jury',
                               bet_id=b4.id))

    db.commit()
    logger.info("Seed complete: %d users, 7 bets across all states.", len(users))


def seed_if_empty() -> bool:
    """Seed only when there are no users yet. Returns True if it seeded."""
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            return False
        _build(db)
        return True
    except Exception as e:  # never let seeding crash app startup
        db.rollback()
        logger.warning("Demo seed skipped: %s", e)
        return False
    finally:
        db.close()


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if "--reset" in argv:
        logger.info("Resetting database (dropping all tables)...")
        Base.metadata.drop_all(bind=engine)
        Base.metadata.create_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(models.User).count() > 0:
            print("Database already has users — nothing to seed. Use --reset to wipe and reseed.")
            return
    finally:
        db.close()

    if seed_if_empty():
        print(f"Seeded demo data. Log in with any of: alex, bella, chris, dana, evan, fiona, gina, hugo")
        print(f"Password for all demo accounts: {DEMO_PASSWORD}")
    else:
        print("Nothing seeded.")


if __name__ == "__main__":
    main()
