#!/usr/bin/env python3
"""Emergence Shelves CLI — Manage shelf configuration.

Commands:
- shelves list — Show all available shelves + status
- shelves enable <id> — Enable a shelf
- shelves disable <id> — Disable a shelf
- shelves priority <id> <value> — Set shelf priority
"""

import json
import sys
from pathlib import Path


def get_config_path() -> Path:
    """Get path to user shelf configuration."""
    return Path.home() / ".openclaw" / "config" / "shelves.json"


def load_config() -> dict:
    """Load user shelf configuration."""
    config_path = get_config_path()

    if not config_path.exists():
        return {"builtins": {}, "custom": {}}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Warning: Could not load {config_path}: {e}", file=sys.stderr)
        return {"builtins": {}, "custom": {}}


def save_config(config: dict) -> bool:
    """Save user shelf configuration."""
    config_path = get_config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)
        return True
    except IOError as e:
        print(f"Error saving config: {e}", file=sys.stderr)
        return False


# Available built-in shelves (in default order)
BUILTIN_SHELVES = {
    "budget": {"name": "Budget Transparency", "priority": 95},
    "drives": {"name": "Drives", "priority": 100},
    "pending-reviews": {"name": "Pending Reviews", "priority": 80},
    "latent-drives": {"name": "Latent Drives", "priority": 75},
    "memory": {"name": "Memory", "priority": 90},
    "aspirations": {"name": "Aspirations", "priority": 85},
}


def list_shelves(verbose: bool = False):
    """List all available shelves with their status."""
    config = load_config()

    print("📚 Emergence Shelves")
    print("=" * 60)
    print()

    # Built-in shelves
    print("Built-in Shelves:")
    print()
    for shelf_id, info in sorted(
        BUILTIN_SHELVES.items(), key=lambda x: x[1]["priority"], reverse=True
    ):
        pref = config.get("builtins", {}).get(shelf_id, {})
        enabled = pref.get("enabled", True)
        priority = pref.get("priority", info["priority"])

        status = "✓ enabled" if enabled else "✗ disabled"

        print(f"  {shelf_id:20} {info['name']:25} (priority: {priority:3}) {status}")

    # Custom shelves
    custom_prefs = config.get("custom", {})
    if custom_prefs:
        print()
        print("Custom Shelves:")
        print()
        for shelf_id, pref in custom_prefs.items():
            enabled = pref.get("enabled", True)
            priority = pref.get("priority", 50)
            status = "✓ enabled" if enabled else "✗ disabled"

            print(f"  {shelf_id:20} (custom) (priority: {priority:3}) {status}")

    print()
    if verbose:
        print(f"Config: {get_config_path()}")
        print()
        print("Use 'emergence shelves <command>' to modify:")
        print("  enable <id>          Enable a shelf")
        print("  disable <id>         Disable a shelf")
        print("  priority <id> <n>    Set shelf priority (higher = first)")


def enable_shelf(shelf_id: str):
    """Enable a shelf."""
    config = load_config()

    # Determine if built-in or custom
    is_builtin = shelf_id in BUILTIN_SHELVES

    if is_builtin:
        if "builtins" not in config:
            config["builtins"] = {}
        if shelf_id not in config["builtins"]:
            config["builtins"][shelf_id] = {}
        config["builtins"][shelf_id]["enabled"] = True
        shelf_type = "built-in"
    else:
        if "custom" not in config:
            config["custom"] = {}
        if shelf_id not in config["custom"]:
            config["custom"][shelf_id] = {}
        config["custom"][shelf_id]["enabled"] = True
        shelf_type = "custom"

    if save_config(config):
        print(f"✓ Enabled {shelf_type} shelf: {shelf_id}")
        print("  Restart Room to apply changes: pkill -f 'room/server' && cd room && npm run dev")
        return 0
    else:
        return 1


def disable_shelf(shelf_id: str):
    """Disable a shelf."""
    config = load_config()

    # Determine if built-in or custom
    is_builtin = shelf_id in BUILTIN_SHELVES

    if is_builtin:
        if "builtins" not in config:
            config["builtins"] = {}
        if shelf_id not in config["builtins"]:
            config["builtins"][shelf_id] = {}
        config["builtins"][shelf_id]["enabled"] = False
        shelf_type = "built-in"
    else:
        if "custom" not in config:
            config["custom"] = {}
        if shelf_id not in config["custom"]:
            config["custom"][shelf_id] = {}
        config["custom"][shelf_id]["enabled"] = False
        shelf_type = "custom"

    if save_config(config):
        print(f"✓ Disabled {shelf_type} shelf: {shelf_id}")
        print("  Restart Room to apply changes: pkill -f 'room/server' && cd room && npm run dev")
        return 0
    else:
        return 1


def set_priority(shelf_id: str, priority: int):
    """Set shelf priority."""
    config = load_config()

    # Determine if built-in or custom
    is_builtin = shelf_id in BUILTIN_SHELVES

    if is_builtin:
        if "builtins" not in config:
            config["builtins"] = {}
        if shelf_id not in config["builtins"]:
            config["builtins"][shelf_id] = {}
        config["builtins"][shelf_id]["priority"] = priority
        shelf_type = "built-in"
    else:
        if "custom" not in config:
            config["custom"] = {}
        if shelf_id not in config["custom"]:
            config["custom"][shelf_id] = {}
        config["custom"][shelf_id]["priority"] = priority
        shelf_type = "custom"

    if save_config(config):
        print(f"✓ Set priority for {shelf_type} shelf '{shelf_id}' to {priority}")
        print("  Restart Room to apply changes: pkill -f 'room/server' && cd room && npm run dev")
        return 0
    else:
        return 1


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Manage Emergence shelf configuration")

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # list command
    list_parser = subparsers.add_parser("list", help="List all shelves")
    list_parser.add_argument("-v", "--verbose", action="store_true", help="Show detailed info")

    # enable command
    enable_parser = subparsers.add_parser("enable", help="Enable a shelf")
    enable_parser.add_argument("shelf_id", help="Shelf ID to enable")

    # disable command
    disable_parser = subparsers.add_parser("disable", help="Disable a shelf")
    disable_parser.add_argument("shelf_id", help="Shelf ID to disable")

    # priority command
    priority_parser = subparsers.add_parser("priority", help="Set shelf priority")
    priority_parser.add_argument("shelf_id", help="Shelf ID")
    priority_parser.add_argument("value", type=int, help="Priority value (higher = first)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    if args.command == "list":
        list_shelves(verbose=args.verbose)
        return 0

    elif args.command == "enable":
        return enable_shelf(args.shelf_id)

    elif args.command == "disable":
        return disable_shelf(args.shelf_id)

    elif args.command == "priority":
        return set_priority(args.shelf_id, args.value)

    return 0


if __name__ == "__main__":
    sys.exit(main())
