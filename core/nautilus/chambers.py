#!/usr/bin/env python3
"""
Nautilus Chambers — Phase 2
Temporal memory layers with automatic promotion.

Chambers:
  - atrium:    Last 48h of interactions (full fidelity)
  - corridor:  Past week (summarized daily narratives)
  - vault:     Older than 1 week (distilled wisdom/lessons)

Builders:
  - promoter:     Moves 48h+ chunks from atrium → corridor (summarize)
  - crystallizer: Moves 7d+ chunks from corridor → vault (distill)
  - classify:     Auto-assign chambers to existing chunks by file date

Usage:
  python -m core.nautilus chambers classify
  python -m core.nautilus chambers promote [--dry-run]
  python -m core.nautilus chambers crystallize [--dry-run]
  python -m core.nautilus chambers status
"""

import sqlite3
import json
import sys
import re
import subprocess
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

from . import config
from .gravity import get_db as get_gravity_db, now_iso
from .logging_config import get_logger
from .db_utils import commit_with_retry

# Setup logging
logger = get_logger("chambers")

# Promotion thresholds
ATRIUM_MAX_AGE_HOURS = 48
CORRIDOR_MAX_AGE_DAYS = 7

# LLM config for summarization
OLLAMA_URL = "http://localhost:11434/api/generate"
SUMMARY_MODEL = "llama3.2:3b"  # Local, free, fast


def get_db() -> sqlite3.Connection:
    """
    Get database connection.

    Returns:
        SQLite database connection.
    """
    return get_gravity_db()


def file_age_days(filepath: str) -> float:
    """
    Get the age of a file in days based on its name or mtime.

    Args:
        filepath: Path to the file (relative to workspace)

    Returns:
        Age in days (999 if cannot be determined).
    """
    workspace = config.get_workspace()
    name = Path(filepath).stem

    # Try to parse YYYY-MM-DD from filename
    match = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    if match:
        try:
            file_date = datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - file_date).total_seconds() / 86400
            logger.debug(f"File age from name for {filepath}: {age:.1f} days")
            return age
        except ValueError as e:
            logger.debug(f"Could not parse date from filename {filepath}: {e}")

    # Fall back to mtime
    full_path = workspace / filepath
    if full_path.exists():
        try:
            mtime = datetime.fromtimestamp(full_path.stat().st_mtime, tz=timezone.utc)
            age = (datetime.now(timezone.utc) - mtime).total_seconds() / 86400
            logger.debug(f"File age from mtime for {filepath}: {age:.1f} days")
            return age
        except (OSError, ValueError) as e:
            logger.warning(f"Could not get mtime for {filepath}: {e}")
    else:
        logger.warning(f"File does not exist: {full_path}")

    return 999.0


def classify_chamber(filepath: str) -> str:
    """
    Determine which chamber a file belongs to based on age.

    Args:
        filepath: Path to the file

    Returns:
        Chamber name: 'atrium', 'corridor', or 'vault'.
    """
    age = file_age_days(filepath)

    if age <= ATRIUM_MAX_AGE_HOURS / 24:
        chamber = "atrium"
    elif age <= CORRIDOR_MAX_AGE_DAYS:
        chamber = "corridor"
    else:
        chamber = "vault"

    logger.debug(f"Classified {filepath} as {chamber} (age={age:.1f}d)")
    return chamber


