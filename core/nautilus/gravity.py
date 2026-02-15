#!/usr/bin/env python3
"""
Nautilus Gravity Engine — Phase 1
Importance-weighted memory scoring layer.

Sits on top of OpenClaw's existing memory_search, adding:
- Access tracking (which memories get retrieved)
- Write-date authority (newer writes outrank old)
- Recency decay (untouched memories fade)
- Effective mass scoring for re-ranking

Usage:
  gravity.py record-access <path> [--lines START:END]
  gravity.py record-write <path>
  gravity.py boost <path> [--amount N]     # Explicit importance bump
  gravity.py decay                          # Apply nightly decay
  gravity.py score <path> [--lines START:END]  # Get gravity score
  gravity.py top [--n 10]                   # Show highest-gravity memories
  gravity.py stats                          # Database stats
  gravity.py rerank --json <results_json>   # Re-rank memory_search results
"""

import sqlite3
import json
import sys
import os
import math
from datetime import datetime, timezone

# Use config for portable paths
from .config import get_db_path, get_config


def get_db():
    """Get or create the gravity database."""
    DB_PATH = get_db_path()
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS gravity (
            path TEXT NOT NULL,
            line_start INTEGER DEFAULT 0,
            line_end INTEGER DEFAULT 0,
            access_count INTEGER DEFAULT 0,
            reference_count INTEGER DEFAULT 0,
            explicit_importance REAL DEFAULT 0.0,
            last_accessed_at TEXT,
            last_written_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            superseded_by TEXT DEFAULT NULL,
            tags TEXT DEFAULT '[]',
            chamber TEXT DEFAULT 'unknown',
            PRIMARY KEY (path, line_start, line_end)
        )
    """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_gravity_path ON gravity(path)
    """
    )
    db.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_gravity_chamber ON gravity(chamber)
    """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            line_start INTEGER DEFAULT 0,
            line_end INTEGER DEFAULT 0,
            accessed_at TEXT DEFAULT (datetime('now')),
            query TEXT DEFAULT NULL,
            score REAL DEFAULT NULL,
            context TEXT DEFAULT '{}'
        )
    """
    )
    db.commit()
    return db


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def days_since(iso_str):
    """Days since an ISO timestamp."""
    if not iso_str:
        return 999  # Never written/accessed = very old
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        delta = datetime.now(timezone.utc) - dt
        return max(0, delta.total_seconds() / 86400)
    except (ValueError, TypeError):
        return 999


def compute_effective_mass(row):
    """
    Compute effective mass with stale-authority mitigations.

    base_mass = (access_count × 0.3) + (reference_count × 0.5) + explicit_importance
    recency_factor = 1 / (1 + days_since_last_write × DECAY_RATE)
    authority_boost = AUTHORITY_BOOST if written in last 48h else 0
    effective_mass = min(base_mass × recency_factor + authority_boost, MASS_CAP)
    """
    config = get_config()
    DECAY_RATE = config.get("decay_rate", 0.05)
    AUTHORITY_BOOST = config.get("authority_boost", 0.3)
    MASS_CAP = config.get("mass_cap", 100.0)

    access_count = row["access_count"] or 0
    reference_count = row["reference_count"] or 0
    explicit_importance = row["explicit_importance"] or 0.0

    base_mass = (access_count * 0.3) + (reference_count * 0.5) + explicit_importance

    # Recency factor based on write date (not access date)
    days_written = days_since(row["last_written_at"])
    recency_factor = 1.0 / (1.0 + days_written * DECAY_RATE)

    # Authority boost for recently-written content (last 48h)
    authority = AUTHORITY_BOOST if days_written < 2.0 else 0.0

    effective_mass = min(base_mass * recency_factor + authority, MASS_CAP)
    return effective_mass


def gravity_score_modifier(effective_mass):
    """
    Convert effective mass to a score multiplier.
    Returns a value >= 1.0 that multiplies the base similarity score.

    At mass 0: modifier = 1.0 (no change)
    At mass 5: modifier ≈ 1.18
    At mass 20: modifier ≈ 1.30
    At mass 100: modifier ≈ 1.46
    """
    return 1.0 + 0.1 * math.log(1.0 + effective_mass)


# === Commands ===


