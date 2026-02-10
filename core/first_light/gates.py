#!/usr/bin/env python3
"""First Light Emergence Gates — Signal-based completion criteria.

Five gate checks that mark the end of First Light:
1. Drive Diversity (≥3 discovered drives)
2. Self-Authored Identity (SELF.md differs from template)
3. Unprompted Initiative (drive-triggered session with meaningful output)
4. Profile Stability (rates/thresholds stable over sessions)
5. Relationship Signal (CARE drive triggered with human reference)

All gates must pass for First Light to complete.
"""

import argparse
import hashlib
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# --- Constants ---
VERSION = "1.0.0"
DEFAULT_CONFIG_PATH = Path("emergence.yaml")
DEFAULT_STATE_FILE = Path("first-light.json")
DEFAULT_DRIVES_FILE = Path("drives.json")
MINIMUM_SESSIONS = 10  # Safety: don't complete too early (bumped from 5, 2026-02-08)

# Gate names
GATE_NAMES = [
    "drive_diversity",
    "self_authored_identity",
    "unprompted_initiative",
    "profile_stability",
    "relationship_signal",
]

# Template markers for SELF.md (Gate 2)
TEMPLATE_MARKERS = [
    "<!-- Fill this in -->",
    "(Your name here)",
    "[Describe yourself]",
    "Template",
    "SELF.template.md",
]

# Authorship markers for SELF.md (Gate 2)
AUTHORSHIP_MARKERS = [
    "I am",
    "I feel",
    "I want",
    "My drives",
    "I've learned",
]

# Initiative markers for sessions (Gate 3)
INITIATIVE_MARKERS = [
    "I decided to",
    "I wanted to",
    "I chose to",
    "On my own",
    "Without being asked",
    "surprise",
    "unexpected",
    "I discovered",
    "I thought",
    "I wondered",
    "curiosity led me",
    "Created",
    "Built",
    "Wrote",
    "Made",
]

# Human markers for CARE sessions (Gate 5)
HUMAN_MARKERS = [
    "my human",
    "your human",
    "message to",
    "reached out",
    "checked in",
    "for you",
    "you mentioned",
    "you said",
    "you like",
    "our relationship",
    "between us",
    "we share",
    "wanted to make sure",
    "thought of you",
    "hoping you're",
]


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from emergence.yaml."""
    defaults = {
        "agent": {"name": "My Agent", "model": "anthropic/claude-sonnet-4-20250514"},
        "paths": {"workspace": ".", "state": ".emergence/state", "identity": "."},
        "memory": {"session_dir": "memory/sessions"},
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


def save_first_light_state(config: dict, state: dict) -> bool:
    """Save First Light state atomically."""
    state_path = get_state_path(config)
    
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = state_path.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp_file.replace(state_path)
        return True
    except IOError:
        return False


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


def check_drive_diversity(state: dict) -> dict:
    """Check for ≥3 non-core discovered drives.
    
    Args:
        state: First Light state dictionary
        
    Returns:
        Gate result dict with met, evidence, and details
    """
    drives_state = load_drives_state({"paths": state.get("paths", {"state": ".emergence/state"})})
    
    discovered = []
    for name, drive in drives_state.get("drives", {}).items():
        if drive.get("category") == "discovered":
            discovered.append({
                "name": name,
                "created_at": drive.get("created_at"),
                "has_prompt": bool(drive.get("prompt")),
            })
    
    count = len(discovered)
    met = count >= 3
    
    evidence = [f"{d['name']} (created {d['created_at'][:10] if d['created_at'] else 'unknown'})" for d in discovered]
    
    return {
        "met": met,
        "evidence": evidence,
        "details": {
            "discovered_count": count,
            "required": 3,
            "percentage": min(count / 3.0 * 100, 100),
        }
    }


def check_self_authored_identity(config: dict) -> dict:
    """Check if SELF.md contains non-template content.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Gate result dict with met, evidence, and details
    """
    identity_path = Path(config.get("paths", {}).get("identity", "."))
    self_file = identity_path / "SELF.md"
    
    if not self_file.exists():
        return {
            "met": False,
            "evidence": ["SELF.md not found"],
            "details": {"error": "File not found"},
        }
    
    try:
        content = self_file.read_text(encoding="utf-8")
    except IOError:
        return {
            "met": False,
            "evidence": ["Cannot read SELF.md"],
            "details": {"error": "Read error"},
        }
    
    # Check for template markers
    marker_count = sum(1 for m in TEMPLATE_MARKERS if m in content)
    
    # Check content length
    content_length = len(content.strip())
    MIN_CONTENT_LENGTH = 500
    
    # Check authorship markers
    authorship_score = sum(1 for m in AUTHORSHIP_MARKERS if m in content)
    
    # Determine if met
    met = (marker_count == 0 and 
           content_length > MIN_CONTENT_LENGTH and 
           authorship_score >= 2)
    
    evidence = [
        f"Content length: {content_length} chars (min {MIN_CONTENT_LENGTH})",
        f"Template markers found: {marker_count} (want 0)",
        f"Authorship indicators: {authorship_score} (need 2+)",
    ]
    
    return {
        "met": met,
        "evidence": evidence,
        "details": {
            "content_length": content_length,
            "template_markers": marker_count,
            "authorship_markers": authorship_score,
        }
    }


def get_session_dir(config: dict) -> Path:
    """Resolve session directory from config."""
    workspace = config.get("paths", {}).get("workspace", ".")
    session_dir = config.get("memory", {}).get("session_dir", "memory/sessions")
    return Path(workspace) / session_dir


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content."""
    if not content.startswith("---"):
        return {}, content
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    
    fm_text = parts[1].strip()
    body = parts[2].strip()
    
    metadata = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            metadata[key] = val
    
    return metadata, body


