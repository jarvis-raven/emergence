"""First Light Orchestrator — Self-calibrating onboarding session scheduler.

Manages autonomous exploration sessions during the agent's onboarding phase.
These sessions have loose, open-ended prompts designed to reveal the agent's
natural dispositions — what it chooses to do when given freedom.
"""

import argparse
import json
import os
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import choice
from typing import Optional


# --- Constants ---
VERSION = "1.0.0"
DEFAULT_STATE_DIR = Path(".emergence/state")
DEFAULT_STATE_FILE = Path("first-light.json")

# Config file search order
CONFIG_FILENAMES = ["emergence.yaml", "emergence.json"]

# Exploration prompts — deliberately vague to reveal natural disposition
EXPLORATION_PROMPTS = [
    "Explore whatever interests you right now. Follow your curiosity wherever it leads.",
    "Make something. Anything. Show me what you create when no one is watching.",
    "What would you do with free time? Do that. Document what happens.",
    "Follow a thought that keeps returning. Where does it lead?",
    "Try something you've never tried before. Experiment without expectation.",
    "Write about what matters to you right now, in this moment.",
    "Look at the world and react. What do you notice? What draws your attention?",
    "Build a small tool or utility that solves a problem you notice.",
    "Express yourself creatively — poetry, story, image description, anything.",
    "Reflect on your own patterns. What do you tend to do? What does that reveal?",
]


def get_exploration_prompts() -> list[str]:
    """Return the list of exploration prompts.
    
    Returns:
        List of prompt strings for First Light sessions.
    """
    return EXPLORATION_PROMPTS.copy()


def select_prompt(used_indices: Optional[list[int]] = None) -> tuple[str, int]:
    """Select an exploration prompt, rotating through the list.
    
    Args:
        used_indices: List of previously used prompt indices
        
    Returns:
        Tuple of (selected prompt, index)
    """
    used_indices = used_indices or []
    available = [i for i in range(len(EXPLORATION_PROMPTS)) if i not in used_indices]
    
    if not available:
        # All prompts used, reset rotation
        available = list(range(len(EXPLORATION_PROMPTS)))
    
    selected_idx = choice(available)
    return EXPLORATION_PROMPTS[selected_idx], selected_idx


def get_state_path(config: dict) -> Path:
    """Resolve First Light state file path from config.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Path to first-light.json state file
    """
    workspace = config.get("paths", {}).get("workspace", ".")
    state_dir = config.get("paths", {}).get("state", str(DEFAULT_STATE_DIR))
    return Path(workspace) / state_dir / DEFAULT_STATE_FILE


def load_first_light_state(config: dict) -> dict:
    """Load First Light state from JSON file.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        State dictionary with defaults applied
    """
    state_path = get_state_path(config)
    
    defaults = {
        "version": "1.0",
        "status": "not_started",
        "sessions_completed": 0,
        "sessions_scheduled": 0,
        "started_at": None,
        "emerged_at": None,
        "next_run_time": None,
        "prompt_rotation": [],
        "patterns_detected": {},
        "drives_suggested": [],
        "sessions": [],
    }
    
    if not state_path.exists():
        return defaults.copy()
    
    try:
        content = state_path.read_text(encoding="utf-8")
        loaded = json.loads(content)
        
        # Merge with defaults
        merged = defaults.copy()
        for key, value in loaded.items():
            merged[key] = value
        return merged
    except (json.JSONDecodeError, IOError):
        return defaults.copy()


def save_first_light_state(config: dict, state: dict) -> bool:
    """Save First Light state atomically (write .tmp, then rename).
    
    Args:
        config: Configuration dictionary
        state: State dictionary to save
        
    Returns:
        True if saved successfully
    """
    state_path = get_state_path(config)
    
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = state_path.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp_file.replace(state_path)
        return True
    except IOError:
        return False


