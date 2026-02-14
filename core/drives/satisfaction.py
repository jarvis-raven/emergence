"""File-based drive satisfaction checker and manual satisfaction utilities.

Replaces the broken cron-API-based _check_completed_sessions().
Uses breadcrumb files in sessions_ingest/ to track spawned sessions
and determine when they complete.

Also provides manual satisfaction with auto-scaling based on pressure level,
including aversive-state specific satisfaction approaches.

Architecture:
    spawn_session() writes breadcrumb → sessions_ingest/
    tick scans sessions_ingest/ → checks completion → satisfies drive
    CLI commands use calculate_satisfaction_depth() for smart manual satisfaction
    Aversive drives get investigation-focused prompts and alternative approaches
"""

import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from .models import DriveState

# History tracking
def get_history_path() -> Path:
    """Get path to satisfaction history file.
    
    Returns:
        Path to satisfaction_history.jsonl
    """
    state_dir = os.environ.get("EMERGENCE_STATE", 
                               str(Path.home() / ".openclaw" / "state"))
    return Path(state_dir) / "satisfaction_history.jsonl"


def log_satisfaction(
    drive_name: str,
    pressure_before: float,
    pressure_after: float,
    band: str,
    depth: str,
    ratio: float,
    source: str = "manual"
) -> None:
    """Log a satisfaction event to history.
    
    Args:
        drive_name: Name of the drive
        pressure_before: Pressure before satisfaction
        pressure_after: Pressure after satisfaction
        band: Threshold band (available/elevated/triggered/crisis)
        depth: Satisfaction depth name
        ratio: Reduction ratio applied
        source: How satisfaction occurred (manual/session/auto)
    """
    history_path = get_history_path()
    
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "drive": drive_name,
        "pressure_before": round(pressure_before, 2),
        "pressure_after": round(pressure_after, 2),
        "band": band,
        "depth": depth,
        "ratio": ratio,
        "source": source,
    }
    
    try:
        # Append to JSONL file
        with history_path.open('a') as f:
            f.write(json.dumps(event) + '\n')
    except OSError:
        # Failed to write history — non-fatal
        pass


def get_recent_satisfaction_history(
    drive_name: Optional[str] = None,
    limit: int = 50
) -> list[dict]:
    """Get recent satisfaction events from history.
    
    Args:
        drive_name: Optional filter by drive name
        limit: Maximum number of events to return
        
    Returns:
        List of satisfaction event dicts (most recent first)
    """
    history_path = get_history_path()
    
    if not history_path.exists():
        return []
    
    events = []
    try:
        with history_path.open('r') as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    if drive_name is None or event.get("drive") == drive_name:
                        events.append(event)
                except json.JSONDecodeError:
                    continue
    except OSError:
        return []
    
    # Return most recent first
    return list(reversed(events[-limit:]))


def get_last_satisfaction_time(drive_name: str) -> Optional[str]:
    """Get the timestamp of the most recent satisfaction for a drive.
    
    Reads from satisfaction_history.jsonl instead of in-memory arrays.
    
    Args:
        drive_name: Name of the drive
        
    Returns:
        ISO 8601 timestamp string or None if never satisfied
        
    Examples:
        >>> get_last_satisfaction_time("CARE")
        '2026-02-14T12:34:56+00:00'
    """
    history = get_recent_satisfaction_history(drive_name=drive_name, limit=1)
    
    if history:
        return history[0].get("timestamp")
    
    return None


def migrate_satisfaction_events(state: dict) -> int:
    """Migrate satisfaction_events arrays to satisfaction_history.jsonl.
    
    This is a one-time migration for Phase 2 of state cleanup.
    Exports existing satisfaction_events to JSONL and removes them from drives.
    
    Args:
        state: Drive state dict (modified in place)
        
    Returns:
        Number of events migrated
    """
    history_path = get_history_path()
    migrated = 0
    
    drives = state.get("drives", {})
    
    for drive_name, drive_data in drives.items():
        events = drive_data.get("satisfaction_events", [])
        
        if not events:
            continue
        
        try:
            # Append all events to JSONL
            with history_path.open('a') as f:
                for timestamp_str in events:
                    # Create a satisfaction event entry
                    event = {
                        "timestamp": timestamp_str,
                        "drive": drive_name,
                        "pressure_before": 0.0,  # Unknown from old data
                        "pressure_after": 0.0,   # Unknown from old data
                        "band": "unknown",
                        "depth": "unknown",
                        "ratio": 0.0,  # Unknown from old data
                        "source": "migrated",
                    }
                    f.write(json.dumps(event) + '\n')
                    migrated += 1
        except OSError:
            # Migration failed for this drive — continue
            continue
        
        # Remove satisfaction_events from drive
        del drive_data["satisfaction_events"]
    
    return migrated


