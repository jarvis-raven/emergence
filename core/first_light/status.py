#!/usr/bin/env python3
"""First Light Status — Progress reporting and dashboard integration.

Provides comprehensive status reporting for the First Light phase,
including progress bars, gate status, and phase determination.
"""

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# --- Constants ---
VERSION = "1.0.0"
DEFAULT_CONFIG_PATH = Path("emergence.yaml")
DEFAULT_STATE_FILE = Path("first-light.json")
DEFAULT_DRIVES_FILE = Path("drives.json")
TARGET_SESSIONS = 10  # Heuristic target for First Light

# Phase thresholds
PHASE_THRESHOLDS = {
    "not_started": {"sessions": 0, "gates": 0},
    "active": {"sessions": 1, "gates": 0},
    "stabilizing": {"sessions": 5, "gates": 2},
    "emerged": {"sessions": 0, "gates": 5},  # All gates required
}


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from emergence.yaml."""
    defaults = {
        "agent": {"name": "My Agent", "model": "anthropic/claude-sonnet-4-20250514"},
        "paths": {"workspace": ".", "state": ".emergence/state"},
        "memory": {"session_dir": "memory/sessions", "daily_dir": "memory"},
    }

    if config_path is None:
        config_path = DEFAULT_CONFIG_PATH

    if not config_path.exists():
        return defaults

    try:
        content = config_path.read_text(encoding="utf-8")
        config = defaults.copy()
        current_section = None

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.endswith(":") and not line.startswith("-"):
                current_section = line[:-1].strip()
                if current_section not in config:
                    config[current_section] = {}
                continue

            if ":" in line and current_section:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")

                if val.lower() in ("true", "yes"):
                    val = True
                elif val.lower() in ("false", "no"):
                    val = False
                elif val.isdigit():
                    val = int(val)
                elif val.replace(".", "").replace("-", "").isdigit() and "." in val:
                    val = float(val)
                elif val == "null" or val == "":
                    val = None

                config[current_section][key] = val

        return config
    except IOError:
        return defaults


def get_state_path(config: dict) -> Path:
    """Resolve state file path from config."""
    workspace = config.get("paths", {}).get("workspace", ".")
    state_dir = config.get("paths", {}).get("state", ".emergence/state")
    return Path(workspace) / state_dir / DEFAULT_STATE_FILE


def get_drives_path(config: dict) -> Path:
    """Resolve drives.json path from config."""
    workspace = config.get("paths", {}).get("workspace", ".")
    state_dir = config.get("paths", {}).get("state", ".emergence/state")
    return Path(workspace) / state_dir / DEFAULT_DRIVES_FILE


def load_first_light_state(config: dict) -> dict:
    """Load First Light state from JSON file."""
    state_path = get_state_path(config)

    defaults = {
        "version": "1.0",
        "status": "not_started",
        "sessions_completed": 0,
        "sessions_scheduled": 0,
        "started_at": None,
        "emerged_at": None,
        "patterns_detected": {},
        "drives_suggested": [],
        "discovered_drives": [],
        "sessions": [],
        "gates": {},
    }

    if not state_path.exists():
        return defaults.copy()

    try:
        content = state_path.read_text(encoding="utf-8")
        loaded = json.loads(content)
        merged = defaults.copy()
        for key, value in loaded.items():
            merged[key] = value
        return merged
    except (json.JSONDecodeError, IOError):
        return defaults.copy()


def load_drives_state(config: dict) -> dict:
    """Load drives.json state."""
    drives_path = get_drives_path(config)

    defaults = {"version": "1.0", "drives": {}}

    if not drives_path.exists():
        return defaults.copy()

    try:
        content = drives_path.read_text(encoding="utf-8")
        loaded = json.loads(content)
        merged = defaults.copy()
        for key, value in loaded.items():
            merged[key] = value
        return merged
    except (json.JSONDecodeError, IOError):
        return defaults.copy()


def count_sessions(config: dict) -> dict:
    """Count sessions from first-light state.

    Args:
        config: Configuration dictionary

    Returns:
        Dict with total, by_trigger, and recent counts
    """
    state = load_first_light_state(config)
    sessions = state.get("sessions", [])

    total = len(sessions)
    analyzed = sum(1 for s in sessions if s.get("analyzed"))

    # Count recent sessions (last 7 days)
    recent = 0
    now = datetime.now(timezone.utc)
    for s in sessions:
        scheduled_at = s.get("scheduled_at")
        if scheduled_at:
            try:
                dt = datetime.fromisoformat(scheduled_at.replace("Z", "+00:00"))
                if (now - dt).days <= 7:
                    recent += 1
            except (ValueError, AttributeError):
                pass

    return {
        "total": total,
        "analyzed": analyzed,
        "scheduled": state.get("sessions_scheduled", 0),
        "recent": recent,
    }


def count_discovered_drives(drives_state: dict) -> int:
    """Count discovered (non-core) drives."""
    drives = drives_state.get("drives", {})
    return sum(1 for d in drives.values() if d.get("category") == "discovered")


def get_discovered_drive_names(drives_state: dict) -> list[str]:
    """Get names of discovered drives."""
    drives = drives_state.get("drives", {})
    return [name for name, d in drives.items() if d.get("category") == "discovered"]


def count_met_gates(state: dict) -> int:
    """Count how many gates are met."""
    gates = state.get("gates", {})
    return sum(1 for g in gates.values() if g.get("met"))


def get_gate_details(state: dict) -> dict:
    """Get detailed gate status."""
    gates = state.get("gates", {})
    details = {}

    for name in [
        "drive_diversity",
        "self_authored_identity",
        "unprompted_initiative",
        "profile_stability",
        "relationship_signal",
    ]:
        gate = gates.get(name, {})
        details[name] = {
            "met": gate.get("met", False),
            "evidence": gate.get("evidence", []),
        }

    return details


def determine_phase(state: dict, sessions_count: int, gates_met: int) -> str:
    """Determine the current First Light phase.

    Phases:
    - not_started: No sessions yet
    - active: Sessions running but <5 sessions or <2 gates
    - stabilizing: ≥5 sessions and ≥2 gates but not all gates
    - emerged: All 5 gates met

    Args:
        state: First Light state
        sessions_count: Number of sessions completed
        gates_met: Number of gates met

    Returns:
        Phase name string
    """
    if state.get("status") == "completed":
        return "emerged"

    if gates_met >= 5:
        return "emerged"

    if sessions_count >= 5 and gates_met >= 2:
        return "stabilizing"

    if sessions_count > 0 or state.get("status") == "active":
        return "active"

    return "not_started"


def calculate_progress_percentage(sessions: int, drives: int, gates: int) -> int:
    """Calculate overall progress percentage.

    Weights:
    - Sessions: 40% (max at TARGET_SESSIONS)
    - Drives: 30% (max at 3 drives)
    - Gates: 30% (max at 5 gates)
    """
    session_pct = min(sessions / TARGET_SESSIONS, 1.0) * 40
    drives_pct = min(drives / 3, 1.0) * 30
    gates_pct = min(gates / 5, 1.0) * 30

    return int(session_pct + drives_pct + gates_pct)


def get_first_light_status(config: dict) -> dict:
    """Compile full First Light status.

    Args:
        config: Configuration dictionary

    Returns:
        Complete status dictionary
    """
    fl_state = load_first_light_state(config)
    drives_state = load_drives_state(config)
    sessions = count_sessions(config)

    discovered_count = count_discovered_drives(drives_state)
    discovered_names = get_discovered_drive_names(drives_state)
    gates_met = count_met_gates(fl_state)
    gate_details = get_gate_details(fl_state)

    phase = determine_phase(fl_state, sessions["analyzed"], gates_met)
    progress_pct = calculate_progress_percentage(sessions["analyzed"], discovered_count, gates_met)

    # Calculate elapsed time
    started_at = fl_state.get("started_at")
    elapsed_days = 0
    if started_at:
        try:
            start_dt = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            elapsed_days = (datetime.now(timezone.utc) - start_dt).days
        except (ValueError, AttributeError):
            pass

    # Estimate completion
    estimated_completion = None
    if phase != "emerged" and sessions["analyzed"] > 0:
        # Rough estimate: each remaining gate needs ~2 sessions
        gates_remaining = 5 - gates_met
        if gates_remaining > 0:
            # Current pace
            pace = sessions["analyzed"] / max(elapsed_days, 1)
            if pace > 0:
                sessions_needed = gates_remaining * 2
                days_needed = sessions_needed / pace
                est_date = datetime.now(timezone.utc) + timedelta(days=days_needed)
                estimated_completion = est_date.strftime("%Y-%m-%d")

    return {
        "status": fl_state.get("status", "not_started"),
        "phase": phase,
        "progress": {
            "percentage": progress_pct,
            "sessions": {
                "completed": sessions["analyzed"],
                "scheduled": sessions["scheduled"],
                "target": TARGET_SESSIONS,
            },
            "drives": {
                "discovered": discovered_count,
                "names": discovered_names,
                "target": 3,
            },
            "gates": {
                "met": gates_met,
                "total": 5,
                "details": gate_details,
            },
        },
        "timing": {
            "started_at": started_at,
            "elapsed_days": elapsed_days,
            "estimated_completion": estimated_completion,
        },
        "emerged": phase == "emerged",
        "emerged_at": fl_state.get("emerged_at"),
    }


def generate_progress_bar(value: float, max_val: float, width: int = 20) -> str:
    """Generate ASCII progress bar."""
    if max_val == 0:
        return "░" * width

    ratio = min(value / max_val, 1.0)
    filled = int(width * ratio)
    empty = width - filled

    return "█" * filled + "░" * empty


def format_status_display(status: dict) -> str:
    """Format status as pretty terminal output with progress bars.

    Args:
        status: Status dictionary from get_first_light_status()

    Returns:
        Formatted string for terminal display
    """
    lines = [
        "═══════════════════════════════════════════════════════════════",
        "                    First Light Status",
        "═══════════════════════════════════════════════════════════════",
        "",
    ]

    # Phase and summary
    phase = status["phase"]
    phase_display = {
        "not_started": "Not Started",
        "active": "Active (exploring)",
        "stabilizing": "Stabilizing",
        "emerged": "✨ EMERGED ✨",
    }.get(phase, phase)

    lines.append(f"Phase: {phase_display}")

    if status["timing"]["started_at"]:
        started = status["timing"]["started_at"][:10]
        elapsed = status["timing"]["elapsed_days"]
        lines.append(f"Started: {started} ({elapsed} days ago)")

    lines.append("")

    # Progress bars
    lines.append("Progress")
    lines.append("────────")

    sessions = status["progress"]["sessions"]
    session_bar = generate_progress_bar(sessions["completed"], sessions["target"])
    lines.append(f"Sessions:  {session_bar}  {sessions['completed']}/{sessions['target']}")

    drives = status["progress"]["drives"]
    drives_bar = generate_progress_bar(drives["discovered"], drives["target"])
    lines.append(f"Drives:    {drives_bar}  {drives['discovered']}/{drives['target']}")

    gates = status["progress"]["gates"]
    gates_bar = generate_progress_bar(gates["met"], gates["total"])
    lines.append(f"Gates:     {gates_bar}  {gates['met']}/{gates['total']}")

    lines.append("")

    # Gates detail
    lines.append("Gates Detail")
    lines.append("────────────")

    gate_names = {
        "drive_diversity": "Drive Diversity",
        "self_authored_identity": "Self-Authored Identity",
        "unprompted_initiative": "Unprompted Initiative",
        "profile_stability": "Profile Stability",
        "relationship_signal": "Relationship Signal",
    }

    for gate_id, display_name in gate_names.items():
        gate_info = gates["details"].get(gate_id, {})
        symbol = "✓" if gate_info.get("met") else "○"
        lines.append(f"{symbol} {display_name}")

    lines.append("")

    # Timing
    if status["timing"]["estimated_completion"] and not status["emerged"]:
        lines.append("Estimated Completion")
        lines.append("────────────────────")
        lines.append(f"Approximately: {status['timing']['estimated_completion']}")
        lines.append("")

    if status["emerged"] and status["emerged_at"]:
        lines.append("Emergence Complete!")
        lines.append("───────────────────")
        lines.append(f"Emerged at: {status['emerged_at'][:10]}")
        lines.append("")

    lines.append("═══════════════════════════════════════════════════════════════")

    return "\n".join(lines)


def format_status_json(status: dict) -> str:
    """Format status as JSON string for dashboard API.

    Args:
        status: Status dictionary from get_first_light_status()

    Returns:
        JSON string
    """
    return json.dumps(status, indent=2)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="First Light Status — Progress reporting")
    parser.add_argument(
        "--config", type=Path, default=None, help="Path to emergence.yaml config file"
    )
    parser.add_argument(
        "--json", action="store_true", help="Output as JSON instead of formatted display"
    )

    args = parser.parse_args()

    config = load_config(args.config)
    status = get_first_light_status(config)

    if args.json:
        print(format_status_json(status))
    else:
        print(format_status_display(status))

    # Exit code: 0 if emerged, 1 if not
    sys.exit(0 if status["emerged"] else 1)


if __name__ == "__main__":
    main()