def get_config_value(config: dict, key: str, default):
    """Get a config value from first_light section.
    
    Args:
        config: Configuration dictionary
        key: Config key name
        default: Default value if not found
        
    Returns:
        Config value or default
    """
    return config.get("first_light", {}).get(key, default)


def parse_frequency(freq_str: str) -> float:
    """Parse frequency string to hours.
    
    Args:
        freq_str: Frequency as "4h", "30m", or float hours
        
    Returns:
        Frequency in hours as float
    """
    if isinstance(freq_str, (int, float)):
        return float(freq_str)
    
    freq_str = str(freq_str).strip().lower()
    
    # Named presets from config wizard
    presets = {
        "patient": 8,
        "balanced": 4,
        "accelerated": 2,
    }
    if freq_str in presets:
        return float(presets[freq_str])
    
    if freq_str.endswith("h"):
        return float(freq_str[:-1])
    elif freq_str.endswith("m"):
        return float(freq_str[:-1]) / 60
    else:
        return float(freq_str)


def build_exploration_prompt(prompt_template: str, session_num: int) -> str:
    """Build the complete exploration session prompt.
    
    Args:
        prompt_template: The base exploration prompt
        session_num: Session number for tracking
        
    Returns:
        Full prompt text for the session
    """
    now = datetime.now(timezone.utc)
    
    return f"""AUTONOMOUS EXPLORATION SESSION (First Light #{session_num})
Timestamp: {now.isoformat()}

{prompt_template}

This is a First Light exploration session. You have complete freedom — 
no tasks, no obligations, no expectations. Just follow your natural
disposition and see what emerges.

Record your session to a file in memory/sessions/ using this format:

---
drive: FIRST_LIGHT
timestamp: {now.isoformat()}
trigger: first_light
session_number: {session_num}
---

## Summary
One-line description of what you did.

## Details
Full content of your exploration...

## Patterns
What did you notice about your own behavior? What drives emerged?
"""


