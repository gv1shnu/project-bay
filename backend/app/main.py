"""
main.py — FastAPI application entry point.

Sets up the app, middleware, rate limiting, routers, and lifespan events.
Start with: uvicorn app.main:app
"""
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.database import engine, Base, SessionLocal
from app.routers import auth
from app.routers.bets import router as bets_router
from app.routers.admin import router as admin_router
from app.routers.notifications import router as notifications_router
from app.config import settings
from app.logging_config import setup_logging, get_logger
from app.exceptions import BettingAPIException, betting_api_exception_handler
from app.deadline_checker import deadline_checker

# Initialize logging before anything else so all modules get the configured logger
setup_logging(level=settings.LOG_LEVEL, format_type=settings.LOG_FORMAT)
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs on app startup/shutdown. Creates DB tables if they don't exist."""
    # Auto-create all tables defined in models.py (safe to call repeatedly)
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")

    logger.info("Application startup complete")

    # Start the deadline checker background thread
    deadline_checker.start()
    
    yield  # App runs here — everything above is startup, below is shutdown
    
    # Stop the deadline checker on shutdown
    deadline_checker.stop()
    logger.info("Application shutting down")


# Rate limiter — throttles requests per IP to prevent abuse
limiter = Limiter(key_func=get_remote_address, enabled=settings.RATELIMIT_ENABLED)

# Create the FastAPI app instance with OpenAPI metadata
app = FastAPI(
    title="Betting Backend API",
    description="Backend API for betting system with authentication and transaction validation",
    version="1.0.0",
    lifespan=lifespan,  # Attach the startup/shutdown handler
    openapi_tags=[
        {"name": "authentication", "description": "User authentication operations"},
        {"name": "bets", "description": "Betting operations"},
    ]
)

# Attach rate limiter to app state so it's accessible in routes
app.state.limiter = limiter
# Register global exception handlers for rate limits and custom API errors
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(BettingAPIException, betting_api_exception_handler)

# CORS — allow frontend dev servers to talk to the API
# Update these origins when deploying to production
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",    # Vite default dev port
        "http://localhost:3000",    # Alternate dev port
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,  # Allow cookies/auth headers
    allow_methods=["*"],     # Allow all HTTP methods
    allow_headers=["*"],     # Allow all headers
)

# Mount route groups — /auth/* and /bets/*
app.include_router(auth.router)
app.include_router(bets_router)
app.include_router(admin_router)
app.include_router(notifications_router)

# Serve uploaded proof files as static assets at /uploads/*
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOADS_DIR, exist_ok=True)  # Create if it doesn't exist
app.mount("/uploads", StaticFiles(directory=UPLOADS_DIR), name="uploads")


@app.get("/")
def root():
    """Root endpoint — confirms the API is running."""
    return {"message": "Betting Backend API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health_check():
    """Health check — used by monitoring tools and Docker health checks."""
    return {"status": "healthy"}