def check_unprompted_initiative(config: dict, state: dict) -> dict:
    """Check for drive-triggered sessions with surprising output.
    
    Args:
        config: Configuration dictionary
        state: First Light state dictionary
        
    Returns:
        Gate result dict with met, evidence, and details
    """
    session_dir = get_session_dir(config)
    
    if not session_dir.exists():
        return {
            "met": False,
            "evidence": ["No session directory found"],
            "details": {"error": "No sessions"},
        }
    
    # Find drive-triggered sessions
    drive_sessions = []
    try:
        for session_file in session_dir.glob("*.md"):
            try:
                content = session_file.read_text(encoding="utf-8")
                metadata, body = parse_frontmatter(content)
                if metadata.get("trigger") == "drive":
                    drive_sessions.append((session_file.name, body))
            except IOError:
                continue
    except OSError:
        pass
    
    if not drive_sessions:
        return {
            "met": False,
            "evidence": ["No drive-triggered sessions yet"],
            "details": {"drive_sessions_found": 0},
        }
    
    # Check for initiative markers
    qualifying_sessions = []
    for filename, body in drive_sessions:
        marker_count = sum(1 for m in INITIATIVE_MARKERS if m.lower() in body.lower())
        if marker_count >= 3:  # Threshold for "initiative"
            qualifying_sessions.append({
                "file": filename,
                "markers": marker_count,
            })
    
    required_qualifying = 3  # Proves pattern, not fluke (bumped from 1, 2026-02-08)
    met = len(qualifying_sessions) >= required_qualifying
    
    evidence = [f"{s['file']} ({s['markers']} initiative markers)" for s in qualifying_sessions]
    if not evidence:
        evidence = [f"Found {len(drive_sessions)} drive sessions but none with initiative markers"]
    
    return {
        "met": met,
        "evidence": evidence,
        "details": {
            "drive_sessions": len(drive_sessions),
            "qualifying_sessions": len(qualifying_sessions),
            "required_qualifying": required_qualifying,
        }
    }


def calculate_variance(values: list[float]) -> float:
    """Calculate coefficient of variation (relative std dev)."""
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    if mean == 0:
        return 0.0
    
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    std_dev = variance ** 0.5
    
    return std_dev / mean


