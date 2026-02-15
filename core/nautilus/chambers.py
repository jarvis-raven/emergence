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
  chambers.py classify              # Classify all chunks by age
  chambers.py promote [--dry-run]   # Atrium → Corridor (summarize via LLM)
  chambers.py crystallize [--dry-run]  # Corridor → Vault (distill via LLM)
  chambers.py status                # Show chamber distribution
  chambers.py search <query> [--chamber atrium,corridor] [--n 10]
"""

import sqlite3
import json
import sys
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from .config import get_db_path, get_workspace, get_config

# Get configuration
WORKSPACE = get_workspace()
SUMMARIES_DIR = WORKSPACE / "memory" / "corridors"
VAULT_DIR = WORKSPACE / "memory" / "vaults"


# Promotion thresholds (will be overridden by config)
def get_chamber_thresholds():
    config = get_config()
    thresholds = config.get("chamber_thresholds", {})
    return {
        "atrium_max_age_hours": thresholds.get("atrium_max_age_hours", 48),
        "corridor_max_age_days": thresholds.get("corridor_max_age_days", 7),
    }


# LLM config for summarization (overridable via config)
def get_summarization_config():
    """Get summarization configuration from emergence.json."""
    config = get_config()
    summ_config = config.get("summarization", {})
    return {
        "ollama_url": summ_config.get("ollama_url", "http://localhost:11434/api/generate"),
        "model": summ_config.get("model", "llama3.2:3b"),
        "enabled": summ_config.get("enabled", True),
        "temperature": summ_config.get("temperature", 0.3),
        "max_tokens": summ_config.get("max_tokens", 1024),
    }


def get_db():
    DB_PATH = get_db_path()
    db = sqlite3.connect(str(DB_PATH))
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")
    return db


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def file_age_days(filepath):
    """Get the age of a file in days based on its name or mtime."""
    name = Path(filepath).stem
    # Try to parse YYYY-MM-DD from filename
    match = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    if match:
        try:
            file_date = datetime.strptime(match.group(1), "%Y-%m-%d").replace(tzinfo=timezone.utc)
            return (datetime.now(timezone.utc) - file_date).total_seconds() / 86400
        except ValueError:
            pass

    # Fall back to mtime
    full_path = WORKSPACE / filepath
    if full_path.exists():
        mtime = datetime.fromtimestamp(full_path.stat().st_mtime, tz=timezone.utc)
        return (datetime.now(timezone.utc) - mtime).total_seconds() / 86400

    return 999


def classify_chamber(filepath):
    """Determine which chamber a file belongs to based on age."""
    thresholds = get_chamber_thresholds()
    age = file_age_days(filepath)
    if age <= thresholds["atrium_max_age_hours"] / 24:
        return "atrium"
    elif age <= thresholds["corridor_max_age_days"]:
        return "corridor"
    else:
        return "vault"


def llm_summarize(text, mode="corridor"):
    """Use local Ollama to summarize text with graceful fallback."""
    summ_config = get_summarization_config()

    # Skip if summarization disabled
    if not summ_config["enabled"]:
        print("  ⚠️  Summarization disabled in config, skipping...", file=sys.stderr)
        return None

    if mode == "corridor":
        prompt = f"""You are summarizing a daily memory log for an AI agent. Create a readable narrative (2-4 paragraphs) that:

PRESERVE:
- Key decisions made and their reasoning
- Important interactions with people (names, context, outcomes)
- Problems encountered and how they were solved
- Lessons learned and insights gained
- Action items or follow-ups
- Technical details that matter (versions, configs, bugs fixed)
- Keywords and searchable terms from the original

DROP:
- Routine status checks and heartbeat logs
- Minor tool output and verbose debugging
- Timestamps (unless critical to the narrative)
- Repetitive confirmations

Keep the voice first-person and maintain the agent's perspective. Focus on what future-you would want to recall.

---
{text[:8000]}
---

Summary:"""
    else:  # vault
        prompt = f"""You are distilling a weekly summary into permanent lessons for an AI agent. Extract only what's worth keeping long-term:

KEEP:
- Reusable patterns and solutions
- Critical architectural decisions
- Relationship insights (people, interactions, dynamics)
- System knowledge (how things work, configs, integrations)
- Permanent lessons learned
- Reference information for future tasks

FORMAT: Clear bullet points grouped by theme.

Be ruthless — only include what future-you absolutely needs 30+ days from now.

---
{text[:6000]}
---

