"""Configuration loading for the Dream Engine.

Loads and validates emergence.json with comment support and defaults.
"""

import json
import sys
from pathlib import Path
from typing import Optional


# Default configuration values
DEFAULT_CONFIG: dict = {
    "agent": {
        "name": "My Agent",
        "model": "anthropic/claude-sonnet-4-20250514",
    },
    "memory": {
        "daily_dir": "memory",
        "dream_dir": "memory/dreams",
    },
    "lifecycle": {
        "dream_hour": 4,
    },
    "dream_engine": {
        "lookback_days": 7,
        "concepts_per_run": 50,
        "pairs_to_generate": 8,
        "min_concept_length": 3,
    },
    "paths": {
        "workspace": ".",
        "state": ".emergence/state",
        "identity": ".",
    },
}


def strip_comments(content: str) -> str:
    """Remove comments from JSON config to enable human-friendly editing.
    
    Supports both // and # style comments. Comments must start at the
    beginning of a line (after optional whitespace) to be stripped.
    
    Args:
        content: Raw file content potentially containing comment lines
        
    Returns:
        Content with comment lines removed
    """
    lines = []
    for line in content.split("\n"):
        stripped = line.strip()
        if not stripped.startswith("//") and not stripped.startswith("#"):
            lines.append(line)
    return "\n".join(lines)


def find_config(start_path: Optional[Path] = None) -> Optional[Path]:
    """Find emergence.json config file searching upward from start path.
    
    Search order:
    1. Start path (or current directory)
    2. Parent directories up to root
    3. ~/.emergence/ directory
    
    Args:
        start_path: Where to start searching (default: current directory)
        
    Returns:
        Path to config file, or None if not found
    """
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
    
    # Merge with defaults (deep merge for nested dicts)
    merged = DEFAULT_CONFIG.copy()
    for key, value in loaded.items():
        if isinstance(value, dict) and key in merged and isinstance(merged[key], dict):
            merged[key] = {**merged[key], **value}
        else:
            merged[key] = value
    
    return merged


def get_dream_dir(config: dict) -> Path:
    """Resolve dream output directory from configuration.
    
    Args:
        config: The configuration dictionary
        
    Returns:
        Resolved Path object for the dream directory
    """
    workspace = config.get("paths", {}).get("workspace", ".")
    dream_dir = config.get("memory", {}).get("dream_dir", "memory/dreams")
    return Path(workspace) / dream_dir


def get_memory_dir(config: dict) -> Path:
    """Resolve daily memory directory from configuration.
    
    Args:
        config: The configuration dictionary
        
    Returns:
        Resolved Path object for the memory directory
    """
    workspace = config.get("paths", {}).get("workspace", ".")
    memory_dir = config.get("memory", {}).get("daily_dir", "memory")
    return Path(workspace) / memory_dir


def get_dream_engine_config(config: dict) -> dict:
    """Extract dream engine specific configuration.
    
    Args:
        config: The full configuration dictionary
        
    Returns:
        Dictionary with dream engine settings
    """
    defaults = DEFAULT_CONFIG["dream_engine"]
    return config.get("dream_engine", defaults)
