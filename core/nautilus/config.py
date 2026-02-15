#!/usr/bin/env python3
"""
Nautilus configuration and path management.
Handles backward compatibility with standalone nautilus and emergence integration.
"""

import os
import json
from pathlib import Path


def get_workspace():
    """Get workspace directory with fallback chain."""
    # 1. Explicit OPENCLAW_WORKSPACE env variable
    if "OPENCLAW_WORKSPACE" in os.environ:
        return Path(os.environ["OPENCLAW_WORKSPACE"])
    
    # 2. Emergence config file
    config_path = Path.home() / ".openclaw" / "workspace" / "projects" / "emergence" / "emergence.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                if "paths" in config and "workspace" in config["paths"]:
                    return Path(config["paths"]["workspace"])
        except (json.JSONDecodeError, KeyError):
            pass
    
    # 3. Default openclaw workspace
    return Path.home() / ".openclaw" / "workspace"


def get_state_dir():
    """Get state directory with fallback chain."""
    # 1. Explicit EMERGENCE_STATE env variable
    if "EMERGENCE_STATE" in os.environ:
        return Path(os.environ["EMERGENCE_STATE"])
    
    # 2. Emergence config file
    config_path = Path.home() / ".openclaw" / "workspace" / "projects" / "emergence" / "emergence.json"
    if config_path.exists():
        try:
            with open(config_path) as f:
                config = json.load(f)
                if "paths" in config and "state" in config["paths"]:
                    return Path(config["paths"]["state"])
        except (json.JSONDecodeError, KeyError):
            pass
    
    # 3. Default state directory
    return Path.home() / ".openclaw" / "state"


def get_config():
    """
    Load nautilus configuration from emergence.json.
    
    Returns dict with:
        - enabled: bool
        - gravity_db: Path
        - memory_dir: str (relative to workspace)
        - auto_classify: bool
        - decay_interval_hours: int
        - chamber_thresholds: dict
    """
    config_path = Path.home() / ".openclaw" / "workspace" / "projects" / "emergence" / "emergence.json"
    
    # Defaults
    defaults = {
        "enabled": True,
        "gravity_db": get_state_dir() / "nautilus" / "gravity.db",
        "memory_dir": "memory",
        "auto_classify": True,
        "decay_interval_hours": 168,  # Weekly
        "chamber_thresholds": {
            "atrium_max_age_hours": 48,
            "corridor_max_age_days": 7
        },
        "decay_rate": 0.05,
        "recency_half_life_days": 14,
        "authority_boost": 0.3,
        "mass_cap": 100.0
    }
    
    if not config_path.exists():
        return defaults
    
    try:
        with open(config_path) as f:
            config = json.load(f)
            if "nautilus" in config:
                nautilus_config = config["nautilus"]
                # Merge with defaults
                for key, value in nautilus_config.items():
                    defaults[key] = value
    except (json.JSONDecodeError, KeyError, IOError):
        pass
    
    return defaults


def get_db_path():
    """Get the gravity.db path, checking for migrations."""
    config = get_config()
    db_path_str = config["gravity_db"]
    
    # Expand ~ and convert to Path
    db_path = Path(db_path_str).expanduser()
    
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    return db_path


def get_legacy_db_paths():
    """Get potential legacy database locations for migration."""
    workspace = get_workspace()
    
    potential_paths = [
        workspace / "tools" / "nautilus" / "gravity.db",
        Path(__file__).parent / "gravity.db",  # Next to this script (old standalone)
    ]
    
    return [p for p in potential_paths if p.exists() and p != get_db_path()]
