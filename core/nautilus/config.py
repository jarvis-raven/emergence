"""
Nautilus Configuration — Path resolution and settings.

Provides portable path resolution for the Nautilus memory system.
Works across different agent installations with no hardcoded paths.
"""

import os
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Any

# Use standard logging (logging_config imports this module, avoid circular import)
logger = logging.getLogger("nautilus.config")

# Environment variable names
ENV_WORKSPACE = "OPENCLAW_WORKSPACE"
ENV_STATE_DIR = "OPENCLAW_STATE_DIR"

# Default relative paths
DEFAULT_MEMORY_DIR = "memory"
DEFAULT_STATE_SUBDIR = "nautilus"
DEFAULT_DB_NAME = "gravity.db"

# Config file paths (in order of precedence)
# Get the project root (where this package lives)
PROJECT_ROOT = Path(__file__).parent.parent.parent

CONFIG_PATHS = [
    Path.home() / ".openclaw" / "config" / "emergence.json",
    Path.home() / ".openclaw" / "emergence.json",
    PROJECT_ROOT / "emergence.json",
    Path("emergence.json"),
]


def _get_config() -> Dict[str, Any]:
    """
    Load emergence.json config if available.

    Returns:
        Dictionary containing config data, or empty dict if not found.
    """
    for path in CONFIG_PATHS:
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    config_data = json.load(f)
                    logger.debug(f"Loaded config from {path}")
                    return config_data
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON in config file {path}: {e}")
                continue
            except IOError as e:
                logger.warning(f"Could not read config file {path}: {e}")
                continue

    logger.debug("No config file found, using defaults")
    return {}


def get_workspace() -> Path:
    """
    Get the workspace directory.

    Resolution order:
    1. OPENCLAW_WORKSPACE environment variable
    2. Config file workspace setting
    3. Inferred from package location
    4. Current working directory

    Returns:
        Path object representing the workspace directory.
    """
    # 1. Environment variable
    if ENV_WORKSPACE in os.environ:
        path = Path(os.environ[ENV_WORKSPACE])
        if path.exists():
            logger.debug(f"Using workspace from env: {path}")
            return path.resolve()
        else:
            logger.warning(f"Workspace path from env does not exist: {path}")

    # 2. Config file
    config = _get_config()
    if "workspace" in config:
        path = Path(config["workspace"]).expanduser()
        if path.exists():
            logger.debug(f"Using workspace from config: {path}")
            return path.resolve()
        else:
            logger.warning(f"Workspace path from config does not exist: {path}")

    # 3. Infer from package location
    # core/nautilus/config.py -> workspace
    try:
        package_dir = Path(__file__).parent  # core/nautilus/
        core_dir = package_dir.parent  # core/
        workspace = core_dir.parent  # workspace root
        if workspace.exists():
            logger.debug(f"Using inferred workspace: {workspace}")
            return workspace.resolve()
    except (NameError, OSError) as e:
        logger.debug(f"Could not infer workspace from package location: {e}")

    # 4. Current working directory
    cwd = Path.cwd().resolve()
    logger.debug(f"Using current directory as workspace: {cwd}")
    return cwd


def get_state_dir() -> Path:
    """
    Get the state directory for nautilus data (gravity.db, etc.).

    Resolution order:
    1. OPENCLAW_STATE_DIR environment variable
    2. Config file: nautilus.state_dir or nautilus.gravity_db
    3. ~/.openclaw/state/nautilus/
    4. <workspace>/state/nautilus/

    Returns:
        Path object representing the state directory.
    """
    # 1. Environment variable
    if ENV_STATE_DIR in os.environ:
        path = Path(os.environ[ENV_STATE_DIR])
        expanded = path.expanduser().resolve()
        logger.debug(f"Using state dir from env: {expanded}")
        return expanded

    # 2. Config file
    config = _get_config()
    nautilus_config = config.get("nautilus", {})

    if "state_dir" in nautilus_config:
        path = Path(nautilus_config["state_dir"]).expanduser()
        logger.debug(f"Using state dir from config: {path}")
        return path.resolve()

    if "gravity_db" in nautilus_config:
        # Extract directory from full path
        path = Path(nautilus_config["gravity_db"]).expanduser().parent
        logger.debug(f"Using state dir from gravity_db path: {path}")
        return path.resolve()

    # 3. Default: ~/.openclaw/state/nautilus/
    default_path = Path.home() / ".openclaw" / "state" / DEFAULT_STATE_SUBDIR
    try:
        default_path.mkdir(parents=True, exist_ok=True)
        logger.debug(f"Using default state dir: {default_path}")
    except OSError as e:
        logger.error(f"Could not create state directory {default_path}: {e}")
        # Fall back to workspace/state if home directory fails
        fallback = get_workspace() / "state" / DEFAULT_STATE_SUBDIR
        fallback.mkdir(parents=True, exist_ok=True)
        logger.info(f"Using fallback state dir: {fallback}")
        return fallback

    return default_path


