#!/usr/bin/env python3
"""Emergence CLI entry point.

Routes commands to appropriate modules when installed via pip.
"""

import os
import sys
from pathlib import Path


def main():
    """Main CLI entry point for pip-installed emergence."""
    # Set EMERGENCE_STATE if not already set
    if "EMERGENCE_STATE" not in os.environ:
        os.environ["EMERGENCE_STATE"] = str(Path.home() / ".openclaw" / "state")

    # Get command
    command = sys.argv[1] if len(sys.argv) > 1 else "help"
    args = sys.argv[2:]

    # Route to appropriate module
    if command in ("awaken", "init"):
        from core.setup.init_wizard import main as wizard_main

        sys.argv = ["emergence-init"] + args
        wizard_main()

    elif command == "drives":
        from core.drives.__main__ import main as drives_main

        sys.argv = ["emergence-drives"] + args
        drives_main()

    elif command == "dream":
        from core.dream_engine.__main__ import main as dream_main

        sys.argv = ["emergence-dream"] + args
        dream_main()

    elif command in ("first-light", "fl"):
        from core.first_light.__main__ import main as fl_main

        sys.argv = ["emergence-first-light"] + args
        fl_main()

    elif command == "memory":
        from core.memory.__main__ import main as memory_main

        sys.argv = ["emergence-memory"] + args
        memory_main()

    elif command == "consolidate":
        from core.memory.consolidation import main as consolidate_main

        sys.argv = ["emergence-consolidate"] + args
        consolidate_main()

    elif command == "migrate":
        from core.setup.migrate.migrate import main as migrate_main

        sys.argv = ["emergence-migrate"] + args
        migrate_main()

    elif command in ("nightly", "nightly-build"):
        from core.memory.nightly_build import main as nightly_main

        sys.argv = ["emergence-nightly"] + args
        nightly_main()

    elif command == "nautilus":
        from core.nautilus.nautilus_cli import main as nautilus_main

        sys.argv = ["emergence-nautilus"] + args
        nautilus_main()

    elif command == "openclaw-hook":
        from core.setup.openclaw_hook import installer

        subcommand = args[0] if args else "status"

        if subcommand == "install":
            force = "--force" in args
            success, message = installer.install_hook(force=force)
            print(message)
            sys.exit(0 if success else 1)

        elif subcommand == "uninstall":
            success, message = installer.uninstall_hook()
            print(message)
            sys.exit(0 if success else 1)

        elif subcommand == "status":
            is_installed, message = installer.hook_status()
            print(message)
            sys.exit(0)

        else:
            print(f"Unknown openclaw-hook subcommand: {subcommand}", file=sys.stderr)
            print("Usage: emergence openclaw-hook [install|uninstall|status]", file=sys.stderr)
            sys.exit(1)

    elif command == "status":
        print("Emergence Status")
        print("================")
        emergence_root = Path(__file__).parent.parent
        emergence_state = os.environ.get("EMERGENCE_STATE", "~/.openclaw/state")
        print(f"Root: {emergence_root}")
        print(f"State: {emergence_state}")
        print()

        try:
            from core.drives.__main__ import main as drives_main

            sys.argv = ["emergence-drives", "status"]
            drives_main()
        except Exception:
            print("Drives: not initialized")

        print()

        try:
            from core.first_light.__main__ import main as fl_main

            sys.argv = ["emergence-first-light", "status"]
            fl_main()
        except Exception:
            print("First Light: not initialized")

    elif command in ("version", "--version", "-v"):
        try:
            from core import __version__

            print(f"Emergence {__version__}")
        except ImportError:
            print("Emergence (version unknown)")

    elif command in ("help", "--help", "-h"):
        print(
            """Emergence — AI Agent Selfhood Toolkit

Usage: emergence <command> [options]

Commands:
  awaken          Initialize a new agent (interactive wizard)
  init            Alias for awaken
  drives          Manage internal drives (tick, status, satisfy)
  dream           Run dream engine
  first-light     First Light orchestrator (run, status, start, pause)
  fl              Alias for first-light
  memory          Memory lifecycle management
  consolidate     Run memory consolidation
  nautilus        Nautilus memory palace (search, status, maintain)
  nightly         Run nightly build routine
  migrate         Migrate agent between machines (export/import/rewrite-paths)
  openclaw-hook   Install/manage OpenClaw drives integration
  status          Show overall Emergence status
  version         Show version

Examples:
  emergence awaken                    # Start the setup wizard
  emergence awaken --non-interactive --name Aurora --human Dan
  emergence drives status             # Check drive pressures
  emergence first-light run           # Trigger First Light tick
  emergence nautilus search "query"   # Search with full nautilus pipeline
  emergence nautilus status           # Show nautilus system status
  emergence nautilus maintain         # Run nightly maintenance
  emergence openclaw-hook install     # Install OpenClaw drives hook
  emergence status                    # Show overall status

Documentation: https://github.com/jarvis-raven/emergence
"""
        )

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Run 'emergence help' for usage.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
