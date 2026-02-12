"""Core drive defaults — loading and protection logic.

Provides functions to load core drive definitions from defaults.json,
ensure their presence in state, protect them from deletion/modification,
and merge human overrides from configuration.

Core drives (CARE, MAINTENANCE, REST) are universal and non-deletable.
They exist for every agent from initialization and persist for the
agent's entire lifecycle. Humans can adjust rate and threshold but
cannot remove core drives or change their category.
"""

import json
from pathlib import Path
from typing import Optional

from .models import DriveState, Drive


# Core drive names that are non-deletable
CORE_DRIVE_NAMES = {"CARE", "MAINTENANCE", "REST", "WANDER"}

# Core drives gated behind conditions (not added until condition is met)
GATED_DRIVES = {"WANDER": "first_light_complete"}

# Fields humans are allowed to override in emergence.yaml
ALLOWED_OVERRIDE_FIELDS = {"threshold", "rate_per_hour", "prompt"}


def _is_first_light_complete() -> bool:
    """Check if First Light has been completed.
    
    Reads the first-light.json state file to determine if the agent
    has graduated from First Light.
    
    Returns:
        True if First Light is completed/graduated, False otherwise
    """
    import os
    
    # Search for first-light.json in common locations
    home = Path.home()
    candidates = [
        home / ".openclaw" / "state" / "first-light.json",
        home / ".openclaw" / "workspace" / ".emergence" / "state" / "first-light.json",
        home / ".emergence" / "state" / "first-light.json",
    ]
    
    # Also check from config if available
    try:
        config = load_config()
        state_dir = config.get("paths", {}).get("state", ".emergence/state")
        workspace = config.get("paths", {}).get("workspace", ".")
        config_path = find_config()
        if config_path:
            base = config_path.parent
            candidates.insert(0, (base / workspace / state_dir / "first-light.json").resolve())
    except Exception:
        pass
    
    for path in candidates:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.loads(f.read())
                return data.get("status") in ("completed", "graduated")
            except Exception:
                continue
    
    return False


def get_defaults_path() -> Path:
    """Get the path to defaults.json (alongside this module)."""
    return Path(__file__).parent / "defaults.json"


