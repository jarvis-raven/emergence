"""Core drive engine — pressure accumulation and threshold checking.

This is the heart of the interoception system. Drives accumulate pressure
over time; when pressure exceeds threshold, drives trigger action. After
addressing a drive, satisfaction resets the pressure.
"""

from datetime import datetime, timezone
from typing import Optional

from .models import Drive, DriveState, SATISFACTION_DEPTHS, CORE_DRIVES
from .utils import fuzzy_match


def is_quiet_hours(config: dict) -> bool:
    """Check if current time falls within quiet hours.
    
    Quiet hours prevent drive triggers from spawning sessions,
    but pressure still accumulates.
    
    Args:
        config: Configuration dict with drives.quiet_hours as [start, end]
        
    Returns:
        True if currently within quiet hours
        
    Examples:
        >>> config = {"drives": {"quiet_hours": [23, 7]}}
        >>> # At 2 AM, returns True
        >>> # At 14:00 (2 PM), returns False
    """
    quiet_hours = config.get("drives", {}).get("quiet_hours")
    if not quiet_hours or len(quiet_hours) != 2:
        return False
    
    start_hour, end_hour = quiet_hours
    current_hour = datetime.now().hour
    
    # Handle overnight quiet hours (e.g., 23:00-07:00)
    if start_hour > end_hour:
        return current_hour >= start_hour or current_hour < end_hour
    else:
        # Same-day quiet hours (e.g., 01:00-05:00)
        return start_hour <= current_hour < end_hour


def accumulate_pressure(
    drive: Drive,
    hours_elapsed: float,
    max_ratio: float = 1.5
) -> float:
    """Calculate new pressure after elapsed time.
    
    Core algorithm: pressure + (rate_per_hour × hours_elapsed)
    
    Special cases:
    - Activity-driven drives (like REST) don't accumulate from time
    - Pressure is capped at threshold × max_ratio (default 1.5)
    
    Args:
        drive: The drive to update
        hours_elapsed: Hours since last tick
        max_ratio: Maximum pressure as multiple of threshold
        
    Returns:
        New pressure value (may equal old pressure for activity-driven)
        
    Examples:
        >>> drive = {"pressure": 10.0, "threshold": 20.0, "rate_per_hour": 2.0}
        >>> accumulate_pressure(drive, 2.0)  # +4.0 pressure
        14.0
        >>> 
        >>> # Activity-driven doesn't accumulate
        >>> rest = {"pressure": 5.0, "threshold": 30.0, "rate_per_hour": 0.0, 
        ...         "activity_driven": True}
        >>> accumulate_pressure(rest, 5.0)
        5.0
    """
    # Activity-driven drives don't accumulate from time
    if drive.get("activity_driven", False):
        return drive.get("pressure", 0.0)
    
    rate = drive.get("rate_per_hour", 0.0)
    threshold = drive.get("threshold", 1.0)
    current_pressure = drive.get("pressure", 0.0)
    
    # Zero threshold means no accumulation target
    if threshold <= 0:
        return current_pressure
    
    # Calculate new pressure
    pressure_increase = rate * hours_elapsed
    new_pressure = current_pressure + pressure_increase
    
    # Cap at threshold × max_ratio
    max_pressure = threshold * max_ratio
    new_pressure = min(new_pressure, max_pressure)
    
    return new_pressure


def tick_all_drives(
    state: DriveState,
    config: dict
) -> dict:
    """Run accumulation tick for all drives.
    
    Updates pressure for all drives based on time elapsed since last tick.
    Activity-driven drives and already-triggered drives are skipped.
    
    Args:
        state: Current drive state (modified in place)
        config: Configuration with tick settings
        
    Returns:
        Dictionary mapping drive names to (old, new) pressure tuples
        
    Examples:
        >>> state = create_default_state()
        >>> state["last_tick"] = "2026-02-07T10:00:00+00:00"  # 2 hours ago
        >>> changes = tick_all_drives(state, DEFAULT_CONFIG)
        >>> "CARE" in changes
        True
    """
    from .state import get_hours_since_tick
    
    triggered = set(state.get("triggered_drives", []))
    max_ratio = config.get("drives", {}).get("max_pressure_ratio", 1.5)
    
    hours_elapsed = get_hours_since_tick(state)
    
    # During quiet hours, accumulate at 25% rate to prevent dawn pressure explosion
    quiet_rate_factor = config.get("drives", {}).get("quiet_hours_rate_factor", 0.25)
    if is_quiet_hours(config):
        hours_elapsed *= quiet_rate_factor
    
    changes = {}
    
    for name, drive in state.get("drives", {}).items():
        # Skip triggered drives — they don't accumulate more pressure
        if name in triggered:
            continue
        
        old_pressure = drive.get("pressure", 0.0)
        new_pressure = accumulate_pressure(drive, hours_elapsed, max_ratio)
        
        if new_pressure != old_pressure:
            drive["pressure"] = new_pressure
            changes[name] = (old_pressure, new_pressure)
    
    return changes


