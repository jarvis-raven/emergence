#!/usr/bin/env python3
# Suppress runpy import warning
import warnings as _w; _w.filterwarnings("ignore", category=RuntimeWarning, module="runpy"); del _w
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
  python -m core.nautilus mirrors create <event_key> --raw <path> [--summary <path>]
  python -m core.nautilus mirrors link <event_key> <raw_path> <summary_path>
  python -m core.nautilus mirrors resolve <path>
  python -m core.nautilus mirrors stats
"""

import sqlite3
import json
import sys
import re
from datetime import datetime, timezone
from typing import List, Dict, Any

from . import config
from .gravity import get_db as get_gravity_db
from .logging_config import get_logger
from .db_utils import commit_with_retry, DatabaseError

# Setup logging
logger = get_logger("mirrors")


def get_db() -> sqlite3.Connection:
    """
    Get database connection.

    Returns:
        SQLite database connection.
    """
    return get_gravity_db()


def now_iso() -> str:
    """
    Get current time in ISO format.

    Returns:
        ISO-formatted timestamp string.
    """
    return datetime.now(timezone.utc).isoformat()


# === Commands ===


def cmd_create(args: List[str]) -> Dict[str, Any]:
    """
    Create a mirror set for an event.

    Args:
        args: Command arguments [event_key, --raw <path>, --summary <path>, --lesson <path>]

    Returns:
        Dictionary with created mirrors.
    """
    if not args:
        logger.error("No event key provided to create")
        print(
            "Usage: mirrors create <event_key> --raw <path> [--summary <path>] [--lesson <path>]",
            file=sys.stderr,
        )
        sys.exit(1)

    event_key = args[0]
    raw_path = summary_path = lesson_path = None

    i = 1
    while i < len(args):
        if args[i] == "--raw" and i + 1 < len(args):
            raw_path = args[i + 1]
            i += 2
        elif args[i] == "--summary" and i + 1 < len(args):
            summary_path = args[i + 1]
            i += 2
        elif args[i] == "--lesson" and i + 1 < len(args):
            lesson_path = args[i + 1]
            i += 2
        else:
            i += 1

    try:
        db = get_db()
        created = []

        for granularity, path in [
            ("raw", raw_path),
            ("summary", summary_path),
            ("lesson", lesson_path),
        ]:
            if path:
                db.execute(
                    """
                    INSERT OR REPLACE INTO mirrors (event_key, granularity, path)
                    VALUES (?, ?, ?)
                """,
                    (event_key, granularity, path),
                )
                created.append({"granularity": granularity, "path": path})
                logger.info(f"Created {granularity} mirror for {event_key}: {path}")

        commit_with_retry(db)
        db.close()

        result = {"event_key": event_key, "mirrors": created}
        print(json.dumps(result, indent=2))
        return result

    except sqlite3.Error as e:
        logger.error(f"Database error in create: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_link(args: List[str]) -> Dict[str, Any]:
    """
    Link three granularity levels for the same event.

    Args:
        args: Command arguments [event_key, raw_path, summary_path, vault_path?]

    Returns:
        Dictionary confirming link creation.
    """
    if len(args) < 3:
        logger.error("Insufficient arguments for link")
        print(
            "Usage: mirrors link <event_key> <raw_path> <summary_path> [vault_path]",
            file=sys.stderr,
        )
        sys.exit(1)

    event_key = args[0]
    raw_path = args[1]
    summary_path = args[2]
    vault_path = args[3] if len(args) > 3 else None

    try:
        db = get_db()

        db.execute(
            "INSERT OR REPLACE INTO mirrors (event_key, granularity, path) VALUES (?, 'raw', ?)",
            (event_key, raw_path),
        )
        db.execute(
            "INSERT OR REPLACE INTO mirrors (event_key, granularity, path) VALUES (?, 'summary', ?)",
            (event_key, summary_path),
        )

        logger.info(f"Linked raw and summary for {event_key}")

        if vault_path:
            db.execute(
                "INSERT OR REPLACE INTO mirrors (event_key, granularity, path) VALUES (?, 'lesson', ?)",
                (event_key, vault_path),
            )
            logger.info(f"Linked lesson for {event_key}")

        commit_with_retry(db)
        db.close()

        result = {"event_key": event_key, "linked": True}
        print(json.dumps(result, indent=2))
        return result

    except DatabaseError as e:
        logger.error(f"Database error in link: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        logger.error(f"Unexpected database error in link: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_resolve(args: List[str]) -> Dict[str, Any]:
    """
    Find all granularity levels for a path or event key.

    Args:
        args: Command arguments [path_or_event_key]

    Returns:
        Dictionary with all mirrors for the event.
    """
    if not args:
        logger.error("No path/event key provided to resolve")
        print("Usage: mirrors resolve <path_or_event_key>", file=sys.stderr)
        sys.exit(1)

    target = args[0]

    try:
        db = get_db()

        # Try as event key first
        rows = db.execute(
            "SELECT * FROM mirrors WHERE event_key = ? ORDER BY granularity", (target,)
        ).fetchall()

        if not rows:
            # Try as path
            rows = db.execute("SELECT * FROM mirrors WHERE path = ?", (target,)).fetchall()
            if rows:
                # Get the event key and find all siblings
                event_key = rows[0]["event_key"]
                rows = db.execute(
                    "SELECT * FROM mirrors WHERE event_key = ? ORDER BY granularity", (event_key,)
                ).fetchall()
                logger.debug(f"Resolved {target} to event {event_key} with {len(rows)} mirrors")

        db.close()

        if rows:
            result = {"event_key": rows[0]["event_key"], "mirrors": [dict(r) for r in rows]}
            logger.info(f"Resolved {target} to {len(rows)} mirrors")
        else:
            result = {"event_key": target, "mirrors": [], "found": False}
            logger.debug(f"No mirrors found for {target}")

        print(json.dumps(result, indent=2))
        return result

    except DatabaseError as e:
        logger.error(f"Database error in resolve: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        logger.error(f"Unexpected database error in resolve: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_stats(args: List[str]) -> Dict[str, Any]:
    """
    Show mirror coverage statistics.

    Args:
        args: Command arguments (currently unused)

    Returns:
        Dictionary with mirror statistics.
    """
    try:
        db = get_db()

        total_events = db.execute("SELECT COUNT(DISTINCT event_key) FROM mirrors").fetchone()[0]

        coverage = {}
        for g in ["raw", "summary", "lesson"]:
            count = db.execute(
                "SELECT COUNT(*) FROM mirrors WHERE granularity = ?", (g,)
            ).fetchone()[0]
            coverage[g] = count

        # Full coverage (all three levels)
        full = db.execute(
            """
            SELECT event_key, COUNT(DISTINCT granularity) as levels
            FROM mirrors GROUP BY event_key HAVING levels = 3
        """
        ).fetchall()

        # Partial coverage
        partial = db.execute(
            """
            SELECT event_key, COUNT(DISTINCT granularity) as levels,
                   GROUP_CONCAT(granularity) as has
            FROM mirrors GROUP BY event_key HAVING levels < 3
        """
        ).fetchall()

        db.close()

        result = {
            "total_events": total_events,
            "coverage": coverage,
            "fully_mirrored": len(full),
            "partially_mirrored": len(partial),
            "partial_details": [{"event": r["event_key"], "has": r["has"]} for r in partial[:10]],
        }

        logger.info(f"Mirror stats: {total_events} events, {len(full)} fully mirrored")
        print(json.dumps(result, indent=2))
        return result

    except DatabaseError as e:
        logger.error(f"Database error in stats: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        logger.error(f"Unexpected database error in stats: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_auto_link(args: List[str]) -> Dict[str, Any]:
    """
    Auto-detect and link corridor summaries to their raw sources.

    Args:
        args: Command arguments (currently unused)

    Returns:
        Dictionary with auto-linking statistics.
    """
    try:
        db = get_db()

        corridors_dir = config.get_corridors_dir()
        if not corridors_dir.exists():
            message = f"No corridors directory found: {corridors_dir}"
            logger.warning(message)
            return {"linked": 0, "message": message}

        workspace = config.get_workspace()
        linked = 0

        logger.info(f"Auto-linking corridors from {corridors_dir}")

        for summary_file in corridors_dir.glob("corridor-*.md"):
            # Extract date from filename
            match = re.search(r"corridor-(.+)\.md", summary_file.name)
            if not match:
                logger.debug(f"Skipping {summary_file.name} (no date match)")
                continue

            base_name = match.group(1)
            raw_path = f"memory/{base_name}.md"

            try:
                summary_rel = str(summary_file.relative_to(workspace))
            except ValueError:
                summary_rel = str(summary_file)

            event_key = f"daily-{base_name}"

            # Check if raw exists
            if (workspace / raw_path).exists():
                db.execute(
                    "INSERT OR REPLACE INTO mirrors (event_key, granularity, path) VALUES (?, 'raw', ?)",
                    (event_key, raw_path),
                )
                db.execute(
                    "INSERT OR REPLACE INTO mirrors (event_key, granularity, path) VALUES (?, 'summary', ?)",
                    (event_key, summary_rel),
                )
                linked += 1
                logger.debug(f"Linked {event_key}: {raw_path} → {summary_rel}")
            else:
                logger.debug(f"Raw file not found for {event_key}: {raw_path}")

        commit_with_retry(db)
        db.close()

        result = {"linked": linked}
        logger.info(f"Auto-linked {linked} corridor summaries")
        print(json.dumps(result, indent=2))
        return result

    except DatabaseError as e:
        logger.error(f"Database error in auto-link: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        logger.error(f"Unexpected database error in auto-link: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


# === Main ===

COMMANDS = {
    "create": cmd_create,
    "link": cmd_link,
    "resolve": cmd_resolve,
    "stats": cmd_stats,
    "auto-link": cmd_auto_link,
}


def main() -> None:
    """Main entry point for mirrors command."""
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python -m core.nautilus mirrors <command> [args]")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    cmd = sys.argv[1]
    logger.info(f"Executing mirrors command: {cmd}")
    COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="runpy")
    # Logging already configured by logging_config module
    main()
