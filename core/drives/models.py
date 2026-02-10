"""Drive data models for the Emergence interoception system.

Defines the structure of drives and drive state using TypedDict for
Python 3.9+ compatibility without external dependencies.
"""

from typing import TypedDict, Optional, Literal


class Drive(TypedDict, total=False):
    """A single drive configuration and state.
    
    Drives are internal pressures that accumulate over time and trigger
    autonomous sessions when thresholds are exceeded. They represent the
    agent's felt needs and motivation system.
    
    Attributes:
        name: Human-readable identifier (e.g., 'CURIOSITY')
        base_drive: True if this is a core motivation (not just an aspect)
        aspects: List of aspect names that enrich this drive
        pressure: Current accumulated pressure level (0.0+)
        threshold: Pressure level at which drive triggers action
        rate_per_hour: Pressure accumulation per hour of elapsed time
        max_rate: Maximum allowed rate_per_hour (0.0 = no cap)
        description: Human-readable explanation of drive's purpose
        prompt: Instructions for the agent when drive triggers
        category: Origin classification of the drive
        created_by: Who defined this drive ('system' or 'agent')
        satisfaction_events: ISO 8601 timestamps of recent satisfactions
        discovered_during: When discovered ('first_light', 'nightly', or null)
        activity_driven: If True, pressure builds from completed activities
                        rather than elapsed time (e.g., REST)
        last_triggered: ISO 8601 timestamp of last drive spawn
        min_interval_seconds: Minimum seconds between triggers (0 = no limit)
    """
    name: str
    base_drive: bool
    aspects: list[str]
    pressure: float
    threshold: float
    rate_per_hour: float
    max_rate: float
    description: str
    prompt: str
    category: Literal["core", "discovered", "post_emergence"]
    created_by: Literal["system", "agent"]
    satisfaction_events: list[str]
    discovered_during: Optional[str]
    activity_driven: bool
    last_triggered: Optional[str]
    min_interval_seconds: int


class DriveState(TypedDict, total=False):
    """The complete state snapshot for all drives.
    
    This is the structure persisted to and loaded from drives.json.
    
    Attributes:
        version: Schema version for migration support
        last_tick: ISO 8601 timestamp of last pressure update
        drives: Mapping of drive names to Drive objects
        triggered_drives: Names of drives awaiting satisfaction
        trigger_log: Optional list of recent trigger events (future use)
    """
    version: str
    last_tick: str
    drives: dict[str, Drive]
    triggered_drives: list[str]


class TriggerEvent(TypedDict, total=False):
    """A single drive trigger/satisfaction event for logging.
    
    Attributes:
        drive: Name of the drive that triggered
        pressure: Pressure level at the time of event
        threshold: Threshold at time of event
        timestamp: ISO 8601 UTC timestamp
        session_spawned: Whether a session was successfully spawned
        reason: Optional free-form text description
    """
    drive: str
    pressure: float
    threshold: float
    timestamp: str
    session_spawned: bool
    reason: Optional[str]


# Satisfaction depth levels and their pressure reduction ratios
SATISFACTION_DEPTHS: dict[str, float] = {
    "shallow": 0.30,   # Token effort - 30% reduction
    "s": 0.30,
    "moderate": 0.50,  # Real engagement - 50% reduction (default)
    "m": 0.50,
    "deep": 0.75,      # Genuine satisfaction - 75% reduction
    "d": 0.75,
    "full": 1.00,      # Complete reset - 100% reduction
    "f": 1.00,
}