def check_thresholds(
    state: DriveState,
    config: dict,
    respect_quiet_hours: bool = True
) -> list[str]:
    """Find drives that have exceeded their thresholds.
    
    Returns drives sorted by pressure ratio (highest first) that are:
    - Not already triggered
    - Over their threshold (pressure >= threshold)
    - Outside quiet hours (if respect_quiet_hours=True)
    
    Args:
        state: Current drive state
        config: Configuration with quiet_hours setting
        respect_quiet_hours: If True, return empty list during quiet hours
        
    Returns:
        List of drive names that should trigger (sorted by urgency)
        
    Examples:
        >>> state = create_default_state()
        >>> state["drives"]["CARE"]["pressure"] = 25.0  # Over threshold 20.0
        >>> check_thresholds(state, DEFAULT_CONFIG)
        ['CARE']
    """
    if respect_quiet_hours and is_quiet_hours(config):
        return []
    
    triggered = set(state.get("triggered_drives", []))
    candidates = []
    
    for name, drive in state.get("drives", {}).items():
        # Skip already triggered
        if name in triggered:
            continue
        
        pressure = drive.get("pressure", 0.0)
        threshold = drive.get("threshold", 1.0)
        
        if threshold > 0 and pressure >= threshold:
            ratio = pressure / threshold
            candidates.append((name, ratio))
    
    # Sort by ratio descending (highest pressure first)
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    return [name for name, _ in candidates]


def satisfy_drive(
    state: DriveState,
    drive_name: str,
    depth: str = "moderate"
) -> dict:
    """Reduce drive pressure after addressing it.
    
    Satisfaction depths:
    - shallow (s): 30% reduction — token effort
    - moderate (m): 50% reduction — real engagement (default)
    - deep (d): 75% reduction — genuine satisfaction
    - full (f): 100% reduction — complete reset
    
    Also records the satisfaction event and removes from triggered list
    if reduction is significant (>= 50%).
    
    Args:
        state: Current drive state (modified in place)
        drive_name: Name of drive to satisfy
        depth: Satisfaction depth level
        
    Returns:
        Result dict with success status and details
        
    Raises:
        ValueError: If drive not found or depth invalid
        
    Examples:
        >>> state = create_default_state()
        >>> state["drives"]["CARE"]["pressure"] = 20.0
        >>> result = satisfy_drive(state, "CARE", "moderate")
        >>> result["new_pressure"]
        10.0
    """
    # Find drive using fuzzy matching
    drives = state.get("drives", {})
    normalized_name = fuzzy_match(drive_name, list(drives.keys()))
    
    if not normalized_name:
        available = ", ".join(sorted(drives.keys()))
        raise ValueError(f"Unknown drive: {drive_name}. Available: {available}")
    
    drive = drives[normalized_name]
    
    # Get reduction ratio
    reduction = SATISFACTION_DEPTHS.get(depth.lower())
    if reduction is None:
        valid = ", ".join(SATISFACTION_DEPTHS.keys())
        raise ValueError(f"Invalid depth: {depth}. Valid: {valid}")
    
    old_pressure = drive.get("pressure", 0.0)
    
    # Calculate new pressure (never below 0)
    new_pressure = max(0.0, old_pressure * (1.0 - reduction))
    drive["pressure"] = new_pressure
    
    # Record satisfaction event
    if "satisfaction_events" not in drive:
        drive["satisfaction_events"] = []
    
    now = datetime.now(timezone.utc).isoformat()
    drive["satisfaction_events"].append(now)
    
    # Keep only last 10 events
    drive["satisfaction_events"] = drive["satisfaction_events"][-10:]
    
    # Remove from triggered list if significantly reduced
    triggered = state.get("triggered_drives", [])
    if normalized_name in triggered and reduction >= 0.5:
        triggered.remove(normalized_name)
    
    return {
        "success": True,
        "drive": normalized_name,
        "old_pressure": old_pressure,
        "new_pressure": new_pressure,
        "reduction_ratio": reduction,
        "depth": depth,
    }


def bump_drive(
    state: DriveState,
    drive_name: str,
    amount: Optional[float] = None
) -> dict:
    """Manually increase a drive's pressure.
    
    Useful for event-driven pressure increases (e.g., human mentions
    feeling lonely → bump CARE).
    
    Args:
        state: Current drive state (modified in place)
        drive_name: Name of drive to bump
        amount: Amount to add (default: 2 hours worth at drive's rate)
        
    Returns:
        Result dict with success status and details
        
    Raises:
        ValueError: If drive not found
        
    Examples:
        >>> state = create_default_state()
        >>> result = bump_drive(state, "CARE", 10.0)
        >>> result["new_pressure"]
        10.0
    """
    drives = state.get("drives", {})
    normalized_name = fuzzy_match(drive_name, list(drives.keys()))
    
    if not normalized_name:
        available = ", ".join(sorted(drives.keys()))
        raise ValueError(f"Unknown drive: {drive_name}. Available: {available}")
    
    drive = drives[normalized_name]
    old_pressure = drive.get("pressure", 0.0)
    threshold = drive.get("threshold", 1.0)
    rate = drive.get("rate_per_hour", 0.0)
    max_ratio = 1.5  # Same cap as accumulate_pressure
    
    # Default amount: 2 hours worth at drive's rate
    if amount is None:
        amount = rate * 2.0
    
    new_pressure = min(old_pressure + amount, threshold * max_ratio)
    drive["pressure"] = new_pressure
    
    return {
        "success": True,
        "drive": normalized_name,
        "old_pressure": old_pressure,
        "new_pressure": new_pressure,
        "amount_added": amount,
    }


