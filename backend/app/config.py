"""
config.py — Application configuration loaded from .env file.

Uses Pydantic BaseSettings to auto-read environment variables.
All required vars must be set in backend/.env or the app won't start.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # --- Authentication ---
    SECRET_KEY: str                           # Used to sign JWT tokens — keep this secret!
    ALGORITHM: str = "HS256"                  # JWT signing algorithm
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30     # How long a login session lasts

    # --- Database ---
    DATABASE_URL: str                         # PostgreSQL connection string (e.g. postgresql://user:pass@host/db)
    TEST_DATABASE_URL: str                    # Separate DB for running tests

    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: int = 60           # Max requests per minute for general endpoints
    RATE_LIMIT_LOGIN_PER_MINUTE: int = 10     # Stricter limit for login to prevent brute force
    RATELIMIT_ENABLED: bool = True            # Set to False to disable rate limiting in dev

    # --- Admin ---
    ADMIN_PASSPHRASE: str                     # Passphrase required to access /admin endpoints

    # --- Logging ---
    LOG_LEVEL: str = "INFO"                   # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "development"           # "development" = human-readable, "production" = JSON

    model_config = {
        "env_file": ".env",       # Auto-loads from backend/.env
        "case_sensitive": True    # Env var names are case-sensitive
    }



# Singleton instance — import this everywhere as `from app.config import settings`
settings = Settings()