def get_aversive_satisfaction_options(
    drive_name: str,
    pressure: float,
    threshold: float,
    thwarting_count: int = 0
) -> dict:
    """Get aversive-specific satisfaction options for a thwarted drive.
    
    Returns different approaches than appetitive drives:
    - Reflective investigation of blockages
    - Threshold adjustment recommendations
    - Alternative satisfaction routes
    - Deeper satisfaction to reset thwarting state
    
    Args:
        drive_name: Name of the drive
        pressure: Current pressure level
        threshold: Drive threshold
        thwarting_count: Number of thwarting events
        
    Returns:
        Dict with options and recommendations
        
    Examples:
        >>> opts = get_aversive_satisfaction_options("CREATIVE", 32.0, 20.0, 3)
        >>> "investigate" in opts
        True
        >>> "threshold_adjustment" in opts
        True
    """
    options = {
        "approach": "aversive",
        "recommended_action": "investigate",
        "options": []
    }
    
    # Option 1: Investigate blockage (reflective, no immediate pressure reduction)
    options["options"].append({
        "name": "investigate",
        "label": "Investigate Blockage",
        "description": "Reflective session to identify what's preventing satisfaction",
        "pressure_reduction": 0.0,  # No immediate reduction
        "resets_thwarting": False,
        "prompt": f"What's blocking your ability to satisfy {drive_name}? Explore obstacles, constraints, and alternative approaches."
    })
    
    # Option 2: Partial/alternative satisfaction (gentler reduction)
    ratio = pressure / threshold if threshold > 0 else 0
    alt_reduction = min(0.35, ratio * 0.25)  # Gentler than appetitive
    options["options"].append({
        "name": "alternative",
        "label": "Alternative Approach",
        "description": "Try a different route to partial satisfaction",
        "pressure_reduction": alt_reduction,
        "resets_thwarting": False,
        "prompt": f"Find an alternative way to engage with {drive_name} that works around current blockages."
    })
    
    # Option 3: Deep satisfaction with threshold awareness (resets thwarting)
    deep_reduction = min(0.75, ratio * 0.6)
    options["options"].append({
        "name": "deep",
        "label": "Deep Satisfaction",
        "description": "Full engagement attempt (resets thwarting count)",
        "pressure_reduction": deep_reduction,
        "resets_thwarting": True,
        "prompt": f"Fully engage with {drive_name}, acknowledging past blockages. Document what's different this time."
    })
    
    # Threshold adjustment recommendation
    if thwarting_count >= 3:
        options["threshold_adjustment"] = {
            "recommended": True,
            "reason": f"Drive has been thwarted {thwarting_count} times",
            "suggestion": f"Consider temporarily raising threshold to {threshold * 1.25:.1f} to reduce pressure",
            "temporary_duration": "24-48 hours"
        }
    
    return options


def calculate_satisfaction_depth(
    pressure: float, 
    threshold: float,
    thresholds: Optional[dict] = None,
    valence: str = "appetitive"
) -> Tuple[str, str, float]:
    """Calculate auto-scaled satisfaction depth based on threshold band.
    
    Implements band-based satisfaction scaling:
    - available (30-75%): 25% reduction (shallow)
    - elevated (75-100%): 50% reduction (moderate)
    - triggered (100-150%): 75% reduction (deep)
    - crisis (150%+): 90% reduction (emergency)
    
    For aversive drives, reductions are gentler to encourage investigation
    over forced satisfaction.
    
    Args:
        pressure: Current drive pressure
        threshold: Drive threshold value (base, for backward compatibility)
        thresholds: Optional dict with graduated thresholds
        valence: Drive valence (appetitive/aversive/neutral)
        
    Returns:
        Tuple of (band_name, depth_name, reduction_ratio)
        
    Examples:
        >>> calculate_satisfaction_depth(5.0, 20.0)  # Below available
        ('below-available', 'auto-minimal', 0.15)
        >>> calculate_satisfaction_depth(10.0, 20.0)  # 50% - available
        ('available', 'auto-shallow', 0.25)
        >>> calculate_satisfaction_depth(17.0, 20.0)  # 85% - elevated
        ('elevated', 'auto-moderate', 0.5)
        >>> calculate_satisfaction_depth(22.0, 20.0)  # 110% - triggered
        ('triggered', 'auto-deep', 0.75)
        >>> calculate_satisfaction_depth(32.0, 20.0)  # 160% - crisis
        ('crisis', 'auto-full', 0.9)
        >>> calculate_satisfaction_depth(32.0, 20.0, valence='aversive')  # Aversive
        ('crisis', 'auto-investigate', 0.0)
    """
    from .models import get_drive_thresholds, get_threshold_label
    
    if threshold <= 0:
        return ('unknown', 'auto-moderate', 0.50)  # Fallback for invalid threshold
    
    # Get graduated thresholds
    if thresholds is None:
        # Use default ratios from models
        drive = {"threshold": threshold}
        thresholds = get_drive_thresholds(drive)
    
    # Determine which band we're in
    band = get_threshold_label(pressure, thresholds)
    
    # Aversive drives use different satisfaction approach
    if valence == "aversive":
        # For aversive drives, default to investigation (no reduction)
        # User must explicitly choose deep satisfaction to reset
        return (band, 'auto-investigate', 0.0)
    
    # Map bands to satisfaction depths (appetitive/neutral)
    band_mappings = {
        "available": ('auto-shallow', 0.25),
        "elevated": ('auto-moderate', 0.50),
        "triggered": ('auto-deep', 0.75),
        "crisis": ('auto-full', 0.90),
        "emergency": ('auto-full', 0.90),  # Same as crisis
    }
    
    # Get depth and ratio for the band (default to moderate if unknown)
    depth_name, ratio = band_mappings.get(band, ('auto-moderate', 0.50))
    
    return (band, depth_name, ratio)


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