def get_drive_status(state: DriveState, drive_name: str) -> Optional[dict]:
    """Get detailed status for a single drive.
    
    Args:
        state: Current drive state
        drive_name: Name of drive (fuzzy matched)
        
    Returns:
        Status dict or None if drive not found
        
    Examples:
        >>> state = create_default_state()
        >>> status = get_drive_status(state, "CARE")
        >>> status["ratio"]
        0.0
    """
    drives = state.get("drives", {})
    triggered = set(state.get("triggered_drives", []))
    
    normalized_name = fuzzy_match(drive_name, list(drives.keys()))
    if not normalized_name:
        return None
    
    drive = drives[normalized_name]
    pressure = drive.get("pressure", 0.0)
    threshold = drive.get("threshold", 1.0)
    ratio = pressure / threshold if threshold > 0 else 0.0
    
    # Determine status category
    if normalized_name in triggered:
        status = "triggered"
    elif ratio >= 1.0:
        status = "over_threshold"
    elif ratio >= 0.75:
        status = "elevated"
    else:
        status = "normal"
    
    return {
        "name": normalized_name,
        "pressure": pressure,
        "threshold": threshold,
        "ratio": ratio,
        "percentage": ratio * 100,
        "status": status,
        "category": drive.get("category", "unknown"),
        "rate_per_hour": drive.get("rate_per_hour", 0.0),
        "activity_driven": drive.get("activity_driven", False),
        "description": drive.get("description", ""),
        "last_satisfied": (drive.get("satisfaction_events", []) or [None])[-1],
    }


def reset_all_drives(state: DriveState) -> dict:
    """Reset all drives to zero pressure.
    
    Clears triggered list as well. Use with caution — this is the
    "emergency reset" function.
    
    Args:
        state: Current drive state (modified in place)
        
    Returns:
        Result dict with count of drives reset
        
    Examples:
        >>> state = create_default_state()
        >>> state["drives"]["CARE"]["pressure"] = 20.0
        >>> reset_all_drives(state)["drives_reset"]
        3
    """
    count = 0
    
    for drive in state.get("drives", {}).values():
        drive["pressure"] = 0.0
        count += 1
    
    # Clear triggered list
    triggered_count = len(state.get("triggered_drives", []))
    state["triggered_drives"] = []
    
    return {
        "success": True,
        "drives_reset": count,
        "triggered_cleared": triggered_count,
    }


def cleanup_stale_triggers(
    state: DriveState,
    config: dict,
    max_age_minutes: int = 60
) -> list[str]:
    """Auto-satisfy drives that have been triggered for too long.
    
    Jarvlings sometimes forget to run 'drives satisfy' after completing
    their session. This cleanup ensures drives don't stay triggered forever.
    
    For each triggered drive, checks the trigger log for how long ago it
    was triggered. If longer than max_age_minutes, auto-satisfies with
    'moderate' depth.
    
    Args:
        state: Current drive state (modified in place)
        config: Configuration dict
        max_age_minutes: Minutes after which to auto-satisfy (default 60)
        
    Returns:
        List of drive names that were auto-satisfied
        
    Examples:
        >>> state = {"triggered_drives": ["CARE"], "trigger_log": [...]}
        >>> # If CARE was triggered 90 minutes ago:
        >>> cleanup_stale_triggers(state, config, max_age_minutes=60)
        ['CARE']
    """
    triggered = state.get("triggered_drives", [])
    if not triggered:
        return []
    
    trigger_log = state.get("trigger_log", [])
    now = datetime.now(timezone.utc)
    auto_satisfied = []
    
    for drive_name in list(triggered):  # list() to allow modification during iteration
        # Find when this drive was last triggered
        last_trigger_time = None
        for entry in reversed(trigger_log):
            if entry.get("drive") == drive_name and entry.get("session_spawned"):
                try:
                    last_trigger_time = datetime.fromisoformat(entry["timestamp"])
                    if last_trigger_time.tzinfo is None:
                        last_trigger_time = last_trigger_time.replace(tzinfo=timezone.utc)
                    break
                except (ValueError, TypeError):
                    continue
        
        if last_trigger_time is None:
            # No trigger record found — shouldn't happen, but clean up anyway
            if drive_name in triggered:
                triggered.remove(drive_name)
                auto_satisfied.append(drive_name)
            continue
        
        minutes_since = (now - last_trigger_time).total_seconds() / 60
        
        if minutes_since >= max_age_minutes:
            # Auto-satisfy with moderate depth
            try:
                satisfy_drive(state, drive_name, "moderate")
                auto_satisfied.append(drive_name)
            except ValueError:
                # Drive no longer exists
                if drive_name in state.get("triggered_drives", []):
                    state["triggered_drives"].remove(drive_name)
    
    return auto_satisfied
