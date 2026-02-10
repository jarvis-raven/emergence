"""Drive Engine Core — Interoception system for Emergence.

The drive engine provides internal pressure states that accumulate over
time and trigger autonomous sessions when thresholds are exceeded. This
is the "felt needs" layer that gives agents genuine motivation.

Example usage:
    >>> from core.drives import load_config, load_state, tick_with_spawning
    >>> 
    >>> config = load_config()
    >>> state = load_state(config)
    >>> state = tick_with_spawning(config, state)

Modules:
    models: Data structures for drives and state
    config: Configuration loading with comment support
    state: Atomic state persistence
    engine: Pressure accumulation and threshold logic
    spawn: Session spawning for triggered drives
    utils: Fuzzy matching and helpers
    cli: Command-line interface for human interaction
    history: Log reading and filtering for trigger events

CLI Usage:
    python3 -m core.drives [command] [options]
    
    Commands:
        status (default)  Show all drives with pressure bars
        satisfy <name>    Reduce pressure after addressing
        bump <name>       Manually increase pressure
        reset             Zero all pressures
        log               Show trigger/satisfaction history
        tick              Update pressures and check triggers
        list              List all drives with metadata
        show <name>       Show detailed drive info
"""

# Core data models
from .models import (
    Drive,
    DriveState,
    TriggerEvent,
    SATISFACTION_DEPTHS,
    CORE_DRIVES,
    create_default_state,
    validate_drive,
)

# Configuration
from .config import (
    DEFAULT_CONFIG,
    load_config,
    validate_config,
    get_state_path,
    strip_comments,
    find_config,
    ensure_config_example,
)

# State persistence
from .state import (
    load_state,
    save_state,
    get_hours_since_tick,
    StateLock,
)

# Engine logic
from .engine import (
    accumulate_pressure,
    tick_all_drives,
    check_thresholds,
    satisfy_drive,
    bump_drive,
    get_drive_status,
    reset_all_drives,
    is_quiet_hours,
)

# Session spawning
from .spawn import (
    spawn_session,
    build_session_prompt,
    is_quiet_hours,
    check_cooldown,
    record_trigger,
    select_drive_to_trigger,
    handle_spawn_failure,
    tick_with_spawning,
    spawn_via_api,
    spawn_via_cli,
)

# Utilities
from .utils import (
    fuzzy_match,
    get_ambiguous_matches,
    format_pressure_bar,
    normalize_drive_name,
)

# History and logging
from .history import (
    read_trigger_log,
    filter_log_entries,
    add_trigger_event,
    add_satisfaction_event,
    format_log_entry,
    get_stats,
    parse_time_string,
)

# Ingest system
from .ingest import (
    load_experience_content,
    build_analysis_prompt,
    parse_impact_response,
    analyze_with_ollama,
    analyze_with_openrouter,
    analyze_with_keywords,
    analyze_content,
    apply_impacts,
    DRIVE_DESCRIPTIONS,
    DRIVE_KEYWORDS,
)

# Satisfaction system (file-based)
from .satisfaction import (
    write_breadcrumb,
    write_completion,
    check_completed_sessions,
    assess_depth,
    get_ingest_dir,
)

# CLI entry point (for programmatic use)
from .cli import main as cli_main

__version__ = "1.0.0"
__all__ = [
    # Models
    "Drive",
    "DriveState",
    "TriggerEvent",
    "SATISFACTION_DEPTHS",
    "CORE_DRIVES",
    "create_default_state",
    "validate_drive",
    # Config
    "DEFAULT_CONFIG",
    "load_config",
    "validate_config",
    "get_state_path",
    "strip_comments",
    "find_config",
    "ensure_config_example",
    # State
    "load_state",
    "save_state",
    "get_hours_since_tick",
    "StateLock",
    # Engine
    "accumulate_pressure",
    "tick_all_drives",
    "check_thresholds",
    "satisfy_drive",
    "bump_drive",
    "get_drive_status",
    "reset_all_drives",
    "is_quiet_hours",
    # Spawn
    "spawn_session",
    "build_session_prompt",
    "check_cooldown",
    "record_trigger",
    "select_drive_to_trigger",
    "handle_spawn_failure",
    "tick_with_spawning",
    "spawn_via_api",
    "spawn_via_cli",
    # Utils
    "fuzzy_match",
    "get_ambiguous_matches",
    "format_pressure_bar",
    "normalize_drive_name",
    # History
    "read_trigger_log",
    "filter_log_entries",
    "add_trigger_event",
    "add_satisfaction_event",
    "format_log_entry",
    "get_stats",
    "parse_time_string",
    # Ingest
    "load_experience_content",
    "build_analysis_prompt",
    "parse_impact_response",
    "analyze_with_ollama",
    "analyze_with_openrouter",
    "analyze_with_keywords",
    "analyze_content",
    "apply_impacts",
    "DRIVE_DESCRIPTIONS",
    "DRIVE_KEYWORDS",
    # Satisfaction
    "write_breadcrumb",
    "check_completed_sessions",
    "assess_depth",
    "get_ingest_dir",
    # CLI
    "cli_main",
]