def llm_summarize(text: str, mode: str = "corridor") -> str:
    """
    Use local Ollama to summarize text.

    Args:
        text: Text to summarize
        mode: 'corridor' for narrative summary, 'vault' for distilled lessons

    Returns:
        Summarized text, or error message if failed.
    """
    if mode == "corridor":
        prompt = (
            "Summarize the following daily memory log into a concise narrative "
            "(2-4 paragraphs).\nPreserve: key decisions, people involved, problems "
            "solved, lessons learned, and any action items.\nDrop: routine checks, "
            "heartbeat logs, false positive alerts, minor tool output.\n\n---\n"
            f"{text[:8000]}\n---\n\nConcise narrative summary:"
        )
    else:  # vault
        prompt = (
            "Distill the following corridor summary into core lessons and patterns "
            "(bullet points).\nExtract only: permanent knowledge, reusable patterns, "
            "critical decisions, relationship notes, and system architecture insights.\n"
            "Be ruthless — only keep what future-you absolutely needs.\n\n---\n"
            f"{text[:6000]}\n---\n\nDistilled lessons:"
        )

    logger.info(f"Summarizing text ({len(text)} chars) in {mode} mode")

    try:
        result = subprocess.run(
            [
                "curl",
                "-s",
                OLLAMA_URL,
                "-d",
                json.dumps(
                    {
                        "model": SUMMARY_MODEL,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.3, "num_predict": 1024},
                    }
                ),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            logger.error(f"Ollama curl failed with code {result.returncode}")
            return f"[Summarization failed: curl returned {result.returncode}]"

        response = json.loads(result.stdout)
        summary = response.get("response", "").strip()

        if summary:
            logger.info(f"Successfully summarized to {len(summary)} chars")
            return summary
        else:
            logger.warning("Ollama returned empty response")
            return "[Summarization failed: empty response]"

    except subprocess.TimeoutExpired:
        logger.error("Ollama summarization timed out")
        return "[Summarization failed: timeout]"
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse Ollama response: {e}")
        return "[Summarization failed: invalid JSON response]"
    except FileNotFoundError:
        logger.error("curl command not found")
        return "[Summarization failed: curl not found]"
    except Exception as e:
        logger.error(f"Unexpected error during summarization: {e}")
        return f"[Summarization failed: {e}]"


# === Helper Functions for Promotion ===


def _find_promotion_candidates(
    memory_dir: Path, workspace: Path, corridors_dir: Path
) -> List[Dict[str, Any]]:
    """
    Find memory files that are candidates for promotion to corridor.

    Args:
        memory_dir: Directory containing daily memory files
        workspace: Workspace root path
        corridors_dir: Corridors output directory

    Returns:
        List of candidate dictionaries with file info.
    """
    candidates = []
    for md_file in sorted(memory_dir.rglob("2*.md")):  # Date-prefixed files (recursive)
        try:
            rel_path = str(md_file.relative_to(workspace))
        except ValueError:
            rel_path = str(md_file)

        age_days = file_age_days(rel_path)

        if age_days > ATRIUM_MAX_AGE_HOURS / 24:
            # Check if already promoted
            summary_name = f"corridor-{md_file.stem}.md"
            summary_path = corridors_dir / summary_name

            if not summary_path.exists():
                try:
                    summary_rel = str(summary_path.relative_to(workspace))
                except ValueError:
                    summary_rel = str(summary_path)

                candidates.append(
                    {
                        "path": rel_path,
                        "full_path": str(md_file),
                        "age_days": round(age_days, 1),
                        "summary_path": str(summary_path),
                        "summary_rel": summary_rel,
                    }
                )
    return candidates


def _promote_single_file(candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Promote a single file from atrium to corridor.

    Args:
        candidate: Candidate dictionary with file paths

    Returns:
        Result dictionary if successful, None otherwise.
    """
    c = candidate

    # Read the source file
    try:
        content = Path(c["full_path"]).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"Skip {c['path']}: could not read file: {e}")
        print(f"  Skip {c['path']}: {e}", file=sys.stderr)
        return None

    if len(content.strip()) < 100:
        logger.debug(f"Skip {c['path']}: too short ({len(content)} chars)")
        return None

    print(f"  Summarizing {c['path']} ({c['age_days']}d old)...", file=sys.stderr)

    # Summarize via LLM
    summary = llm_summarize(content, mode="corridor")

    if not summary or summary.startswith("[Summarization failed"):
        logger.warning(f"Summarization failed for {c['path']}: {summary}")
        return None

    # Write corridor summary
    header = f"# Corridor Summary: {Path(c['path']).stem}\n\n"
    header += f"*Promoted from atrium on {datetime.now().strftime('%Y-%m-%d')}. "
    header += f"Original: `{c['path']}` ({len(content)} chars)*\n\n---\n\n"

    try:
        Path(c["summary_path"]).write_text(header + summary, encoding="utf-8")
        logger.info(f"Promoted {c['path']} → {c['summary_rel']}")
    except (OSError, UnicodeEncodeError) as e:
        logger.error(f"Failed to write summary for {c['path']}: {e}")
        return None

    # Update gravity database
    try:
        db = get_db()
        db.execute(
            """
            UPDATE gravity SET chamber = 'corridor', promoted_at = ?
            WHERE path = ?
        """,
            (now_iso(), c["path"]),
        )

        # Add corridor summary to gravity
        db.execute(
            """
            INSERT OR REPLACE INTO gravity
            (path, line_start, line_end, chamber, last_written_at, source_chunk)
            VALUES (?, 0, 0, 'corridor', ?, ?)
        """,
            (c["summary_rel"], now_iso(), c["path"]),
        )

        commit_with_retry(db)
        db.close()
    except sqlite3.Error as e:
        logger.error(f"Database error promoting {c['path']}: {e}")
        return None

    return {
        "source": c["path"],
        "summary": c["summary_rel"],
        "original_size": len(content),
        "summary_size": len(summary),
    }


# === Helper Functions for Crystallization ===


def _check_crystallization_candidate(
    md_file: Path, workspace: Path, memory_dir: Path, vault_dir: Path
) -> Optional[Dict[str, Any]]:
    """
    Check if a corridor file is a candidate for crystallization.

    Args:
        md_file: Path to corridor markdown file
        workspace: Workspace root path
        memory_dir: Memory directory for age checking
        vault_dir: Vault output directory

    Returns:
        Candidate dictionary if valid, None otherwise.
    """
    try:
        rel_path = str(md_file.relative_to(workspace))
    except ValueError:
        rel_path = str(md_file)

    # Extract date from filename
    match = re.search(r"(\d{4}-\d{2}-\d{2})", md_file.stem)
    if not match:
        return None

    # Check age of original file
    original_path = memory_dir / f"{match.group(1)}.md"
    if not original_path.exists():
        return None

    age = file_age_days(f"memory/{match.group(1)}.md")
    if age <= CORRIDOR_MAX_AGE_DAYS:
        return None

    vault_name = f"vault-{match.group(1)}.md"
    vault_path = vault_dir / vault_name

    if vault_path.exists():
        return None

    try:
        vault_rel = str(vault_path.relative_to(workspace))
    except ValueError:
        vault_rel = str(vault_path)

    return {
        "path": rel_path,
        "full_path": str(md_file),
        "age_days": round(age, 1),
        "vault_path": str(vault_path),
        "vault_rel": vault_rel,
    }


def _find_crystallization_candidates(
    corridors_dir: Path, workspace: Path, memory_dir: Path, vault_dir: Path
) -> List[Dict[str, Any]]:
    """
    Find corridor summaries that are candidates for crystallization to vault.

    Args:
        corridors_dir: Directory containing corridor summaries
        workspace: Workspace root path
        memory_dir: Memory directory for age checking
        vault_dir: Vault output directory

    Returns:
        List of candidate dictionaries with file info.
    """
    if not corridors_dir.exists():
        return []

    candidates = []
    for md_file in sorted(corridors_dir.glob("corridor-*.md")):
        candidate = _check_crystallization_candidate(md_file, workspace, memory_dir, vault_dir)
        if candidate:
            candidates.append(candidate)

    return candidates


def _crystallize_single_file(candidate: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Crystallize a single corridor summary to vault.

    Args:
        candidate: Candidate dictionary with file paths

    Returns:
        Result dictionary if successful, None otherwise.
    """
    c = candidate

    try:
        content = Path(c["full_path"]).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as e:
        logger.warning(f"Skip {c['path']}: could not read file: {e}")
        return None

    if len(content.strip()) < 50:
        logger.debug(f"Skip {c['path']}: too short ({len(content)} chars)")
        return None

    print(f"  Crystallizing {c['path']} ({c['age_days']}d old)...", file=sys.stderr)

    lessons = llm_summarize(content, mode="vault")

    if not lessons or lessons.startswith("[Summarization failed"):
        logger.warning(f"Crystallization failed for {c['path']}: {lessons}")
        return None

    header = f"# Vault Lessons: {Path(c['path']).stem}\n\n"
    header += f"*Crystallized on {datetime.now().strftime('%Y-%m-%d')}. "
    header += f"Source: `{c['path']}`*\n\n---\n\n"

    try:
        Path(c["vault_path"]).write_text(header + lessons, encoding="utf-8")
        logger.info(f"Crystallized {c['path']} → {c['vault_rel']}")
    except (OSError, UnicodeEncodeError) as e:
        logger.error(f"Failed to write vault for {c['path']}: {e}")
        return None

    try:
        db = get_db()
        db.execute(
            """
            UPDATE gravity SET chamber = 'vault', promoted_at = ?
            WHERE path = ?
        """,
            (now_iso(), c["path"]),
        )

        db.execute(
            """
            INSERT OR REPLACE INTO gravity
            (path, line_start, line_end, chamber, last_written_at, source_chunk)
            VALUES (?, 0, 0, 'vault', ?, ?)
        """,
            (c["vault_rel"], now_iso(), c["path"]),
        )

        commit_with_retry(db)
        db.close()
    except sqlite3.Error as e:
        logger.error(f"Database error crystallizing {c['path']}: {e}")
        return None

    return {"source": c["path"], "vault": c["vault_rel"], "lessons_size": len(lessons)}


# === Commands ===


def cmd_classify(args: List[str]) -> Dict[str, Any]:
    """
    Auto-classify all memory files into chambers based on age.

    Args:
        args: Command arguments (currently unused)

    Returns:
        Dictionary with classification statistics.
    """
    try:
        db = get_db()
        workspace = config.get_workspace()

        # Get all memory files
        memory_dir = config.get_memory_dir()
        if not memory_dir.exists():
            error_msg = f"No memory directory found: {memory_dir}"
            logger.error(error_msg)
            print(json.dumps({"error": error_msg, "path": str(memory_dir)}))
            sys.exit(1)

        classified = {"atrium": 0, "corridor": 0, "vault": 0}

        logger.info(f"Classifying files in {memory_dir}")

        for md_file in sorted(memory_dir.glob("*.md")):
            try:
                rel_path = str(md_file.relative_to(workspace))
            except ValueError:
                rel_path = str(md_file)

            chamber = classify_chamber(rel_path)
            classified[chamber] += 1

            # Upsert into gravity with chamber
            db.execute(
                """
                INSERT INTO gravity (path, line_start, line_end, chamber, last_written_at)
                VALUES (?, 0, 0, ?, ?)
                ON CONFLICT(path, line_start, line_end) DO UPDATE SET
                    chamber = ?
            """,
                (rel_path, chamber, now_iso(), chamber),
            )

        commit_with_retry(db)
        db.close()

        result = {
            "classified": classified,
            "total": sum(classified.values()),
            "timestamp": now_iso(),
        }

        logger.info(f"Classified {result['total']} files: {classified}")
        print(json.dumps(result, indent=2))
        return result

    except sqlite3.Error as e:
        logger.error(f"Database error in classify: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_promote(args: List[str]) -> Dict[str, Any]:
    """
    Promote atrium memories (>48h) to corridor (summarized).

    Args:
        args: Command arguments [--dry-run]

    Returns:
        Dictionary with promotion statistics.
    """
    dry_run = "--dry-run" in args

    try:
        corridors_dir = config.get_corridors_dir()
        corridors_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Could not create corridors directory: {e}")
        print(
            json.dumps({"error": f"Could not create corridors dir: {e}"}),
            file=sys.stderr,
        )
        sys.exit(1)

    workspace = config.get_workspace()
    memory_dir = config.get_memory_dir()

    logger.info(f"Searching for promotion candidates in {memory_dir}")
    candidates = _find_promotion_candidates(memory_dir, workspace, corridors_dir)

    if dry_run:
        result = {
            "mode": "dry-run",
            "candidates": len(candidates),
            "files": [c["path"] for c in candidates],
        }
        logger.info(f"Dry-run: found {len(candidates)} promotion candidates")
        print(json.dumps(result, indent=2))
        return result

    promoted = []
    for c in candidates:
        result = _promote_single_file(c)
        if result:
            promoted.append(result)

    result = {"promoted": len(promoted), "details": promoted, "timestamp": now_iso()}

    logger.info(f"Promoted {len(promoted)} files to corridor")
    print(json.dumps(result, indent=2))
    return result


def cmd_crystallize(args: List[str]) -> Dict[str, Any]:
    """
    Crystallize corridor summaries (>7d) into vault lessons.

    Args:
        args: Command arguments [--dry-run]

    Returns:
        Dictionary with crystallization statistics.
    """
    dry_run = "--dry-run" in args

    try:
        vault_dir = config.get_vaults_dir()
        vault_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Could not create vaults directory: {e}")
        print(
            json.dumps({"error": f"Could not create vaults dir: {e}"}),
            file=sys.stderr,
        )
        sys.exit(1)

    corridors_dir = config.get_corridors_dir()
    workspace = config.get_workspace()
    memory_dir = config.get_memory_dir()

    logger.info(f"Searching for crystallization candidates in {corridors_dir}")
    candidates = _find_crystallization_candidates(corridors_dir, workspace, memory_dir, vault_dir)

    if dry_run:
        result = {
            "mode": "dry-run",
            "candidates": len(candidates),
            "files": [c["path"] for c in candidates],
        }
        logger.info(f"Dry-run: found {len(candidates)} crystallization candidates")
        print(json.dumps(result, indent=2))
        return result

    crystallized = []
    for c in candidates:
        result = _crystallize_single_file(c)
        if result:
            crystallized.append(result)

    result = {
        "crystallized": len(crystallized),
        "details": crystallized,
        "timestamp": now_iso(),
    }

    logger.info(f"Crystallized {len(crystallized)} files to vault")
    print(json.dumps(result, indent=2))
    return result


def cmd_status(args: List[str]) -> Dict[str, Any]:
    """
    Show chamber distribution.

    Args:
        args: Command arguments (currently unused)

    Returns:
        Dictionary with chamber statistics.
    """
    try:
        db = get_db()

        chambers = db.execute(
            """
            SELECT chamber, COUNT(*) as count
            FROM gravity
            GROUP BY chamber
        """
        ).fetchall()

        total = db.execute("SELECT COUNT(*) FROM gravity").fetchone()[0]

        # Recent promotions
        recent = db.execute(
            """
            SELECT path, chamber, promoted_at
            FROM gravity
            WHERE promoted_at IS NOT NULL
            ORDER BY promoted_at DESC
            LIMIT 5
        """
        ).fetchall()

        db.close()

        # Check summary directories
        corridor_count = (
            len(list(config.get_corridors_dir().glob("*.md")))
            if config.get_corridors_dir().exists()
            else 0
        )
        vault_count = (
            len(list(config.get_vaults_dir().glob("*.md")))
            if config.get_vaults_dir().exists()
            else 0
        )

        result = {
            "chambers": {row["chamber"]: row["count"] for row in chambers},
            "total_tracked": total,
            "summary_files": {"corridors": corridor_count, "vaults": vault_count},
            "recent_promotions": [dict(r) for r in recent],
            "directories": {
                "corridors": str(config.get_corridors_dir()),
                "vaults": str(config.get_vaults_dir()),
            },
        }

        logger.info(
            f"Chamber status: {total} tracked, {corridor_count} corridors, " f"{vault_count} vaults"
        )
        print(json.dumps(result, indent=2, default=str))
        return result

    except sqlite3.Error as e:
        logger.error(f"Database error in status: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


# === Main ===

COMMANDS = {
    "classify": cmd_classify,
    "promote": cmd_promote,
    "crystallize": cmd_crystallize,
    "status": cmd_status,
}


def main() -> None:
    """Main entry point for chambers command."""
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("Usage: python -m core.nautilus chambers <command> [args]")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    cmd = sys.argv[1]
    logger.info(f"Executing chambers command: {cmd}")
    result = COMMANDS[cmd](sys.argv[2:])
    if result and not sys.stdout.isatty():
        # Already printed if interactive
        pass


if __name__ == "__main__":
    # Configure logging if running as main
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    main()
