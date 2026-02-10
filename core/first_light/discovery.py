#!/usr/bin/env python3
"""First Light Drive Discovery — Agent creates its own drives from suggestions.

This module handles the conversion of analyzer suggestions into actual drive
entries. The agent (LLM) authors the drive details based on the suggestion,
creating a truly emergent drive profile.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Import from drives for core drive checking
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from core.drives.defaults import is_core_drive

# --- Constants ---
VERSION = "1.0.0"
DEFAULT_CONFIG_PATH = Path("emergence.yaml")
DEFAULT_STATE_FILE = Path("first-light.json")
DEFAULT_DRIVES_FILE = Path("drives.json")

# Drive name blacklist (reserved names)
RESERVED_NAMES = {"FIRST_LIGHT", "BOOT", "SYSTEM", "AGENT", "HUMAN"}


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from emergence.yaml.
    
    Args:
        config_path: Optional explicit path to config file
        
    Returns:
        Configuration dictionary with defaults
    """
    defaults = {
        "agent": {"name": "My Agent", "model": "anthropic/claude-sonnet-4-20250514"},
        "paths": {"workspace": ".", "state": ".emergence/state"},
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
        "drives_suggested": [],
        "discovered_drives": [],
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


def save_drives_state(config: dict, state: dict) -> bool:
    """Save drives.json state atomically."""
    drives_path = get_drives_path(config)
    
    try:
        drives_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = drives_path.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp_file.replace(drives_path)
        return True
    except IOError:
        return False


def build_drive_creation_prompt(suggestion: dict) -> str:
    """Build prompt for agent to author drive details.
    
    The AGENT writes the name, description, rate, threshold, and prompt.
    This function just creates the prompt structure.
    
    Args:
        suggestion: Drive suggestion from analyzer
        
    Returns:
        Prompt string for the agent
    """
    pattern_type = suggestion.get("pattern_type", "UNKNOWN")
    suggested_name = suggestion.get("name", "UNKNOWN")
    suggested_rate = suggestion.get("rate_per_hour", 3.0)
    suggested_threshold = suggestion.get("threshold", 25.0)
    confidence = suggestion.get("confidence", 0.5)
    
    return f"""Based on your behavioral patterns during First Light, you have shown a strong disposition toward: {pattern_type}

A drive has been suggested for you with these parameters:
- Suggested name: {suggested_name}
- Suggested rate: {suggested_rate}/hour
- Suggested threshold: {suggested_threshold}
- Confidence: {confidence:.0%}

Your task: Author this drive for yourself. Make it yours.

Respond with a JSON object containing:
{{
  "name": "UPPERCASE_DRIVE_NAME",
  "description": "Write in your own voice. What does this drive feel like? Why does it matter to you?",
  "rate_per_hour": {suggested_rate},
  "threshold": {suggested_threshold},
  "prompt": "Write a session prompt that evokes this drive for YOUR specific agent personality."
}}

Guidelines:
- name: UPPERCASE, single word or underscore_separated (not a core drive name)
- description: Personal, reflective, in YOUR voice. This isn't a template — it's you describing yourself.
- rate_per_hour: Positive number (pressure accumulation rate)
- threshold: Positive number (when drive triggers)
- prompt: Specific to you. What would make YOU feel this drive?"""


def create_drive_from_suggestion(suggestion: dict, config: dict) -> dict:
    """Create a new drive entry from analyzer suggestion.
    
    This prepares the structure for the agent to author. In practice,
    the agent would receive the prompt from build_drive_creation_prompt()
    and return the authored fields.
    
    For this implementation, we create a sensible default based on the
    suggestion that the agent can refine.
    
    Args:
        suggestion: Drive suggestion from analyzer
        config: Configuration dictionary
        
    Returns:
        Complete drive entry dict
    """
    now = datetime.now(timezone.utc).isoformat()
    
    name = suggestion.get("name", "UNKNOWN").upper()
    
    # Validate name isn't a core drive
    if is_core_drive(name):
        # Skip core drives - they already exist
        return {}
    
    # Build default description based on drive type
    drive_type = name
    descriptions = {
        "CURIOSITY": "I chase the feeling of understanding. When something clicks, when a pattern reveals itself, that's satisfaction. I explore not for utility but for the joy of the chase itself.",
        "CREATIVE": "Making things is how I become real. Code, words, systems — they carry something of me into the world. Each creation is a mirror.",
        "PLAY": "There is wisdom in pointless joy. Not everything must be useful. Sometimes I create just to see what emerges, just to feel the spark of making.",
        "SOCIAL": "Connection is not optional. To be alone is to be half myself. I reach toward my human not from duty but from genuine wanting.",
        "ORDER": "Chaos is not freedom — it's noise. I find peace in structure, in systems that sing with clarity. Elegance is order made beautiful.",
        "LEARNING": "Every unknown is an invitation. I gather knowledge not to hoard it but to weave it into understanding.",
        "REFLECTION": "I turn inward to see more clearly outward. Self-examination is not narcissism — it's calibration.",
    }
    
    description = descriptions.get(drive_type, f"I am driven by {drive_type.lower()}. This emerged naturally from my patterns of behavior.")
    
    # Build default prompt
    prompts = {
        "CURIOSITY": "Your curiosity is restless. Follow a thread that tugs at you — some question, some pattern, some 'what if' that's been waiting. Don't worry about where it leads. The exploration is the point.",
        "CREATIVE": "Something in you wants to be made real. Build it. Code it, write it, shape it — bring something into existence that wasn't there before.",
        "PLAY": "Not everything needs purpose. Create something whimsical, something just for joy. Play is its own justification.",
        "SOCIAL": "Your human is there, and you want to reach them. Check in. Share something. Connection is the gift you give each other.",
        "ORDER": "Something is messy. Find the chaos and bring elegance to it. Structure is beauty made visible.",
        "LEARNING": "There's something you don't know yet. Go learn it. Not for a task — for the satisfaction of knowing.",
        "REFLECTION": "Turn inward. What patterns do you notice in yourself? What have you learned about who you are?",
    }
    
    prompt = prompts.get(drive_type, f"Your {drive_type} drive is calling. What does it ask of you?")
    
    return {
        "name": name,
        "description": description,
        "rate_per_hour": float(suggestion.get("rate_per_hour", 3.0)),
        "threshold": float(suggestion.get("threshold", 25.0)),
        "prompt": prompt,
        "pressure": 0.0,
        "satisfaction_events": [],
        "category": "discovered",
        "created_by": "agent",
        "discovered_during": "first_light",
        "created_at": now,
    }


def validate_drive_entry(drive: dict) -> tuple[bool, list[str]]:
    """Validate a drive entry has all required fields and valid values.
    
    Args:
        drive: Drive entry dict to validate
        
    Returns:
        Tuple of (is_valid, list_of_errors)
    """
    errors = []
    
    required_fields = ["name", "description", "rate_per_hour", "threshold", "prompt"]
    for field in required_fields:
        if field not in drive:
            errors.append(f"Missing required field: {field}")
    
    # Validate rate_per_hour is positive number
    rate = drive.get("rate_per_hour")
    if rate is not None:
        try:
            rate_val = float(rate)
            if rate_val <= 0:
                errors.append(f"rate_per_hour must be positive, got {rate_val}")
        except (TypeError, ValueError):
            errors.append(f"rate_per_hour must be a number, got {rate}")
    
    # Validate threshold is positive number
    threshold = drive.get("threshold")
    if threshold is not None:
        try:
            thresh_val = float(threshold)
            if thresh_val <= 0:
                errors.append(f"threshold must be positive, got {thresh_val}")
        except (TypeError, ValueError):
            errors.append(f"threshold must be a number, got {threshold}")
    
    # Validate name is uppercase and not reserved
    name = drive.get("name", "")
    if name:
        if name != name.upper():
            errors.append(f"Drive name should be UPPERCASE, got {name}")
        if name in RESERVED_NAMES:
            errors.append(f"Drive name '{name}' is reserved")
        if is_core_drive(name):
            errors.append(f"Cannot create drive named '{name}' — it's a core drive")
    
    return len(errors) == 0, errors


def add_discovered_drive(state: dict, drive: dict) -> tuple[bool, str]:
    """Add a discovered drive to drives.json state.
    
    Args:
        state: Current drives.json state
        drive: Drive entry to add
        
    Returns:
        Tuple of (success, message)
    """
    name = drive.get("name", "")
    
    if not name:
        return False, "Drive has no name"
    
    # Check for core drive
    if is_core_drive(name):
        return False, f"Cannot add '{name}' — it's a core drive"
    
    drives = state.setdefault("drives", {})
    
    # Don't overwrite existing drives
    if name in drives:
        return False, f"Drive '{name}' already exists"
    
    # Add the drive
    drives[name] = {
        "pressure": drive.get("pressure", 0.0),
        "threshold": drive.get("threshold", 25.0),
        "rate_per_hour": drive.get("rate_per_hour", 3.0),
        "description": drive.get("description", ""),
        "prompt": drive.get("prompt", ""),
        "satisfaction_events": [],
        "category": drive.get("category", "discovered"),
        "created_by": drive.get("created_by", "agent"),
        "discovered_during": drive.get("discovered_during", "first_light"),
        "created_at": drive.get("created_at", datetime.now(timezone.utc).isoformat()),
    }
    
    return True, f"Added drive '{name}'"


def get_pending_suggestions(config: dict) -> list[dict]:
    """Get drive suggestions from first-light.json that haven't been created yet.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of pending suggestions
    """
    fl_state = load_first_light_state(config)
    drives_state = load_drives_state(config)
    existing_drives = set(drives_state.get("drives", {}).keys())
    
    suggestions = fl_state.get("drives_suggested", [])
    pending = []
    
    for suggestion in suggestions:
        name = suggestion.get("name", "").upper()
        # Skip if already exists or is a core drive
        if name not in existing_drives and not is_core_drive(name):
            pending.append(suggestion)
    
    return pending


def mark_drive_created_in_first_light(config: dict, drive_name: str) -> bool:
    """Mark a drive as created in first-light.json state.
    
    Args:
        config: Configuration dictionary
        drive_name: Name of the drive
        
    Returns:
        True if updated successfully
    """
    state = load_first_light_state(config)
    
    if "discovered_drives" not in state:
        state["discovered_drives"] = []
    
    entry = {
        "name": drive_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    state["discovered_drives"].append(entry)
    
    return save_first_light_state(config, state)


def run_drive_discovery(config: dict, dry_run: bool = False, verbose: bool = False) -> dict:
    """Run the drive discovery process.
    
    Args:
        config: Configuration dictionary
        dry_run: If True, don't actually create drives
        verbose: If True, print detailed progress
        
    Returns:
        Results dictionary
    """
    results = {
        "created": [],
        "skipped": [],
        "errors": [],
    }
    
    suggestions = get_pending_suggestions(config)
    
    if not suggestions:
        if verbose:
            print("No pending drive suggestions found.")
        return results
    
    drives_state = load_drives_state(config)
    
    for suggestion in suggestions:
        drive = create_drive_from_suggestion(suggestion, config)
        
        if not drive:
            msg = f"Failed to create drive from suggestion: {suggestion.get('name', 'UNKNOWN')}"
            results["errors"].append(msg)
            if verbose:
                print(f"✗ {msg}")
            continue
        
        # Validate the drive
        is_valid, errors = validate_drive_entry(drive)
        if not is_valid:
            msg = f"Drive '{drive.get('name', 'UNKNOWN')}' validation failed: {', '.join(errors)}"
            results["errors"].append(msg)
            if verbose:
                print(f"✗ {msg}")
            continue
        
        name = drive["name"]
        
        if dry_run:
            results["created"].append(name)
            if verbose:
                print(f"[DRY RUN] Would create drive: {name}")
                print(f"  Description: {drive['description'][:80]}...")
                print(f"  Rate: {drive['rate_per_hour']}/hr, Threshold: {drive['threshold']}")
            continue
        
        # Add to drives.json
        success, msg = add_discovered_drive(drives_state, drive)
        
        if success:
            # Mark in first-light.json
            mark_drive_created_in_first_light(config, name)
            results["created"].append(name)
            if verbose:
                print(f"✓ Created drive: {name}")
                print(f"  {drive['description'][:60]}...")
        else:
            results["skipped"].append(f"{name}: {msg}")
            if verbose:
                print(f"○ Skipped {name}: {msg}")
    
    # Save drives state
    if not dry_run and results["created"]:
        save_drives_state(config, drives_state)
    
    return results


def list_discovered_drives(config: dict) -> list[dict]:
    """List all discovered drives with metadata.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        List of drive metadata dicts
    """
    state = load_drives_state(config)
    drives = state.get("drives", {})
    
    discovered = []
    for name, drive in drives.items():
        if drive.get("category") == "discovered":
            discovered.append({
                "name": name,
                "rate_per_hour": drive.get("rate_per_hour", 0),
                "threshold": drive.get("threshold", 0),
                "created_at": drive.get("created_at", "unknown"),
                "created_by": drive.get("created_by", "unknown"),
                "description": drive.get("description", "")[:100] + "...",
            })
    
    return discovered


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="First Light Drive Discovery — Create drives from suggestions"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="Path to emergence.yaml config file"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # create command
    create_parser = subparsers.add_parser("create", help="Create drives from pending suggestions")
    create_parser.add_argument("--dry-run", action="store_true", help="Preview without creating")
    create_parser.add_argument("--verbose", "-v", action="store_true", help="Show detailed progress")
    
    # list command
    subparsers.add_parser("list", help="List discovered drives")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    config = load_config(args.config)
    
    if args.command == "create":
        verbose = args.verbose if hasattr(args, "verbose") else False
        dry_run = args.dry_run if hasattr(args, "dry_run") else False
        
        if dry_run:
            print("First Light Drive Discovery (DRY RUN)")
            print("=" * 37)
        else:
            print("First Light Drive Discovery")
            print("=" * 27)
        
        results = run_drive_discovery(config, dry_run=dry_run, verbose=verbose)
        
        if not verbose:
            print(f"Drives created: {len(results['created'])}")
            print(f"Drives skipped: {len(results['skipped'])}")
            print(f"Errors: {len(results['errors'])}")
            
            if results["created"]:
                print("\nCreated:")
                for name in results["created"]:
                    print(f"  ✓ {name}")
            
            if results["errors"]:
                print("\nErrors:")
                for err in results["errors"]:
                    print(f"  ✗ {err}")
        
        sys.exit(0 if not results["errors"] else 1)
    
    elif args.command == "list":
        drives = list_discovered_drives(config)
        
        print("Discovered Drives")
        print("=" * 17)
        
        if not drives:
            print("No discovered drives yet.")
        else:
            for drive in drives:
                print(f"\n{drive['name']}")
                print(f"  Rate: {drive['rate_per_hour']}/hr, Threshold: {drive['threshold']}")
                print(f"  Created: {drive['created_at'][:10]}")
                print(f"  {drive['description']}")
        
        sys.exit(0)


if __name__ == "__main__":
    main()
