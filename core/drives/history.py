"""History and log management for the drive engine.

Provides functions for reading, filtering, and formatting the trigger log
from drive state.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional


def parse_time_string(time_str: str) -> Optional[datetime]:
    """Parse a human-readable time string into a datetime.
    
    Supports formats like:
    - "2 hours ago"
    - "30 minutes ago"
    - "1 day ago"
    - "2026-02-07 14:30"
    - ISO 8601 timestamps
    
    Args:
        time_str: Human-readable time string
        
    Returns:
        Datetime object or None if parsing fails
        
    Examples:
        >>> result = parse_time_string("2 hours ago")
        >>> result is not None
        True
    """
    if not time_str:
        return None
    
    time_str = time_str.strip().lower()
    now = datetime.now(timezone.utc)
    
    # Handle "X units ago" format
    if "ago" in time_str:
        parts = time_str.replace("ago", "").strip().split()
        if len(parts) >= 2:
            try:
                amount = float(parts[0])
                unit = parts[1].rstrip("s")  # Normalize plural
                
                if unit in ("hour", "hr"):
                    return now - timedelta(hours=amount)
                elif unit in ("minute", "min"):
                    return now - timedelta(minutes=amount)
                elif unit in ("day", "d"):
                    return now - timedelta(days=amount)
                elif unit == "week":
                    return now - timedelta(weeks=amount)
            except (ValueError, IndexError):
                pass
    
    # Try ISO format (use original case for ISO parsing)
    try:
        iso_str = time_str.upper().replace("Z", "+00:00") if "t" in time_str else time_str.replace("z", "+00:00")
        return datetime.fromisoformat(iso_str)
    except (ValueError, TypeError):
        pass
    
    # Try common date formats
    formats = [
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]
    
    for fmt in formats:
        try:
            dt = datetime.strptime(time_str, fmt)
            return dt.replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    
    return None


def read_trigger_log(state: dict) -> list[dict]:
    """Read trigger log from state.
    
    Args:
        state: Drive state dictionary
        
    Returns:
        List of trigger event dictionaries
        
    Examples:
        >>> state = {"trigger_log": [{"drive": "CARE", "timestamp": "2026-02-07T10:00:00Z"}]}
        >>> log = read_trigger_log(state)
        >>> len(log)
        1
    """
    return state.get("trigger_log", [])


def filter_log_entries(
    log_entries: list[dict],
    drive_name: Optional[str] = None,
    since: Optional[str] = None,
    until: Optional[str] = None,
) -> list[dict]:
    """Filter log entries by various criteria.
    
    Args:
        log_entries: List of log entry dictionaries
        drive_name: Filter to specific drive (case-insensitive)
        since: Filter entries after this time (parsed)
        until: Filter entries before this time (parsed)
        
    Returns:
        Filtered list of log entries
        
    Examples:
        >>> entries = [
        ...     {"drive": "CARE", "timestamp": "2026-02-07T10:00:00Z"},
        ...     {"drive": "REST", "timestamp": "2026-02-07T08:00:00Z"},
        ... ]
        >>> filtered = filter_log_entries(entries, drive_name="CARE")
        >>> len(filtered)
        1
    """
    result = log_entries
    
    # Filter by drive name
    if drive_name:
        drive_name_lower = drive_name.lower()
        result = [e for e in result if e.get("drive", "").lower() == drive_name_lower]
    
    # Filter by start time
    if since:
        since_dt = parse_time_string(since)
        if since_dt:
            result = [
                e for e in result
                if _entry_timestamp(e) is not None and _entry_timestamp(e) >= since_dt
            ]
    
    # Filter by end time
    if until:
        until_dt = parse_time_string(until)
        if until_dt:
            result = [
                e for e in result
                if _entry_timestamp(e) is not None and _entry_timestamp(e) <= until_dt
            ]
    
    return result


def _entry_timestamp(entry: dict) -> Optional[datetime]:
    """Extract datetime from a log entry."""
    ts_str = entry.get("timestamp", "")
    if not ts_str:
        return None
    
    try:
        return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def add_trigger_event(
    state: dict,
    drive_name: str,
    pressure: float,
    threshold: float,
    session_spawned: bool = False,
    reason: Optional[str] = None,
) -> None:
    """Add a trigger event to the log.
    
    Args:
        state: Drive state (modified in place)
        drive_name: Name of the drive that triggered
        pressure: Pressure at time of trigger
        threshold: Threshold at time of trigger
        session_spawned: Whether a session was spawned
        reason: Optional reason/description
    """
    if "trigger_log" not in state:
        state["trigger_log"] = []
    
    event = {
        "drive": drive_name,
        "pressure": pressure,
        "threshold": threshold,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_spawned": session_spawned,
        "reason": reason,
    }
    
    state["trigger_log"].append(event)
    
    # Keep only last 1000 entries to prevent unbounded growth
    if len(state["trigger_log"]) > 1000:
        state["trigger_log"] = state["trigger_log"][-1000:]


def add_satisfaction_event(
    state: dict,
    drive_name: str,
    old_pressure: float,
    new_pressure: float,
    depth: str,
) -> None:
    """Add a satisfaction event to the log.
    
    Args:
        state: Drive state (modified in place)
        drive_name: Name of the drive that was satisfied
        old_pressure: Pressure before satisfaction
        new_pressure: Pressure after satisfaction
        depth: Satisfaction depth level
    """
    if "trigger_log" not in state:
        state["trigger_log"] = []
    
    drive = state.get("drives", {}).get(drive_name, {})
    threshold = drive.get("threshold", 0.0)
    
    event = {
        "drive": drive_name,
        "pressure": new_pressure,
        "threshold": threshold,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "session_spawned": False,
        "reason": f"SATISFIED-{depth} (was {old_pressure:.1f})",
    }
    
    state["trigger_log"].append(event)
    
    # Keep only last 1000 entries
    if len(state["trigger_log"]) > 1000:
        state["trigger_log"] = state["trigger_log"][-1000:]


def format_log_entry(entry: dict, include_details: bool = False) -> str:
    """Format a log entry for display.
    
    Args:
        entry: Log entry dictionary
        include_details: Whether to include full details
        
    Returns:
        Formatted string
    """
    ts_str = entry.get("timestamp", "")
    try:
        ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        ts_formatted = ts.strftime("%Y-%m-%d %H:%M")
    except (ValueError, TypeError):
        ts_formatted = ts_str[:16] if ts_str else "unknown"
    
    drive = entry.get("drive", "UNKNOWN")
    pressure = entry.get("pressure", 0.0)
    threshold = entry.get("threshold", 1.0)
    
    reason = entry.get("reason", "")
    if "satisfied" in reason.lower():
        event_type = f"SATISFIED-{reason.split('-')[1].split()[0] if '-' in reason else ''}"
    elif entry.get("session_spawned"):
        event_type = "TRIGGERED → spawned session"
    else:
        event_type = "TRIGGERED"
    
    if include_details:
        return f"{ts_formatted}  {drive:12} {pressure:.1f}/{threshold:.0f}   {event_type}  {reason}"
    else:
        return f"{ts_formatted}  {drive:12} {pressure:.1f}/{threshold:.0f}   {event_type}"


def get_stats(log_entries: list[dict]) -> dict:
    """Calculate statistics from log entries.
    
    Args:
        log_entries: List of log entry dictionaries
        
    Returns:
        Dictionary with statistics
    """
    if not log_entries:
        return {
            "total_events": 0,
            "triggers": 0,
            "satisfactions": 0,
            "by_drive": {},
        }
    
    triggers = 0
    satisfactions = 0
    by_drive = {}
    
    for entry in log_entries:
        drive = entry.get("drive", "UNKNOWN")
        reason = entry.get("reason", "")
        
        if "satisfied" in reason.lower():
            satisfactions += 1
        else:
            triggers += 1
        
        if drive not in by_drive:
            by_drive[drive] = {"triggers": 0, "satisfactions": 0}
        
        if "satisfied" in reason.lower():
            by_drive[drive]["satisfactions"] += 1
        else:
            by_drive[drive]["triggers"] += 1
    
    return {
        "total_events": len(log_entries),
        "triggers": triggers,
        "satisfactions": satisfactions,
        "by_drive": by_drive,
    }