def cmd_record_access(args):
    """Record that a memory chunk was accessed (retrieved by search)."""
    path = args[0] if args else None
    if not path:
        print(
            "Usage: gravity.py record-access <path> [--lines START:END] [--query Q] [--score S]",
            file=sys.stderr,
        )
        sys.exit(1)

    line_start, line_end = 0, 0
    query, score = None, None

    i = 1
    while i < len(args):
        if args[i] == "--lines" and i + 1 < len(args):
            parts = args[i + 1].split(":")
            line_start = int(parts[0])
            line_end = int(parts[1]) if len(parts) > 1 else line_start
            i += 2
        elif args[i] == "--query" and i + 1 < len(args):
            query = args[i + 1]
            i += 2
        elif args[i] == "--score" and i + 1 < len(args):
            score = float(args[i + 1])
            i += 2
        else:
            i += 1

    db = get_db()
    now = now_iso()

    # Upsert gravity record
    db.execute(
        """
        INSERT INTO gravity (
            path, line_start, line_end, access_count,
            last_accessed_at, last_written_at
        )
        VALUES (?, ?, ?, 1, ?, ?)
        ON CONFLICT(path, line_start, line_end) DO UPDATE SET
            access_count = access_count + 1,
            last_accessed_at = ?
    """,
        (path, line_start, line_end, now, now, now),
    )

    # Log access
    db.execute(
        """
        INSERT INTO access_log (path, line_start, line_end, query, score)
        VALUES (?, ?, ?, ?, ?)
    """,
        (path, line_start, line_end, query, score),
    )

    db.commit()

    row = db.execute(
        """
        SELECT * FROM gravity WHERE path = ? AND line_start = ? AND line_end = ?
    """,
        (path, line_start, line_end),
    ).fetchone()

    mass = compute_effective_mass(row)
    print(
        json.dumps(
            {
                "path": path,
                "lines": f"{line_start}:{line_end}",
                "access_count": row["access_count"],
                "effective_mass": round(mass, 3),
                "modifier": round(gravity_score_modifier(mass), 3),
            }
        )
    )
    db.close()


def cmd_record_write(args):
    """Record that a memory file was written/updated."""
    path = args[0] if args else None
    if not path:
        print("Usage: gravity.py record-write <path>", file=sys.stderr)
        sys.exit(1)

    db = get_db()
    now = now_iso()

    # Update all chunks for this path
    updated = db.execute(
        """
        UPDATE gravity SET last_written_at = ? WHERE path = ?
    """,
        (now, path),
    ).rowcount

    # If no existing records, create one for the whole file
    if updated == 0:
        db.execute(
            """
            INSERT INTO gravity (path, line_start, line_end, last_written_at)
            VALUES (?, 0, 0, ?)
        """,
            (path, now),
        )

    db.commit()
    print(json.dumps({"path": path, "updated_chunks": max(updated, 1), "written_at": now}))
    db.close()


def cmd_boost(args):
    """Explicitly boost a memory's importance."""
    path = args[0] if args else None
    amount = 2.0
    line_start, line_end = 0, 0

    i = 1
    while i < len(args):
        if args[i] == "--amount" and i + 1 < len(args):
            amount = float(args[i + 1])
            i += 2
        elif args[i] == "--lines" and i + 1 < len(args):
            parts = args[i + 1].split(":")
            line_start = int(parts[0])
            line_end = int(parts[1]) if len(parts) > 1 else line_start
            i += 2
        else:
            i += 1

    if not path:
        print("Usage: gravity.py boost <path> [--amount N] [--lines START:END]", file=sys.stderr)
        sys.exit(1)

    db = get_db()
    now = now_iso()

    db.execute(
        """
        INSERT INTO gravity (path, line_start, line_end, explicit_importance, last_written_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(path, line_start, line_end) DO UPDATE SET
            explicit_importance = explicit_importance + ?,
            last_written_at = ?
    """,
        (path, line_start, line_end, amount, now, amount, now),
    )

    db.commit()

    row = db.execute(
        """
        SELECT * FROM gravity WHERE path = ? AND line_start = ? AND line_end = ?
    """,
        (path, line_start, line_end),
    ).fetchone()

    mass = compute_effective_mass(row)
    print(
        json.dumps(
            {
                "path": path,
                "explicit_importance": row["explicit_importance"],
                "effective_mass": round(mass, 3),
                "modifier": round(gravity_score_modifier(mass), 3),
            }
        )
    )
    db.close()


