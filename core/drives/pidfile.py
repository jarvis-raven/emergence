from typing import Optional

"""PID file management for the drive daemon.

Provides atomic PID file operations for singleton enforcement and
daemon lifecycle management.
"""

import os
from pathlib import Path


def write_pid(path: Path) -> bool:
    """Write current PID to file atomically.

    Uses write-to-temp-then-rename pattern for atomicity.

    Args:
        path: Path to the PID file

    Returns:
        True if PID was written successfully

    Raises:
        IOError: If write fails due to permissions or disk issues

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     pid_path = Path(tmp) / "test.pid"
        ...     write_pid(pid_path)
        ...     read_pid(pid_path) == os.getpid()
        True
    """
    # Ensure parent directory exists
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to temp file in same directory
    temp_path = path.with_suffix(".tmp")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))

        # Atomic rename
        temp_path.rename(path)
        return True

    except Exception:
        # Clean up temp file on failure
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def read_pid(path: Path) -> Optional[int]:
    """Read PID from file and validate it's a running process.

    Args:
        path: Path to the PID file

    Returns:
        The PID if file exists and contains valid PID, None otherwise

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     pid_path = Path(tmp) / "test.pid"
        ...     read_pid(pid_path) is None
        True
    """
    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().strip()

        if not content:
            return None

        pid = int(content)

        # Validate PID is positive
        if pid <= 0:
            return None

        return pid

    except (ValueError, IOError, OSError):
        return None


def remove_pid(path: Path) -> bool:
    """Remove PID file if it exists.

    Args:
        path: Path to the PID file

    Returns:
        True if file was removed or didn't exist, False on error

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     pid_path = Path(tmp) / "test.pid"
        ...     write_pid(pid_path)
        ...     remove_pid(pid_path)
        ...     pid_path.exists()
        False
    """
    try:
        if path.exists():
            path.unlink()
        return True
    except OSError:
        return False


def is_process_alive(pid: int) -> bool:
    """Check if a process with given PID is currently running.

    Uses Unix kill(0) which checks if signal can be sent without
    actually sending any signal.

    Args:
        pid: Process ID to check

    Returns:
        True if process exists, False otherwise

    Examples:
        >>> is_process_alive(os.getpid())  # Current process
        True
        >>> is_process_alive(99999999)  # Invalid PID
        False
    """
    if pid <= 0:
        return False

    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def is_running(path: Path) -> tuple:
    """Check if daemon is running by reading PID file and checking process.

    Also cleans up stale PID files (process no longer exists).

    Args:
        path: Path to the PID file

    Returns:
        Tuple of (is_running, pid) where is_running is True if daemon
        is confirmed running, and pid is the process ID or None

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     pid_path = Path(tmp) / "test.pid"
        ...     running, pid = is_running(pid_path)
        ...     running
        False
    """
    pid = read_pid(path)

    if pid is None:
        return False, None

    if is_process_alive(pid):
        return True, pid

    # Stale PID file - clean it up
    remove_pid(path)
    return False, None


def acquire_pidfile(path: Path) -> tuple:
    """Attempt to acquire exclusive PID file ownership.

    Checks if another daemon is running and writes our PID if not.

    Args:
        path: Path to the PID file

    Returns:
        Tuple of (success, existing_pid) where success is True if we
        acquired the lock, and existing_pid is the blocking PID if failed

    Examples:
        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as tmp:
        ...     pid_path = Path(tmp) / "test.pid"
        ...     acquired, blocking = acquire_pidfile(pid_path)
        ...     acquired
        True
    """
    running, existing_pid = is_running(path)

    if running and existing_pid is not None:
        if existing_pid != os.getpid():
            return False, existing_pid

    # Write our PID
    try:
        write_pid(path)
        return True, None
    except IOError:
        return False, None
