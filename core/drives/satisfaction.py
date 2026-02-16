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
    state_dir = os.environ.get("EMERGENCE_STATE", str(Path.home() / ".openclaw" / "state"))
    return Path(state_dir) / "satisfaction_history.jsonl"


def log_satisfaction(
    drive_name: str,
    pressure_before: float,
    pressure_after: float,
    band: str,
    depth: str,
    ratio: float,
    source: str = "manual",
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
        with history_path.open("a") as f:
            f.write(json.dumps(event) + "\n")
    except OSError:
        # Failed to write history — non-fatal
        pass


def get_recent_satisfaction_history(
    drive_name: Optional[str] = None, limit: int = 50
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
        with history_path.open("r") as f:
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


def _parse_breadcrumb(bc_path: Path) -> Optional[dict]:
    """Parse breadcrumb file and extract relevant data.

    Args:
        bc_path: Path to breadcrumb file

    Returns:
        Dict with breadcrumb data or None if invalid
    """
    try:
        breadcrumb = json.loads(bc_path.read_text())
        drive_name = breadcrumb.get("drive", "")
        session_key = breadcrumb.get("session_key", "")
        spawned_at = breadcrumb.get("spawned_at", "")
        spawned_epoch = breadcrumb.get("spawned_epoch", 0)

        if not drive_name or not session_key:
            return None

        return {
            "drive": drive_name,
            "session_key": session_key,
            "spawned_at": spawned_at,
            "spawned_epoch": spawned_epoch,
        }
    except (json.JSONDecodeError, OSError):
        return None


def _check_completion_markers(ingest_dir: Path, drive_name: str, session_key: str) -> str:
    """Check for completion marker files and return session status.

    Args:
        ingest_dir: Path to sessions_ingest directory
        drive_name: Name of the drive
        session_key: Session key to match

    Returns:
        Session status string (pending/completed)
    """
    for cf in ingest_dir.glob(f"COMPLETE-*-{drive_name}.json"):
        try:
            cdata = json.loads(cf.read_text())
            if cdata.get("drive") == drive_name or cdata.get("session_key") == session_key:
                session_status = cdata.get("status", "completed")
                # Clean up completion marker
                cf.unlink()
                return session_status
        except (json.JSONDecodeError, OSError):
            pass

    return "pending"


def _write_trigger_log_event(
    drive_name: str,
    session_key: str,
    spawned_at: str,
    spawned_epoch: int,
    session_status: str,
) -> None:
    """Write trigger log event for migrated breadcrumb.

    Args:
        drive_name: Name of the drive
        session_key: Session key
        spawned_at: Spawn timestamp (ISO)
        spawned_epoch: Spawn epoch time
        session_status: Session status string
    """
    from .history import get_trigger_log_path

    log_path = get_trigger_log_path()

    event = {
        "drive": drive_name,
        "pressure": 0.0,  # Unknown from breadcrumb
        "threshold": 0.0,  # Unknown from breadcrumb
        "timestamp": spawned_at,
        "session_spawned": True,
        "reason": "Migrated from breadcrumb",
        "session_key": session_key,
        "session_status": session_status,
        "spawned_epoch": spawned_epoch,
    }

    # Append to trigger log
    with log_path.open("a") as f:
        f.write(json.dumps(event) + "\n")


def migrate_breadcrumbs_to_trigger_log() -> int:
    """Migrate existing breadcrumb files to trigger-log.jsonl entries.

    One-time migration for Phase 3: converts sessions_ingest/*.json files
    to trigger-log.jsonl entries with session tracking.

    Returns:
        Number of breadcrumbs migrated
    """
    state_dir = os.environ.get("EMERGENCE_STATE", str(Path.home() / ".openclaw" / "state"))
    ingest_dir = Path(state_dir) / "sessions_ingest"

    if not ingest_dir.exists():
        return 0

    migrated = 0

    try:
        for bc_path in ingest_dir.glob("*.json"):
            # Skip temp files and completion markers
            if bc_path.name.startswith(".tmp-") or bc_path.name.startswith("COMPLETE-"):
                continue

            breadcrumb_data = _parse_breadcrumb(bc_path)
            if not breadcrumb_data:
                continue

            # Check for completion markers
            session_status = _check_completion_markers(
                ingest_dir,
                breadcrumb_data["drive"],
                breadcrumb_data["session_key"],
            )

            # Write to trigger log
            _write_trigger_log_event(
                breadcrumb_data["drive"],
                breadcrumb_data["session_key"],
                breadcrumb_data["spawned_at"],
                breadcrumb_data["spawned_epoch"],
                session_status,
            )

            migrated += 1

            # Remove breadcrumb file
            bc_path.unlink()

    except OSError:
        return migrated

    return migrated


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
            with history_path.open("a") as f:
                for timestamp_str in events:
                    # Create a satisfaction event entry
                    event = {
                        "timestamp": timestamp_str,
                        "drive": drive_name,
                        "pressure_before": 0.0,  # Unknown from old data
                        "pressure_after": 0.0,  # Unknown from old data
                        "band": "unknown",
                        "depth": "unknown",
                        "ratio": 0.0,  # Unknown from old data
                        "source": "migrated",
                    }
                    f.write(json.dumps(event) + "\n")
                    migrated += 1
        except OSError:
            # Migration failed for this drive — continue
            continue

        # Remove satisfaction_events from drive
        del drive_data["satisfaction_events"]

    return migrated


def get_aversive_satisfaction_options(
    drive_name: str, pressure: float, threshold: float, thwarting_count: int = 0
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
    options = {"approach": "aversive", "recommended_action": "investigate", "options": []}

    # Option 1: Investigate blockage (reflective, no immediate pressure reduction)
    options["options"].append(
        {
            "name": "investigate",
            "label": "Investigate Blockage",
            "description": "Reflective session to identify what's preventing satisfaction",
            "pressure_reduction": 0.0,  # No immediate reduction
            "resets_thwarting": False,
            "prompt": (
                f"What's blocking your ability to satisfy {drive_name}? "
                "Explore obstacles, constraints, and alternative approaches."
            ),
        }
    )

    # Option 2: Partial/alternative satisfaction (gentler reduction)
    ratio = pressure / threshold if threshold > 0 else 0
    alt_reduction = min(0.35, ratio * 0.25)  # Gentler than appetitive
    options["options"].append(
        {
            "name": "alternative",
            "label": "Alternative Approach",
            "description": "Try a different route to partial satisfaction",
            "pressure_reduction": alt_reduction,
            "resets_thwarting": False,
            "prompt": (
                f"Find an alternative way to engage with {drive_name} "
                "that works around current blockages."
            ),
        }
    )

    # Option 3: Deep satisfaction with threshold awareness (resets thwarting)
    deep_reduction = min(0.75, ratio * 0.6)
    options["options"].append(
        {
            "name": "deep",
            "label": "Deep Satisfaction",
            "description": "Full engagement attempt (resets thwarting count)",
            "pressure_reduction": deep_reduction,
            "resets_thwarting": True,
            "prompt": (
                f"Fully engage with {drive_name}, acknowledging past "
                "blockages. Document what's different this time."
            ),
        }
    )

    # Threshold adjustment recommendation
    if thwarting_count >= 3:
        options["threshold_adjustment"] = {
            "recommended": True,
            "reason": f"Drive has been thwarted {thwarting_count} times",
            "suggestion": (
                f"Consider temporarily raising threshold to "
                f"{threshold * 1.25:.1f} to reduce pressure"
            ),
            "temporary_duration": "24-48 hours",
        }

    return options


def calculate_satisfaction_depth(
    pressure: float,
    threshold: float,
    thresholds: Optional[dict] = None,
    valence: str = "appetitive",
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
        return ("unknown", "auto-moderate", 0.50)  # Fallback for invalid threshold

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
        return (band, "auto-investigate", 0.0)

    # Map bands to satisfaction depths (appetitive/neutral)
    band_mappings = {
        "available": ("auto-shallow", 0.25),
        "elevated": ("auto-moderate", 0.50),
        "triggered": ("auto-deep", 0.75),
        "crisis": ("auto-full", 0.90),
        "emergency": ("auto-full", 0.90),  # Same as crisis
    }

    # Get depth and ratio for the band (default to moderate if unknown)
    depth_name, ratio = band_mappings.get(band, ("auto-moderate", 0.50))

    return (band, depth_name, ratio)


def assess_depth(
    trigger_entry: dict,
    pressure: float = 0.0,
    thresholds: Optional[dict] = None,
    timeout_seconds: int = 900,
) -> Tuple[str, str, float]:
    """Assess satisfaction depth for a completed session using threshold bands.

    Combines session quality signals with threshold band to determine satisfaction:
    - Session timed out/errored: reduce by one band level
    - Session completed normally: use band-appropriate depth

    Args:
        trigger_entry: Trigger log entry dict with spawn info
        pressure: Current drive pressure
        thresholds: Optional graduated thresholds dict
        timeout_seconds: Session timeout in seconds

    Returns:
        Tuple of (band, depth_name, ratio)

    Examples:
        >>> entry = {"spawned_epoch": 0, "session_status": "error"}
        >>> assess_depth(entry, 15.0)
        ('session-error', 'shallow', 0.25)
    """
    from .models import get_drive_thresholds, get_threshold_label

    # Check session status
    status = trigger_entry.get("session_status", "pending")
    timed_out = status in ["error", "timeout"]

    # Also check age if status is still pending
    if not timed_out and status == "pending":
        spawn_epoch = trigger_entry.get("spawned_epoch", 0)
        if spawn_epoch > 0:
            age = time.time() - spawn_epoch
            if age > (timeout_seconds * 2):
                timed_out = True

    # Get threshold band for current pressure
    if thresholds is None:
        threshold = trigger_entry.get("threshold", 20.0)
        drive = {"threshold": threshold}
        thresholds = get_drive_thresholds(drive)

    band = get_threshold_label(pressure, thresholds)

    # Map bands to base satisfaction depths
    band_depths = {
        "available": ("shallow", 0.25),
        "elevated": ("moderate", 0.50),
        "triggered": ("deep", 0.75),
        "crisis": ("full", 0.90),
        "emergency": ("full", 0.90),
    }

    # Session quality affects satisfaction
    if timed_out:
        # Timed out: reduce satisfaction by one level
        depth_name, ratio = ("shallow", 0.25)
        band = "session-error"
    elif band in band_depths:
        depth_name, ratio = band_depths[band]
    else:
        # Below available
        depth_name, ratio = ("shallow", 0.25)

    return (band, depth_name, ratio)


def _handle_completed_session(
    state: DriveState,
    config: dict,
    entry: dict,
    drive_name: str,
    timeout_seconds: int,
) -> bool:
    """Handle a completed session and apply satisfaction.

    Args:
        state: Current drive state (modified in place)
        config: Configuration dict
        entry: Trigger log entry
        drive_name: Name of the drive
        timeout_seconds: Session timeout in seconds

    Returns:
        True if drive was satisfied
    """
    from .engine import satisfy_drive
    from .models import get_drive_thresholds

    # Get drive data for threshold calculation
    drive_data = state.get("drives", {}).get(drive_name, {})
    current_pressure = drive_data.get("pressure", 0.0)

    # Get thresholds
    thresholds = get_drive_thresholds(drive_data, config.get("drives", {}).get("thresholds"))

    # Assess satisfaction depth using threshold bands
    band, depth_name, ratio = assess_depth(entry, current_pressure, thresholds, timeout_seconds)

    # Calculate new pressure
    pressure_after = max(0.0, current_pressure * (1.0 - ratio))

    # Satisfy the drive
    try:
        satisfy_drive(state, drive_name, depth=depth_name)

        # Log satisfaction history
        log_satisfaction(
            drive_name=drive_name,
            pressure_before=current_pressure,
            pressure_after=pressure_after,
            band=band,
            depth=depth_name,
            ratio=ratio,
            source="session",
        )
    except (KeyError, ValueError):
        # Drive doesn't exist — just continue
        pass

    # Remove from triggered list
    triggered = state.get("triggered_drives", [])
    if drive_name in triggered:
        state["triggered_drives"] = [d for d in triggered if d != drive_name]

    return True


def _handle_timed_out_session(
    state: DriveState,
    config: dict,
    entry: dict,
    drive_name: str,
    session_key: str,
    timeout_seconds: int,
) -> bool:
    """Handle a timed-out session and apply reduced satisfaction.

    Args:
        state: Current drive state (modified in place)
        config: Configuration dict
        entry: Trigger log entry (modified in place)
        drive_name: Name of the drive
        session_key: Session key
        timeout_seconds: Session timeout in seconds

    Returns:
        True if drive was satisfied
    """
    from .engine import satisfy_drive
    from .history import update_session_status
    from .models import get_drive_thresholds

    # Session timed out - mark as error and apply reduced satisfaction
    update_session_status(session_key, "timeout")

    # Get drive data
    drive_data = state.get("drives", {}).get(drive_name, {})
    current_pressure = drive_data.get("pressure", 0.0)

    # Get thresholds
    thresholds = get_drive_thresholds(drive_data, config.get("drives", {}).get("thresholds"))

    # Mark entry as timed out for assessment
    entry["session_status"] = "timeout"
    band, depth_name, ratio = assess_depth(entry, current_pressure, thresholds, timeout_seconds)

    # Apply reduced satisfaction (shallow due to timeout)
    pressure_after = max(0.0, current_pressure * (1.0 - ratio))

    try:
        satisfy_drive(state, drive_name, depth=depth_name)

        log_satisfaction(
            drive_name=drive_name,
            pressure_before=current_pressure,
            pressure_after=pressure_after,
            band=band,
            depth=depth_name,
            ratio=ratio,
            source="session-timeout",
        )
    except (KeyError, ValueError):
        # Drive doesn't exist — just continue
        pass

    # Remove from triggered list
    triggered = state.get("triggered_drives", [])
    if drive_name in triggered:
        state["triggered_drives"] = [d for d in triggered if d != drive_name]

    return True


def check_completed_sessions(state: DriveState, config: dict) -> list[str]:
    """Query trigger-log.jsonl for completed drive sessions and satisfy them.

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
    from .history import get_active_sessions

    timeout_seconds = config.get("drives", {}).get("session_timeout", 900)
    satisfied = []

    # Get all active sessions from trigger log
    active_sessions = get_active_sessions(timeout_seconds=timeout_seconds)

    for entry in active_sessions:
        drive_name = entry.get("drive", "")
        session_key = entry.get("session_key", "")
        session_status = entry.get("session_status", "pending")
        spawn_epoch = entry.get("spawned_epoch", 0)

        # Check if session has completed
        if session_status == "completed":
            if _handle_completed_session(state, config, entry, drive_name, timeout_seconds):
                satisfied.append(drive_name)

        # Check for timeout (stale sessions)
        elif session_status == "pending" and spawn_epoch > 0:
            age = time.time() - spawn_epoch
            if age > (timeout_seconds + 60):
                if _handle_timed_out_session(
                    state, config, entry, drive_name, session_key, timeout_seconds
                ):
                    satisfied.append(drive_name)

    return satisfied
