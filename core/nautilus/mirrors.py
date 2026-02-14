#!/usr/bin/env python3
"""
Nautilus Mirrors — Phase 4
Multi-granularity indexing for the same event.

Each significant event exists at three levels:
  - raw:     Full detail from daily memory (atrium)
  - summary: Compressed narrative (corridor)  
  - lesson:  Distilled wisdom/pattern (vault)

Different embeddings for each level — the lesson is retrievable
by concept even after details fade.

Usage:
  mirrors.py create <path> [--lesson "..."] [--summary "..."]
  mirrors.py link <raw_path> <summary_path> <vault_path>
  mirrors.py resolve <path>     # Find all granularity levels
  mirrors.py stats              # Show mirror coverage
"""

import sqlite3
import json
import sys
import os
from pathlib import Path
from datetime import datetime, timezone

from .config import get_db_path, get_workspace

WORKSPACE = get_workspace()


def get_db():
    DB_PATH = get_db_path()
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("""
        CREATE TABLE IF NOT EXISTS mirrors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_key TEXT NOT NULL,
            granularity TEXT NOT NULL CHECK(granularity IN ('raw', 'summary', 'lesson')),
            path TEXT NOT NULL,
            line_start INTEGER DEFAULT 0,
            line_end INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(event_key, granularity)
        )
    """)
    db.execute("CREATE INDEX IF NOT EXISTS idx_mirrors_event ON mirrors(event_key)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_mirrors_path ON mirrors(path)")
    db.commit()
    return db


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def cmd_create(args):
    """Create a mirror set for an event."""
    if not args:
        print("Usage: mirrors.py create <event_key> --raw <path> [--summary <path>] [--lesson <path>]", file=sys.stderr)
        sys.exit(1)
    
    event_key = args[0]
    raw_path = summary_path = lesson_path = None
    
    i = 1
    while i < len(args):
        if args[i] == '--raw' and i + 1 < len(args):
            raw_path = args[i+1]
            i += 2
        elif args[i] == '--summary' and i + 1 < len(args):
            summary_path = args[i+1]
            i += 2
        elif args[i] == '--lesson' and i + 1 < len(args):
            lesson_path = args[i+1]
            i += 2
        else:
            i += 1
    
    db = get_db()
    created = []
    
    for granularity, path in [('raw', raw_path), ('summary', summary_path), ('lesson', lesson_path)]:
        if path:
            db.execute("""
                INSERT OR REPLACE INTO mirrors (event_key, granularity, path)
                VALUES (?, ?, ?)
            """, (event_key, granularity, path))
            created.append({"granularity": granularity, "path": path})
    
    db.commit()
    print(json.dumps({"event_key": event_key, "mirrors": created}))
    db.close()


def cmd_link(args):
    """Link three granularity levels for the same event."""
    if len(args) < 3:
        print("Usage: mirrors.py link <event_key> <raw_path> <summary_path> [vault_path]", file=sys.stderr)
        sys.exit(1)
    
    event_key = args[0]
    raw_path = args[1]
    summary_path = args[2]
    vault_path = args[3] if len(args) > 3 else None
    
    db = get_db()
    
    db.execute("INSERT OR REPLACE INTO mirrors (event_key, granularity, path) VALUES (?, 'raw', ?)", 
               (event_key, raw_path))
    db.execute("INSERT OR REPLACE INTO mirrors (event_key, granularity, path) VALUES (?, 'summary', ?)", 
               (event_key, summary_path))
    if vault_path:
        db.execute("INSERT OR REPLACE INTO mirrors (event_key, granularity, path) VALUES (?, 'lesson', ?)", 
                   (event_key, vault_path))
    
    db.commit()
    print(json.dumps({"event_key": event_key, "linked": True}))
    db.close()


def cmd_resolve(args):
    """Find all granularity levels for a path or event key."""
    if not args:
        print("Usage: mirrors.py resolve <path_or_event_key>", file=sys.stderr)
        sys.exit(1)
    
    target = args[0]
    db = get_db()
    
    # Try as event key first
    rows = db.execute("SELECT * FROM mirrors WHERE event_key = ? ORDER BY granularity", (target,)).fetchall()
    
    if not rows:
        # Try as path
        rows = db.execute("SELECT * FROM mirrors WHERE path = ?", (target,)).fetchall()
        if rows:
            # Get the event key and find all siblings
            event_key = rows[0]['event_key']
            rows = db.execute("SELECT * FROM mirrors WHERE event_key = ? ORDER BY granularity", (event_key,)).fetchall()
    
    if rows:
        print(json.dumps({
            "event_key": rows[0]['event_key'],
            "mirrors": [dict(r) for r in rows]
        }, indent=2, default=str))
    else:
        print(json.dumps({"event_key": target, "mirrors": [], "found": False}))
    
    db.close()


def cmd_stats(args):
    """Show mirror coverage statistics."""
    db = get_db()
    
    total_events = db.execute("SELECT COUNT(DISTINCT event_key) FROM mirrors").fetchone()[0]
    
    coverage = {}
    for g in ['raw', 'summary', 'lesson']:
        count = db.execute("SELECT COUNT(*) FROM mirrors WHERE granularity = ?", (g,)).fetchone()[0]
        coverage[g] = count
    
    # Full coverage (all three levels)
    full = db.execute("""
        SELECT event_key, COUNT(DISTINCT granularity) as levels
        FROM mirrors GROUP BY event_key HAVING levels = 3
    """).fetchall()
    
    # Partial coverage
    partial = db.execute("""
        SELECT event_key, COUNT(DISTINCT granularity) as levels,
               GROUP_CONCAT(granularity) as has
        FROM mirrors GROUP BY event_key HAVING levels < 3
    """).fetchall()
    
    print(json.dumps({
        "total_events": total_events,
        "coverage": coverage,
        "fully_mirrored": len(full),
        "partially_mirrored": len(partial),
        "partial_details": [{"event": r['event_key'], "has": r['has']} for r in partial[:10]]
    }, indent=2))
    db.close()


def cmd_auto_link(args):
    """Auto-detect and link corridor summaries to their raw sources."""
    db = get_db()
    
    corridors_dir = WORKSPACE / "memory" / "corridors"
    if not corridors_dir.exists():
        print(json.dumps({"linked": 0, "message": "No corridors directory"}))
        return
    
    linked = 0
    for summary_file in corridors_dir.glob("corridor-*.md"):
        # Extract date from filename
        import re
        match = re.search(r'corridor-(.+)\.md', summary_file.name)
        if not match:
            continue
        
        base_name = match.group(1)
        raw_path = f"memory/{base_name}.md"
        summary_path = str(summary_file.relative_to(WORKSPACE))
        event_key = f"daily-{base_name}"
        
        # Check if raw exists
        if (WORKSPACE / raw_path).exists():
            db.execute("INSERT OR REPLACE INTO mirrors (event_key, granularity, path) VALUES (?, 'raw', ?)",
                       (event_key, raw_path))
            db.execute("INSERT OR REPLACE INTO mirrors (event_key, granularity, path) VALUES (?, 'summary', ?)",
                       (event_key, summary_path))
            linked += 1
    
    db.commit()
    print(json.dumps({"linked": linked}))
    db.close()


# === Main ===

COMMANDS = {
    'create': cmd_create,
    'link': cmd_link,
    'resolve': cmd_resolve,
    'stats': cmd_stats,
    'auto-link': cmd_auto_link,
}

def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: mirrors.py <command> [args]")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
    
    COMMANDS[sys.argv[1]](sys.argv[2:])

if __name__ == '__main__':
    main()
