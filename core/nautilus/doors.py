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
  python -m core.nautilus doors tag <path> <tags...>
  python -m core.nautilus doors untag <path> <tags...>
  python -m core.nautilus doors show <path>
  python -m core.nautilus doors auto-tag
"""

import sqlite3
import json
import sys
import re
import warnings
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Optional

from . import config
from .gravity import get_db as get_gravity_db
from .logging_config import get_logger
from .db_utils import commit_with_retry, DatabaseError

# Suppress runpy import warning
warnings.filterwarnings("ignore", category=RuntimeWarning, module="runpy")

# Setup logging
logger = get_logger("doors")

# Context patterns for auto-classification (used by classify_text for query classification)
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

# Path-based auto-tagging rules: (path substring → tag)
PATH_TAG_RULES = [
    ("sessions/", "jarvis-time"),
    ("correspondence/", "communication"),
    ("memory/", "memory"),
]

# Content-based auto-tagging rules: (keywords list → tag)
CONTENT_TAG_RULES = [
    (["dan", "katy", "walter"], "personal"),
    (["github", " pr ", "issue", "commit", "merge"], "work"),
    (["moltbook"], "social"),
]

# Path-based project inference: (path substring → tag)
PATH_PROJECT_RULES = [
    ("emergence", "project:emergence"),
    ("openclaw", "project:openclaw"),
    ("ourblock", "project:ourblock"),
    ("nautilus", "project:nautilus"),
]


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


# === Auto-tagging API ===


def _tags_from_path(path_lower: str) -> List[str]:
    """Infer tags from file path patterns."""
    tags = []
    for path_substr, tag in PATH_TAG_RULES:
        if path_substr in path_lower:
            tags.append(tag)
    for path_substr, tag in PATH_PROJECT_RULES:
        if path_substr in path_lower:
            tags.append(tag)
    return tags


def _read_file_content(path: str) -> str:
    """Read up to 5KB of file content for classification."""
    workspace = config.get_workspace()
    file_path = Path(path)
    if not file_path.is_absolute():
        file_path = workspace / file_path

    if not (file_path.exists() and file_path.is_file()):
        return ""

    try:
        return file_path.read_text(encoding="utf-8")[:5000]
    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"Could not read {path} for auto-tagging: {e}")
        return ""


def _tags_from_content(content: str) -> List[str]:
    """Infer tags from file content using keywords and CONTEXT_PATTERNS."""
    tags = []
    content_lower = content.lower()

    for keywords, tag in CONTENT_TAG_RULES:
        if any(kw in content_lower for kw in keywords):
            tags.append(tag)

    tags.extend(classify_text(content))
    return tags


def _deduplicate_tags(tags: List[str]) -> List[str]:
    """Deduplicate tags while preserving order."""
    seen: set = set()
    result = []
    for tag in tags:
        if tag not in seen:
            seen.add(tag)
            result.append(tag)
    return result


def auto_tag_file(path: str) -> List[str]:
    """
    Infer context tags from file path and content.

    Combines:
    1. Path-based rules (e.g. sessions/ → jarvis-time)
    2. Path-based project inference (e.g. emergence → project:emergence)
    3. Content-based keyword matching (e.g. "dan" → personal)
    4. Full content classification via CONTEXT_PATTERNS

    Args:
        path: File path (relative to workspace or absolute)

    Returns:
        Deduplicated list of inferred context tags.
    """
    tags = _tags_from_path(path.lower())

    content = _read_file_content(path)
    if content:
        tags.extend(_tags_from_content(content))

    unique_tags = _deduplicate_tags(tags)
    logger.debug(f"Auto-tagged {path} → {unique_tags}")
    return unique_tags


def update_context_tags(path: str, db: Optional[sqlite3.Connection] = None) -> List[str]:
    """
    Auto-tag a file and save the tags to gravity.db.

    Runs auto_tag_file() and merges results with any existing tags
    in the database. Creates a gravity record if one doesn't exist.

    Args:
        path: File path (relative to workspace)
        db: Optional database connection (caller manages lifecycle).
            If None, opens and closes its own connection.

    Returns:
        The final merged list of context tags for the file.
    """
    tags = auto_tag_file(path)
    if not tags:
        return []

    own_db = db is None
    if own_db:
        db = get_db()

    try:
        _merge_tags_to_db(db, path, tags)
        if own_db:
            commit_with_retry(db)

        # Read back the final merged tags
        row = db.execute(
            "SELECT context_tags FROM gravity WHERE path = ? LIMIT 1", (path,)
        ).fetchone()

        final_tags = []
        if row:
            try:
                final_tags = json.loads(row["context_tags"] or "[]")
            except json.JSONDecodeError:
                final_tags = tags

        logger.info(f"Updated context tags for {path}: {final_tags}")
        return final_tags

    finally:
        if own_db:
            db.close()


def get_context_tags(path: str) -> List[str]:
    """
    Get the current context tags for a file from gravity.db.

    Args:
        path: File path (relative to workspace)

    Returns:
        List of context tags, or empty list if not found.
    """
    db = get_db()
    try:
        row = db.execute(
            "SELECT context_tags FROM gravity WHERE path = ? LIMIT 1", (path,)
        ).fetchone()

        if row:
            try:
                return json.loads(row["context_tags"] or "[]")
            except json.JSONDecodeError:
                return []
        return []
    finally:
        db.close()


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


def _add_tags_to_record(db: sqlite3.Connection, path: str, new_tags: List[str]) -> List[str]:
    """Add tags to a gravity record, creating one if needed. Returns added tags."""
    row = db.execute("SELECT context_tags FROM gravity WHERE path = ? LIMIT 1", (path,)).fetchone()

    if row:
        existing = _parse_context_tags(row["context_tags"], path)
        added = [t for t in new_tags if t not in existing]
        existing.extend(added)
        if added:
            logger.info(f"Added tags {added} to {path}")
        db.execute(
            "UPDATE gravity SET context_tags = ? WHERE path = ?",
            (json.dumps(existing), path),
        )
        return added

    logger.info(f"Creating new gravity record for {path} with tags {new_tags}")
    db.execute(
        "INSERT INTO gravity (path, line_start, line_end, context_tags) VALUES (?, 0, 0, ?)",
        (path, json.dumps(new_tags)),
    )
    return list(new_tags)


def _parse_context_tags(raw: Optional[str], path: str = "") -> List[str]:
    """Parse context_tags JSON, returning empty list on error."""
    try:
        return json.loads(raw or "[]")
    except json.JSONDecodeError as e:
        logger.warning(f"Corrupted context_tags for {path}: {e}")
        return []


def cmd_tag(args: List[str]) -> Dict[str, Any]:  # noqa: C901
    """
    Manually tag a file with one or more context tags.

    Usage: doors tag <path> <tag1> [tag2] [tag3...]

    Args:
        args: Command arguments [path, tag1, tag2, ...]

    Returns:
        Dictionary with tagging result.
    """
    if len(args) < 2:
        logger.error("Insufficient arguments for tag")
        print("Usage: doors tag <path> <tag1> [tag2] [tag3...]", file=sys.stderr)
        sys.exit(1)

    path = args[0]
    new_tags = args[1:]

    try:
        db = get_db()
        added = _add_tags_to_record(db, path, new_tags)
        commit_with_retry(db)

        row = db.execute(
            "SELECT context_tags FROM gravity WHERE path = ? LIMIT 1", (path,)
        ).fetchone()
        final_tags = _parse_context_tags(row["context_tags"] if row else None, path) or new_tags

        db.close()

        result = {"path": path, "added": added, "tags": final_tags, "status": "updated"}
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


def cmd_untag(args: List[str]) -> Dict[str, Any]:
    """
    Remove one or more context tags from a file.

    Usage: doors untag <path> <tag1> [tag2] [tag3...]

    Args:
        args: Command arguments [path, tag1, tag2, ...]

    Returns:
        Dictionary with untagging result.
    """
    if len(args) < 2:
        logger.error("Insufficient arguments for untag")
        print("Usage: doors untag <path> <tag1> [tag2] [tag3...]", file=sys.stderr)
        sys.exit(1)

    path = args[0]
    remove_tags = args[1:]

    try:
        db = get_db()

        row = db.execute(
            "SELECT context_tags FROM gravity WHERE path = ? LIMIT 1", (path,)
        ).fetchone()

        if not row:
            db.close()
            result = {
                "path": path,
                "removed": [],
                "tags": [],
                "status": "not_found",
                "message": f"No gravity record for {path}",
            }
            print(json.dumps(result, indent=2))
            return result

        existing = _parse_context_tags(row["context_tags"], path)
        removed = [t for t in remove_tags if t in existing]
        remaining = [t for t in existing if t not in remove_tags]

        db.execute(
            "UPDATE gravity SET context_tags = ? WHERE path = ?", (json.dumps(remaining), path)
        )
        commit_with_retry(db)
        db.close()

        if removed:
            logger.info(f"Removed tags {removed} from {path}")
        else:
            logger.debug(f"None of {remove_tags} found on {path}")

        result = {"path": path, "removed": removed, "tags": remaining, "status": "updated"}
        print(json.dumps(result, indent=2))
        return result

    except DatabaseError as e:
        logger.error(f"Database error in untag: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        logger.error(f"Unexpected database error in untag: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_show(args: List[str]) -> Dict[str, Any]:
    """
    Show current context tags for a file.

    Usage: doors show <path>

    Args:
        args: Command arguments [path]

    Returns:
        Dictionary with current tags.
    """
    if not args:
        logger.error("No path provided to show")
        print("Usage: doors show <path>", file=sys.stderr)
        sys.exit(1)

    path = args[0]
    tags = get_context_tags(path)

    result = {"path": path, "context_tags": tags}
    print(json.dumps(result, indent=2))
    return result


def _read_and_classify_file(md_file, workspace) -> tuple:
    """
    Read file content and classify it using auto_tag_file.

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

    tags = auto_tag_file(rel_path)
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


