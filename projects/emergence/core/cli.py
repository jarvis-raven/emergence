#!/usr/bin/env python3
"""
🌊 Emergence CLI v0.3.0

Main entry point for the Emergence AI framework.

Usage:
    emergence <command> [args]
    python -m core.cli <command> [args]
    python -m core <command> [args]

Commands:
    nautilus    Nautilus memory palace commands
    help        Show this help message

Examples:
    emergence nautilus search "project status"
    emergence nautilus status
    emergence nautilus maintain --verbose
"""

import sys
import os
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


def cmd_nautilus(args):
    """Delegate to nautilus CLI module."""
    from core.nautilus.cli import main as nautilus_main
    
    # Replace sys.argv temporarily - nautilus_main expects sys.argv[1] to be the command
    old_argv = sys.argv
    sys.argv = ["emergence"] + args
    
    try:
        nautilus_main()
    except SystemExit as e:
        # Re-raise SystemExit to preserve exit codes
        raise e
    finally:
        sys.argv = old_argv


def cmd_help(args):
    """Show help message."""
    print(__doc__)
    print("\nNautilus Commands:")
    print("  search <query>       Full pipeline search")
    print("  status               Show system status")
    print("  maintain             Run maintenance tasks")
    print("  classify [file]      Classify into chambers")
    print("  gravity <file>       Show gravity score")
    print("  chambers <cmd>       Chambers subcommands")
    print("  doors <cmd>          Doors subcommands")
    print("  mirrors <cmd>        Mirrors subcommands")
    print("\nExamples:")
    print('  emergence nautilus search "project status" --n 10')
    print('  emergence nautilus maintain --register-recent --verbose')
    print('  emergence nautilus status')


def main():
    """Main CLI entry point."""
    commands = {
        "nautilus": cmd_nautilus,
        "help": cmd_help,
        "--help": cmd_help,
        "-h": cmd_help,
    }
    
    if len(sys.argv) < 2:
        cmd_help([])
        sys.exit(0)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command in commands:
        try:
            commands[command](args)
        except KeyboardInterrupt:
            print("\nInterrupted", file=sys.stderr)
            sys.exit(130)
        except SystemExit as e:
            # Preserve exit codes from subcommands
            sys.exit(e.code)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            sys.exit(1)
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print("Run 'emergence help' for usage", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
