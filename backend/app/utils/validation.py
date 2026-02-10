"""
validation.py — Validates that bet titles are personal commitments.

Uses a two-tier approach:
  1. LLM (Llama 3.2 via Ollama) — asks AI to classify as TRUE/FALSE
  2. Regex fallback — if LLM is unavailable, uses pattern matching

This prevents users from creating bets on external events
(e.g., "Team A will win") — only personal commitments allowed
(e.g., "I will run 5km every day").
"""
import re
import httpx
import logging
from app.config import settings

# The specific Ollama model used for classification
MODEL_NAME = "llama3.2:1b"

# ── Regex patterns for fallback detection ──
# Match first-person pronouns
FIRST_PERSON = r"\b(i|we|my|me|our|us)\b"
# Match commitment/intention words
COMMITMENT = r"\b(will|gonna|going to|commit|promise|plan to)\b"
# Combined pattern: first-person + commitment in either order
COMMITMENT_PATTERN = re.compile(
    rf"(?i){FIRST_PERSON}.*{COMMITMENT}|{COMMITMENT}.*{FIRST_PERSON}"
)

logger = logging.getLogger(__name__)

# Singleton HTTP client for Ollama — reused across requests to avoid connection overhead
_llama_client: httpx.AsyncClient | None = None


def get_llama_client() -> httpx.AsyncClient:
    """Get or create the singleton Ollama HTTP client."""
    global _llama_client
    if _llama_client is None:
        _llama_client = httpx.AsyncClient(
            base_url=settings.LLAMA_API_URL,
            timeout=20.0,  # 20 second timeout — LLM can be slow on first call
        )
    return _llama_client


async def is_personal(text: str) -> bool:
    """
    Returns True if the text is a personal commitment by the user.
    
    Strategy:
      1. Quick checks to reject obvious non-personal text
      2. Ask LLM to classify (TRUE = personal, FALSE = not)
      3. If LLM fails for any reason, fall back to regex matching
    
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

    # ── Try LLM classification ──
    client = get_llama_client()

    # Build the chat completion request (OpenAI-compatible API format)
    payload = {
        "model": MODEL_NAME,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a strict binary classifier.\n"
                    "Return ONLY one token: TRUE or FALSE.\n"
                    "TRUE = the user commits to an action they personally control.\n"
                    "FALSE = betting on external events or other people.\n"
                    "No explanations. No punctuation."
                ),
            },
            {"role": "user", "content": text_clean},  # The bet title to classify
        ],
        "max_tokens": 1,      # Only need one word: TRUE or FALSE
        "temperature": 0,      # Deterministic output — no randomness
    }

    try:
        # Call Ollama's OpenAI-compatible chat endpoint
        response = await client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()

        # Extract the single-word response from the nested JSON structure
        result = (
            response.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
            .upper()
        )

        # Clean TRUE/FALSE response — use it directly
        if result in {"TRUE", "FALSE"}:
            return result == "TRUE"

        # LLM returned something unexpected — fall back to regex
        logger.warning("Unexpected LLM output: %r", result)
        return bool(COMMITMENT_PATTERN.search(text_clean))

    except httpx.ConnectError:
        # Ollama container is still starting up or model is loading
        logger.warning("Ollama not ready yet — falling back to regex")
        return bool(COMMITMENT_PATTERN.search(text_clean))

    except httpx.HTTPError as e:
        # HTTP-level error (4xx, 5xx, timeout, etc.)
        logger.error("Ollama HTTP error: %s", e)
        return bool(COMMITMENT_PATTERN.search(text_clean))

    except Exception:
        # Catch-all for any other failure — never block bet creation entirely
        logger.exception("Unexpected LLM failure")
        return bool(COMMITMENT_PATTERN.search(text_clean))