def _auto_tag_db_rows(db: sqlite3.Connection, new_only: bool) -> int:
    """Auto-tag existing gravity.db rows. Returns count of tagged files."""
    query = "SELECT path FROM gravity"
    if new_only:
        query += " WHERE context_tags = '[]' OR context_tags IS NULL"
    rows = db.execute(query).fetchall()

    tagged = 0
    logger.info(f"Auto-tagging {len(rows)} files (new_only={new_only})")

    for row in rows:
        tags = auto_tag_file(row["path"])
        if tags:
            _merge_tags_to_db(db, row["path"], tags)
            tagged += 1
    return tagged


def _auto_tag_new_memory_files(db: sqlite3.Connection) -> int:
    """Scan memory dir for files not in gravity.db and tag them."""
    workspace = config.get_workspace()
    memory_dir = config.get_memory_dir()
    if not memory_dir.exists():
        return 0

    tagged = 0
    for md_file in sorted(memory_dir.glob("**/*.md")):
        try:
            rel_path = str(md_file.relative_to(workspace))
        except ValueError:
            rel_path = str(md_file)

        if db.execute("SELECT 1 FROM gravity WHERE path = ? LIMIT 1", (rel_path,)).fetchone():
            continue

        tags = auto_tag_file(rel_path)
        if tags:
            _merge_tags_to_db(db, rel_path, tags)
            tagged += 1
    return tagged


def cmd_auto_tag(args: List[str]) -> Dict[str, Any]:
    """
    Auto-tag all files in gravity.db based on path and content analysis.

    Uses auto_tag_file() which combines path-based rules, project inference,
    content keyword matching, and full CONTEXT_PATTERNS classification.

    Flags:
        --new-only  Only tag files that currently have no context tags

    Args:
        args: Command arguments

    Returns:
        Dictionary with auto-tagging statistics.
    """
    new_only = "--new-only" in args

    try:
        db = get_db()

        tagged = _auto_tag_db_rows(db, new_only)
        tagged += _auto_tag_new_memory_files(db)

        commit_with_retry(db)
        tag_counts = _collect_tag_stats(db)
        db.close()

        result = {"files_tagged": tagged, "new_only": new_only, "tag_distribution": tag_counts}
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
    "untag": cmd_untag,
    "show": cmd_show,
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