def get_gravity_db_path() -> Path:
    """
    Get the path to the gravity database file.

    Returns:
        Path object representing the gravity database file.
    """
    state_dir = get_state_dir()
    db_path = state_dir / DEFAULT_DB_NAME
    logger.debug(f"Gravity DB path: {db_path}")
    return db_path


def get_memory_dir() -> Path:
    """
    Get the memory directory path.

    Resolution order:
    1. Config file: nautilus.memory_dir
    2. <workspace>/memory/

    Returns:
        Path object representing the memory directory.
    """
    config = _get_config()
    nautilus_config = config.get("nautilus", {})

    if "memory_dir" in nautilus_config:
        path = Path(nautilus_config["memory_dir"]).expanduser()
        if path.is_absolute():
            logger.debug(f"Using absolute memory dir from config: {path}")
            return path.resolve()
        else:
            resolved = (get_workspace() / path).resolve()
            logger.debug(f"Using relative memory dir from config: {resolved}")
            return resolved

    default_path = get_workspace() / DEFAULT_MEMORY_DIR
    logger.debug(f"Using default memory dir: {default_path}")
    return default_path


def get_corridors_dir() -> Path:
    """
    Get the corridors directory (summarized memories).

    Returns:
        Path object representing the corridors directory.
    """
    return get_memory_dir() / "corridors"


def get_vaults_dir() -> Path:
    """
    Get the vaults directory (distilled lessons).

    Returns:
        Path object representing the vaults directory.
    """
    return get_memory_dir() / "vaults"


def get_nautilus_config() -> Dict[str, Any]:
    """
    Get the nautilus-specific configuration section.

    Returns:
        Dictionary containing nautilus configuration, or empty dict.
    """
    config = _get_config()
    return config.get("nautilus", {})


def is_auto_classify_enabled() -> bool:
    """
    Check if auto-classify is enabled in config.

    Returns:
        True if auto-classify is enabled (default), False otherwise.
    """
    nautilus_cfg = get_nautilus_config()
    enabled = nautilus_cfg.get("auto_classify", True)
    logger.debug(f"Auto-classify enabled: {enabled}")
    return enabled


def get_decay_interval_hours() -> int:
    """
    Get the decay interval in hours.

    Returns:
        Decay interval in hours (default: 168 = 1 week).
    """
    nautilus_cfg = get_nautilus_config()
    interval = nautilus_cfg.get("decay_interval_hours", 168)
    logger.debug(f"Decay interval: {interval} hours")
    return interval


# Legacy path for migration
LEGACY_DB_PATH = Path("/Users/jarvis/.openclaw/workspace/tools/nautilus/gravity.db")


def migrate_legacy_db() -> bool:
    """
    Migrate gravity.db from legacy location to new state directory.

    Returns:
        True if migration was performed, False otherwise.
    """
    new_path = get_gravity_db_path()

    # Check if already at new location
    if new_path.exists():
        logger.debug("Database already at new location, skipping migration")
        return False

    # Check for legacy location
    if LEGACY_DB_PATH.exists():
        try:
            new_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(LEGACY_DB_PATH, new_path)
            logger.info(f"Migrated gravity.db from {LEGACY_DB_PATH} to {new_path}")
            return True
        except (OSError, shutil.Error) as e:
            logger.error(f"Failed to migrate database from {LEGACY_DB_PATH}: {e}")
            return False

    # Check for other potential legacy locations
    for parent in [
        Path(__file__).parent,
        Path(__file__).parent.parent.parent / "tools" / "nautilus",
    ]:
        legacy = parent / "gravity.db"
        if legacy.exists():
            try:
                new_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(legacy, new_path)
                logger.info(f"Migrated gravity.db from {legacy} to {new_path}")
                return True
            except (OSError, shutil.Error) as e:
                logger.error(f"Failed to migrate database from {legacy}: {e}")
                continue

    logger.debug("No legacy database found to migrate")
    return False
