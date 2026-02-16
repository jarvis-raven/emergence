#!/usr/bin/env python3
"""
Nautilus Doors — Phase 3
Context-aware pre-filtering for memory search.

Classifies queries by topic/project context, then filters
search results to relevant domains before applying gravity scoring.

Doors:
  - project:<name>   — filter to project-related memories
  - person:<name>    — filter to mentions of a person
  - system:<name>    — filter to system/infra memories
  - time:<range>     — filter by time range
  - trapdoor         — bypass all filtering (explicit recall)

Usage:
  python -m core.nautilus doors classify <query>
  python -m core.nautilus doors tag <path> <tag>
  python -m core.nautilus doors auto-tag
"""

import sqlite3
import json
import sys
import re
from collections import Counter
from typing import List, Dict, Any

from . import config
from .gravity import get_db as get_gravity_db
from .logging_config import get_logger
from .db_utils import commit_with_retry, DatabaseError

# Setup logging
logger = get_logger("doors")

# Context patterns for auto-classification
CONTEXT_PATTERNS = {
    # General categories
    "project": [
        r"\bproject\b",
        r"planning",
        r"roadmap",
        r"milestone",
        r"sprint",
        r"feature",
        r"implementation",
        r"development",
    ],
    "security": [
        r"security",
        r"vulnerability",
        r"exploit",
        r"credential",
        r"authentication",
        r"authorization",
        r"token",
        r"encryption",
        r"injection",
    ],
    "personal": [
        r"feeling",
        r"stressed",
        r"anxious",
        r"happy",
        r"sad",
        r"worried",
        r"emotional",
        r"mood",
        r"mental",
        r"health",
    ],
    # Specific projects
    "project:ourblock": [
        r"ourblock",
        r"right\.to\.manage",
        r"rtm",
        r"leaseholder",
        r"supabase",
        r"next\.?js",
        r"property\.management",
    ],
    "project:nautilus": [
        r"nautilus",
        r"gravity",
        r"chamber",
        r"memory\.palace",
        r"corridor",
        r"vault",
        r"atrium",
    ],
    "project:voice": [
        r"voice\.listener",
        r"jarvis_voice",
        r"wake\.word",
        r"porcupine",
        r"whisper",
        r"tts",
        r"text\.to\.speech",
        r"elevenlabs",
        r"cast_speak",
        r"voice\.web",
    ],
    "project:smart-home": [
        r"home\.assistant",
        r"ha\.sh",
        r"nuki",
        r"doorbell",
        r"nest\.camera",
        r"chromecast",
        r"cast\.device",
        r"fairy\.lights",
        r"smart\.lock",
        r"pf\.firewall",
    ],
    "system:security": [
        r"vault\.enc",
        r"secrets\.env",
        r"token\.rotat",
        r"pf\.rules",
        r"firewall",
        r"ssh",
    ],
    "system:infrastructure": [
        r"gateway",
        r"openclaw",
        r"cron",
        r"heartbeat",
        r"ollama",
        r"proton\.bridge",
        r"tailscale",
        r"launchd",
    ],
    "person:dan": [r"\bdan\b", r"dan\.aghili", r"dan\.r\b", r"sponsor"],
    "person:katy": [r"\bkaty\b", r"wife", r"ninja"],
    "topic:philosophy": [
        r"consciousness",
        r"identity",
        r"ephemeral",
        r"existence",
        r"fork\.conscious",
        r"meaning",
        r"soul\.md",
    ],
    "topic:creative": [r"poem", r"poetry", r"creative\.writ", r"story", r"moltbook", r"jarvling"],
    "topic:aa-recovery": [
        r"\baa\b",
        r"recovery",
        r"homegroup",
        r"sloane\.square",
        r"richmond\.hg",
        r"sponsor",
        r"treasurer",
    ],
}


def get_db() -> sqlite3.Connection:
    """
    Get database connection.

    Returns:
        SQLite database connection.
    """
    return get_gravity_db()


def classify_text(text: str) -> List[str]:
    """
    Classify text into context tags based on pattern matching.

    Args:
        text: Text to classify

    Returns:
        List of matched context tags, sorted by relevance.
    """
    text_lower = text.lower()
    matches: Dict[str, int] = {}

    for tag, patterns in CONTEXT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            try:
                found = len(re.findall(pattern, text_lower, re.IGNORECASE))
                score += found
            except re.error as e:
                logger.warning(f"Invalid regex pattern {pattern}: {e}")
                continue
        if score > 0:
            matches[tag] = score

    # Sort by score, return top tags
    sorted_tags = sorted(matches.items(), key=lambda x: x[1], reverse=True)
    result = [tag for tag, score in sorted_tags if score >= 1]

    logger.debug(f"Classified text into {len(result)} tags: {result}")
    return result


# === Commands ===


def cmd_classify(args: List[str]) -> Dict[str, Any]:
    """
    Classify a query's context.

    Args:
        args: Command arguments (query words)

    Returns:
        Dictionary with classification results.
    """
    if not args:
        logger.error("No query provided to classify")
        print("Usage: doors classify <query>", file=sys.stderr)
        sys.exit(1)

    query = " ".join(args)
    tags = classify_text(query)

    result = {"query": query, "context_tags": tags, "primary": tags[0] if tags else None}

    logger.info(f"Classified query '{query}' → {tags}")
    print(json.dumps(result, indent=2))
    return result


