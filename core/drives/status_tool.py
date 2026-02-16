"""Drive status tool for agent self-introspection.

Provides the check_drive_status() tool that agents can call to check their
own motivational state. Also includes automatic periodic polling for long
sessions to prevent stale interoception.
"""

import time
from pathlib import Path
from typing import Optional, Callable
from datetime import datetime, timezone

from .runtime_state import load_runtime_state, get_state_path
from .config import load_config

# Global tracking for periodic polling
_last_poll_time: float = 0.0
_last_poll_state: Optional[dict] = None
_poll_interval_seconds: int = 300  # 5 minutes
_turn_counter: int = 0
_poll_every_n_turns: int = 10


def check_drive_status(config: Optional[dict] = None) -> dict:
    """Check current drive status and pressures.

    This tool allows an agent to introspect their own motivational state.
    Useful when asked "how are you doing?" or during self-reflection.

    Args:
        config: Optional configuration dict (auto-detected if not provided)

    Returns:
        Dictionary with drive states and summary information

    Example return value:
        {
            "drives": {
                "CARE": {
                    "pressure": 22.0,
                    "threshold": 25.0,
                    "status": "building",
                    "description": "Attending to Dan, relationship maintenance"
                },
                "CREATIVE": {
                    "pressure": 18.5,
                    "threshold": 20.0,
                    "status": "building",
                    "description": "Making things, building, writing, coding"
                }
            },
            "summary": {
                "total_drives": 5,
                "building": 3,
                "triggered": 0,
                "highest_pressure": {"drive": "CARE", "ratio": 0.88}
            }
        }
    """
    if config is None:
        config = load_config()

    state_dir = Path(get_state_path(config)).parent
    runtime_state_path = state_dir / "drives-state.json"

    runtime_state = load_runtime_state(runtime_state_path)
    drives = runtime_state.get("drives", {})

    # Build summary
    summary = {
        "total_drives": len(drives),
        "building": 0,
        "triggered": 0,
        "satisfied": 0,
        "latent": 0,
        "highest_pressure": None,
    }

    max_ratio = 0.0
    highest_drive = None

    for name, drive in drives.items():
        pressure = drive.get("pressure", 0.0)
        threshold = drive.get("threshold", 20.0)
        status = drive.get("status", "building")

        summary[status] = summary.get(status, 0) + 1

        ratio = pressure / threshold if threshold > 0 else 0.0
        if ratio > max_ratio:
            max_ratio = ratio
            highest_drive = name

    if highest_drive:
        summary["highest_pressure"] = {
            "drive": highest_drive,
            "ratio": round(max_ratio, 2),
            "percentage": round(max_ratio * 100, 0),
        }

    return {
        "drives": drives,
        "summary": summary,
        "last_updated": runtime_state.get("last_tick", datetime.now(timezone.utc).isoformat()),
    }


def format_drive_status_for_agent(status_result: dict) -> str:
    """Format drive status into a natural language response for the agent.

    Args:
        status_result: Result from check_drive_status()

    Returns:
        Natural language description of drive state
    """
    drives = status_result.get("drives", {})
    summary = status_result.get("summary", {})

    if not drives:
        return "No drives configured."

    lines = []

    # Summary line
    total = summary.get("total_drives", 0)
    triggered = summary.get("triggered", 0)

    if triggered > 0:
        drive_word = "drive" + ("s" if triggered > 1 else "")
        verb = "are" if triggered > 1 else "is"
        lines.append(f"I have {triggered} {drive_word} that {verb} ready for attention.")
    else:
        lines.append(f"All {total} drives are building pressure, none triggered yet.")

    # Highest pressure drive
    highest = summary.get("highest_pressure")
    if highest:
        drive_name = highest["drive"]
        percentage = int(highest["percentage"])
        drive_info = drives.get(drive_name, {})
        pressure = drive_info.get("pressure", 0.0)
        threshold = drive_info.get("threshold", 20.0)

        lines.append(
            f"\nMy {drive_name} drive is at {percentage}% "
            f"({pressure:.1f}/{threshold:.1f}) - "
            f"this feels most present right now."
        )

        # Add description if available
        desc = drive_info.get("description", "")
        if desc:
            lines.append(f"It's about: {desc}")

    # Other notable drives (above 75%)
    notable = []
    for name, drive in drives.items():
        if name == highest["drive"] if highest else None:
            continue
        pressure = drive.get("pressure", 0.0)
        threshold = drive.get("threshold", 20.0)
        ratio = pressure / threshold if threshold > 0 else 0.0
        if ratio >= 0.75:
            notable.append(f"{name} ({int(ratio * 100)}%)")

    if notable:
        lines.append(f"\nAlso notable: {', '.join(notable)}")

    return "\n".join(lines)


