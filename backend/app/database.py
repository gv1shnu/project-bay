"""
database.py — Database engine, session factory, and dependency injection.

Creates the SQLAlchemy engine and provides a get_db() dependency
that auto-manages DB sessions for each request.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings
from app.logging_config import get_logger

logger = get_logger(__name__)

# Create the DB engine with connection pooling
# pool_size:     Number of persistent connections kept open (default was 5)
# max_overflow:  Extra connections allowed beyond pool_size under load
# pool_pre_ping: Test connections before using them (detects stale/dropped connections)
# pool_recycle:  Recreate connections after this many seconds (prevents DB timeout issues)
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,          # 10 persistent connections
    max_overflow=20,       # Up to 30 total connections under peak load
    pool_pre_ping=True,    # Auto-reconnect stale connections
    pool_recycle=1800,     # Recycle connections every 30 minutes
)

# Session factory — each call to SessionLocal() creates a new DB session
# autocommit=False: we manually call db.commit()
# autoflush=False: we control when changes are flushed to DB
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base class for all ORM models — every model inherits from this
Base = declarative_base()


def get_db():
    """
    FastAPI dependency that provides a DB session per request.
    Usage: db: Session = Depends(get_db)
    
    The session is automatically closed when the request finishes,
    even if an error occurs (thanks to the finally block).
    """
    db = SessionLocal()
    try:
        yield db  # Hand the session to the route handler
    finally:
        db.close()  # Always close the session when done


