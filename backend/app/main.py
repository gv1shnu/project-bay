from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from app.database import engine, Base
from app.routers import auth
from app.routers.bets import router as bets_router
from app.config import settings
from app.logging_config import setup_logging, get_logger
from app.exceptions import BettingAPIException, betting_api_exception_handler

# Setup logging
setup_logging(level=settings.LOG_LEVEL, format_type=settings.LOG_FORMAT)
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")
    logger.info("Application startup complete")
    
    yield
    
    logger.info("Application shutting down")

# Rate limiter
limiter = Limiter(key_func=get_remote_address, enabled=settings.RATELIMIT_ENABLED)

app = FastAPI(
    title="Betting Backend API",
    description="Backend API for betting system with authentication and transaction validation",
    version="1.0.0",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "authentication", "description": "User authentication operations"},
        {"name": "bets", "description": "Betting operations"},
    ]
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_exception_handler(BettingAPIException, betting_api_exception_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(bets_router)


@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Betting Backend API", "version": "1.0.0", "docs": "/docs"}


@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}