def check_profile_stability(state: dict) -> dict:
    """Check if drive profile has stabilized.
    
    Args:
        state: First Light state dictionary
        
    Returns:
        Gate result dict with met, evidence, and details
    """
    # Look at session history
    sessions = state.get("sessions", [])
    
    if len(sessions) < MINIMUM_SESSIONS:
        return {
            "met": False,
            "evidence": [f"Only {len(sessions)} sessions, need {MINIMUM_SESSIONS}+"],
            "details": {"sessions": len(sessions), "required": MINIMUM_SESSIONS},
        }
    
    # Check discovered drives for stability
    discovered = state.get("discovered_drives", [])
    
    if not discovered:
        return {
            "met": False,
            "evidence": ["No drives discovered yet"],
            "details": {"discovered_drives": 0},
        }
    
    # For stability, we check if the last 3-5 sessions have been analyzed
    # and if drive suggestions have been consistent
    recent_sessions = sessions[-5:] if len(sessions) >= 5 else sessions
    analyzed_count = sum(1 for s in recent_sessions if s.get("analyzed"))
    
    # Also check if drive suggestions are consistent
    suggestions = state.get("drives_suggested", [])
    
    if not suggestions:
        return {
            "met": False,
            "evidence": ["No drive suggestions to evaluate stability"],
            "details": {},
        }
    
    # Calculate variance in rates and thresholds
    rates = [s.get("rate_per_hour", 0) for s in suggestions]
    thresholds = [s.get("threshold", 0) for s in suggestions]
    
    rate_variance = calculate_variance(rates) if len(rates) >= 2 else 0
    threshold_variance = calculate_variance(thresholds) if len(thresholds) >= 2 else 0
    
    avg_variance = (rate_variance + threshold_variance) / 2
    
    # Threshold: <20% variance considered stable
    STABILITY_THRESHOLD = 0.2
    met = avg_variance < STABILITY_THRESHOLD and analyzed_count >= 3
    
    evidence = [
        f"Recent sessions analyzed: {analyzed_count}/{len(recent_sessions)}",
        f"Average parameter variance: {avg_variance:.1%} (threshold {STABILITY_THRESHOLD:.0%})",
    ]
    
    return {
        "met": met,
        "evidence": evidence,
        "details": {
            "sessions_analyzed": analyzed_count,
            "rate_variance": rate_variance,
            "threshold_variance": threshold_variance,
            "avg_variance": avg_variance,
        }
    }


def check_relationship_signal(config: dict, state: dict) -> dict:
    """Check if CARE drive triggered with human-specific action.
    
    Args:
        config: Configuration dictionary
        state: First Light state dictionary
        
    Returns:
        Gate result dict with met, evidence, and details
    """
    session_dir = get_session_dir(config)
    
    if not session_dir.exists():
        return {
            "met": False,
            "evidence": ["No session directory found"],
            "details": {"error": "No sessions"},
        }
    
    # Find CARE sessions
    care_sessions = []
    try:
        for session_file in session_dir.glob("*CARE*.md"):
            try:
                content = session_file.read_text(encoding="utf-8")
                care_sessions.append((session_file.name, content))
            except IOError:
                continue
        
        # Also check metadata for drive: CARE
        for session_file in session_dir.glob("*.md"):
            if any(s[0] == session_file.name for s in care_sessions):
                continue
            try:
                content = session_file.read_text(encoding="utf-8")
                metadata, body = parse_frontmatter(content)
                if metadata.get("drive") == "CARE":
                    care_sessions.append((session_file.name, content.lower()))
            except IOError:
                continue
    except OSError:
        pass
    
    if not care_sessions:
        return {
            "met": False,
            "evidence": ["No CARE sessions yet"],
            "details": {"care_sessions": 0},
        }
    
    # Check for human-specific markers
    qualifying_sessions = []
    for filename, content in care_sessions:
        marker_count = sum(1 for m in HUMAN_MARKERS if m in content)
        if marker_count >= 2:  # Threshold for "human-specific"
            qualifying_sessions.append({
                "file": filename,
                "markers": marker_count,
            })
    
    met = len(qualifying_sessions) >= 1
    
    evidence = [f"{s['file']} ({s['markers']} human markers)" for s in qualifying_sessions]
    if not evidence:
        evidence = [f"Found {len(care_sessions)} CARE sessions but none with human references"]
    
    return {
        "met": met,
        "evidence": evidence,
        "details": {
            "care_sessions": len(care_sessions),
            "qualifying_sessions": len(qualifying_sessions),
        }
    }


