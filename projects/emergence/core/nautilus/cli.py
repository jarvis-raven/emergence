#!/usr/bin/env python3
"""
🐚 Nautilus CLI — Command handlers for Emergence integration.

Commands:
  search <query>       Full Nautilus pipeline search
  status               System status report
  maintain             Run all maintenance tasks
  classify [file]      Classify file(s) into chambers
  gravity <file>       Show gravity score for file
  chambers             Chambers subcommands
  doors                Doors subcommands  
  mirrors              Mirrors subcommands
"""

import json
import sys
import os
from pathlib import Path
from typing import List, Optional

# Import from the nautilus package
from . import config
from .gravity import (
    cmd_score as gravity_score,
    cmd_stats as gravity_stats,
    cmd_decay as gravity_decay,
    cmd_top as gravity_top,
    cmd_rerank as gravity_rerank,
    cmd_record_access,
    cmd_record_write,
    cmd_boost,
)
from .chambers import (
    cmd_classify as chambers_classify,
    cmd_status as chambers_status,
    cmd_promote,
    cmd_crystallize,
)
from .doors import (
    cmd_classify as doors_classify,
    cmd_auto_tag,
    cmd_tag,
)
from .mirrors import (
    cmd_stats as mirrors_stats,
    cmd_auto_link,
    cmd_resolve,
)
from .search import run_full_search


def cmd_search(args: List[str]) -> None:
    """Full Nautilus search pipeline."""
    if not args or args[0] in ("--help", "-h"):
        print("""Usage: emergence nautilus search <query> [options]

Options:
  --n N                Number of results (default: 5)
  --trapdoor           Bypass context filtering
  --verbose            Show pipeline steps
  --chamber CHAMBERS   Filter to chambers (atrium,corridor,vault)

Examples:
  emergence nautilus search "project status"
  emergence nautilus search "security review" --n 10 --verbose
""")
        return
    
    # Parse arguments
    query_parts = []
    n = 5
    trapdoor = False
    verbose = False
    chambers = None
    
    i = 0
    while i < len(args):
        if args[i] == "--n" and i + 1 < len(args):
            n = int(args[i + 1])
            i += 2
        elif args[i] == "--trapdoor":
            trapdoor = True
            i += 1
        elif args[i] == "--verbose":
            verbose = True
            i += 1
        elif args[i] == "--chamber" and i + 1 < len(args):
            chambers = args[i + 1]
            i += 2
        else:
            query_parts.append(args[i])
            i += 1
    
    query = " ".join(query_parts)
    
    if not query.strip():
        print("Error: No query provided", file=sys.stderr)
        sys.exit(1)
    
    # Run the full search pipeline
    result = run_full_search(
        query=query,
        n=n,
        trapdoor=trapdoor,
        verbose=verbose,
        chambers_filter=chambers,
    )
    
    print(json.dumps(result, indent=2))


def cmd_status(args: List[str]) -> None:
    """Show full Nautilus system status."""
    import sqlite3
    
    # Get gravity stats
    from .gravity import get_db as get_gravity_db
    db = get_gravity_db()
    
    total_chunks = db.execute("SELECT COUNT(*) FROM gravity").fetchone()[0]
    total_accesses = db.execute("SELECT COUNT(*) FROM access_log").fetchone()[0]
    superseded = db.execute("SELECT COUNT(*) FROM gravity WHERE superseded_by IS NOT NULL").fetchone()[0]
    tagged = db.execute("SELECT COUNT(*) FROM gravity WHERE tags != '[]' AND tags IS NOT NULL").fetchone()[0]
    
    db.close()
    
    # Get chamber distribution
    chambers = chambers_status([])
    
    # Get mirrors stats
    mirrors = mirrors_stats([])
    
    # Get config info
    workspace = config.get_workspace()
    state_dir = config.get_state_dir()
    db_path = config.get_gravity_db_path()
    
    print(json.dumps({
        "🐚 nautilus": {
            "phase_1_gravity": {
                "total_chunks": total_chunks,
                "total_accesses": total_accesses,
                "superseded": superseded,
                "tagged": tagged,
                "coverage": f"{tagged}/{total_chunks}" if total_chunks else "0/0"
            },
            "phase_2_chambers": chambers.get("chambers", {}),
            "phase_3_doors": {
                "patterns_defined": 11,  # From doors.py CONTEXT_PATTERNS
            },
            "phase_4_mirrors": mirrors,
            "config": {
                "workspace": str(workspace),
                "state_dir": str(state_dir),
                "gravity_db": str(db_path),
                "db_exists": db_path.exists()
            }
        }
    }, indent=2))


