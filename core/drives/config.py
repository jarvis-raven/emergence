"""Configuration loading for the drive engine.

Loads and validates emergence.json with comment support and defaults.
"""

import json
import os
import sys
from pathlib import Path
from typing import Optional


# Default graduated thresholds for all drives
DEFAULT_THRESHOLDS: dict = {
    "available": 0.30,    # 30% - Drive is available but not pressing
    "elevated": 0.75,     # 75% - Drive is building, noticeable
    "triggered": 1.0,     # 100% - Drive triggers action (old threshold)
    "crisis": 1.5,        # 150% - High urgency, sustained neglect
    "emergency": 2.0,     # 200% - Critical, needs immediate attention
}

# Default configuration values
DEFAULT_CONFIG: dict = {
    "agent": {
        "name": "My Agent",
        "model": "anthropic/claude-sonnet-4-20250514",
    },
    "drives": {
        "tick_interval": 900,       # 15 minutes in seconds
        "quiet_hours": [23, 7],     # 11 PM to 7 AM
        "daemon_mode": True,
        "cooldown_minutes": 30,     # Minimum between triggers
        "max_pressure_ratio": 1.5,  # Cap pressure at threshold * 1.5
        "manual_mode": False,       # If True, disable auto-spawn (v0.3.0+)
        "emergency_spawn": True,    # Auto-spawn at 200%+ even in manual mode (safety valve)
        "emergency_threshold": 2.0, # Pressure ratio that triggers emergency spawn
        "emergency_cooldown_hours": 6,  # Max 1 emergency spawn per drive per N hours
        "thresholds": DEFAULT_THRESHOLDS.copy(),  # Global threshold ratios
    },
    "paths": {
        "workspace": ".",
        "state": ".emergence/state",
        "identity": ".",
    },
}


def strip_comments(content: str) -> str:
    """Remove comments from JSON config to enable human-friendly editing.
    
    Strips both // and # style comments:
    - Full-line comments (line starts with // or #)
    - Inline comments after values (e.g. "key": "value"  // comment)
    
    Args:
        content: Raw file content potentially containing comment lines
        
    Returns:
        Content with comments removed
        
    Examples:
        >>> strip_comments('{"key": "value"} // stripped')
        '{"key": "value"} '
        >>> strip_comments('[\\n// This is a comment\\n"value"\\n]')
        '[\\n"value"\\n]'
    """
    import re
    lines = []
    for line in content.split("\n"):
        stripped = line.strip()
        # Skip full-line comments
        if stripped.startswith("//") or stripped.startswith("#"):
            continue
        # Strip inline // comments (not inside strings)
        # Simple heuristic: strip // that appears after a comma, bracket, or value
        line = re.sub(r'\s*//[^"]*$', '', line)
        lines.append(line)
    return "\n".join(lines)


