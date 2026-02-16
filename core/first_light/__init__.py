"""First Light module — Self-calibrating onboarding for agent emergence."""

from .orchestrator import (
    get_exploration_prompts,
    select_prompt,
    load_first_light_state,
    save_first_light_state,
    schedule_exploration_session,
    run_first_light_tick,
    start_first_light,
    pause_first_light,
    get_status as get_first_light_status,
)

from .analyzer import (
    analyze_session,
    detect_patterns,
    correlate_patterns,
    get_drive_suggestions,
    get_pattern_summary,
    PATTERN_CATEGORIES,
    DRIVE_MAPPINGS,
)

from .discovery import (
    create_drive_from_suggestion,
    add_discovered_drive,
    build_drive_creation_prompt,
    validate_drive_entry,
    get_pending_suggestions,
    run_drive_discovery,
    list_discovered_drives,
)

from .gates import (
    check_drive_diversity,
    check_self_authored_identity,
    check_unprompted_initiative,
    check_profile_stability,
    check_relationship_signal,
    check_all_gates,
    is_emerged,
)

from .status import (
    get_first_light_status,
    format_status_display,
    format_status_json,
)

from .completion import (
    load_first_light_json,
    save_first_light_json,
    check_first_light_completion,
    complete_first_light,
    notify_first_light_completion,
    increment_session_count,
    manual_complete_first_light,
    check_and_notify_startup,
    calculate_gate_status,
    DEFAULT_GATES,
)

__all__ = [
    # Orchestrator
    "get_exploration_prompts",
    "select_prompt",
    "load_first_light_state",
    "save_first_light_state",
    "schedule_exploration_session",
    "run_first_light_tick",
    "start_first_light",
    "pause_first_light",
    "get_first_light_status",
    # Analyzer
    "analyze_session",
    "detect_patterns",
    "correlate_patterns",
    "get_drive_suggestions",
    "get_pattern_summary",
    "PATTERN_CATEGORIES",
    "DRIVE_MAPPINGS",
    # Discovery
    "create_drive_from_suggestion",
    "add_discovered_drive",
    "build_drive_creation_prompt",
    "validate_drive_entry",
    "get_pending_suggestions",
    "run_drive_discovery",
    "list_discovered_drives",
    # Gates
    "check_drive_diversity",
    "check_self_authored_identity",
    "check_unprompted_initiative",
    "check_profile_stability",
    "check_relationship_signal",
    "check_all_gates",
    "is_emerged",
    # Status
    "format_status_display",
    "format_status_json",
    # Completion
    "load_first_light_json",
    "save_first_light_json",
    "check_first_light_completion",
    "complete_first_light",
    "notify_first_light_completion",
    "increment_session_count",
    "manual_complete_first_light",
    "check_and_notify_startup",
    "calculate_gate_status",
    "DEFAULT_GATES",
]
