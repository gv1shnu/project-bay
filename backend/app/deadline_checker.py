"""
deadline_checker.py — Background thread that monitors bet deadlines.

Runs every 60 seconds and handles two transitions:
  1. ACTIVE → AWAITING_PROOF:  When a bet's deadline passes, the creator gets
     a 1-hour window to upload proof of completion.
  2. AWAITING_PROOF → LOST:    If the creator doesn't upload proof within
     the 1-hour window, the bet is auto-resolved as lost.
"""
import threading
import time
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.models import BetStatus, ChallengeStatus
from app.logging_config import get_logger
from app.cache import feed_cache

logger = get_logger(__name__)

# How often the checker runs (seconds)
CHECK_INTERVAL = 60

# How long the creator has to upload proof after the deadline
PROOF_WINDOW_HOURS = 1


class DeadlineChecker:
    """Background thread that transitions bets based on their deadlines."""

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self):
        """Start the background checker thread."""
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True, name="deadline-checker")
        self._thread.start()
        logger.info("Deadline checker started (interval: %ds)", CHECK_INTERVAL)

    def stop(self):
        """Signal the thread to stop and wait for it to finish."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=10)
        logger.info("Deadline checker stopped")

    def _run(self):
        """Main loop — runs until stop() is called."""
        while not self._stop_event.is_set():
            try:
                self._check_deadlines()
            except Exception as e:
                logger.error("Deadline checker error: %s", e)
            self._stop_event.wait(CHECK_INTERVAL)

    def _check_deadlines(self):
        """Single check pass — transitions eligible bets."""
        db: Session = SessionLocal()
        now = datetime.now(timezone.utc)
        changed = False

        try:
            # ── 1. ACTIVE bets past their deadline → AWAITING_PROOF ──
            expired_active = db.query(models.Bet).filter(
                models.Bet.status == BetStatus.ACTIVE,
                models.Bet.deadline <= now,
            ).all()

            for bet in expired_active:
                bet.status = BetStatus.AWAITING_PROOF
                bet.proof_deadline = bet.deadline + timedelta(hours=PROOF_WINDOW_HOURS)
                logger.info("Bet %d → AWAITING_PROOF (proof deadline: %s)", bet.id, bet.proof_deadline)
                changed = True

            # ── 2. AWAITING_PROOF bets past their proof_deadline → LOST ──
            expired_proof = db.query(models.Bet).filter(
                models.Bet.status == BetStatus.AWAITING_PROOF,
                models.Bet.proof_deadline <= now,
            ).all()

            for bet in expired_proof:
                bet.status = BetStatus.LOST
                # Distribute points to accepted challengers (same logic as resolve_bet LOST)
                accepted_challenges = [
                    c for c in bet.challenges if c.status == ChallengeStatus.ACCEPTED
                ]
                for challenge in accepted_challenges:
                    challenger = db.query(models.User).filter(
                        models.User.id == challenge.challenger_id
                    ).first()
                    if challenger:
                        challenger.points = int(challenger.points) + (challenge.amount * 2)
                        logger.info(
                            "Auto-loss: Challenger %s won %d pts from bet %d",
                            challenger.username, challenge.amount * 2, bet.id
                        )
                logger.info("Bet %d → LOST (proof window expired)", bet.id)
                changed = True

            if changed:
                db.commit()
                feed_cache.invalidate()
        finally:
            db.close()


# Singleton instance — import and use deadline_checker.start() / .stop()
deadline_checker = DeadlineChecker()