def cmd_maintain(args: List[str]) -> None:
    """Run all Nautilus maintenance tasks."""
    from datetime import datetime, timezone
    
    verbose = "--verbose" in args
    register_recent = "--register-recent" in args
    
    print("🐚 Nautilus maintenance starting...", file=sys.stderr)
    
    # Step 1: Register recently modified files
    if register_recent:
        print("\n📂 Registering recent files...", file=sys.stderr)
        import subprocess
        workspace = config.get_workspace()
        memory_dir = config.get_memory_dir()
        
        if memory_dir.exists():
            try:
                result = subprocess.run(
                    ["find", str(memory_dir), "-name", "*.md", "-mtime", "-1", "-type", "f"],
                    capture_output=True, text=True, timeout=30
                )
                recent_files = [f for f in result.stdout.strip().split("\n") if f]
                
                for filepath in recent_files:
                    try:
                        rel_path = str(Path(filepath).relative_to(workspace))
                        cmd_record_write([rel_path])
                    except ValueError:
                        pass  # File not in workspace
                
                if verbose:
                    print(f"   Registered {len(recent_files)} recent files", file=sys.stderr)
            except Exception as e:
                if verbose:
                    print(f"   Error registering files: {e}", file=sys.stderr)
    
    # Step 2: Classify chambers
    print("\n📂 Classifying chambers...", file=sys.stderr)
    classify_result = chambers_classify([])
    if verbose:
        print(f"   {json.dumps(classify_result.get('classified', {}))}", file=sys.stderr)
    
    # Step 3: Auto-tag contexts
    print("\n🏷️ Auto-tagging contexts...", file=sys.stderr)
    tag_result = cmd_auto_tag([])
    if verbose:
        print(f"   {tag_result.get('files_tagged', 0)} files tagged", file=sys.stderr)
    
    # Step 4: Run gravity decay
    print("\n⚖️ Running gravity decay...", file=sys.stderr)
    decay_result = gravity_decay([])
    if verbose:
        print(f"   {decay_result.get('decayed', 0)} chunks decayed", file=sys.stderr)
    
    # Step 5: Auto-link mirrors
    print("\n🔗 Auto-linking mirrors...", file=sys.stderr)
    link_result = cmd_auto_link([])
    if verbose:
        print(f"   {link_result.get('linked', 0)} mirrors linked", file=sys.stderr)
    
    print("\n✅ Maintenance complete", file=sys.stderr)
    
    # Output summary
    print(json.dumps({
        "chambers": classify_result.get("classified", {}),
        "tagged": tag_result.get("files_tagged", 0),
        "decayed": decay_result.get("decayed", 0),
        "mirrors_linked": link_result.get("linked", 0),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }, indent=2))


def cmd_classify(args: List[str]) -> None:
    """Classify file(s) into chambers."""
    if args and args[0] in ("--help", "-h"):
        print("""Usage: emergence nautilus classify [file]

Classify memory files into chambers (atrium/corridor/vault).
If no file specified, classifies all memory files.

Examples:
  emergence nautilus classify
  emergence nautilus classify memory/2024-01-15.md
""")
        return
    
    if args:
        # Classify specific file(s)
        from .chambers import classify_chamber
        import sqlite3
        
        db_path = config.get_gravity_db_path()
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
        
        results = []
        for filepath in args:
            if not filepath.startswith("memory/"):
                filepath = f"memory/{filepath}"
            
            chamber = classify_chamber(filepath)
            
            db.execute("""
                INSERT INTO gravity (path, line_start, line_end, chamber)
                VALUES (?, 0, 0, ?)
                ON CONFLICT(path, line_start, line_end) DO UPDATE SET
                    chamber = ?
            """, (filepath, chamber, chamber))
            
            results.append({"path": filepath, "chamber": chamber})
        
        db.commit()
        db.close()
        
        print(json.dumps({"classified": results}, indent=2))
    else:
        # Classify all
        result = chambers_classify([])
        print(json.dumps(result, indent=2))


def cmd_gravity(args: List[str]) -> None:
    """Show gravity score for a file."""
    if not args or args[0] in ("--help", "-h"):
        print("""Usage: emergence nautilus gravity <file>

Show the gravity (importance) score for a memory file.

Examples:
  emergence nautilus gravity memory/2024-01-15.md
  emergence nautilus gravity memory/2024-01-15.md --lines 1:50
""")
        return
    
    filepath = args[0]
    
    # Parse line range
    line_args = []
    i = 1
    while i < len(args):
        if args[i] in ("--lines", "-l") and i + 1 < len(args):
            line_args.extend(["--lines", args[i + 1]])
            i += 2
        else:
            i += 1
    
    result = gravity_score([filepath] + line_args)


