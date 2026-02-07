# Detects whether first person (personal) commitments using a combination of LLM and regex.

import re
import httpx
import logging
from app.config import settings

MODEL_NAME = "llama3.2:1b"

FIRST_PERSON = r"\b(i|we|my|me|our|us)\b"
COMMITMENT = r"\b(will|gonna|going to|commit|promise|plan to)\b"
COMMITMENT_PATTERN = re.compile(
    rf"(?i){FIRST_PERSON}.*{COMMITMENT}|{COMMITMENT}.*{FIRST_PERSON}"
)

logger = logging.getLogger(__name__)

_llama_client: httpx.AsyncClient | None = None


def get_llama_client() -> httpx.AsyncClient:
    global _llama_client
    if _llama_client is None:
        _llama_client = httpx.AsyncClient(
            base_url=settings.LLAMA_API_URL,
            timeout=20.0,
        )
    return _llama_client


async def is_personal(text: str) -> bool:
    """
    Returns True if the text is a personal commitment by the user.
    Uses LLM first, regex as fallback.
    """
    text_clean = text.strip()

    # Fast rejects
    if len(text_clean) < 5:
        return False

    lowered = text_clean.lower()
    if not any(w in lowered for w in ("i", "we", "my", "me")):
        return False

    client = get_llama_client()

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
            {"role": "user", "content": text_clean},
        ],
        "max_tokens": 1,
        "temperature": 0,
    }

    try:
        response = await client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()

        result = (
            response.json()
            .get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
            .upper()
        )

        if result in {"TRUE", "FALSE"}:
            return result == "TRUE"

        logger.warning("Unexpected LLM output: %r", result)
        return bool(COMMITMENT_PATTERN.search(text_clean))

    except httpx.ConnectError:
        # Ollama still booting / model warming up
        logger.warning("Ollama not ready yet — falling back to regex")
        return bool(COMMITMENT_PATTERN.search(text_clean))

    except httpx.HTTPError as e:
        logger.error("Ollama HTTP error: %s", e)
        return bool(COMMITMENT_PATTERN.search(text_clean))

    except Exception:
        logger.exception("Unexpected LLM failure")
        return bool(COMMITMENT_PATTERN.search(text_clean))
