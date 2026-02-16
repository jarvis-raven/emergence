"""
Nightly maintenance scheduler for daemon.

Tracks last run time and determines when to run nightly tasks.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Tuple


def get_nightly_state_path(config: dict) -> Path:
    """Get path to nightly maintenance state file.

    Args:
        config: Configuration dictionary

    Returns:
        Path to nightly state file
    """
    workspace = config.get("paths", {}).get("workspace", ".")
    return Path(workspace) / ".emergence" / "state" / "nightly.json"


def load_nightly_state(config: dict) -> dict:
    """Load nightly maintenance state.

    Args:
        config: Configuration dictionary

    Returns:
        State dictionary
    """
    state_path = get_nightly_state_path(config)

    if not state_path.exists():
        return {
            "last_nautilus_run": None,
            "last_nightly_run": None,
        }

    try:
        with open(state_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {
            "last_nautilus_run": None,
            "last_nightly_run": None,
        }


def save_nightly_state(config: dict, state: dict) -> None:
    """Save nightly maintenance state.

    Args:
        config: Configuration dictionary
        state: State dictionary to save
    """
    state_path = get_nightly_state_path(config)
    state_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(state_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except IOError:
        pass  # Silent failure


def should_run_nautilus_nightly(config: dict, state: dict) -> Tuple[bool, str]:
    """Check if Nautilus nightly maintenance should run.

    Args:
        config: Configuration dictionary
        state: Nightly state dictionary

    Returns:
        Tuple of (should_run, reason)
    """
    # Check if Nautilus is enabled
    nautilus_config = config.get("nautilus", {})
    if not nautilus_config.get("enabled", False):
        return False, "Nautilus disabled"

    # Check if nightly maintenance is enabled
    if not nautilus_config.get("nightly_enabled", True):
        return False, "Nightly maintenance disabled"

    # Get preferred schedule (default: 2:30 AM)
    preferred_hour = nautilus_config.get("nightly_hour", 2)
    preferred_minute = nautilus_config.get("nightly_minute", 30)

    # Check last run time
    last_run = state.get("last_nautilus_run")
    now = datetime.now(timezone.utc)

    if last_run:
        try:
            last_dt = datetime.fromisoformat(last_run)
            if last_dt.tzinfo is None:
                last_dt = last_dt.replace(tzinfo=timezone.utc)

            # Don't run more than once per day
            hours_since_last = (now - last_dt).total_seconds() / 3600
            if hours_since_last < 23:
                return False, f"Last run {hours_since_last:.1f}h ago"
        except (ValueError, TypeError):
            pass  # Invalid timestamp, allow run

    # Check if we're in the preferred time window (±30 minutes)
    current_hour = now.hour
    current_minute = now.minute

    # Convert to minutes for easier comparison
    current_time_mins = current_hour * 60 + current_minute
    preferred_time_mins = preferred_hour * 60 + preferred_minute

    # Allow ±30 minute window
    time_diff = abs(current_time_mins - preferred_time_mins)

    # Handle midnight wraparound
    if time_diff > 12 * 60:
        time_diff = 24 * 60 - time_diff

    if time_diff <= 30:
        return True, f"In preferred window ({preferred_hour:02d}:{preferred_minute:02d})"

    # Also run if we've never run and it's been >24h since daemon start
    if not last_run:
        # If daemon just started, wait for the preferred time
        return False, "Waiting for preferred time on first run"

    return False, f"Outside preferred window (current: {current_hour:02d}:{current_minute:02d})"


def mark_nautilus_run(config: dict, state: dict) -> None:
    """Mark Nautilus nightly maintenance as completed.

    Args:
        config: Configuration dictionary
        state: Nightly state dictionary (modified in place)
    """
    state["last_nautilus_run"] = datetime.now(timezone.utc).isoformat()
    save_nightly_state(config, state)