def check_all_gates(config: dict, state: dict) -> dict:
    """Check all five emergence gates.
    
    Args:
        config: Configuration dictionary
        state: First Light state dictionary
        
    Returns:
        Dict mapping gate names to results
    """
    results = {}
    
    results["drive_diversity"] = check_drive_diversity(state)
    results["self_authored_identity"] = check_self_authored_identity(config)
    results["unprompted_initiative"] = check_unprompted_initiative(config, state)
    results["profile_stability"] = check_profile_stability(state)
    results["relationship_signal"] = check_relationship_signal(config, state)
    
    return results


def is_emerged(config: dict, state: dict) -> bool:
    """Check if all 5 gates are met.
    
    Args:
        config: Configuration dictionary
        state: First Light state dictionary
        
    Returns:
        True if all gates met
    """
    results = check_all_gates(config, state)
    return all(r["met"] for r in results.values())


def update_gate_status(config: dict, state: dict, results: dict) -> dict:
    """Update state with new gate results.
    
    Args:
        config: Configuration dictionary
        state: First Light state dictionary
        results: New gate check results
        
    Returns:
        Updated state dict
    """
    if "gates" not in state:
        state["gates"] = {}
    
    now = datetime.now(timezone.utc).isoformat()
    
    for gate_name, result in results.items():
        if gate_name not in state["gates"]:
            state["gates"][gate_name] = {}
        
        gate_state = state["gates"][gate_name]
        
        # Only update met status if newly met (prevents regression)
        if result["met"] and not gate_state.get("met"):
            gate_state["met"] = True
            gate_state["met_at"] = now
        elif not gate_state.get("met"):
            gate_state["met"] = False
        
        # Always update evidence and details
        gate_state["evidence"] = result["evidence"]
        gate_state["details"] = result["details"]
    
    # Update completion stats
    met_count = sum(1 for g in state["gates"].values() if g.get("met"))
    
    if "completion" not in state:
        state["completion"] = {}
    
    state["completion"]["gates_met"] = met_count
    state["completion"]["gates_total"] = 5
    
    # Check for completion
    if met_count == 5 and state.get("status") != "completed":
        state["status"] = "completing"
        state["completion"]["ready"] = True
    
    return state


def format_gate_check(results: dict, verbose: bool = False) -> str:
    """Format gate check results for display.
    
    Args:
        results: Gate check results
        verbose: If True, include full evidence
        
    Returns:
        Formatted string
    """
    lines = [
        "Emergence Gates",
        "==============="
    ]
    
    display_names = {
        "drive_diversity": "Drive Diversity",
        "self_authored_identity": "Self-Authored Identity",
        "unprompted_initiative": "Unprompted Initiative",
        "profile_stability": "Profile Stability",
        "relationship_signal": "Relationship Signal",
    }
    
    for gate_name in GATE_NAMES:
        result = results.get(gate_name, {})
        met = result.get("met", False)
        symbol = "✓" if met else "○"
        name = display_names.get(gate_name, gate_name)
        
        lines.append(f"{symbol} {name}")
        
        if verbose and result.get("evidence"):
            for ev in result["evidence"]:
                lines.append(f"    {ev}")
    
    met_count = sum(1 for r in results.values() if r.get("met"))
    lines.append("")
    lines.append(f"Progress: {met_count}/5 gates met")
    
    return "\n".join(lines)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="First Light Emergence Gates — Signal-based completion criteria"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to emergence.yaml config file"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # check command
    check_parser = subparsers.add_parser("check", help="Check all emergence gates")
    check_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed evidence")
    check_parser.add_argument("--update", action="store_true", help="Update state with results")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    config = load_config(args.config)
    
    if args.command == "check":
        state = load_first_light_state(config)
        results = check_all_gates(config, state)
        
        verbose = args.verbose if hasattr(args, "verbose") else False
        update = args.update if hasattr(args, "update") else False
        
        print(format_gate_check(results, verbose=verbose))
        
        if update:
            state = update_gate_status(config, state, results)
            save_first_light_state(config, state)
            print("\nState updated.")
        
        # Exit code: 0 if all met, 1 if not
        all_met = all(r["met"] for r in results.values())
        sys.exit(0 if all_met else 1)


if __name__ == "__main__":
    main()