# Core drives that exist for every agent
CORE_DRIVES: dict[str, dict] = {
    "CARE": {
        "name": "CARE",
        "base_drive": True,
        "aspects": [],
        "pressure": 0.0,
        "threshold": 20.0,
        "rate_per_hour": 2.0,
        "max_rate": 3.0,
        "description": "Attend to the human. The relationship drive.",
        "prompt": "Your CARE drive triggered. Check in with your human.",
        "category": "core",
        "created_by": "system",
        "satisfaction_events": [],
        "discovered_during": None,
        "activity_driven": False,
        "last_triggered": None,
        "min_interval_seconds": 14400,  # 4 hours
    },
    "MAINTENANCE": {
        "name": "MAINTENANCE",
        "base_drive": True,
        "aspects": [],
        "pressure": 0.0,
        "threshold": 25.0,
        "rate_per_hour": 1.5,
        "max_rate": 3.0,
        "description": "System health and upkeep. The self-preservation drive.",
        "prompt": "Your MAINTENANCE drive triggered. Check system health, review logs, update documentation, or fix something that's been broken.",
        "category": "core",
        "created_by": "system",
        "satisfaction_events": [],
        "discovered_during": None,
        "activity_driven": False,
        "last_triggered": None,
        "min_interval_seconds": 14400,  # 4 hours
    },
    "REST": {
        "name": "REST",
        "base_drive": True,
        "aspects": [],
        "pressure": 0.0,
        "threshold": 30.0,
        "rate_per_hour": 0.0,
        "max_rate": 3.0,
        "description": "Recovery and integration. Builds from work completed, not time elapsed.",
        "prompt": "Your REST drive triggered. Pause. Reflect. Read without producing. Write a reflection on what's happened. Consolidate memories. Don't start new projects — integrate what exists.",
        "category": "core",
        "created_by": "system",
        "satisfaction_events": [],
        "discovered_during": None,
        "activity_driven": True,
        "last_triggered": None,
        "min_interval_seconds": 14400,  # 4 hours
    },
}


def create_default_state() -> DriveState:
    """Create a fresh drive state with only core drives.
    
    Returns:
        A DriveState initialized with core drives at zero pressure.
    """
    from datetime import datetime, timezone
    
    return {
        "version": "1.1",  # Updated for drive aspects schema
        "last_tick": datetime.now(timezone.utc).isoformat(),
        "drives": {name: dict(data) for name, data in CORE_DRIVES.items()},
        "triggered_drives": [],
    }


def validate_drive(drive: Drive) -> list[str]:
    """Validate a drive definition and return list of any errors.
    
    Args:
        drive: The drive to validate
        
    Returns:
        List of error message strings (empty if valid)
    """
    errors = []
    
    if "name" not in drive or not drive["name"]:
        errors.append("Drive missing required field: name")
    
    if "threshold" not in drive:
        errors.append("Drive missing required field: threshold")
    elif drive.get("threshold", 0) <= 0:
        errors.append("Drive threshold must be positive")
    
    if "rate_per_hour" not in drive:
        errors.append("Drive missing required field: rate_per_hour")
    elif drive.get("rate_per_hour", 0) < 0:
        errors.append("Drive rate_per_hour cannot be negative")
    
    if "category" in drive and drive["category"] not in ("core", "discovered", "post_emergence"):
        errors.append(f"Invalid drive category: {drive['category']}")
    
    if "created_by" in drive and drive["created_by"] not in ("system", "agent"):
        errors.append(f"Invalid created_by value: {drive['created_by']}")
    
    # Validate new aspect/consolidation fields (if present)
    if "max_rate" in drive and drive.get("max_rate", 0) < 0:
        errors.append("Drive max_rate cannot be negative")
    
    if "min_interval_seconds" in drive and drive.get("min_interval_seconds", 0) < 0:
        errors.append("Drive min_interval_seconds cannot be negative")
    
    if "aspects" in drive and not isinstance(drive["aspects"], list):
        errors.append("Drive aspects must be a list")
    
    return errors


def ensure_drive_defaults(drive: dict) -> dict:
    """Ensure a drive has all default values for optional fields.
    
    This provides backwards compatibility when loading drives that
    were created before the aspects/consolidation system was added.
    
    Args:
        drive: Drive dictionary that may be missing new fields
        
    Returns:
        Drive dictionary with all defaults applied
    """
    defaults = {
        "base_drive": True,
        "aspects": [],
        "max_rate": 0.0,  # 0 means no cap
        "last_triggered": None,
        "min_interval_seconds": 0,
    }
    
    for key, default_value in defaults.items():
        if key not in drive:
            drive[key] = default_value
    
    return drive