def should_poll_drives() -> bool:
    """Check if it's time to poll drive status (time-based).

    Returns:
        True if enough time has passed since last poll
    """
    global _last_poll_time
    current_time = time.time()

    if _last_poll_time == 0.0:
        # First poll
        _last_poll_time = current_time
        return True

    elapsed = current_time - _last_poll_time
    return elapsed >= _poll_interval_seconds


def check_and_poll_drives(
    config: Optional[dict] = None, on_change: Optional[Callable[[str], None]] = None
) -> Optional[str]:
    """Check if polling is due and return status update if drives changed.

    This function is designed to be called periodically during long sessions.
    It checks if enough time has passed, polls drive status, and returns a
    message if any drives changed significantly.

    Args:
        config: Optional configuration dict
        on_change: Optional callback function that receives change message

    Returns:
        Message about drive changes, or None if no significant changes
    """
    global _last_poll_time, _last_poll_state

    if not should_poll_drives():
        return None

    current_state = check_drive_status(config)
    _last_poll_time = time.time()

    if _last_poll_state is None:
        # First poll in this session
        _last_poll_state = current_state
        return None

    # Compare to previous state
    changes = []
    prev_drives = _last_poll_state.get("drives", {})
    curr_drives = current_state.get("drives", {})

    for name, curr_drive in curr_drives.items():
        prev_drive = prev_drives.get(name, {})

        curr_pressure = curr_drive.get("pressure", 0.0)
        prev_pressure = prev_drive.get("pressure", 0.0)
        curr_threshold = curr_drive.get("threshold", 20.0)

        pressure_change = curr_pressure - prev_pressure

        # Significant change: > 2.0 pressure or crossed threshold
        if abs(pressure_change) >= 2.0:
            ratio = curr_pressure / curr_threshold if curr_threshold > 0 else 0.0
            percentage = int(ratio * 100)

            if pressure_change > 0:
                changes.append(f"📈 {name} increased to {percentage}% (+{pressure_change:.1f})")
            else:
                changes.append(f"📉 {name} decreased to {percentage}% ({pressure_change:.1f})")

        # Check for threshold crossing
        prev_ratio = prev_pressure / curr_threshold if curr_threshold > 0 else 0.0
        curr_ratio = curr_pressure / curr_threshold if curr_threshold > 0 else 0.0

        if prev_ratio < 1.0 and curr_ratio >= 1.0:
            changes.append(f"🔥 {name} just triggered! ({int(curr_ratio * 100)}%)")

    _last_poll_state = current_state

    if changes:
        message = "\n".join(changes)
        if on_change:
            on_change(message)
        return f"[Drive Update - {time.strftime('%H:%M')}]\n{message}"

    return None


def increment_turn_counter() -> int:
    """Increment the turn counter and return current count.

    Returns:
        Current turn count
    """
    global _turn_counter
    _turn_counter += 1
    return _turn_counter


def should_poll_on_turn() -> bool:
    """Check if we should poll based on turn count.

    Returns:
        True if we've hit the turn interval
    """
    return _turn_counter % _poll_every_n_turns == 0


def reset_polling_state():
    """Reset polling state (call at session start)."""
    global _last_poll_time, _last_poll_state, _turn_counter
    _last_poll_time = time.time()
    _last_poll_state = None
    _turn_counter = 0
