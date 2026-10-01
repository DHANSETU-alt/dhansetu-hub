"""
Logging setup for research and publishing jobs.

Writes to research_job_log table and optional file logs.
"""

import logging
import logging.handlers
from pathlib import Path

from .. import config

# Setup file logging
LOG_DIR = config.ROOT / "logs" / "research"
LOG_DIR.mkdir(parents=True, exist_ok=True)

def get_logger(name: str) -> logging.Logger:
    """Get configured logger for job modules."""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # File handler
    log_file = LOG_DIR / f"{name.split('.')[-1]}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
