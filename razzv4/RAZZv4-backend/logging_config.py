"""
Centralized logging configuration for RAZZv4 Backend
"""
import logging
import sys
from pathlib import Path

# Create logs directory if it doesn't exist
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


def setup_logging(log_level: str = "INFO", log_file: str = "logs/app.log"):
    """
    Configure logging for the entire application
    
    Args:
        log_level: Minimum log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file
    """
    
    # Convert string to logging level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Configure root logger
    logging.basicConfig(
        level=numeric_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            # Console handler
            logging.StreamHandler(sys.stdout),
            # File handler
            logging.FileHandler(log_file, mode='a')
        ]
    )
    
    # Set specific log levels for noisy libraries
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("deep_sort_realtime").setLevel(logging.WARNING)
    
    # Set our application loggers
    logging.getLogger("services").setLevel(numeric_level)
    logging.getLogger("routes").setLevel(numeric_level)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured at {log_level} level")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name
    
    Args:
        name: Name of the logger (usually __name__)
    
    Returns:
        Logger instance
    """
    return logging.getLogger(name)
