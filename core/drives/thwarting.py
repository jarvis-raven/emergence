"""Thwarting detection for drive system.

Thwarting occurs when a drive is repeatedly triggered without satisfaction,
shifting from appetitive (approach) to aversive (distress) motivation.

This module provides detection logic and reporting for thwarted drives.
"""

from typing import Optional
from .models import Drive, DriveState, get_drive_thresholds


def is_thwarted(
    drive: Drive, threshold: Optional[float] = None, thresholds: Optional[dict] = None
) -> bool:
    """Determine if a drive is in a thwarted state.

    A drive is thwarted when:
    - Thwarting count >= 3 (triggered 3+ times without satisfaction), OR
    - Pressure >= 150% of threshold (crisis level)

    Args:
        drive: The drive to check
        threshold: Optional threshold override (uses drive's threshold if not provided)
        thresholds: Optional graduated thresholds dict

    Returns:
        True if drive is thwarted (aversive state)

    Examples:
        >>> drive = {"pressure": 10.0, "threshold": 20.0, "thwarting_count": 3}
        >>> is_thwarted(drive)
        True

        >>> drive = {"pressure": 32.0, "threshold": 20.0, "thwarting_count": 0}
        >>> is_thwarted(drive)  # 160% pressure
        True

        >>> drive = {"pressure": 15.0, "threshold": 20.0, "thwarting_count": 1}
        >>> is_thwarted(drive)  # 75% pressure, low thwarting
        False
    """
    thwarting_count = drive.get("thwarting_count", 0)
    pressure = drive.get("pressure", 0.0)

    if threshold is None:
        threshold = drive.get("threshold", 1.0)

    # Condition 1: High thwarting count (3+ consecutive triggers)
    if thwarting_count >= 3:
        return True

    # Condition 2: Extreme pressure (>=150% of threshold)
    if threshold > 0 and pressure >= (threshold * 1.5):
        return True

    return False


def get_thwarting_status(
    drive: Drive, threshold: Optional[float] = None, thresholds: Optional[dict] = None
) -> dict:
    """Get detailed thwarting status for a drive.

    Returns comprehensive information about thwarting state including:
    - Whether drive is currently thwarted
    - Thwarting count
    - Pressure ratio
    - Valence state
    - Reason for thwarting (if applicable)

    Args:
        drive: The drive to analyze
        threshold: Optional threshold override
        thresholds: Optional graduated thresholds dict

    Returns:
        Dictionary with thwarting status details

    Examples:
        >>> drive = {"pressure": 15.0, "threshold": 20.0, "thwarting_count": 3, "valence": "aversive"}
        >>> status = get_thwarting_status(drive)
        >>> status["is_thwarted"]
        True
        >>> status["reason"]
        'consecutive_triggers'
    """
    thwarting_count = drive.get("thwarting_count", 0)
    pressure = drive.get("pressure", 0.0)

    if threshold is None:
        threshold = drive.get("threshold", 1.0)

    pressure_ratio = pressure / threshold if threshold > 0 else 0.0
    valence = drive.get("valence", "appetitive")

    # Determine if thwarted and why
    thwarted = False
    reason = None

    if thwarting_count >= 3:
        thwarted = True
        reason = "consecutive_triggers"
    elif pressure_ratio >= 1.5:
        thwarted = True
        reason = "extreme_pressure"

    return {
        "is_thwarted": thwarted,
        "thwarting_count": thwarting_count,
        "pressure": pressure,
        "threshold": threshold,
        "pressure_ratio": pressure_ratio,
        "pressure_percent": int(pressure_ratio * 100),
        "valence": valence,
        "reason": reason,
    }


def get_thwarted_drives(state: DriveState, config: Optional[dict] = None) -> list[dict]:
    """Find all drives currently in thwarted state.

    Scans all drives and returns those that meet thwarting criteria,
    sorted by severity (highest thwarting count or pressure first).

    Args:
        state: Current drive state
        config: Optional configuration (for global thresholds)

    Returns:
        List of dicts with drive name and thwarting status,
        sorted by severity (most thwarted first)

    Examples:
        >>> state = {"drives": {
        ...     "CREATIVE": {"pressure": 10.0, "threshold": 20.0, "thwarting_count": 5},
        ...     "SOCIAL": {"pressure": 15.0, "threshold": 20.0, "thwarting_count": 1},
        ... }}
        >>> thwarted = get_thwarted_drives(state)
        >>> len(thwarted)
        1
        >>> thwarted[0]["name"]
        'CREATIVE'
    """
    drives = state.get("drives", {})
    global_thresholds = config.get("drives", {}).get("thresholds") if config else None

    thwarted = []

    for name, drive in drives.items():
        thresholds = get_drive_thresholds(drive, global_thresholds)

        if is_thwarted(drive, thresholds=thresholds):
            status = get_thwarting_status(drive, thresholds=thresholds)
            status["name"] = name
            thwarted.append(status)

    # Sort by severity: thwarting count descending, then pressure ratio descending
    thwarted.sort(key=lambda x: (x["thwarting_count"], x["pressure_ratio"]), reverse=True)

    return thwarted


def format_thwarting_message(drive_name: str, status: dict) -> str:
    """Format a human-readable thwarting status message.

    Args:
        drive_name: Name of the thwarted drive
        status: Thwarting status dict from get_thwarting_status()

    Returns:
        Formatted message string

    Examples:
        >>> status = {"is_thwarted": True, "thwarting_count": 4,
        ...           "pressure_percent": 180, "reason": "consecutive_triggers"}
        >>> msg = format_thwarting_message("CREATIVE", status)
        >>> "thwarted" in msg
        True
        >>> "4 triggers" in msg
        True
    """
    if not status["is_thwarted"]:
        return f"{drive_name} is not thwarted"

    count = status["thwarting_count"]
    pct = status["pressure_percent"]
    reason = status["reason"]

    if reason == "consecutive_triggers":
        return f"{drive_name} is thwarted ({count} triggers, no satisfaction) at {pct}%"
    elif reason == "extreme_pressure":
        return f"{drive_name} is thwarted (extreme pressure: {pct}%, {count} triggers)"
    else:
        return f"{drive_name} is thwarted ({count} triggers, {pct}% pressure)"


def get_thwarting_emoji(status: dict) -> str:
    """Get emoji indicator for thwarting status.

    Args:
        status: Thwarting status dict

    Returns:
        Emoji string ("⚠" for thwarted, "→" for appetitive, "○" for neutral)
    """
    if status["is_thwarted"]:
        # Show count if available
        count = status.get("thwarting_count", 0)
        if count > 0:
            return f"⚠{count}"
        return "⚠"

    valence = status.get("valence", "appetitive")
    return {
        "neutral": "○",
        "appetitive": "→",
        "aversive": "⚠",
    }.get(valence, "→")