def load_core_drives(defaults_path: Optional[Path] = None) -> dict[str, Drive]:
    """Load core drive definitions from defaults.json.
    
    Reads the JSON defaults file and converts it to full Drive objects
    with all required fields populated. Core drives are initialized
    with zero pressure and marked as category="core", created_by="system".
    
    Args:
        defaults_path: Path to defaults.json, or None to use default location
        
    Returns:
        Dictionary mapping drive names to Drive dictionaries
        
    Raises:
        FileNotFoundError: If defaults.json cannot be found
        json.JSONDecodeError: If defaults.json contains invalid JSON
        ValueError: If defaults.json is missing required 'drives' section
        
    Examples:
        >>> drives = load_core_drives()
        >>> "CARE" in drives
        True
        >>> drives["CARE"]["category"]
        'core'
    """
    if defaults_path is None:
        defaults_path = get_defaults_path()
    
    with open(defaults_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    parsed = json.loads(content)
    
    if "drives" not in parsed:
        raise ValueError("defaults.json missing 'drives' section")
    
    defaults: dict[str, Drive] = {}
    
    for name, config in parsed["drives"].items():
        # Build complete Drive object with all required fields
        drive: Drive = {
            "name": name,
            "pressure": 0.0,
            "threshold": float(config["threshold"]),
            "rate_per_hour": float(config["rate_per_hour"]),
            "description": config["description"],
            "prompt": config["prompt"],
            "category": "core",
            "created_by": "system",
            "satisfaction_events": [],
            "discovered_during": None,
            "activity_driven": config.get("activity_driven", False),
        }
        # Carry forward optional fields
        if "min_interval_seconds" in config:
            drive["min_interval_seconds"] = config["min_interval_seconds"]
        if "gated_until" in config:
            drive["gated_until"] = config["gated_until"]
        defaults[name] = drive
    
    return defaults


def is_core_drive(name: str) -> bool:
    """Check if a drive name is a core (non-deletable) drive.
    
    Args:
        name: Drive name to check
        
    Returns:
        True if the drive is a core drive, False otherwise
        
    Examples:
        >>> is_core_drive("CARE")
        True
        >>> is_core_drive("CURIOSITY")
        False
    """
    return name in CORE_DRIVE_NAMES


def ensure_core_drives(state: DriveState) -> bool:
    """Verify core drives exist in state, add any that are missing.
    
    This function ensures state integrity by:
    1. Checking for missing core drives and adding them at zero pressure
    2. Restoring category="core" and created_by="system" if modified
    3. Ensuring all required fields are present
    
    Args:
        state: Current drive state (modified in place)
        
    Returns:
        True if any changes were made to state, False if unchanged
        
    Examples:
        >>> state = {"drives": {}, "triggered_drives": []}
        >>> ensure_core_drives(state)
        True
        >>> "CARE" in state["drives"]
        True
    """
    defaults = load_core_drives()
    drives = state.setdefault("drives", {})
    changed = False
    
    # Check First Light status for gated drives
    first_light_done = _is_first_light_complete()
    
    for name, default_drive in defaults.items():
        # Skip gated drives if condition not met
        gate = GATED_DRIVES.get(name)
        if gate == "first_light_complete" and not first_light_done:
            continue
        
        if name not in drives:
            # Missing core drive — add it fresh
            drives[name] = default_drive.copy()
            changed = True
        else:
            # Existing drive — ensure protected fields are correct
            existing = drives[name]
            
            # Restore category and created_by if tampered with
            if existing.get("category") != "core":
                existing["category"] = "core"
                changed = True
            if existing.get("created_by") != "system":
                existing["created_by"] = "system"
                changed = True
            
            # Ensure all required fields exist (use defaults if missing)
            for field, default_value in default_drive.items():
                if field not in existing:
                    existing[field] = default_value
                    changed = True
    
    return changed


def merge_human_overrides(defaults: dict[str, Drive], overrides: dict) -> dict[str, Drive]:
    """Merge human overrides from emergence.yaml into core drive defaults.
    
    Humans can adjust certain fields of core drives via configuration:
    - threshold: Trigger point for the drive
    - rate_per_hour: Pressure accumulation rate
    - prompt: Instructions when drive triggers
    
    Humans CANNOT:
    - Remove core drives
    - Change category from "core"
    - Change created_by from "system"
    - Add new drives via overrides
    
    Args:
        defaults: Core drive defaults from load_core_drives()
        overrides: Override dict from config (e.g., config.get("drives", {}).get("core_overrides", {}))
        
    Returns:
        New dictionary with overrides applied to defaults
        
    Examples:
        >>> defaults = load_core_drives()
        >>> overrides = {"CARE": {"threshold": 15, "rate_per_hour": 3.0}}
        >>> merged = merge_human_overrides(defaults, overrides)
        >>> merged["CARE"]["threshold"]
        15.0
        >>> merged["CARE"]["category"]  # Unchanged
        'core'
    """
    # Create a deep copy to avoid modifying the input
    result: dict[str, Drive] = {}
    for name, drive in defaults.items():
        result[name] = drive.copy()
    
    for name, override in overrides.items():
        # Skip unknown drives — can't add new ones via override
        if name not in result:
            continue
        
        # Only apply allowed field overrides
        for field, value in override.items():
            if field in ALLOWED_OVERRIDE_FIELDS:
                # Convert numeric fields to float
                if field in ("threshold", "rate_per_hour"):
                    result[name][field] = float(value)  # type: ignore[literal-required]
                else:
                    result[name][field] = value  # type: ignore[literal-required]
    
    return result


def get_core_drive_template(name: str) -> Optional[Drive]:
    """Get a fresh template for a single core drive.
    
    Useful for recreating a specific core drive if it was corrupted
    or manually deleted.
    
    Args:
        name: Name of the core drive (CARE, MAINTENANCE, REST)
        
    Returns:
        Drive template dictionary, or None if not a core drive
        
    Examples:
        >>> care = get_core_drive_template("CARE")
        >>> care["threshold"]
        20.0
        >>> get_core_drive_template("NOT_CORE")
        None
    """
    if not is_core_drive(name):
        return None
    
    defaults = load_core_drives()
    return defaults.get(name, {}).copy()


def validate_core_overrides(overrides: dict) -> list[str]:
    """Validate human overrides and return list of any errors or warnings.
    
    Checks that overrides don't try to modify protected fields
    and that numeric values are reasonable.
    
    Args:
        overrides: The core_overrides dict from config
        
    Returns:
        List of error/warning message strings (empty if valid)
        
    Examples:
        >>> validate_core_overrides({"CARE": {"threshold": 10}})
        []
        >>> validate_core_overrides({"UNKNOWN": {"threshold": 10}})
        ["Unknown drive in overrides: UNKNOWN (ignored)"]
    """
    errors = []
    
    for name, override in overrides.items():
        if not is_core_drive(name):
            errors.append(f"Unknown drive in overrides: {name} (ignored)")
            continue
        
        for field, value in override.items():
            if field not in ALLOWED_OVERRIDE_FIELDS:
                errors.append(
                    f"Cannot override '{field}' for {name} — field is protected"
                )
                continue
            
            # Validate numeric fields
            if field in ("threshold", "rate_per_hour"):
                try:
                    float_value = float(value)
                    if float_value < 0:
                        errors.append(
                            f"Invalid value for {name}.{field}: must be non-negative"
                        )
                    elif field == "threshold" and float_value == 0:
                        errors.append(
                            f"Warning: {name}.threshold=0 means drive never triggers"
                        )
                except (ValueError, TypeError):
                    errors.append(
                        f"Invalid value for {name}.{field}: must be a number"
                    )
    
    return errors
