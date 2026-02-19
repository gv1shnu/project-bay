"""
logging_config.py — Centralized logging configuration.

Two log formats available:
  - "development": Human-readable with timestamps (default)
  - "production": JSON format for log aggregation tools (e.g., ELK, Datadog)

Usage:
  from app.logging_config import get_logger
  logger = get_logger(__name__)
  logger.info("Something happened")
"""
import logging
import sys


def setup_logging(level: str = "INFO", format_type: str = "development") -> None:
    """
    Configure the root logger. Called once at app startup in main.py.
    
    Args:
        level: Logging level string (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: "development" for readable logs, "production" for JSON logs
    """
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    if format_type == "production":
        # JSON format — each log line is valid JSON, easy to parse by log tools
        formatter = logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}'
        )
    else:
        # Human-readable format — nice for reading in terminal during development
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
    
    # Reset the root logger — remove any existing handlers to avoid duplicates
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Single console handler — all logs go to stdout
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # File handler — save logs to file (max 10MB, 5 backups)
    from logging.handlers import RotatingFileHandler
    import os
    
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")
    os.makedirs(log_dir, exist_ok=True)
    file_path = os.path.join(log_dir, "app.log")
    
    file_handler = RotatingFileHandler(file_path, maxBytes=10*1024*1024, backupCount=5)
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)
    
    # Silence noisy third-party loggers — they spam on every request/query
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger instance.
    Pass __name__ to automatically use the module path as the logger name.
    """
    return logging.getLogger(name)
