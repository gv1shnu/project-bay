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

# Create the DB engine from the connection string in .env
# NOTE: No connection pooling configured — fine for dev, add pool_size for production
engine = create_engine(settings.DATABASE_URL)

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


