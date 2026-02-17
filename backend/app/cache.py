"""
cache.py — Simple in-memory TTL cache for hot endpoints.

Reduces redundant database queries for data that doesn't change every second
(e.g., public feed, user profiles). Each cache entry expires after a configurable TTL.

Usage:
    from app.cache import feed_cache

    cached = feed_cache.get("page_1_limit_10")
    if cached:
        return cached

    result = expensive_db_query()
    feed_cache.set("page_1_limit_10", result)
    return result
"""
import time
from threading import Lock
from app.logging_config import get_logger

logger = get_logger(__name__)


class TTLCache:
    """Thread-safe in-memory cache with per-key expiration."""

    def __init__(self, ttl_seconds: int = 30, max_size: int = 100):
        self._store: dict[str, tuple[float, object]] = {}   # key → (expires_at, value)
        self._ttl = ttl_seconds
        self._max_size = max_size
        self._lock = Lock()

    def get(self, key: str):
        """Return cached value if it exists and hasn't expired, else None."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, value = entry
            if time.time() > expires_at:
                del self._store[key]      # Expired — clean up
                return None
            return value

    def set(self, key: str, value: object):
        """Store a value with a TTL. Evicts oldest entry if cache is full."""
        with self._lock:
            # Evict oldest if at capacity
            if len(self._store) >= self._max_size and key not in self._store:
                oldest_key = min(self._store, key=lambda k: self._store[k][0])
                del self._store[oldest_key]
            self._store[key] = (time.time() + self._ttl, value)

    def invalidate(self, key: str = None):
        """Clear a specific key, or the entire cache if no key is given."""
        with self._lock:
            if key:
                self._store.pop(key, None)
            else:
                self._store.clear()


# ── Cache instances for different data ──

# Public feed: 15s TTL — users see near-real-time data, but we avoid
# hitting the DB on every single page load
feed_cache = TTLCache(ttl_seconds=15, max_size=50)

# User profiles: 30s TTL — profile data changes infrequently
profile_cache = TTLCache(ttl_seconds=30, max_size=200)
