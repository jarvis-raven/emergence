"""
Nautilus Database Utilities

Provides robust database operations with:
- SQLite lock retry logic (3x with exponential backoff)
- Error handling and recovery suggestions
- Connection pooling helpers
"""

import sqlite3
import time
import functools
from typing import TypeVar, Callable, Any, Optional
from pathlib import Path

from .logging_config import get_logger

logger = get_logger("db_utils")

# Retry configuration
MAX_RETRIES = 3
INITIAL_BACKOFF_MS = 100
BACKOFF_MULTIPLIER = 2

T = TypeVar('T')


class DatabaseError(Exception):
    """Base exception for database errors with actionable messages."""
    pass


class DatabaseLockError(DatabaseError):
    """Database is locked and retries exhausted."""
    pass


class DatabaseCorruptionError(DatabaseError):
    """Database file appears to be corrupted."""
    pass


def with_retry(func: Callable[..., T]) -> Callable[..., T]:
    """
    Decorator to retry database operations on lock errors.
    
    Implements exponential backoff:
    - 1st retry after 100ms
    - 2nd retry after 200ms
    - 3rd retry after 400ms
    
    Args:
        func: Function to wrap with retry logic
        
    Returns:
        Wrapped function with retry behavior
        
    Raises:
        DatabaseLockError: If all retries are exhausted
        DatabaseCorruptionError: If database appears corrupted
        DatabaseError: For other database errors
    """
    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        backoff_ms = INITIAL_BACKOFF_MS
        last_error: Optional[Exception] = None
        
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except sqlite3.OperationalError as e:
                last_error = e
                error_msg = str(e).lower()
                
                # Check for database locked error
                if "locked" in error_msg:
                    if attempt < MAX_RETRIES - 1:
                        logger.warning(
                            f"Database locked on attempt {attempt + 1}/{MAX_RETRIES}, "
                            f"retrying in {backoff_ms}ms..."
                        )
                        time.sleep(backoff_ms / 1000.0)
                        backoff_ms *= BACKOFF_MULTIPLIER
                        continue
                    else:
                        # All retries exhausted
                        logger.error(
                            f"Database lock timeout after {MAX_RETRIES} attempts. "
                            "Another process may be holding a long transaction."
                        )
                        raise DatabaseLockError(
                            f"Database is locked after {MAX_RETRIES} retry attempts. "
                            "Try again in a few seconds, or check for other processes "
                            "accessing the database."
                        ) from e
                
                # Check for corruption
                elif "malformed" in error_msg or "corrupt" in error_msg:
                    logger.error(f"Database corruption detected: {e}")
                    raise DatabaseCorruptionError(
                        "Database file appears to be corrupted. "
                        "Try running: sqlite3 <db_path> 'PRAGMA integrity_check;' "
                        "You may need to restore from backup or rebuild the database."
                    ) from e
                
                # Other operational errors
                else:
                    logger.error(f"Database operational error: {e}")
                    raise DatabaseError(f"Database error: {e}") from e
            
            except sqlite3.DatabaseError as e:
                logger.error(f"Database error: {e}")
                raise DatabaseError(f"Database error: {e}") from e
        
        # Should never reach here, but just in case
        if last_error:
            raise DatabaseError(f"Unexpected retry failure: {last_error}") from last_error
        
        return func(*args, **kwargs)  # Final attempt
    
    return wrapper


def execute_with_retry(
    conn: sqlite3.Connection,
    query: str,
    params: tuple = ()
) -> sqlite3.Cursor:
    """
    Execute a query with retry logic.
    
    Args:
        conn: Database connection
        query: SQL query string
        params: Query parameters
        
    Returns:
        Cursor with query results
        
    Raises:
        DatabaseLockError: If database is locked after retries
        DatabaseError: For other database errors
    """
    @with_retry
    def _execute() -> sqlite3.Cursor:
        return conn.execute(query, params)
    
    return _execute()


def safe_connect(
    db_path: Path,
    timeout: float = 5.0,
    check_same_thread: bool = False
) -> sqlite3.Connection:
    """
    Safely connect to a database with error handling.
    
    Args:
        db_path: Path to database file
        timeout: Connection timeout in seconds
        check_same_thread: SQLite same_thread check
        
    Returns:
        Database connection
        
    Raises:
        DatabaseError: If connection fails
    """
    try:
        # Ensure parent directory exists
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"Connecting to database: {db_path}")
        
        conn = sqlite3.connect(
            str(db_path),
            timeout=timeout,
            check_same_thread=check_same_thread
        )
        conn.row_factory = sqlite3.Row
        
        # Enable WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode=WAL")
        
        # Verify connection is working
        conn.execute("SELECT 1").fetchone()
        
        logger.debug(f"Successfully connected to {db_path}")
        return conn
        
    except sqlite3.OperationalError as e:
        error_msg = str(e).lower()
        
        if "unable to open database" in error_msg:
            logger.error(f"Cannot open database file: {db_path}")
            raise DatabaseError(
                f"Cannot open database file: {db_path}\n"
                f"Check that the path is correct and you have write permissions."
            ) from e
        
        elif "malformed" in error_msg or "corrupt" in error_msg:
            logger.error(f"Database is corrupted: {db_path}")
            raise DatabaseCorruptionError(
                f"Database file is corrupted: {db_path}\n"
                f"Try running: sqlite3 {db_path} 'PRAGMA integrity_check;'\n"
                f"You may need to restore from backup or rebuild."
            ) from e
        
        else:
            logger.error(f"Database connection error: {e}")
            raise DatabaseError(f"Database connection error: {e}") from e
    
    except Exception as e:
        logger.error(f"Unexpected error connecting to database: {e}")
        raise DatabaseError(f"Unexpected database error: {e}") from e


def commit_with_retry(conn: sqlite3.Connection) -> None:
    """
    Commit a transaction with retry logic.
    
    Args:
        conn: Database connection
        
    Raises:
        DatabaseLockError: If commit fails due to lock
        DatabaseError: For other errors
    """
    @with_retry
    def _commit() -> None:
        conn.commit()
    
    _commit()