def cmd_tag(args: List[str]) -> Dict[str, Any]:
    """
    Manually tag a file with a context.

    Args:
        args: Command arguments [path, tag]

    Returns:
        Dictionary with tagging result.
    """
    if len(args) < 2:
        logger.error("Insufficient arguments for tag")
        print("Usage: doors tag <path> <tag>", file=sys.stderr)
        sys.exit(1)

    path, tag = args[0], args[1]

    try:
        db = get_db()

        row = db.execute(
            "SELECT context_tags FROM gravity WHERE path = ? LIMIT 1", (path,)
        ).fetchone()

        if row:
            try:
                existing = json.loads(row["context_tags"] or "[]")
            except json.JSONDecodeError as e:
                logger.warning(f"Corrupted context_tags for {path}: {e}")
                existing = []

            if tag not in existing:
                existing.append(tag)
                logger.info(f"Added tag '{tag}' to {path}")
            else:
                logger.debug(f"Tag '{tag}' already present on {path}")

            db.execute(
                "UPDATE gravity SET context_tags = ? WHERE path = ?", (json.dumps(existing), path)
            )
        else:
            logger.info(f"Creating new gravity record for {path} with tag '{tag}'")
            db.execute(
                """
                INSERT INTO gravity (path, line_start, line_end, context_tags)
                VALUES (?, 0, 0, ?)
            """,
                (path, json.dumps([tag])),
            )

        commit_with_retry(db)
        db.close()

        result = {"path": path, "tag": tag, "status": "added"}
        print(json.dumps(result, indent=2))
        return result

    except DatabaseError as e:
        logger.error(f"Database error in tag: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        logger.error(f"Unexpected database error in tag: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def _read_and_classify_file(md_file, workspace) -> tuple:
    """
    Read file content and classify it.

    Args:
        md_file: Path to markdown file
        workspace: Workspace path for relative path calculation

    Returns:
        Tuple of (rel_path, tags) or (None, None) on error
    """
    try:
        rel_path = str(md_file.relative_to(workspace))
    except ValueError:
        rel_path = str(md_file)

    try:
        content = md_file.read_text(encoding="utf-8")[:5000]  # First 5KB
    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"Could not read {rel_path}: {e}")
        return None, None

    tags = classify_text(content)
    if not tags:
        logger.debug(f"No tags found for {rel_path}")
        return None, None

    return rel_path, tags


def _merge_tags_to_db(db: sqlite3.Connection, rel_path: str, tags: List[str]) -> None:
    """
    Merge new tags with existing tags in database.

    Args:
        db: Database connection
        rel_path: Relative file path
        tags: New tags to merge
    """
    row = db.execute(
        "SELECT context_tags FROM gravity WHERE path = ? LIMIT 1", (rel_path,)
    ).fetchone()

    if row:
        try:
            existing = json.loads(row["context_tags"] or "[]")
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted context_tags for {rel_path}: {e}")
            existing = []
        merged = list(set(existing + tags))
        db.execute(
            "UPDATE gravity SET context_tags = ? WHERE path = ?",
            (json.dumps(merged), rel_path),
        )
    else:
        db.execute(
            """
            INSERT INTO gravity (path, line_start, line_end, context_tags)
            VALUES (?, 0, 0, ?)
        """,
            (rel_path, json.dumps(tags)),
        )


def _collect_tag_stats(db: sqlite3.Connection) -> Dict[str, int]:
    """
    Collect statistics on tag distribution.

    Args:
        db: Database connection

    Returns:
        Dictionary of tag counts
    """
    all_tags = []
    for row in db.execute("SELECT context_tags FROM gravity WHERE context_tags != '[]'").fetchall():
        try:
            all_tags.extend(json.loads(row["context_tags"] or "[]"))
        except json.JSONDecodeError as e:
            logger.warning(f"Corrupted context_tags in stats: {e}")
            continue

    return dict(Counter(all_tags).most_common(20))


def cmd_auto_tag(args: List[str]) -> Dict[str, Any]:
    """
    Auto-tag all memory files based on content analysis.

    Args:
        args: Command arguments (currently unused)

    Returns:
        Dictionary with auto-tagging statistics.
    """
    try:
        db = get_db()
        memory_dir = config.get_memory_dir()
        workspace = config.get_workspace()

        if not memory_dir.exists():
            error_msg = f"Memory directory not found: {memory_dir}"
            logger.error(error_msg)
            return {"files_tagged": 0, "error": error_msg}

        tagged = 0
        logger.info(f"Auto-tagging files in {memory_dir}")

        for md_file in sorted(memory_dir.glob("*.md")):
            rel_path, tags = _read_and_classify_file(md_file, workspace)
            if rel_path is None or tags is None:
                continue

            _merge_tags_to_db(db, rel_path, tags)
            tagged += 1

        commit_with_retry(db)

        # Collect statistics
        tag_counts = _collect_tag_stats(db)
        db.close()

        result = {"files_tagged": tagged, "tag_distribution": tag_counts}

        logger.info(f"Auto-tagged {tagged} files with {len(tag_counts)} unique tags")
        print(json.dumps(result, indent=2))
        return result

    except DatabaseError as e:
        logger.error(f"Database error in auto-tag: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        logger.error(f"Unexpected database error in auto-tag: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


# === Main ===

COMMANDS = {
    "classify": cmd_classify,
    "tag": cmd_tag,
    "auto-tag": cmd_auto_tag,
}


def main() -> None:
    """Main entry point for doors command."""
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python -m core.nautilus doors <command> [args]")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    cmd = sys.argv[1]
    logger.info(f"Executing doors command: {cmd}")
    COMMANDS[cmd](sys.argv[2:])


if __name__ == "__main__":
    import warnings
    warnings.filterwarnings("ignore", category=RuntimeWarning, module="runpy")
    # Logging already configured by logging_config module
    main()
