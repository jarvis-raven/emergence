"""File-based drive satisfaction checker.

Replaces the broken cron-API-based _check_completed_sessions().
Uses breadcrumb files in sessions_ingest/ to track spawned sessions
and determine when they complete.

Architecture:
    spawn_session() writes breadcrumb → sessions_ingest/
    tick scans sessions_ingest/ → checks completion → satisfies drive
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import DriveState


def get_ingest_dir() -> Path:
    """Get the sessions_ingest directory path.
    
    Returns:
        Path to sessions_ingest directory
        
    Examples:
        >>> p = get_ingest_dir()
        >>> p.name
        'sessions_ingest'
    """
    state_dir = os.environ.get("EMERGENCE_STATE", 
                               str(Path.home() / ".openclaw" / "state"))
    ingest_dir = Path(state_dir) / "sessions_ingest"
    ingest_dir.mkdir(parents=True, exist_ok=True)
    return ingest_dir


def write_breadcrumb(
    drive_name: str,
    session_key: str,
    timeout_seconds: int = 300
) -> Path:
    """Write a breadcrumb file when a drive session is spawned.
    
    Uses atomic write (temp file + rename) to prevent race conditions
    with the tick scanner.
    
    Args:
        drive_name: Name of the drive (e.g., "CREATIVE")
        session_key: OpenClaw session key for the spawned session
        timeout_seconds: Max expected session duration
        
    Returns:
        Path to the written breadcrumb file
        
    Examples:
        >>> p = write_breadcrumb("CREATIVE", "agent:main:cron:abc123", 300)
        >>> p.suffix
        '.json'
        >>> "CREATIVE" in p.name
        True
    """
    ingest_dir = get_ingest_dir()
    timestamp = int(time.time())
    filename = f"{timestamp}-{drive_name}.json"
    filepath = ingest_dir / filename
    tmp_path = ingest_dir / f".tmp-{filename}"
    
    breadcrumb = {
        "drive": drive_name,
        "spawned_at": datetime.now(timezone.utc).isoformat(),
        "spawned_epoch": timestamp,
        "session_key": session_key,
        "timeout_seconds": timeout_seconds,
    }
    
    # Atomic write: write to temp, then rename
    try:
        tmp_path.write_text(json.dumps(breadcrumb, indent=2))
        tmp_path.rename(filepath)
    except OSError:
        # Fallback: direct write
        filepath.write_text(json.dumps(breadcrumb, indent=2))
    
    return filepath


def write_completion(drive_name: str, session_key: Optional[str] = None, status: str = "completed") -> Path:
    """Write a completion breadcrumb when a drive session finishes.
    
    Called by the session itself (via drive prompt instructions) or by
    the main session when it receives a sub-agent completion announce.
    
    Args:
        drive_name: Name of the drive (e.g., "CREATIVE")
        session_key: OpenClaw session key (optional - matches on drive name if not provided)
        status: Completion status ("completed", "error", "timeout")
        
    Returns:
        Path to the written completion file
        
    Examples:
        >>> p = write_completion("CREATIVE")
        >>> "COMPLETE" in p.name
        True
    """
    ingest_dir = get_ingest_dir()
    timestamp = int(time.time())
    filename = f"COMPLETE-{timestamp}-{drive_name}.json"
    filepath = ingest_dir / filename
    
    completion = {
        "drive": drive_name,
        "session_key": session_key,
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "completed_epoch": timestamp,
        "status": status,
    }
    
    try:
        tmp_path = ingest_dir / f".tmp-{filename}"
        tmp_path.write_text(json.dumps(completion, indent=2))
        tmp_path.rename(filepath)
    except OSError:
        filepath.write_text(json.dumps(completion, indent=2))
    
    return filepath


def assess_depth(breadcrumb: dict) -> str:
    """Assess satisfaction depth for a completed session.
    
    Deterministic assessment based on observable signals:
    - shallow: session errored or timed out
    - moderate: session completed normally
    - deep: session completed AND wrote files
    
    Args:
        breadcrumb: Parsed breadcrumb dict with spawn info
        
    Returns:
        Depth string: "shallow", "moderate", or "deep"
        
    Examples:
        >>> assess_depth({"spawned_epoch": 0, "timeout_seconds": 300, "timed_out": True})
        'shallow'
    """
    # Check if session timed out (age > timeout × 2)
    if breadcrumb.get("timed_out", False):
        return "shallow"
    
    spawn_epoch = breadcrumb.get("spawned_epoch", 0)
    timeout = breadcrumb.get("timeout_seconds", 300)
    
    if spawn_epoch > 0 and (time.time() - spawn_epoch) > (timeout * 2):
        return "shallow"  # Likely timed out or stuck
    
    # Check if the session wrote any files since spawn
    if _check_file_writes(spawn_epoch):
        return "deep"
    
    return "moderate"


def _check_file_writes(since_epoch: int) -> bool:
    """Check if any memory/identity files were modified since the given time.
    
    Recursively checks subdirectories of memory/ to catch session logs,
    daily notes, and other files in nested directories.
    
    Args:
        since_epoch: Unix timestamp to check modifications after
        
    Returns:
        True if relevant files were modified
        
    Examples:
        >>> _check_file_writes(0)  # epoch 0 = everything is newer
        True
    """
    workspace = os.environ.get("EMERGENCE_WORKSPACE",
                               str(Path.home() / ".openclaw" / "workspace"))
    workspace = Path(workspace)
    
    check_paths = [
        workspace / "memory",
        workspace / "ASPIRATIONS.md",
        workspace / "INTERESTS.md",
        workspace / "SELF.md",
    ]
    
    def _check_recursive(path: Path) -> bool:
        """Recursively check a directory tree for modified files."""
        try:
            for item in path.iterdir():
                if item.is_file():
                    try:
                        if item.stat().st_mtime > since_epoch:
                            return True
                    except OSError:
                        continue
                elif item.is_dir():
                    # Recurse into subdirectories
                    if _check_recursive(item):
                        return True
        except OSError:
            return False
        return False
    
    for check_path in check_paths:
        if check_path.is_file():
            try:
                if check_path.stat().st_mtime > since_epoch:
                    return True
            except OSError:
                continue
        elif check_path.is_dir():
            if _check_recursive(check_path):
                return True
    
    return False


def _is_session_complete(drive_name: str, session_key: str, timeout_seconds: int, spawn_epoch: int) -> Optional[bool]:
    """Check if a session has completed.
    
    Uses a breadcrumb-first approach:
    1. Check for COMPLETE-*.json files matching this drive — instant detection
    2. Fall back to time-based if no completion breadcrumb found (crash/timeout)
    
    Args:
        drive_name: Name of the drive (used for matching completion breadcrumbs)
        session_key: OpenClaw session key (optional match)
        timeout_seconds: Configured timeout for the session
        spawn_epoch: When the session was spawned
        
    Returns:
        True if complete, False if still running, None if unknown
        
    Examples:
        >>> _is_session_complete("CREATIVE", "key", 300, time.time() - 30)
        False
    """
    # Check for completion breadcrumb first (instant satisfaction)
    ingest_dir = get_ingest_dir()
    try:
        for f in ingest_dir.glob("COMPLETE-*.json"):
            try:
                data = json.loads(f.read_text())
                # Match on drive name (primary) or session_key (secondary)
                if data.get("drive") == drive_name:
                    return True
                if session_key and data.get("session_key") == session_key:
                    return True
            except (json.JSONDecodeError, OSError):
                continue
    except OSError:
        pass
    
    # Fallback: time-based estimation (handles crashes, forgotten completions)
    age = time.time() - spawn_epoch
    
    # If well past timeout, definitely done (completed or died)
    if age > timeout_seconds + 60:
        return True
    
    # Too early to tell without a completion breadcrumb
    if age < timeout_seconds:
        return None
    
    return None  # Between timeout and timeout+60 — still uncertain


def check_completed_sessions(state: DriveState, config: dict) -> list[str]:
    """Scan sessions_ingest/ for completed drive sessions and satisfy them.
    
    This is the main entry point called by the tick cycle.
    
    Args:
        state: Current drive state (modified in place)
        config: Configuration dict
        
    Returns:
        List of drive names that were satisfied
        
    Examples:
        >>> state = {"drives": {}, "triggered_drives": []}
        >>> satisfied = check_completed_sessions(state, {})
        >>> isinstance(satisfied, list)
        True
    """
    from .engine import satisfy_drive
    
    ingest_dir = get_ingest_dir()
    satisfied = []
    
    # Scan for breadcrumb files
    try:
        breadcrumb_files = sorted(ingest_dir.glob("*.json"))
    except OSError:
        return satisfied
    
    for bc_path in breadcrumb_files:
        # Skip temp files and completion markers (those are read by _is_session_complete)
        if bc_path.name.startswith(".tmp-") or bc_path.name.startswith("COMPLETE-"):
            continue
        
        try:
            breadcrumb = json.loads(bc_path.read_text())
        except (json.JSONDecodeError, OSError):
            # Corrupted breadcrumb — remove it
            try:
                bc_path.unlink()
            except OSError:
                pass
            continue
        
        drive_name = breadcrumb.get("drive", "")
        session_key = breadcrumb.get("session_key", "")
        timeout = breadcrumb.get("timeout_seconds", 300)
        spawn_epoch = breadcrumb.get("spawned_epoch", 0)
        
        # Check if session is complete
        complete = _is_session_complete(drive_name, session_key, timeout, spawn_epoch)
        
        if complete is None:
            continue  # Can't tell yet, try next tick
        
        if complete:
            # Assess satisfaction depth
            depth = assess_depth(breadcrumb)
            
            # Satisfy the drive
            try:
                satisfy_drive(state, drive_name, depth=depth)
                satisfied.append(drive_name)
            except (KeyError, ValueError):
                # Drive doesn't exist — just clean up
                satisfied.append(drive_name)
            
            # Remove from triggered list
            triggered = state.get("triggered_drives", [])
            if drive_name in triggered:
                state["triggered_drives"] = [
                    d for d in triggered if d != drive_name
                ]
            
            # Clean up spawn breadcrumb
            try:
                bc_path.unlink()
            except OSError:
                pass
            
            # Clean up matching completion breadcrumb(s)
            try:
                for cf in ingest_dir.glob("COMPLETE-*.json"):
                    try:
                        cdata = json.loads(cf.read_text())
                        # Match on drive name (primary) or session_key (secondary)
                        if cdata.get("drive") == drive_name or cdata.get("session_key") == session_key:
                            cf.unlink()
                    except (json.JSONDecodeError, OSError):
                        pass
            except OSError:
                pass
    
    # Clean up orphaned completion breadcrumbs (no matching spawn breadcrumb, older than 1 hour)
    try:
        for cf in ingest_dir.glob("COMPLETE-*.json"):
            try:
                cdata = json.loads(cf.read_text())
                age = time.time() - cdata.get("completed_epoch", 0)
                if age > 3600:
                    cf.unlink()
            except (json.JSONDecodeError, OSError):
                try:
                    cf.unlink()
                except OSError:
                    pass
    except OSError:
        pass
    
    return satisfied
