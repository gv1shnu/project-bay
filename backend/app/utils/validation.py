"""
validation.py — Validates that bet titles are personal commitments.

Uses regex pattern matching to ensure bets are personal commitments
(e.g., "I will run 5km every day") and not external event predictions
(e.g., "Team A will win").
"""
import re
import logging

# ── Regex patterns for personal commitment detection ──
# Match first-person pronouns
FIRST_PERSON = r"\b(i|we|my|me|our|us)\b"
# Match commitment/intention words
COMMITMENT = r"\b(will|gonna|going to|commit|promise|plan to)\b"
# Combined pattern: first-person + commitment in either order
COMMITMENT_PATTERN = re.compile(
    rf"(?i){FIRST_PERSON}.*{COMMITMENT}|{COMMITMENT}.*{FIRST_PERSON}"
)

logger = logging.getLogger(__name__)


def is_personal(text: str) -> bool:
    """
    Returns True if the text is a personal commitment by the user.

    Uses regex pattern matching to detect first-person pronouns
    combined with commitment/intention words.

    Args:
        text: The bet title to validate (e.g., "I will finish this book")

    Returns:
        True if the text appears to be a personal commitment
    """
    text_clean = text.strip()

    # Fast reject: too short to be meaningful
    if len(text_clean) < 5:
        return False

    # Fast reject: no first-person pronouns at all — can't be personal
    lowered = text_clean.lower()
    if not any(w in lowered for w in ("i", "we", "my", "me")):
        return False

    # Check for commitment pattern (first-person + commitment words)
    return bool(COMMITMENT_PATTERN.search(text_clean))