def cmd_chambers(args: List[str]) -> None:
    """Chambers subcommands."""
    if not args or args[0] in ("--help", "-h"):
        print("""Usage: emergence nautilus chambers <command>

Commands:
  status               Show chamber distribution
  promote [--dry-run]  Promote atrium → corridor
  crystallize          Promote corridor → vault

Examples:
  emergence nautilus chambers status
  emergence nautilus chambers promote --dry-run
""")
        return
    
    subcommand = args[0]
    sub_args = args[1:]
    
    if subcommand == "status":
        result = chambers_status(sub_args)
        print(json.dumps(result, indent=2))
    elif subcommand == "promote":
        result = cmd_promote(sub_args)
        print(json.dumps(result, indent=2))
    elif subcommand == "crystallize":
        result = cmd_crystallize(sub_args)
        print(json.dumps(result, indent=2))
    else:
        print(f"Unknown chambers command: {subcommand}", file=sys.stderr)
        sys.exit(1)


def cmd_doors(args: List[str]) -> None:
    """Doors subcommands."""
    if not args or args[0] in ("--help", "-h"):
        print("""Usage: emergence nautilus doors <command>

Commands:
  classify <query>     Classify query context
  auto-tag             Auto-tag all memory files
  tag <file> <tag>     Tag a file manually

Examples:
  emergence nautilus doors classify "project status"
  emergence nautilus doors auto-tag
""")
        return
    
    subcommand = args[0]
    sub_args = args[1:]
    
    if subcommand == "classify":
        result = doors_classify(sub_args)
        print(json.dumps(result, indent=2))
    elif subcommand == "auto-tag":
        result = cmd_auto_tag(sub_args)
        print(json.dumps(result, indent=2))
    elif subcommand == "tag":
        if len(sub_args) < 2:
            print("Usage: emergence nautilus doors tag <file> <tag>", file=sys.stderr)
            sys.exit(1)
        result = cmd_tag(sub_args)
        print(json.dumps(result, indent=2))
    else:
        print(f"Unknown doors command: {subcommand}", file=sys.stderr)
        sys.exit(1)


def cmd_mirrors(args: List[str]) -> None:
    """Mirrors subcommands."""
    if not args or args[0] in ("--help", "-h"):
        print("""Usage: emergence nautilus mirrors <command>

Commands:
  stats                Show mirror statistics
  resolve <path>       Find all granularity levels
  auto-link            Auto-link corridor summaries

Examples:
  emergence nautilus mirrors stats
  emergence nautilus mirrors resolve memory/2024-01-15.md
""")
        return
    
    subcommand = args[0]
    sub_args = args[1:]
    
    if subcommand == "stats":
        result = mirrors_stats(sub_args)
        print(json.dumps(result, indent=2))
    elif subcommand == "resolve":
        if not sub_args:
            print("Usage: emergence nautilus mirrors resolve <path>", file=sys.stderr)
            sys.exit(1)
        result = cmd_resolve(sub_args)
        print(json.dumps(result, indent=2))
    elif subcommand == "auto-link":
        result = cmd_auto_link(sub_args)
        print(json.dumps(result, indent=2))
    else:
        print(f"Unknown mirrors command: {subcommand}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main CLI entry point."""
    commands = {
        "search": cmd_search,
        "status": cmd_status,
        "maintain": cmd_maintain,
        "classify": cmd_classify,
        "gravity": cmd_gravity,
        "chambers": cmd_chambers,
        "doors": cmd_doors,
        "mirrors": cmd_mirrors,
    }
    
    if len(sys.argv) < 2:
        print("""🐚 Nautilus Memory Palace for Emergence v0.3.0

Usage: emergence nautilus <command> [args]

Commands:
  search <query>       Full pipeline search with gravity + context
  status               Show system status
  maintain             Run all maintenance tasks
  classify [file]      Classify into chambers (atrium/corridor/vault)
  gravity <file>       Show gravity score for file
  chambers <cmd>       Chambers subcommands (status, promote, crystallize)
  doors <cmd>          Doors subcommands (classify, auto-tag, tag)
  mirrors <cmd>        Mirrors subcommands (stats, resolve, auto-link)

Examples:
  emergence nautilus search "project status" --n 10
  emergence nautilus maintain --verbose
  emergence nautilus status

For command help:
  emergence nautilus <command> --help
""")
        sys.exit(1)
    
    command = sys.argv[1]
    args = sys.argv[2:]
    
    if command in ("--help", "-h"):
        print("""🐚 Nautilus Memory Palace for Emergence v0.3.0

Usage: python -m core.nautilus <command> [args]
       emergence nautilus <command> [args]

Commands:
  search <query>       Full pipeline search
  status               Show system status  
  maintain             Run maintenance
  classify [file]      Classify file(s)
  gravity <file>       Show gravity score
  chambers <cmd>       Chambers commands
  doors <cmd>          Doors commands
  mirrors <cmd>        Mirrors commands

See --help on individual commands for details.
""")
        sys.exit(0)
    
    if command not in commands:
        print(f"Unknown command: {command}", file=sys.stderr)
        print(f"Available: {', '.join(commands.keys())}", file=sys.stderr)
        sys.exit(1)
    
    try:
        commands[command](args)
    except KeyboardInterrupt:
        print("\nInterrupted", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