def cmd_decay(args):
    """Apply nightly decay — reduce gravity on stale memories."""
    db = get_db()

    rows = db.execute("SELECT *, rowid FROM gravity").fetchall()
    decayed = 0

    for row in rows:
        days_written = days_since(row["last_written_at"])
        days_accessed = days_since(row["last_accessed_at"])

        # If not accessed in 30+ days AND not written in 14+ days,
        # reduce explicit importance by 10%
        if days_accessed > 30 and days_written > 14 and (row["explicit_importance"] or 0) > 0.1:
            new_importance = max(0, row["explicit_importance"] * 0.9)
            db.execute(
                """
                UPDATE gravity SET explicit_importance = ?
                WHERE path = ? AND line_start = ? AND line_end = ?
            """,
                (new_importance, row["path"], row["line_start"], row["line_end"]),
            )
            decayed += 1

    db.commit()

    total = len(rows)
    print(json.dumps({"total_records": total, "decayed": decayed, "timestamp": now_iso()}))
    db.close()


def cmd_score(args):
    """Get the gravity score for a specific path."""
    path = args[0] if args else None
    line_start, line_end = 0, 0

    i = 1
    while i < len(args):
        if args[i] == "--lines" and i + 1 < len(args):
            parts = args[i + 1].split(":")
            line_start = int(parts[0])
            line_end = int(parts[1]) if len(parts) > 1 else line_start
            i += 2
        else:
            i += 1

    if not path:
        print("Usage: gravity.py score <path> [--lines START:END]", file=sys.stderr)
        sys.exit(1)

    db = get_db()

    # Try exact match first, then path-level
    row = db.execute(
        """
        SELECT * FROM gravity WHERE path = ? AND line_start = ? AND line_end = ?
    """,
        (path, line_start, line_end),
    ).fetchone()

    if not row:
        # Try any chunk from this file
        row = db.execute("SELECT * FROM gravity WHERE path = ? LIMIT 1", (path,)).fetchone()

    if not row:
        print(json.dumps({"path": path, "effective_mass": 0, "modifier": 1.0, "exists": False}))
    else:
        mass = compute_effective_mass(row)
        print(
            json.dumps(
                {
                    "path": row["path"],
                    "lines": f"{row['line_start']}:{row['line_end']}",
                    "access_count": row["access_count"],
                    "reference_count": row["reference_count"],
                    "explicit_importance": row["explicit_importance"],
                    "days_since_write": round(days_since(row["last_written_at"]), 1),
                    "days_since_access": round(days_since(row["last_accessed_at"]), 1),
                    "effective_mass": round(mass, 3),
                    "modifier": round(gravity_score_modifier(mass), 3),
                    "superseded_by": row["superseded_by"],
                    "chamber": row.get("chamber", "unknown"),
                    "exists": True,
                }
            )
        )
    db.close()


def cmd_top(args):
    """Show highest-gravity memories."""
    n = 10
    if args and args[0] == "--n" and len(args) > 1:
        n = int(args[1])

    db = get_db()
    rows = db.execute("SELECT * FROM gravity ORDER BY access_count DESC").fetchall()

    results = []
    for row in rows:
        mass = compute_effective_mass(row)
        results.append(
            {
                "path": row["path"],
                "lines": f"{row['line_start']}:{row['line_end']}",
                "access_count": row["access_count"],
                "explicit_importance": row["explicit_importance"],
                "effective_mass": round(mass, 3),
                "modifier": round(gravity_score_modifier(mass), 3),
                "days_since_write": round(days_since(row["last_written_at"]), 1),
                "chamber": row["chamber"] if row["chamber"] else "unknown",
                "superseded_by": row["superseded_by"],
            }
        )

    # Sort by effective mass
    results.sort(key=lambda x: x["effective_mass"], reverse=True)
    results = results[:n]

    print(json.dumps(results, indent=2))
    db.close()


