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

    # --- CORS ---
    # Comma-separated list of allowed frontend origins. Defaults to local dev
    # ports; set CORS_ORIGINS to your real frontend URL(s) in production.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    # --- Logging ---
    LOG_LEVEL: str = "INFO"                   # DEBUG, INFO, WARNING, ERROR, CRITICAL
    LOG_FORMAT: str = "development"           # "development" = human-readable, "production" = JSON
    
    # --- LLM ---
    GROQ_API_KEY: str                         # Required for LangGraph Groq API calls

    # --- Demo data ---
    SEED_DEMO_DATA: bool = True               # On startup, populate demo data if the DB is empty. Set False in production.

    model_config = {
        "env_file": ".env",       # Auto-loads from backend/.env
        "case_sensitive": True    # Env var names are case-sensitive
    }



# Singleton instance — import this everywhere as `from app.config import settings`
settings = Settings()