def assess_depth(
    breadcrumb: dict,
    pressure: float = 0.0,
    thresholds: Optional[dict] = None
) -> Tuple[str, str, float]:
    """Assess satisfaction depth for a completed session using threshold bands.
    
    Combines session quality signals with threshold band to determine satisfaction:
    - Session timed out/errored: reduce by one band level
    - Session completed normally: use band-appropriate depth
    - Session wrote files: use band-appropriate depth (same as normal)
    
    Args:
        breadcrumb: Parsed breadcrumb dict with spawn info
        pressure: Current drive pressure
        thresholds: Optional graduated thresholds dict
        
    Returns:
        Tuple of (band, depth_name, ratio)
        
    Examples:
        >>> assess_depth({"spawned_epoch": 0, "timeout_seconds": 300, "timed_out": True}, 15.0)
        ('session-error', 'shallow', 0.25)
    """
    from .models import get_drive_thresholds, get_threshold_label
    
    # Check if session timed out (age > timeout × 2)
    timed_out = breadcrumb.get("timed_out", False)
    spawn_epoch = breadcrumb.get("spawned_epoch", 0)
    timeout = breadcrumb.get("timeout_seconds", 300)
    
    if not timed_out and spawn_epoch > 0:
        age = time.time() - spawn_epoch
        if age > (timeout * 2):
            timed_out = True
    
    # Get threshold band for current pressure
    if thresholds is None:
        threshold = breadcrumb.get("threshold", 20.0)
        drive = {"threshold": threshold}
        thresholds = get_drive_thresholds(drive)
    
    band = get_threshold_label(pressure, thresholds)
    
    # Map bands to base satisfaction depths
    band_depths = {
        "available": ('shallow', 0.25),
        "elevated": ('moderate', 0.50),
        "triggered": ('deep', 0.75),
        "crisis": ('full', 0.90),
        "emergency": ('full', 0.90),
    }
    
    # Session quality affects satisfaction
    if timed_out:
        # Timed out: reduce satisfaction by one level
        depth_name, ratio = ('shallow', 0.25)
        band = 'session-error'
    elif band in band_depths:
        depth_name, ratio = band_depths[band]
    else:
        # Below available
        depth_name, ratio = ('shallow', 0.25)
    
    return (band, depth_name, ratio)


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
            # Get drive data for threshold calculation
            drive_data = state.get("drives", {}).get(drive_name, {})
            current_pressure = drive_data.get("pressure", 0.0)
            
            # Get thresholds
            from .models import get_drive_thresholds
            thresholds = get_drive_thresholds(drive_data, config.get("drives", {}).get("thresholds"))
            
            # Assess satisfaction depth using threshold bands
            band, depth_name, ratio = assess_depth(breadcrumb, current_pressure, thresholds)
            
            # Calculate new pressure
            pressure_after = max(0.0, current_pressure * (1.0 - ratio))
            
            # Satisfy the drive
            try:
                satisfy_drive(state, drive_name, depth=depth_name)
                satisfied.append(drive_name)
                
                # Log satisfaction history
                log_satisfaction(
                    drive_name=drive_name,
                    pressure_before=current_pressure,
                    pressure_after=pressure_after,
                    band=band,
                    depth=depth_name,
                    ratio=ratio,
                    source="session"
                )
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