def cmd_rerank(args):
    """
    Re-rank memory_search results using gravity scores.

    Expects JSON array of results with {path, startLine, endLine, score, snippet}.
    Outputs same array with adjusted scores and gravity metadata.
    """
    json_str = None
    i = 0
    while i < len(args):
        if args[i] == "--json" and i + 1 < len(args):
            json_str = args[i + 1]
            i += 2
        else:
            i += 1

    if not json_str:
        # Try stdin
        if not sys.stdin.isatty():
            json_str = sys.stdin.read()
        else:
            print(
                "Usage: gravity.py rerank --json '<results>' or pipe JSON via stdin",
                file=sys.stderr,
            )
            sys.exit(1)

    try:
        results = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)

    db = get_db()
    now = now_iso()

    reranked = []
    for r in results:
        path = r.get("path", "")
        start = r.get("startLine", 0)
        end = r.get("endLine", 0)
        base_score = r.get("score", 0)

        # Look up gravity
        row = db.execute(
            """
            SELECT * FROM gravity WHERE path = ? AND line_start = ? AND line_end = ?
        """,
            (path, start, end),
        ).fetchone()

        if not row:
            # Try file-level match
            row = db.execute("SELECT * FROM gravity WHERE path = ? LIMIT 1", (path,)).fetchone()

        if row:
            mass = compute_effective_mass(row)
            modifier = gravity_score_modifier(mass)
            is_superseded = row["superseded_by"] is not None

            # Penalize superseded chunks
            if is_superseded:
                modifier *= 0.5

            adjusted_score = base_score * modifier
        else:
            mass = 0
            modifier = 1.0
            adjusted_score = base_score
            is_superseded = False

        entry = dict(r)
        entry["original_score"] = base_score
        entry["score"] = round(adjusted_score, 4)
        entry["gravity"] = {
            "effective_mass": round(mass, 3),
            "modifier": round(modifier, 3),
            "superseded": is_superseded,
        }
        reranked.append(entry)

        # Record access
        db.execute(
            """
            INSERT INTO gravity (path, line_start, line_end, access_count, last_accessed_at)
            VALUES (?, ?, ?, 1, ?)
            ON CONFLICT(path, line_start, line_end) DO UPDATE SET
                access_count = access_count + 1,
                last_accessed_at = ?
        """,
            (path, start, end, now, now),
        )

    db.commit()
    db.close()

    # Sort by adjusted score
    reranked.sort(key=lambda x: x["score"], reverse=True)
    print(json.dumps(reranked, indent=2))


def cmd_stats(args):
    """Show database statistics."""
    db = get_db()
    DB_PATH = get_db_path()

    total = db.execute("SELECT COUNT(*) FROM gravity").fetchone()[0]
    total_accesses = db.execute("SELECT COUNT(*) FROM access_log").fetchone()[0]
    superseded = db.execute(
        "SELECT COUNT(*) FROM gravity WHERE superseded_by IS NOT NULL"
    ).fetchone()[0]

    # Top 5 most accessed
    top = db.execute(
        """
        SELECT path, line_start, line_end, access_count, explicit_importance
        FROM gravity ORDER BY access_count DESC LIMIT 5
    """
    ).fetchall()

    # Recent accesses
    recent = db.execute(
        """
        SELECT path, query, score, accessed_at
        FROM access_log ORDER BY id DESC LIMIT 5
    """
    ).fetchall()

    print(
        json.dumps(
            {
                "total_chunks": total,
                "total_accesses": total_accesses,
                "superseded_chunks": superseded,
                "db_path": str(DB_PATH),
                "db_size_bytes": os.path.getsize(str(DB_PATH)) if DB_PATH.exists() else 0,
                "top_accessed": [dict(r) for r in top],
                "recent_accesses": [dict(r) for r in recent],
            },
            indent=2,
            default=str,
        )
    )
    db.close()


def cmd_supersede(args):
    """Mark a chunk as superseded by a newer one."""
    if len(args) < 2:
        print(
            "Usage: gravity.py supersede <old_path> <new_path> "
            "[--lines OLD_START:END NEW_START:END]",
            file=sys.stderr,
        )
        sys.exit(1)

    old_path = args[0]
    new_path = args[1]

    db = get_db()
    updated = db.execute(
        """
        UPDATE gravity SET superseded_by = ? WHERE path = ?
    """,
        (new_path, old_path),
    ).rowcount

    db.commit()
    print(json.dumps({"old_path": old_path, "new_path": new_path, "updated": updated}))
    db.close()


# === Main ===

COMMANDS = {
    "record-access": cmd_record_access,
    "record-write": cmd_record_write,
    "boost": cmd_boost,
    "decay": cmd_decay,
    "score": cmd_score,
    "top": cmd_top,
    "rerank": cmd_rerank,
    "stats": cmd_stats,
    "supersede": cmd_supersede,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: gravity.py <command> [args]")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    cmd = sys.argv[1]
    COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    main()
