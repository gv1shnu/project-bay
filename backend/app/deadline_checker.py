"""
deadline_checker.py — Background thread that monitors bet deadlines.

Runs every 60 seconds and handles one transition:
  ACTIVE → LOST:  When a bet's deadline passes without proof uploaded,
  the bet is auto-resolved as lost and challengers receive their winnings.
"""
import threading
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app import models
from app.models import BetStatus, ChallengeStatus
from app.logging_config import get_logger
from app.cache import feed_cache

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
            self._stop_event.wait(CHECK_INTERVAL)

    def _check_deadlines(self):
        """Single check pass — ACTIVE bets past deadline without proof → LOST."""
        db: Session = SessionLocal()
        now = datetime.now(timezone.utc)
        changed = False

        try:
            # Find ACTIVE bets whose deadline has passed (no proof was uploaded in time)
            expired_active = db.query(models.Bet).filter(
                models.Bet.status == BetStatus.ACTIVE,
                models.Bet.deadline <= now,
            ).all()

            for bet in expired_active:
                bet.status = BetStatus.LOST
                # Distribute points to accepted challengers (Proportional Risk)
                active_challenges = [
                    c for c in bet.challenges if c.status == ChallengeStatus.PENDING
                ]
                
                total_challenger_stake = sum(c.amount for c in active_challenges)
                
                if total_challenger_stake > 0:
                    for challenge in active_challenges:
                        challenger = db.query(models.User).filter(
                            models.User.id == challenge.challenger_id
                        ).first()
                        
                        if challenger:
                            # Formula: Payout = ChallengerStake + (ChallengerStake / TotalChallengerStake) * CreatorStake
                            import math  # Ensure math is imported or available in scope (adding import to be safe)
                            share = (challenge.amount / total_challenger_stake) * bet.amount
                            payout = challenge.amount + math.floor(share)
                            
                            challenger.points = int(challenger.points) + int(payout)
                            logger.info(
                                "Auto-loss: Challenger %s won %d pts from bet %d (Stake: %d, Share: %.2f)",
                                challenger.username, payout - challenge.amount, bet.id, challenge.amount, share
                            )
                else:
                    logger.info("Bet %d auto-lost (deadline) but no challengers. Points burned.", bet.id)

                logger.info("Bet %d -> LOST (deadline passed without proof)", bet.id)
                changed = True

            if changed:
                db.commit()
                feed_cache.invalidate()
        finally:
            db.close()


# Singleton instance — import and use deadline_checker.start() / .stop()
deadline_checker = DeadlineChecker()

