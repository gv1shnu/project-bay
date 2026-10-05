"""
deadline_checker.py — Background thread that monitors bet deadlines.

Runs every 60 seconds and handles three time-based transitions:
  ACTIVE   → LOST:  bet deadline passed with no proof uploaded → challengers win.
  PENDING  → WON:   proof review window lapsed with no dispute → creator wins
                    (Level 3 fail-safe: challengers ignored the proof).
  DISPUTED → WON:   jury window lapsed without a 3-vote majority → creator wins
                    (Level 3 fail-safe: "innocent until proven guilty").

The last two guarantee funds are never trapped in a stalled review.

When SEED_DEMO_DATA is on, each pass also rebuilds the open demo bets once they
have all expired, so a long-running demo deployment never shows an empty feed.
"""
import threading
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.models import BetStatus
from app.services.bet_service import apply_resolution
from app.logging_config import get_logger
from app.cache import feed_cache
from app.config import settings

logger = get_logger(__name__)

# How often the checker runs (seconds)
CHECK_INTERVAL = 60


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
            if settings.SEED_DEMO_DATA:
                from app.seed import refresh_demo_bets_if_stale
                refresh_demo_bets_if_stale()
            self._stop_event.wait(CHECK_INTERVAL)

    def _check_deadlines(self):
        """Single check pass — handle all three time-based transitions."""
        db: Session = SessionLocal()
        now = datetime.now(timezone.utc)
        changed = False

        try:
            # 1) ACTIVE past deadline, no proof uploaded → creator LOSES.
            for bet in db.query(models.Bet).filter(
                models.Bet.status == BetStatus.ACTIVE,
                models.Bet.deadline <= now,
            ).all():
                apply_resolution(db, bet, BetStatus.LOST, commit=False)
                logger.info("Bet %d -> LOST (deadline passed without proof)", bet.id)
                changed = True

            # 2) PENDING past review window, no challenger disputed → creator WINS.
            for bet in db.query(models.Bet).filter(
                models.Bet.status == BetStatus.PENDING,
                models.Bet.proof_deadline.isnot(None),
                models.Bet.proof_deadline <= now,
            ).all():
                apply_resolution(db, bet, BetStatus.WON, commit=False)
                logger.info("Bet %d -> WON (review window lapsed, proof unchallenged)", bet.id)
                changed = True

            # 3) DISPUTED past jury window with no 3-vote majority → creator WINS.
            for bet in db.query(models.Bet).filter(
                models.Bet.status == BetStatus.DISPUTED,
                models.Bet.dispute_deadline.isnot(None),
                models.Bet.dispute_deadline <= now,
            ).all():
                apply_resolution(db, bet, BetStatus.WON, commit=False)
                logger.info("Bet %d -> WON (jury window lapsed without a verdict)", bet.id)
                changed = True

            if changed:
                db.commit()
                feed_cache.invalidate()
        finally:
            db.close()


# Singleton instance — import and use deadline_checker.start() / .stop()
deadline_checker = DeadlineChecker()

