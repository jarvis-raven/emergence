"""
Nautilus Logging Configuration

Centralized logging setup for all Nautilus modules with:
- Configurable log levels via NAUTILUS_LOG_LEVEL environment variable
- File logging to ~/.openclaw/state/nautilus/nautilus.log
- Console logging for CLI usage
- Structured logging with JSON format option
"""

import logging
import os
import sys
from pathlib import Path
from typing import Optional
from logging.handlers import RotatingFileHandler

# Default log level
DEFAULT_LOG_LEVEL = "INFO"

# Log format strings
CONSOLE_FORMAT = "%(levelname)s: %(message)s"
FILE_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
DEBUG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s"

# Max log file size: 10MB
MAX_LOG_FILE_SIZE = 10 * 1024 * 1024
# Keep 5 backup files
BACKUP_COUNT = 5


def get_log_level() -> int:
    """
    Get configured log level from environment variable.
    
    Returns:
        Logging level constant (DEBUG, INFO, WARN, ERROR).
    """
    level_name = os.environ.get("NAUTILUS_LOG_LEVEL", DEFAULT_LOG_LEVEL).upper()
    
    level_map = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARN": logging.WARNING,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL,
    }
    
    return level_map.get(level_name, logging.INFO)


def get_log_file_path() -> Path:
    """
    Get the log file path.
    
    Returns:
        Path to the nautilus.log file.
    """
    # Default state directory (avoid circular import with config)
    state_dir = Path.home() / ".openclaw" / "state" / "nautilus"
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        # Fallback to temp directory if home not writable
        import tempfile
        state_dir = Path(tempfile.gettempdir()) / "nautilus"
        state_dir.mkdir(parents=True, exist_ok=True)
    
    return state_dir / "nautilus.log"


def setup_logging(
    name: Optional[str] = None,
    console: bool = True,
    file_logging: bool = True,
    force: bool = False
) -> logging.Logger:
    """
    Configure logging for Nautilus modules.
    
    Args:
        name: Logger name (defaults to 'nautilus')
        console: Enable console logging
        file_logging: Enable file logging
        force: Force reconfiguration even if already set up
        
    Returns:
        Configured logger instance.
    """
    logger_name = name or "nautilus"
    logger = logging.getLogger(logger_name)
    
    # Skip if already configured (unless forced)
    if logger.handlers and not force:
        return logger
    
    # Remove existing handlers if forcing reconfiguration
    if force:
        logger.handlers.clear()
    
    log_level = get_log_level()
    logger.setLevel(log_level)
    
    # Determine format based on log level
    if log_level == logging.DEBUG:
        console_fmt = DEBUG_FORMAT
    else:
        console_fmt = CONSOLE_FORMAT
    
    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setLevel(log_level)
        console_formatter = logging.Formatter(console_fmt)
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)
    
    # File handler with rotation
    if file_logging:
        try:
            log_file = get_log_file_path()
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=MAX_LOG_FILE_SIZE,
                backupCount=BACKUP_COUNT,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.DEBUG)  # Always log DEBUG+ to file
            file_formatter = logging.Formatter(FILE_FORMAT)
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            # Fallback: log to console only if file logging fails
            logger.warning(f"Could not set up file logging: {e}")
    
    # Don't propagate to root logger
    logger.propagate = False
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger for a specific Nautilus module.
    
    Args:
        name: Module name (e.g., 'nautilus.gravity')
        
    Returns:
        Configured logger instance.
    """
    # Ensure parent logger is configured
    if not logging.getLogger("nautilus").handlers:
        setup_logging("nautilus")
    
    return logging.getLogger(f"nautilus.{name}")


# Auto-configure on import
_root_logger = setup_logging("nautilus", console=False, file_logging=True)
