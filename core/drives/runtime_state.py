"""Drive state models - Lightweight runtime state for context loading.

This module provides minimal drive state structures to prevent context bloat.
The full drives.json contains descriptions, prompts, history, etc.
The drives-state.json contains only runtime values (pressure, threshold, status).
"""

from typing import TypedDict, Optional
from datetime import datetime, timezone
from pathlib import Path
import json


class DriveRuntimeState(TypedDict, total=False):
    """Minimal runtime state for a single drive.

    This is the lightweight version loaded into regular session context.
    Contains only values that change during operation, not config.

    Attributes:
        pressure: Current accumulated pressure level
        threshold: Pressure level at which drive triggers
        status: 'building', 'triggered', 'satisfied', 'latent'
        description: Short description of drive purpose (not full prompt)
        last_triggered: ISO 8601 timestamp of last trigger
    """

    pressure: float
    threshold: float
    status: str  # 'building', 'triggered', 'satisfied', 'latent'
    description: Optional[str]  # Short description, not full prompt
    last_triggered: Optional[str]


class DrivesRuntimeState(TypedDict, total=False):
    """Complete lightweight runtime state for all drives.

    This is the structure persisted to and loaded from drives-state.json.
    Designed to be small enough to load into every session context.

    Attributes:
        version: Schema version for migration support
        last_tick: ISO 8601 timestamp of last pressure update
        drives: Mapping of drive names to DriveRuntimeState
    """

    version: str
    last_tick: str
    drives: dict[str, DriveRuntimeState]


def create_default_runtime_state() -> DrivesRuntimeState:
    """Create empty default runtime state.

    Returns:
        DrivesRuntimeState with default values
    """
    return {"version": "1.0", "last_tick": datetime.now(timezone.utc).isoformat(), "drives": {}}


def extract_runtime_state(full_drives_state: dict) -> DrivesRuntimeState:
    """Extract minimal runtime state from full drives state.

    This converts the full drives.json format to the lightweight
    drives-state.json format, keeping only runtime values.

    Args:
        full_drives_state: The full state from drives.json

    Returns:
        DrivesRuntimeState with only runtime values

    Examples:
        >>> full_state = {"drives": {"CARE": {"pressure": 22.0, "threshold": 25.0, ...}}}
        >>> runtime = extract_runtime_state(full_state)
        >>> runtime["drives"]["CARE"]["pressure"]
        22.0
    """
    runtime_state = create_default_runtime_state()

    # Copy timestamp if available
    if "last_tick" in full_drives_state:
        runtime_state["last_tick"] = full_drives_state["last_tick"]

    # Extract only runtime values from each drive
    full_drives = full_drives_state.get("drives", {})
    for name, drive in full_drives.items():
        runtime_drive: DriveRuntimeState = {
            "pressure": drive.get("pressure", 0.0),
            "threshold": drive.get("threshold", 20.0),
            "status": "building",  # Default status
        }

        # Determine status based on pressure vs threshold
        if drive.get("pressure", 0.0) >= drive.get("threshold", 20.0):
            runtime_drive["status"] = "triggered"

        # Include short description (first 100 chars, not full prompt)
        full_desc = drive.get("description", "")
        if full_desc:
            # Truncate to ~100 chars, breaking at word boundary
            if len(full_desc) > 100:
                truncated = full_desc[:97].rsplit(" ", 1)[0] + "..."
                runtime_drive["description"] = truncated
            else:
                runtime_drive["description"] = full_desc

        # Include last_triggered if available
        if "last_triggered" in drive and drive["last_triggered"]:
            runtime_drive["last_triggered"] = drive["last_triggered"]

        runtime_state["drives"][name] = runtime_drive

    return runtime_state


def load_runtime_state(state_path: Path) -> DrivesRuntimeState:
    """Load lightweight runtime state from JSON file.

    Falls back to extracting from full drives.json if runtime
    state file doesn't exist.

    Args:
        state_path: Path to the runtime state JSON file

    Returns:
        DrivesRuntimeState with loaded or default values
    """
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass

    # Try to extract from full drives.json
    full_state_path = state_path.parent / "drives.json"
    if full_state_path.exists():
        try:
            with open(full_state_path, "r", encoding="utf-8") as f:
                full_state = json.load(f)
            return extract_runtime_state(full_state)
        except (json.JSONDecodeError, IOError):
            pass

    # Return empty default
    return create_default_runtime_state()


def save_runtime_state(state_path: Path, state: DrivesRuntimeState) -> None:
    """Save lightweight runtime state to JSON file.

    Uses atomic write pattern for crash safety.

    Args:
        state_path: Target path for the state file
        state: DrivesRuntimeState to save
    """
    # Ensure parent directory exists
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Update timestamp
    state["last_tick"] = datetime.now(timezone.utc).isoformat()

    # Write to temp file
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
