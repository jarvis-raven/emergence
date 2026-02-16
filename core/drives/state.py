"""State persistence for the drive engine.

Provides atomic read/write operations for drives.json (config) and
drives-state.json (runtime) files. Uses write-to-temp-then-rename
pattern for crash safety.

Phase 1 of state duplication cleanup (issues #55, #59, #60):
- drives.json: Static configuration only
- drives-state.json: Runtime state (pressure, triggered_drives, last_tick)
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Tuple

from .models import DriveState, create_default_state, ensure_drive_defaults


# Static config fields that belong in drives.json
STATIC_CONFIG_FIELDS = {
    "name",
    "description",
    "prompt",
    "threshold",
    "thresholds",
    "rate_per_hour",
    "max_rate",
    "category",
    "created_by",
    "created_at",
    "discovered_during",
    "activity_driven",
    "min_interval_seconds",
    "base_drive",
    "aspects",
    "gated_until",
}

# Runtime state fields that belong in drives-state.json
RUNTIME_STATE_FIELDS = {
    "pressure",
    "status",
    "last_triggered",
    "valence",
    "thwarting_count",
    "last_emergency_spawn",
    "session_count_since",
}

# Deprecated fields that should be removed during migration (Phase 2)
DEPRECATED_FIELDS = {
    "satisfaction_events",  # Now in satisfaction_history.jsonl
    "trigger_log",  # Now in trigger-log.jsonl
}


def split_drive_config_and_state(drive: dict) -> Tuple[dict, dict]:
    """Split a drive dict into config and runtime state.

    Args:
        drive: Complete drive dictionary

    Returns:
        Tuple of (config_dict, state_dict)
    """
    config = {}
    state = {}

    for key, value in drive.items():
        if key in DEPRECATED_FIELDS:
            # Skip deprecated fields (migrated to JSONL in Phase 2)
            continue
        elif key in STATIC_CONFIG_FIELDS:
            config[key] = value
        elif key in RUNTIME_STATE_FIELDS:
            state[key] = value
        else:
            # Unknown field - keep in config for safety
            config[key] = value

    return config, state


def merge_drive_config_and_state(config: dict, state: dict) -> dict:
    """Merge config and runtime state into a complete drive dict.

    Args:
        config: Static configuration
        state: Runtime state

    Returns:
        Complete drive dictionary
    """
    return {**config, **state}


def load_drive_config(config_path: Path) -> dict:
    """Load static drive configuration from drives.json.

    Returns empty config if file doesn't exist.

    Args:
        config_path: Path to drives.json

    Returns:
        Dict with version and drives config
    """
    if not config_path.exists():
        # Return minimal default config
        return {"version": "1.1", "drives": {}}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Config file corrupted: {config_path}", file=sys.stderr)
        print(f"  Error: {e}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading config file: {e}", file=sys.stderr)
        return {"version": "1.1", "drives": {}}

    # Validate minimal structure
    if "version" not in data:
        data["version"] = "1.1"
    if "drives" not in data:
        data["drives"] = {}

    return data


def save_drive_config(config_path: Path, config: dict, backup: bool = True) -> None:
    """Save static drive configuration to drives.json.

    Args:
        config_path: Path to drives.json
        config: Config dict with version and drives
        backup: Whether to create .bak backup
    """
    # Ensure parent directory exists
    config_path.parent.mkdir(parents=True, exist_ok=True)

    # Create backup if requested
    if backup and config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        try:
            with open(config_path, "r", encoding="utf-8") as src:
                with open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
        except IOError:
            pass

    # Write to temp file
    temp_path = config_path.with_suffix(".tmp")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # Atomic rename
        temp_path.rename(config_path)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def load_drive_state(state_path: Path) -> dict:
    """Load runtime drive state from drives-state.json.

    Returns default state if file doesn't exist.

    Args:
        state_path: Path to drives-state.json

    Returns:
        Dict with version, last_tick, drives state, and triggered_drives
    """
    if not state_path.exists():
        # Return minimal default state
        return {
            "version": "1.1",
            "last_tick": datetime.now(timezone.utc).isoformat(),
            "drives": {},
            "triggered_drives": [],
        }

    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"State file corrupted: {state_path}", file=sys.stderr)
        print(f"  Error: {e}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading state file: {e}", file=sys.stderr)
        return {
            "version": "1.1",
            "last_tick": datetime.now(timezone.utc).isoformat(),
            "drives": {},
            "triggered_drives": [],
        }

    # Validate minimal structure
    if "version" not in data:
        data["version"] = "1.1"
    if "last_tick" not in data:
        data["last_tick"] = datetime.now(timezone.utc).isoformat()
    if "drives" not in data:
        data["drives"] = {}
    if "triggered_drives" not in data:
        data["triggered_drives"] = []

    return data


def save_drive_state(state_path: Path, state: dict, backup: bool = True) -> None:
    """Save runtime drive state to drives-state.json.

    Args:
        state_path: Path to drives-state.json
        state: State dict with version, last_tick, drives, triggered_drives
        backup: Whether to create .bak backup
    """
    # Ensure parent directory exists
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Update timestamp
    state["last_tick"] = datetime.now(timezone.utc).isoformat()

    # Create backup if requested
    if backup and state_path.exists():
        backup_path = state_path.with_suffix(".json.bak")
        try:
            with open(state_path, "r", encoding="utf-8") as src:
                with open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
        except IOError:
            pass

    # Write to temp file
    temp_path = state_path.with_suffix(".tmp")

    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)

        # Atomic rename
        temp_path.rename(state_path)
    except Exception:
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        raise


def load_state(state_path: Path) -> DriveState:
    """Load complete drive state from both config and state files.

    This is the main entry point that combines drives.json (config) and
    drives-state.json (runtime) into a unified DriveState structure.

    For backward compatibility, if drives-state.json doesn't exist,
    it will try to load everything from drives.json (legacy format).

    Args:
        state_path: Path to drives.json (config file)

    Returns:
        DriveState dictionary with complete drive data
    """
    # Determine paths
    config_path = state_path  # drives.json
    runtime_path = state_path.parent / "drives-state.json"

    # Try new split format first
    if config_path.exists() or runtime_path.exists():
        config = load_drive_config(config_path)
        state = load_drive_state(runtime_path)

        # Merge drives
        combined_drives = {}
        all_drive_names = set(config.get("drives", {}).keys()) | set(state.get("drives", {}).keys())

        for name in all_drive_names:
            drive_config = config.get("drives", {}).get(name, {})
            drive_state = state.get("drives", {}).get(name, {})
            combined_drives[name] = merge_drive_config_and_state(drive_config, drive_state)
            # Apply defaults for backward compatibility
            combined_drives[name] = ensure_drive_defaults(combined_drives[name])

        # Build combined state
        result: DriveState = {
            "version": config.get("version", "1.1"),
            "last_tick": state.get("last_tick", datetime.now(timezone.utc).isoformat()),
            "drives": combined_drives,
            "triggered_drives": state.get("triggered_drives", []),
        }

        # Phase 2 migration: Move event logs from state to JSONL
        _run_phase2_migration(result)

        return result

    # Fall back to legacy format (everything in drives.json)
    if not state_path.exists():
        return create_default_state()

    # Load legacy format
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"State file corrupted: {state_path}", file=sys.stderr)
        print(f"  Error: {e}", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading state file: {e}", file=sys.stderr)
        return create_default_state()

    # Validate and apply defaults
    if "version" not in data:
        data["version"] = "1.0"
    if "drives" not in data:
        data["drives"] = {}
    if "triggered_drives" not in data:
        data["triggered_drives"] = []
    if "last_tick" not in data and "last_updated" in data:
        data["last_tick"] = data["last_updated"]
    if "last_tick" not in data:
        data["last_tick"] = datetime.now(timezone.utc).isoformat()

    # Apply defaults to drives
    for name, drive in list(data["drives"].items()):
        data["drives"][name] = ensure_drive_defaults(drive)

    return data


def save_state(state_path: Path, state: DriveState, backup: bool = True) -> None:
    """Save complete drive state to both config and state files.

    This splits the unified DriveState into:
    - drives.json: Static configuration
    - drives-state.json: Runtime state

    Args:
        state_path: Path to drives.json (config file)
        state: Complete DriveState to save
        backup: Whether to create .bak backups
    """
    # Determine paths
    config_path = state_path  # drives.json
    runtime_path = state_path.parent / "drives-state.json"

    # Split drives into config and state
    config_drives = {}
    state_drives = {}

    for name, drive in state.get("drives", {}).items():
        drive_config, drive_state = split_drive_config_and_state(drive)
        config_drives[name] = drive_config
        state_drives[name] = drive_state

    # Build config structure
    config = {"version": "1.1", "drives": config_drives}  # Always use 1.1 for split format

    # Build state structure
    runtime = {
        "version": "1.1",  # Always use 1.1 for split format
        "last_tick": state.get("last_tick", datetime.now(timezone.utc).isoformat()),
        "drives": state_drives,
        "triggered_drives": state.get("triggered_drives", []),
    }

    # Save both files
    save_drive_config(config_path, config, backup=backup)
    save_drive_state(runtime_path, runtime, backup=backup)


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


def _run_phase2_migration(state: DriveState) -> None:
    """Run Phase 2 migration: Move event logs from state to JSONL files.

    This is a one-time migration that:
    1. Exports trigger_log to trigger-log.jsonl
    2. Exports satisfaction_events arrays to satisfaction_history.jsonl
    3. Removes these fields from state

    Migration is idempotent - safe to run multiple times.
    Silent if no migration needed.

    Args:
        state: DriveState dict (modified in place if migration needed)
    """
    from .history import migrate_trigger_log
    from .satisfaction import migrate_satisfaction_events

    # Migrate trigger_log if it exists AND has entries
    if "trigger_log" in state and state.get("trigger_log"):
        count = migrate_trigger_log(state)
        if count > 0:
            print(f"✓ Migrated {count} trigger log entries to trigger-log.jsonl", file=sys.stderr)

    # Migrate satisfaction_events from all drives (only if non-empty)
    drives = state.get("drives", {})
    has_non_empty_events = any(
        drive.get("satisfaction_events") for drive in drives.values()  # Check for non-empty list
    )

    if has_non_empty_events:
        count = migrate_satisfaction_events(state)
        if count > 0:
            print(
                f"✓ Migrated {count} satisfaction events to satisfaction_history.jsonl",
                file=sys.stderr,
            )


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