Lessons:"""

    try:
        # Test Ollama availability first
        health_check = subprocess.run(
            [
                "curl",
                "-s",
                "-o",
                "/dev/null",
                "-w",
                "%{http_code}",
                summ_config["ollama_url"].replace("/api/generate", ""),
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        if health_check.stdout.strip() != "200":
            print(
                f"  ⚠️  Ollama not available (HTTP {health_check.stdout.strip()}), skipping summarization...",
                file=sys.stderr,
            )
            return None

        # Generate summary
        result = subprocess.run(
            [
                "curl",
                "-s",
                summ_config["ollama_url"],
                "-d",
                json.dumps(
                    {
                        "model": summ_config["model"],
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": summ_config["temperature"],
                            "num_predict": summ_config["max_tokens"],
                        },
                    }
                ),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if result.returncode != 0:
            print(
                f"  ⚠️  Ollama request failed (exit code {result.returncode}), skipping...",
                file=sys.stderr,
            )
            return None

        response = json.loads(result.stdout)
        summary = response.get("response", "").strip()

        if not summary:
            print("  ⚠️  Ollama returned empty response, skipping...", file=sys.stderr)
            return None

        return summary

    except subprocess.TimeoutExpired:
        print("  ⚠️  Ollama request timed out, skipping summarization...", file=sys.stderr)
        return None
    except json.JSONDecodeError as e:
        print(f"  ⚠️  Ollama response invalid JSON ({e}), skipping...", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("  ⚠️  curl not found, skipping summarization...", file=sys.stderr)
        return None
    except Exception as e:
        print(f"  ⚠️  Summarization error: {e}, skipping...", file=sys.stderr)
        return None


def cmd_classify(args):
    """Auto-classify all memory files into chambers based on age."""
    db = get_db()

    # Get all memory files
    memory_dir = WORKSPACE / "memory"
    if not memory_dir.exists():
        print("No memory directory found", file=sys.stderr)
        sys.exit(1)

    classified = {"atrium": 0, "corridor": 0, "vault": 0}

    for md_file in sorted(memory_dir.glob("*.md")):
        rel_path = str(md_file.relative_to(WORKSPACE))
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

    db.commit()
    db.close()

    print(
        json.dumps(
            {"classified": classified, "total": sum(classified.values()), "timestamp": now_iso()},
            indent=2,
        )
    )


def cmd_promote(args):
    """Promote atrium memories (>48h) to corridor (summarized)."""
    dry_run = "--dry-run" in args
    thresholds = get_chamber_thresholds()

    SUMMARIES_DIR.mkdir(parents=True, exist_ok=True)

    # Find daily memory files older than threshold (FIXED: search recursively)
    memory_dir = WORKSPACE / "memory"
    candidates = []

    if not memory_dir.exists():
        print(
            json.dumps({"error": "Memory directory not found", "path": str(memory_dir)}, indent=2)
        )
        return

    # Search recursively for date-prefixed files (rglob instead of glob)
    for md_file in sorted(memory_dir.rglob("2*.md")):
        # Skip corridor and vault directories to avoid re-promoting summaries
        if "corridor" in md_file.parts or "vault" in md_file.parts:
            continue

        rel_path = str(md_file.relative_to(WORKSPACE))
        age_days = file_age_days(rel_path)

        if age_days > thresholds["atrium_max_age_hours"] / 24:
            # Check if already promoted
            # Use just the filename stem for the summary name
            summary_name = f"corridor-{md_file.stem}.md"
            summary_path = SUMMARIES_DIR / summary_name

            if not summary_path.exists():
                candidates.append(
                    {
                        "path": rel_path,
                        "full_path": str(md_file),
                        "age_days": round(age_days, 1),
                        "summary_path": str(summary_path),
                        "summary_rel": str(summary_path.relative_to(WORKSPACE)),
                    }
                )

    if dry_run:
        print(
            json.dumps(
                {
                    "mode": "dry-run",
                    "candidates": len(candidates),
                    "files": [c["path"] for c in candidates],
                    "config": {
                        "atrium_max_age_hours": thresholds["atrium_max_age_hours"],
                        "summarization": get_summarization_config(),
                    },
                },
                indent=2,
            )
        )
        return

    promoted = []
    skipped = []

    for c in candidates:
        # Read the source file
        try:
            content = Path(c["full_path"]).read_text(encoding="utf-8")
        except Exception as e:
            print(f"  ❌ Skip {c['path']}: {e}", file=sys.stderr)
            skipped.append({"path": c["path"], "reason": str(e)})
            continue

        if len(content.strip()) < 100:
            print(f"  ⏭️  Skip {c['path']}: file too small ({len(content)} chars)", file=sys.stderr)
            skipped.append({"path": c["path"], "reason": "file too small"})
            continue

        print(
            f"  📝 Summarizing {c['path']} ({c['age_days']}d old, {len(content)} chars)...",
            file=sys.stderr,
        )

        # Summarize via LLM (with graceful fallback)
        summary = llm_summarize(content, mode="corridor")

        if summary:
            # Write corridor summary
            header = f"# Corridor Summary: {Path(c['path']).stem}\n\n"
            header += f"*Promoted from atrium on {datetime.now().strftime('%Y-%m-%d')}. "
            header += f"Original: `{c['path']}` ({len(content)} chars → {len(summary)} chars summary)*\n\n---\n\n"

            Path(c["summary_path"]).write_text(header + summary, encoding="utf-8")

            # Update gravity database
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

            db.commit()
            db.close()

            promoted.append(
                {
                    "source": c["path"],
                    "summary": c["summary_rel"],
                    "original_size": len(content),
                    "summary_size": len(summary),
                    "compression_ratio": (
                        round(len(content) / len(summary), 2) if len(summary) > 0 else 0
                    ),
                }
            )

            print(
                f"  ✅ Created {c['summary_rel']} ({len(summary)} chars, {round(len(content)/len(summary), 1)}x compression)",
                file=sys.stderr,
            )
        else:
            # Summarization skipped or failed - mark as promoted anyway to avoid retry loops
            print(
                f"  ⚠️  Skipped summarization for {c['path']} (marked as corridor anyway)",
                file=sys.stderr,
            )

            db = get_db()
            db.execute(
                """
                UPDATE gravity SET chamber = 'corridor', promoted_at = ?
                WHERE path = ?
            """,
                (now_iso(), c["path"]),
            )
            db.commit()
            db.close()

            skipped.append({"path": c["path"], "reason": "summarization unavailable"})

    print(
        json.dumps(
            {
                "promoted": len(promoted),
                "skipped": len(skipped),
                "details": promoted,
                "skipped_files": skipped,
                "timestamp": now_iso(),
            },
            indent=2,
        )
    )


def cmd_crystallize(args):
    """Crystallize corridor summaries (>7d) into vault lessons."""
    dry_run = "--dry-run" in args
    thresholds = get_chamber_thresholds()

    VAULT_DIR.mkdir(parents=True, exist_ok=True)

    # Find corridor summaries older than threshold
    candidates = []

    if SUMMARIES_DIR.exists():
        for md_file in sorted(SUMMARIES_DIR.glob("corridor-*.md")):
            rel_path = str(md_file.relative_to(WORKSPACE))
            # Extract date from filename
            match = re.search(r"(\d{4}-\d{2}-\d{2})", md_file.stem)
            if match:
                age = file_age_days(f"memory/{match.group(1)}.md")
                if age > thresholds["corridor_max_age_days"]:
                    vault_name = f"vault-{match.group(1)}.md"
                    vault_path = VAULT_DIR / vault_name

                    if not vault_path.exists():
                        candidates.append(
                            {
                                "path": rel_path,
                                "full_path": str(md_file),
                                "age_days": round(age, 1),
                                "vault_path": str(vault_path),
                                "vault_rel": str(vault_path.relative_to(WORKSPACE)),
                            }
                        )

    if dry_run:
        print(
            json.dumps(
                {
                    "mode": "dry-run",
                    "candidates": len(candidates),
                    "files": [c["path"] for c in candidates],
                    "config": {
                        "corridor_max_age_days": thresholds["corridor_max_age_days"],
                        "summarization": get_summarization_config(),
                    },
                },
                indent=2,
            )
        )
        return

    crystallized = []
    skipped = []

    for c in candidates:
        try:
            content = Path(c["full_path"]).read_text(encoding="utf-8")
        except Exception as e:
            print(f"  ❌ Skip {c['path']}: {e}", file=sys.stderr)
            skipped.append({"path": c["path"], "reason": str(e)})
            continue

        if len(content.strip()) < 50:
            print(f"  ⏭️  Skip {c['path']}: file too small", file=sys.stderr)
            skipped.append({"path": c["path"], "reason": "file too small"})
            continue

        print(f"  🔮 Crystallizing {c['path']} ({c['age_days']}d old)...", file=sys.stderr)

        lessons = llm_summarize(content, mode="vault")

        if lessons:
            header = f"# Vault Lessons: {Path(c['path']).stem}\n\n"
            header += f"*Crystallized on {datetime.now().strftime('%Y-%m-%d')}. "
            header += f"Source: `{c['path']}`*\n\n---\n\n"

            Path(c["vault_path"]).write_text(header + lessons, encoding="utf-8")

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

            db.commit()
            db.close()

            crystallized.append(
                {"source": c["path"], "vault": c["vault_rel"], "lessons_size": len(lessons)}
            )

            print(f"  ✅ Created {c['vault_rel']} ({len(lessons)} chars)", file=sys.stderr)
        else:
            # Crystallization skipped - mark as vault anyway
            print(
                f"  ⚠️  Skipped crystallization for {c['path']} (marked as vault anyway)",
                file=sys.stderr,
            )

            db = get_db()
            db.execute(
                """
                UPDATE gravity SET chamber = 'vault', promoted_at = ?
                WHERE path = ?
            """,
                (now_iso(), c["path"]),
            )
            db.commit()
            db.close()

            skipped.append({"path": c["path"], "reason": "crystallization unavailable"})

    print(
        json.dumps(
            {
                "crystallized": len(crystallized),
                "skipped": len(skipped),
                "details": crystallized,
                "skipped_files": skipped,
                "timestamp": now_iso(),
            },
            indent=2,
        )
    )


def cmd_status(args):
    """Show chamber distribution."""
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

    # Check summary directories
    corridor_count = len(list(SUMMARIES_DIR.glob("*.md"))) if SUMMARIES_DIR.exists() else 0
    vault_count = len(list(VAULT_DIR.glob("*.md"))) if VAULT_DIR.exists() else 0

    print(
        json.dumps(
            {
                "chambers": {row["chamber"]: row["count"] for row in chambers},
                "total_tracked": total,
                "summary_files": {"corridors": corridor_count, "vaults": vault_count},
                "recent_promotions": [dict(r) for r in recent],
                "directories": {"corridors": str(SUMMARIES_DIR), "vaults": str(VAULT_DIR)},
            },
            indent=2,
            default=str,
        )
    )
    db.close()


def cmd_search(args):
    """
    Search with chamber awareness.
    Defaults to atrium + corridor. Use --chamber to specify.
    """
    if not args:
        print(
            "Usage: chambers.py search <query> [--chamber atrium,corridor] [--n 10]",
            file=sys.stderr,
        )
        sys.exit(1)

    query = args[0]
    chambers_filter = "atrium,corridor"
    n = 10

    i = 1
    while i < len(args):
        if args[i] == "--chamber" and i + 1 < len(args):
            chambers_filter = args[i + 1]
            i += 2
        elif args[i] == "--n" and i + 1 < len(args):
            n = int(args[i + 1])
            i += 2
        else:
            i += 1

    allowed_chambers = set(chambers_filter.split(","))

    # Run openclaw memory search
    try:
        result = subprocess.run(
            ["openclaw", "memory", "search", query, "--max-results", str(n * 2), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
            env={**os.environ},
        )
        results = json.loads(result.stdout)
    except Exception as e:
        print(json.dumps({"error": str(e)}))
        return

    if not isinstance(results, list):
        results = results.get("results", [])

    # Filter by chamber
    db = get_db()
    filtered = []

    for r in results:
        path = r.get("path", "")

        # Look up chamber
        row = db.execute("SELECT chamber FROM gravity WHERE path = ? LIMIT 1", (path,)).fetchone()

        if row:
            chamber = row["chamber"]
        else:
            # Auto-classify
            chamber = classify_chamber(path)

        if chamber in allowed_chambers:
            r["chamber"] = chamber
            filtered.append(r)

    db.close()

    # Truncate to n
    filtered = filtered[:n]

    print(
        json.dumps(
            {
                "query": query,
                "chambers": list(allowed_chambers),
                "results": filtered,
                "total_before_filter": len(results),
                "total_after_filter": len(filtered),
            },
            indent=2,
        )
    )


# === Main ===

COMMANDS = {
    "classify": cmd_classify,
    "promote": cmd_promote,
    "crystallize": cmd_crystallize,
    "status": cmd_status,
    "search": cmd_search,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: chambers.py <command> [args]")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)

    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
