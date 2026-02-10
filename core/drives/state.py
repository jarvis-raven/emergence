"""State persistence for the drive engine.

Provides atomic read/write operations for drives.json state file.
Uses write-to-temp-then-rename pattern for crash safety.
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import DriveState, create_default_state, validate_drive, ensure_drive_defaults


def load_state(state_path: Path) -> DriveState:
    """Load drive state from JSON file.
    
    Returns empty default state if file doesn't exist.
    Validates state structure on load.
    
    Args:
        state_path: Path to the state JSON file
        
    Returns:
        DriveState dictionary with loaded or default values
        
    Raises:
        SystemExit: If state file exists but is corrupted JSON
        
    Examples:
        >>> state = load_state(Path(".emergence/state/drives.json"))
        >>> "drives" in state
        True
    """
    if not state_path.exists():
        # Return fresh default state
        return create_default_state()
    
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"State file corrupted: {state_path}", file=sys.stderr)
        print(f"  Error: {e}", file=sys.stderr)
        print("  Options:", file=sys.stderr)
        print("    1. Fix the JSON manually", file=sys.stderr)
        print(f"    2. Reset: mv '{state_path}' '{state_path}.bak'", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading state file: {e}", file=sys.stderr)
        return create_default_state()
    
    # Validate minimal structure
    if "version" not in data:
        data["version"] = "1.0"
    if "drives" not in data:
        data["drives"] = {}
    if "triggered_drives" not in data:
        data["triggered_drives"] = []
    if "last_tick" not in data:
        data["last_tick"] = datetime.now(timezone.utc).isoformat()
    
    # Apply defaults to existing drives for backwards compatibility
    for name, drive in list(data["drives"].items()):
        data["drives"][name] = ensure_drive_defaults(drive)
    
    # Validate individual drives
    invalid_drives = []
    for name, drive in list(data["drives"].items()):
        errors = validate_drive(drive)
        if errors:
            invalid_drives.append(f"{name}: {'; '.join(errors)}")
    
    if invalid_drives:
        print("Warning: Some drives have validation errors:", file=sys.stderr)
        for error in invalid_drives:
            print(f"  - {error}", file=sys.stderr)
    
    return data


def save_state(state_path: Path, state: DriveState, backup: bool = True) -> None:
    """Atomically save drive state to JSON file.
    
    Writes to a temporary file first, then renames for atomicity.
    This ensures state is never partially written.
    
    Args:
        state_path: Target path for the state file
        state: DriveState dictionary to save
        backup: If True, create .bak backup before overwriting
        
    Raises:
        IOError: If write fails (permissions, disk full, etc.)
        
    Examples:
        >>> state = create_default_state()
        >>> save_state(Path("drives.json"), state)
    """
    # Ensure parent directory exists
    state_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Update timestamp
    state["last_tick"] = datetime.now(timezone.utc).isoformat()
    
    # Create backup if requested and target exists
    if backup and state_path.exists():
        backup_path = state_path.with_suffix(".json.bak")
        try:
            # Copy contents to backup
            with open(state_path, "r", encoding="utf-8") as src:
                with open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
        except IOError:
            # Backup failure shouldn't prevent save
            pass
    
    # Write to temp file in same directory (for atomic rename)
    temp_path = state_path.with_suffix(".tmp")
    
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        temp_path.rename(state_path)
        
    except Exception:
        # Clean up temp file on failure
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def get_hours_since_tick(state: DriveState) -> float:
    """Calculate hours elapsed since last tick.
    
    Args:
        state: Current drive state with last_tick timestamp
        
    Returns:
        Hours elapsed as float (can be 0.0 or negative on error)
        
    Examples:
        >>> state = {"last_tick": "2026-02-07T10:00:00+00:00"}
        >>> hours = get_hours_since_tick(state)  # If current time is 12:00
        >>> hours >= 2.0
        True
    """
    last_tick_str = state.get("last_tick", "")
    if not last_tick_str:
        return 0.0
    
    try:
        last_tick = datetime.fromisoformat(last_tick_str)
        now = datetime.now(timezone.utc)
        elapsed = (now - last_tick).total_seconds() / 3600
        return max(0.0, elapsed)
    except (ValueError, TypeError):
        return 0.0


def is_state_locked(state_path: Path) -> Optional[int]:
    """Check if state file is locked by another process.
    
    This is a lightweight check using a lock file mechanism.
    Not foolproof but helps detect concurrent access.
    
    Args:
        state_path: Path to the state file
        
    Returns:
        PID of locking process if locked, None otherwise
        
    Note:
        This is advisory locking only — not enforced at OS level
    """
    lock_path = state_path.with_suffix(".lock")
    
    if not lock_path.exists():
        return None
    
    try:
        with open(lock_path, "r", encoding="utf-8") as f:
            pid_str = f.read().strip()
            pid = int(pid_str)
        
        # Check if process still exists (Unix only)
        try:
            os.kill(pid, 0)
            return pid
        except OSError:
            # Process dead, stale lock
            lock_path.unlink()
            return None
            
    except (ValueError, IOError, OSError):
        # Lock file corrupted, remove it
        try:
            lock_path.unlink()
        except OSError:
            pass
        return None


def acquire_lock(state_path: Path) -> bool:
    """Acquire advisory lock on state file.
    
    Args:
        state_path: Path to the state file
        
    Returns:
        True if lock acquired, False otherwise
    """
    lock_path = state_path.with_suffix(".lock")
    
    # Check existing lock
    existing = is_state_locked(state_path)
    if existing:
        return False
    
    try:
        with open(lock_path, "w", encoding="utf-8") as f:
            f.write(str(os.getpid()))
        return True
    except IOError:
        return False


def release_lock(state_path: Path) -> None:
    """Release advisory lock on state file.
    
    Args:
        state_path: Path to the state file
    """
    lock_path = state_path.with_suffix(".lock")
    
    try:
        if lock_path.exists():
            lock_path.unlink()
    except OSError:
        pass


class StateLock:
    """Context manager for state file locking.
    
    Use this to safely lock state during read-modify-write operations:
    
    Examples:
        >>> with StateLock(state_path, timeout=3.0) as lock:
        ...     if lock.acquired:
        ...         state = load_state(state_path)
        ...         # modify state
        ...         save_state(state_path, state)
    """
    
    def __init__(self, state_path: Path, timeout: float = 0.0):
        self.state_path = state_path
        self.timeout = timeout
        self.acquired = False
    
    def __enter__(self):
        import time
        
        start = time.time()
        while True:
            if acquire_lock(self.state_path):
                self.acquired = True
                return self
            
            if self.timeout <= 0:
                return self
            
            if time.time() - start >= self.timeout:
                return self
            
            time.sleep(0.1)
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.acquired:
            release_lock(self.state_path)
        return False