def find_config(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find emergence.json config file searching upward from start path.
    
    Search order:
    0. EMERGENCE_CONFIG environment variable (if set)
    1. Start path (or current directory)
    2. Parent directories up to root
    3. ~/.openclaw/workspace/ directory
    4. ~/.emergence/ directory
    
    Args:
        start_path: Where to start searching (default: current directory)
        
    Returns:
        Path to config file, or None if not found
    """
    # Check EMERGENCE_CONFIG env var first
    env_config = os.environ.get("EMERGENCE_CONFIG")
    if env_config:
        env_path = Path(env_config)
        if env_path.exists():
            return env_path
    
    if start_path is None:
        start_path = Path.cwd()
    
    config_name = "emergence.json"
    
    # Search upward from start path
    current = start_path.resolve()
    for _ in range(100):  # Prevent infinite loops
        config_path = current / config_name
        if config_path.exists():
            return config_path
        
        parent = current.parent
        if parent == current:  # At root
            break
        current = parent
    
    # Fall back to OpenClaw workspace
    env_workspace = os.environ.get("OPENCLAW_WORKSPACE",
                                    str(Path.home() / ".openclaw" / "workspace"))
    workspace_config = Path(env_workspace) / config_name
    if workspace_config.exists():
        return workspace_config
    
    # Fall back to ~/.emergence/
    home_config = Path.home() / ".emergence" / config_name
    if home_config.exists():
        return home_config
    
    return None


def load_config(path: Optional[Path] = None) -> dict:
    """Load and validate configuration from emergence.json.
    
    Merges loaded config with defaults for any missing values.
    Strips comments before parsing.
    
    Args:
        path: Explicit config path, or None to search
        
    Returns:
        Validated configuration dictionary with defaults applied
        
    Raises:
        SystemExit: If config file exists but contains invalid JSON
        
    Examples:
        >>> config = load_config(Path("./emergence.json"))
        >>> config["agent"]["name"]
        'My Agent'
    """
    if path is None:
        path = find_config()
    
    if path is None or not path.exists():
        # Return defaults if no config found
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw_content = f.read()
    except IOError as e:
        print(f"Error reading config file: {e}", file=sys.stderr)
        return DEFAULT_CONFIG.copy()
    
    # Strip comments and parse
    clean_content = strip_comments(raw_content)
    
    try:
        loaded = json.loads(clean_content)
    except json.JSONDecodeError as e:
        print(f"Config error: {path} is not valid JSON", file=sys.stderr)
        print(f"  Parse error: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Merge with defaults (shallow merge for top-level only)
    merged = DEFAULT_CONFIG.copy()
    for key, value in loaded.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            # Deep merge for nested dicts
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    
    # Store config file location for path resolution
    merged["_config_dir"] = str(path.resolve().parent)
    
    return merged


def validate_config(config: dict) -> list[str]:
    """Validate configuration and return list of errors.
    
    Args:
        config: The configuration dictionary to validate
        
    Returns:
        List of error message strings (empty if valid)
        
    Examples:
        >>> errors = validate_config({"paths": {"workspace": "../outside"}})
        >>> len(errors) > 0
        True
    """
    errors = []
    
    # Check required top-level sections
    if "agent" not in config:
        errors.append("Missing required section: agent")
    elif "name" not in config.get("agent", {}):
        errors.append("Missing required field: agent.name")
    
    # Validate paths are not outside workspace (basic check)
    paths = config.get("paths", {})
    workspace = paths.get("workspace", ".")
    
    for path_name, path_value in paths.items():
        if path_value.startswith("..") or "/.." in path_value:
            errors.append(f"Path '{path_name}' contains '..': {path_value}")
        if path_value.startswith("/") and path_name != "workspace":
            # Absolute paths are generally discouraged but allowed for workspace
            pass
    
    # Validate quiet_hours format
    quiet_hours = config.get("drives", {}).get("quiet_hours")
    if quiet_hours is not None:
        if not isinstance(quiet_hours, (list, tuple)) or len(quiet_hours) != 2:
            errors.append("quiet_hours must be a list of [start_hour, end_hour]")
        else:
            start, end = quiet_hours
            if not (0 <= start <= 23 and 0 <= end <= 23):
                errors.append("quiet_hours hours must be between 0 and 23")
    
    # Validate numeric ranges
    tick_interval = config.get("drives", {}).get("tick_interval")
    if tick_interval is not None and tick_interval < 60:
        errors.append("tick_interval should be at least 60 seconds")
    
    return errors


def resolve_workspace(config: dict) -> Path:
    """Resolve the workspace path from config, relative to config file location.
    
    Args:
        config: Configuration dictionary (with optional _config_dir from load_config)
        
    Returns:
        Absolute workspace path
    """
    config_dir = Path(config.get("_config_dir", "."))
    workspace = Path(config.get("paths", {}).get("workspace", "."))
    if not workspace.is_absolute():
        workspace = config_dir / workspace
    return workspace.resolve()


def get_state_path(config: dict, filename: str = "drives.json") -> Path:
    """Resolve state file path from configuration.
    
    Args:
        config: The configuration dictionary
        filename: State file name (default: drives.json)
        
    Returns:
        Resolved Path object for the state file
        
    Examples:
        >>> config = {"paths": {"state": ".emergence/state", "workspace": "."}}
        >>> get_state_path(config)
        PosixPath('.emergence/state/drives.json')
    """
    state_dir = config.get("paths", {}).get("state", ".emergence/state")
    workspace_path = resolve_workspace(config)
    
    state_path = workspace_path / state_dir / filename
    return state_path.resolve()


def ensure_config_example() -> str:
    """Generate example emergence.json content.
    
    Returns:
        A JSON string with comments showing a complete example config
    """
    return """{
  // Agent identity
  "agent": {
    "name": "My Agent",
    "model": "anthropic/claude-sonnet-4-20250514"
  },

  // Drive engine settings
  "drives": {
    "tick_interval": 900,       // 15 minutes in seconds
    "quiet_hours": [23, 7],     // No triggers 11 PM - 7 AM
    "daemon_mode": true,        // Run as persistent process
    "cooldown_minutes": 30,     // Min time between triggers
    "manual_mode": false        // If true, never auto-spawn (v0.3.0+)
  },

  // Paths (relative to workspace)
  "paths": {
    "workspace": ".",
    "state": ".emergence/state",
    "identity": "."
  }
}
"""