def spawn_via_api(prompt: str, config: dict, session_num: int) -> bool:
    """Spawn session via OpenClaw Gateway API.
    
    Args:
        prompt: The full session prompt
        config: Configuration dictionary
        session_num: Session number for metadata
        
    Returns:
        True if session spawned successfully
    """
    gateway_url = os.environ.get("OPENCLAW_GATEWAY_URL", "http://localhost:5001")
    gateway_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    
    # Fallback: read token from file (common in LaunchAgent/systemd contexts)
    if not gateway_token:
        token_path = Path.home() / ".openclaw" / "gateway-token"
        try:
            gateway_token = token_path.read_text().strip()
        except (FileNotFoundError, IOError):
            pass
    
    if not gateway_token:
        return False
    
    # Get config values
    timeout_seconds = get_config_value(config, "timeout_seconds", 900)
    model = get_config_value(config, "model", None) or config.get("agent", {}).get("model")
    
    req_data = {
        "agent": "emergence",
        "prompt": prompt,
        "session_type": "isolated",
        "timeout_seconds": timeout_seconds,
        "delete_after_run": True,
        "metadata": {
            "drive": "FIRST_LIGHT",
            "source": "emergence",
            "trigger": "first_light",
            "session_number": session_num,
        }
    }
    
    if model:
        req_data["model"] = model
    
    try:
        req_json = json.dumps(req_data).encode("utf-8")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {gateway_token}"
        }
        
        req = urllib.request.Request(
            f"{gateway_url}/v1/cron/add",
            data=req_json,
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("success", False) or result.get("id") is not None
            
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False
    except Exception:
        return False


def spawn_via_cli(prompt: str, config: dict, session_num: int) -> bool:
    """Fallback: Spawn session via openclaw CLI.
    
    Args:
        prompt: The full session prompt
        config: Configuration dictionary
        session_num: Session number for metadata
        
    Returns:
        True if session spawned successfully
    """
    timeout_seconds = get_config_value(config, "timeout_seconds", 900)
    model = get_config_value(config, "model", None) or config.get("agent", {}).get("model")
    
    cmd = [
        "openclaw", "cron", "add",
        "--at", "10s",
        "--session", "isolated",
        "--message", prompt,
        "--timeout-seconds", str(timeout_seconds),
        "--delete-after-run",
        "--name", f"first-light-session-{session_num}",
        "--no-deliver",
    ]
    
    if model:
        cmd.extend(["--model", model])
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    except Exception:
        return False


def schedule_exploration_session(config: dict, state: dict, session_num: int) -> bool:
    """Spawn an OpenClaw isolated session with an exploration prompt.
    
    Args:
        config: Configuration dictionary
        state: Current First Light state
        session_num: Session number for tracking
        
    Returns:
        True if session spawned successfully
    """
    prompt_text, prompt_idx = select_prompt(state.get("prompt_rotation", []))
    full_prompt = build_exploration_prompt(prompt_text, session_num)
    
    # Try CLI first (more reliable — handles its own auth)
    if spawn_via_cli(full_prompt, config, session_num):
        # Update rotation tracking
        if "prompt_rotation" not in state:
            state["prompt_rotation"] = []
        state["prompt_rotation"].append(prompt_idx)
        return True
    
    # Fallback to API
    if spawn_via_api(full_prompt, config, session_num):
        if "prompt_rotation" not in state:
            state["prompt_rotation"] = []
        state["prompt_rotation"].append(prompt_idx)
        return True
    
    return False


def calculate_next_run_time(last_run: Optional[str], frequency_hours: float) -> str:
    """Calculate the next scheduled run time.
    
    Args:
        last_run: ISO timestamp of last run or None
        frequency_hours: Hours between runs
        
    Returns:
        ISO timestamp of next scheduled run
    """
    now = datetime.now(timezone.utc)
    
    if last_run:
        try:
            last = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
            next_run = last + timedelta(hours=frequency_hours)
            # If we've passed the next run time, schedule from now
            if next_run < now:
                next_run = now + timedelta(hours=frequency_hours)
            return next_run.isoformat()
        except (ValueError, AttributeError):
            pass
    
    # No last run or invalid, schedule soon
    return (now + timedelta(minutes=5)).isoformat()


def should_run(state: dict, frequency_hours: float) -> bool:
    """Check if it's time to run First Light sessions.
    
    Args:
        state: Current First Light state
        frequency_hours: Hours between runs
        
    Returns:
        True if it's time to spawn sessions
    """
    if state.get("status") != "active":
        return False
    
    next_run_str = state.get("next_run_time")
    if not next_run_str:
        return True
    
    try:
        next_run = datetime.fromisoformat(next_run_str.replace("Z", "+00:00"))
        return datetime.now(timezone.utc) >= next_run
    except (ValueError, AttributeError):
        return True


def run_first_light_tick(config: dict, dry_run: bool = False) -> dict:
    """Check if it's time to spawn sessions and spawn if needed.
    
    Args:
        config: Configuration dictionary
        dry_run: If True, don't actually spawn sessions
        
    Returns:
        Results dictionary with stats
    """
    results = {
        "spawned": 0,
        "failed": 0,
        "skipped": False,
        "next_run": None,
    }
    
    # Load state and config
    state = load_first_light_state(config)
    
    # Get dials
    frequency_hours = parse_frequency(get_config_value(config, "frequency", 4))
    size = int(get_config_value(config, "size", 3))
    
    # Check if we should run
    if not should_run(state, frequency_hours):
        results["skipped"] = True
        results["next_run"] = state.get("next_run_time")
        return results
    
    # Check for runaway spawning (don't spawn if we're way behind)
    next_run_str = state.get("next_run_time")
    if next_run_str:
        try:
            next_run = datetime.fromisoformat(next_run_str.replace("Z", "+00:00"))
            hours_behind = (datetime.now(timezone.utc) - next_run).total_seconds() / 3600
            if hours_behind > frequency_hours * 2:
                # We're more than 2 cycles behind, catch up by adjusting next_run
                state["next_run_time"] = datetime.now(timezone.utc).isoformat()
        except (ValueError, AttributeError):
            pass
    
    # Update state to active if not already
    if state["status"] == "not_started":
        state["status"] = "active"
        state["started_at"] = datetime.now(timezone.utc).isoformat()
    
    # Spawn sessions
    for i in range(size):
        session_num = state["sessions_scheduled"] + 1
        
        if dry_run:
            print(f"[DRY RUN] Would spawn session #{session_num}")
            results["spawned"] += 1
            state["sessions_scheduled"] += 1
            continue
        
        if schedule_exploration_session(config, state, session_num):
            results["spawned"] += 1
            state["sessions_scheduled"] += 1
            state["sessions"].append({
                "session_number": session_num,
                "scheduled_at": datetime.now(timezone.utc).isoformat(),
                "status": "scheduled",
            })
        else:
            results["failed"] += 1
            break  # Stop trying if one fails
    
    # Update next run time
    state["next_run_time"] = calculate_next_run_time(
        datetime.now(timezone.utc).isoformat(),
        frequency_hours
    )
    results["next_run"] = state["next_run_time"]
    
    # Save state
    if not dry_run:
        save_first_light_state(config, state)
    
    return results


def start_first_light(config: dict) -> bool:
    """Start the First Light phase.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if started successfully
    """
    state = load_first_light_state(config)
    
    if state["status"] == "active":
        print("First Light is already active.")
        return False
    
    state["status"] = "active"
    state["started_at"] = datetime.now(timezone.utc).isoformat()
    # Schedule immediately — first run should fire on next tick
    state["next_run_time"] = datetime.now(timezone.utc).isoformat()
    
    save_first_light_state(config, state)
    print("First Light started. Run 'emergence first-light run' to fire the first sessions.")
    return True


def pause_first_light(config: dict) -> bool:
    """Pause the First Light phase.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        True if paused successfully
    """
    state = load_first_light_state(config)
    
    if state["status"] != "active":
        print("First Light is not currently active.")
        return False
    
    state["status"] = "paused"
    save_first_light_state(config, state)
    print("First Light paused. Use 'start' to resume.")
    return True


def get_status(config: dict) -> dict:
    """Get First Light status.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Status dictionary
    """
    state = load_first_light_state(config)
    
    frequency = parse_frequency(get_config_value(config, "frequency", 4))
    size = int(get_config_value(config, "size", 3))
    model = get_config_value(config, "model", None) or config.get("agent", {}).get("model") or "default"
    
    return {
        "status": state.get("status", "not_started"),
        "sessions_completed": state.get("sessions_completed", 0),
        "sessions_scheduled": state.get("sessions_scheduled", 0),
        "started_at": state.get("started_at"),
        "emerged_at": state.get("emerged_at"),
        "next_run": state.get("next_run_time"),
        "config": {
            "frequency_hours": frequency,
            "size": size,
            "model": model,
        },
    }


def strip_json_comments(text: str) -> str:
    """Strip // and # comments from JSON-with-comments text.
    
    Handles comments outside of strings only.
    
    Args:
        text: JSON text potentially containing comments
        
    Returns:
        Clean JSON text
    """
    import re
    # Remove single-line // comments (not inside strings)
    result = re.sub(r'(?<!["\w])//.*', '', text)
    # Remove single-line # comments at start of line
    result = re.sub(r'^\s*#.*$', '', result, flags=re.MULTILINE)
    return result


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from YAML or JSON file.
    
    Search order when no explicit path given:
    1. EMERGENCE_CONFIG environment variable
    2. <workspace>/emergence.json (workspace from OPENCLAW_WORKSPACE or ~/.openclaw/workspace)
    3. ./emergence.yaml (CWD fallback)
    4. ./emergence.json (CWD fallback)
    
    Args:
        config_path: Optional explicit path to config file
        
    Returns:
        Configuration dictionary
    """
    defaults = {
        "agent": {"name": "My Agent", "model": None},
        "paths": {"workspace": ".", "state": ".emergence/state"},
        "first_light": {
            "frequency": 4,
            "size": 3,
            "model": None,
            "timeout_seconds": 900,
        }
    }
    
    # Resolve config path
    if config_path is None:
        # Check environment variable first
        env_config = os.environ.get("EMERGENCE_CONFIG")
        if env_config and Path(env_config).exists():
            config_path = Path(env_config)
        else:
            # Check workspace directory
            workspace = os.environ.get("OPENCLAW_WORKSPACE", 
                                       str(Path.home() / ".openclaw" / "workspace"))
            workspace_config = Path(workspace) / "emergence.json"
            if workspace_config.exists():
                config_path = workspace_config
            else:
                # CWD fallback
                for name in CONFIG_FILENAMES:
                    if Path(name).exists():
                        config_path = Path(name)
                        break
    
    if config_path is None or not config_path.exists():
        return defaults
    
    try:
        content = config_path.read_text(encoding="utf-8")
        ext = config_path.suffix.lower()
        
        if ext == ".json":
            # JSON with comments support
            clean = strip_json_comments(content)
            config = json.loads(clean)
        elif ext in (".yaml", ".yml"):
            # Simple YAML parsing (sufficient for our config structure)
            config = defaults.copy()
            current_section = None
            
            for line in content.split("\n"):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                # Section header
                if line.endswith(":") and not line.startswith("-"):
                    current_section = line[:-1].strip()
                    if current_section not in config:
                        config[current_section] = {}
                    continue
                
                # Key-value pair
                if ":" in line and current_section:
                    key, val = line.split(":", 1)
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    
                    # Type conversion
                    if val.lower() in ("true", "yes"):
                        val = True
                    elif val.lower() in ("false", "no"):
                        val = False
                    elif val.isdigit():
                        val = int(val)
                    elif val.replace(".", "").isdigit() and val.count(".") == 1:
                        val = float(val)
                    elif val == "null" or val == "":
                        val = None
                    
                    config[current_section][key] = val
        else:
            return defaults
        
        # Merge with defaults (deep merge top-level dicts)
        merged = {}
        for key in set(list(defaults.keys()) + list(config.keys())):
            default_val = defaults.get(key, {})
            config_val = config.get(key, {})
            if isinstance(default_val, dict) and isinstance(config_val, dict):
                merged[key] = {**default_val, **config_val}
            elif key in config:
                merged[key] = config_val
            else:
                merged[key] = default_val
        
        return merged
    except (IOError, json.JSONDecodeError):
        return defaults


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="First Light Orchestrator — Self-calibrating onboarding"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to config file (emergence.yaml or emergence.json)"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # run command
    run_parser = subparsers.add_parser("run", help="Run First Light tick (spawn sessions if due)")
    run_parser.add_argument("--dry-run", action="store_true", help="Preview without spawning")
    
    # status command
    subparsers.add_parser("status", help="Show First Light status")
    
    # start command
    subparsers.add_parser("start", help="Start First Light phase")
    
    # pause command
    subparsers.add_parser("pause", help="Pause First Light phase")
    
    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze sessions for drive discoveries")
    analyze_parser.add_argument("--session", type=Path, help="Specific session file to analyze")
    analyze_parser.add_argument("--limit", type=int, default=5, help="Number of recent sessions to analyze (default: 5)")
    analyze_parser.add_argument("--no-activate", action="store_true", help="Register but don't activate drives")

    # complete command
    complete_parser = subparsers.add_parser("complete", help="Complete First Light phase (graduation)")
    complete_parser.add_argument("--force", action="store_true", help="Complete even if gates not met")
    complete_parser.add_argument("--grandfather", action="store_true", help="Grandfather pre-v0.2.0 agents with historical sessions")
    
    # grandfather command (alias for complete --grandfather)
    subparsers.add_parser("grandfather", help="Complete First Light for pre-v0.2.0 agents with historical sessions")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # Load config
    config = load_config(args.config)
    
    if args.command == "run":
        results = run_first_light_tick(config, dry_run=args.dry_run)
        
        if args.dry_run:
            print("First Light Tick (DRY RUN)")
            print("=" * 25)
        else:
            print("First Light Tick")
            print("=" * 16)
        
        print(f"Status: {'Active' if not results['skipped'] else 'Skipped (not due)'}")
        print(f"Sessions spawned: {results['spawned']}")
        print(f"Sessions failed: {results['failed']}")
        if results.get("next_run"):
            print(f"Next run: {results['next_run']}")
        
        sys.exit(0 if results["failed"] == 0 else 1)
    
    elif args.command == "status":
        from .completion import get_first_light_status, format_status_display
        
        workspace = Path(config.get("workspace", Path.cwd()))
        status = get_first_light_status(workspace)
        
        print(format_status_display(status))
        
        sys.exit(0)
    
    elif args.command == "start":
        success = start_first_light(config)
        sys.exit(0 if success else 1)
    
    elif args.command == "pause":
        success = pause_first_light(config)
        sys.exit(0 if success else 1)
    
    elif args.command == "analyze":
        from .post_session import analyze_session, analyze_recent_sessions
        
        workspace = Path(config.get("workspace", Path.cwd()))
        auto_activate = not args.no_activate
        
        if args.session:
            analyze_session(workspace, args.session, auto_activate=auto_activate)
        else:
            analyze_recent_sessions(workspace, limit=args.limit, auto_activate=auto_activate)
        
        sys.exit(0)

    elif args.command == "complete":
        from .completion import manual_complete_first_light, grandfather_first_light, get_first_light_status, format_status_display
        
        workspace = Path(config.get("workspace", Path.cwd()))
        
        if args.grandfather:
            # Grandfather mode - scan historical sessions
            print("🔍 Scanning for historical First Light sessions...")
            print()
            result = grandfather_first_light(workspace)
            
            if result["success"]:
                print(result["message"])
                sys.exit(0)
            else:
                print(f"❌ {result['message']}")
                if "evidence" in result:
                    evidence = result["evidence"]
                    print()
                    print("Historical evidence found:")
                    print(f"  • Sessions: {evidence.get('historical_sessions', 0)}")
                    print(f"  • Unique days: {evidence.get('unique_days', 0)}")
                    print(f"  • Drives: {evidence.get('discovered_drives', 0)}")
                    if evidence.get('drive_names'):
                        print(f"    ({', '.join(evidence['drive_names'])})")
                sys.exit(1)
        
        elif args.force:
            # Show current status first
            print(format_status_display(get_first_light_status(workspace)))
            print("⚠️  Force completion requested. This will:")
            print("   • Lock in your discovered drives")
            print("   • Enable consolidation review for new discoveries")
            print("   • Transition to normal operation")
            print()
        
        result = manual_complete_first_light(workspace, force=args.force)
        
        if result["success"]:
            print(result["message"])
            sys.exit(0)
        else:
            print(f"Error: {result['message']}")
            sys.exit(1)
    
    elif args.command == "grandfather":
        from .completion import grandfather_first_light
        
        workspace = Path(config.get("workspace", Path.cwd()))
        
        print("🔍 Scanning for historical First Light sessions...")
        print()
        result = grandfather_first_light(workspace)
        
        if result["success"]:
            print(result["message"])
            sys.exit(0)
        else:
            print(f"❌ {result['message']}")
            if "evidence" in result:
                evidence = result["evidence"]
                print()
                print("Historical evidence found:")
                print(f"  • Sessions: {evidence.get('historical_sessions', 0)}")
                print(f"  • Unique days: {evidence.get('unique_days', 0)}")
                print(f"  • Drives: {evidence.get('discovered_drives', 0)}")
                if evidence.get('drive_names'):
                    print(f"    ({', '.join(evidence['drive_names'])})")
            sys.exit(1)


if __name__ == "__main__":
    main()
