#!/usr/bin/env python3
"""
🐚 Nautilus — Unified Memory Palace CLI

Wraps OpenClaw's memory search with Nautilus re-ranking and filtering.

Search pipeline:
  1. Call `openclaw memory search` for vector similarity candidates
  2. Enrich each result with Nautilus metadata (access_count, chamber, context_tags)
  3. Apply optional filters (--context, --chamber)
  4. Re-rank: final_score = vector_score * (1 + log(access_count + 1)) * recency_boost
  5. Return top N results as JSON

Usage:
  nautilus search <query> [--n 5] [--context TAG] [--chamber atrium,corridor] [--verbose]
  nautilus status          # Full system status
  nautilus maintain        # Run all maintenance (classify, auto-tag, decay)
"""

import json
import math
import sys
import sqlite3
import subprocess
from datetime import datetime, timezone

from .config import get_workspace, get_gravity_db_path


# Chamber-based recency boost factors
CHAMBER_RECENCY = {
    "atrium": 1.2,  # Recent/active memories get a boost
    "corridor": 1.0,  # Summarised memories are neutral
    "vault": 0.8,  # Crystallised lessons slightly discounted for recency
}


def _parse_search_args(args):
    """Parse search command arguments.

    Returns:
        Tuple of (query, n, context, chambers, trapdoor, verbose)
    """
    query_parts = []
    n = 5
    context = None
    chambers = None
    trapdoor = False
    verbose = False

    i = 0
    while i < len(args):
        if args[i] == "--n" and i + 1 < len(args):
            n = int(args[i + 1])
            i += 2
        elif args[i] == "--context" and i + 1 < len(args):
            context = args[i + 1]
            i += 2
        elif args[i] == "--chamber" and i + 1 < len(args):
            chambers = [c.strip() for c in args[i + 1].split(",")]
            i += 2
        elif args[i] == "--trapdoor":
            trapdoor = True
            i += 1
        elif args[i] == "--verbose":
            verbose = True
            i += 1
        else:
            query_parts.append(args[i])
            i += 1

    return " ".join(query_parts), n, context, chambers, trapdoor, verbose


def _get_gravity_metadata(db, path, start_line, end_line):
    """Look up Nautilus gravity metadata for a search result.

    Tries exact chunk match first, then falls back to file-level match.

    Args:
        db: SQLite connection to gravity.db
        path: File path of the result
        start_line: Start line of the chunk
        end_line: End line of the chunk

    Returns:
        Dict with access_count, chamber, context_tags, last_accessed_at
    """
    # Try exact chunk match
    row = db.execute(
        """SELECT access_count, chamber, context_tags, last_accessed_at
           FROM gravity WHERE path = ? AND line_start = ? AND line_end = ?""",
        (path, start_line, end_line),
    ).fetchone()

    # Fall back to file-level match
    if not row:
        row = db.execute(
            """SELECT access_count, chamber, context_tags, last_accessed_at
               FROM gravity WHERE path = ? LIMIT 1""",
            (path,),
        ).fetchone()

    if row:
        try:
            tags = json.loads(row["context_tags"]) if row["context_tags"] else []
        except (json.JSONDecodeError, TypeError):
            tags = []
        return {
            "access_count": row["access_count"] or 0,
            "chamber": row["chamber"] or "atrium",
            "context_tags": tags,
            "last_accessed_at": row["last_accessed_at"],
        }

    return {
        "access_count": 0,
        "chamber": "atrium",
        "context_tags": [],
        "last_accessed_at": None,
    }


def _compute_final_score(vector_score, access_count, chamber):
    """Compute re-ranked score using the Nautilus formula.

    Formula: final_score = vector_score * (1 + log(access_count + 1)) * recency_boost

    Args:
        vector_score: Original vector similarity score
        access_count: Number of times this chunk has been accessed
        chamber: Chamber classification (atrium/corridor/vault)

    Returns:
        Final re-ranked score
    """
    importance = 1 + math.log(access_count + 1)
    recency = CHAMBER_RECENCY.get(chamber, 1.0)
    return vector_score * importance * recency


def _fetch_openclaw_results(query, fetch_count):
    """Call OpenClaw memory search and return candidate list.

    Args:
        query: Search query string
        fetch_count: Number of results to request

    Returns:
        List of result dicts, or None on failure (error printed to stdout)
    """
    try:
        result = subprocess.run(
            [
                "openclaw",
                "memory",
                "search",
                query,
                "--max-results",
                str(fetch_count),
                "--json",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        raw = json.loads(result.stdout)
    except Exception as e:
        print(json.dumps({"error": f"Memory search failed: {e}"}))
        return None
    return raw if isinstance(raw, list) else raw.get("results", [])


def _enrich_and_filter(candidates, context, chambers, trapdoor, verbose):
    """Enrich candidates with gravity metadata, apply filters, and re-rank.

    Args:
        candidates: List of raw search results
        context: Context tag filter (or None)
        chambers: List of chamber names to keep (or None)
        trapdoor: If True, skip context filtering
        verbose: Print debug info to stderr

    Returns:
        Re-ranked and filtered candidate list
    """
    db = sqlite3.connect(str(get_gravity_db_path()))
    db.row_factory = sqlite3.Row

    for c in candidates:
        meta = _get_gravity_metadata(
            db, c.get("path", ""), c.get("startLine", 0), c.get("endLine", 0)
        )
        c["access_count"] = meta["access_count"]
        c["chamber"] = meta["chamber"]
        c["context_tags"] = meta["context_tags"]

    db.close()

    # Apply filters
    if context and not trapdoor:
        candidates = [c for c in candidates if context in c.get("context_tags", [])]
        if verbose:
            print(
                f"🚪 Context filter '{context}': {len(candidates)} remain",
                file=sys.stderr,
            )

    if chambers:
        candidates = [c for c in candidates if c.get("chamber") in chambers]
        if verbose:
            print(
                f"🏛️ Chamber filter {chambers}: {len(candidates)} remain",
                file=sys.stderr,
            )

    # Re-rank using the Nautilus formula
    for c in candidates:
        vector_score = c.get("score", 0)
        c["vector_score"] = vector_score
        c["final_score"] = round(
            _compute_final_score(vector_score, c["access_count"], c["chamber"]),
            4,
        )

    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    return candidates


def _format_results(candidates, n):
    """Truncate to top N results and clean up output format.

    Args:
        candidates: Sorted candidate list
        n: Maximum number of results

    Returns:
        List of cleaned result dicts
    """
    results = candidates[:n]
    for r in results:
        r["score"] = r.pop("final_score")
        if "snippet" in r and len(r.get("snippet", "")) > 300:
            r["snippet"] = r["snippet"][:300] + "..."
    return results


def cmd_search(args):  # noqa: C901
    """Nautilus search — wraps OpenClaw memory search with gravity re-ranking.

    Pipeline:
      1. Call `openclaw memory search` for vector candidates
      2. Look up each result's Nautilus metadata from gravity.db
      3. Apply filters (context tags, chamber)
      4. Re-rank: final_score = vector_score * (1 + log(access_count + 1)) * recency_boost
      5. Return top N results as JSON
    """
    if not args:
        print(
            "Usage: nautilus search <query> [--n 5] [--context TAG]"
            " [--chamber atrium,corridor] [--trapdoor] [--verbose]",
            file=sys.stderr,
        )
        sys.exit(1)

    query, n, context, chambers, trapdoor, verbose = _parse_search_args(args)

    if not query:
        print("Error: no query provided", file=sys.stderr)
        sys.exit(1)

    # Step 1: Fetch candidates from OpenClaw
    candidates = _fetch_openclaw_results(query, n * 3)
    if candidates is None:
        return

    if verbose:
        print(
            f"🔍 Base search: {len(candidates)} candidates for '{query}'",
            file=sys.stderr,
        )

    # Step 2-4: Enrich, filter, re-rank
    candidates = _enrich_and_filter(candidates, context, chambers, trapdoor, verbose)

    if verbose:
        print(f"⚖️ Re-ranked: {len(candidates)} results", file=sys.stderr)

    # Step 5: Format and output
    results = _format_results(candidates, n)

    print(json.dumps({"query": query, "results": results}, indent=2))


def cmd_status(args):
    """Full Nautilus system status."""
    # Get stats from each module
    grav_result = subprocess.run(
        [sys.executable, "-m", "core.nautilus.gravity", "stats"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    cham_result = subprocess.run(
        [sys.executable, "-m", "core.nautilus.chambers", "status"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    mir_result = subprocess.run(
        [sys.executable, "-m", "core.nautilus.mirrors", "stats"],
        capture_output=True,
        text=True,
        timeout=30,
    )

    try:
        gravity_stats = json.loads(grav_result.stdout)
    except BaseException:
        gravity_stats = {"error": "Failed to load gravity stats"}

    try:
        chambers_stats = json.loads(cham_result.stdout)
    except BaseException:
        chambers_stats = {"error": "Failed to load chambers stats"}

    try:
        mirrors_stats = json.loads(mir_result.stdout)
    except BaseException:
        mirrors_stats = {"error": "Failed to load mirrors stats"}

    # Quick tag stats
    import sqlite3
    from .config import get_gravity_db_path

    db = sqlite3.connect(str(get_gravity_db_path()))
    tagged = db.execute(
        "SELECT COUNT(*) FROM gravity WHERE tags != '[]' AND tags IS NOT NULL"
    ).fetchone()[0]
    total = db.execute("SELECT COUNT(*) FROM gravity").fetchone()[0]
    db.close()

    print(
        json.dumps(
            {
                "🐚 nautilus": {
                    "phase_1_gravity": {
                        "total_chunks": gravity_stats.get("total_chunks", 0),
                        "total_accesses": gravity_stats.get("total_accesses", 0),
                        "superseded": gravity_stats.get("superseded_chunks", 0),
                        "db_path": gravity_stats.get("db_path", "unknown"),
                        "db_size": gravity_stats.get("db_size_bytes", 0),
                    },
                    "phase_2_chambers": chambers_stats.get("chambers", {}),
                    "phase_3_doors": {
                        "tagged_files": tagged,
                        "total_files": total,
                        "coverage": f"{tagged}/{total}" if total else "0/0",
                    },
                    "phase_4_mirrors": {
                        "total_events": mirrors_stats.get("total_events", 0),
                        "fully_mirrored": mirrors_stats.get("fully_mirrored", 0),
                        "coverage": mirrors_stats.get("coverage", {}),
                    },
                    "summary_files": chambers_stats.get("summary_files", {}),
                }
            },
            indent=2,
        )
    )


def cmd_maintain(args):  # noqa: C901
    """Run all maintenance tasks."""
    print("🐚 Nautilus maintenance starting...", file=sys.stderr)

    # Register recent writes if --register-recent flag
    if "--register-recent" in args:
        print("\n📝 Registering recent writes...", file=sys.stderr)
        workspace = get_workspace()
        memory_dir = workspace / "memory"

        if memory_dir.exists():
            # Find files modified in last 24h
            import time

            now = time.time()
            day_ago = now - 86400

            for md_file in memory_dir.glob("*.md"):
                mtime = md_file.stat().st_mtime
                if mtime >= day_ago:
                    rel_path = str(md_file.relative_to(workspace))
                    subprocess.run(
                        [sys.executable, "-m", "core.nautilus.gravity", "record-write", rel_path],
                        capture_output=True,
                    )
            print("   Recent writes registered", file=sys.stderr)

    print("\n📂 Classifying chambers...", file=sys.stderr)
    classify_result = subprocess.run(
        [sys.executable, "-m", "core.nautilus.chambers", "classify"], capture_output=True, text=True
    )
    try:
        classify = json.loads(classify_result.stdout)
        print(f"   {json.dumps(classify.get('classified', {}))}", file=sys.stderr)
    except BaseException:
        print("   Chamber classification failed", file=sys.stderr)
        classify = {}

    print("\n🏷️ Auto-tagging contexts...", file=sys.stderr)
    tags_result = subprocess.run(
        [sys.executable, "-m", "core.nautilus.doors", "auto-tag"], capture_output=True, text=True
    )
    try:
        tags = json.loads(tags_result.stdout)
        print(f"   {tags.get('files_tagged', 0)} files tagged", file=sys.stderr)
    except BaseException:
        print("   Auto-tagging failed", file=sys.stderr)
        tags = {}

    print("\n⚖️ Running gravity decay...", file=sys.stderr)
    decay_result = subprocess.run(
        [sys.executable, "-m", "core.nautilus.gravity", "decay"], capture_output=True, text=True
    )
    try:
        decay = json.loads(decay_result.stdout)
        print(f"   {decay.get('decayed', 0)} chunks decayed", file=sys.stderr)
    except BaseException:
        print("   Gravity decay failed", file=sys.stderr)
        decay = {}

    print("\n🔗 Auto-linking mirrors...", file=sys.stderr)
    mirrors_result = subprocess.run(
        [sys.executable, "-m", "core.nautilus.mirrors", "auto-link"], capture_output=True, text=True
    )
    try:
        mir = json.loads(mirrors_result.stdout)
        print(f"   {mir.get('linked', 0)} mirrors linked", file=sys.stderr)
    except BaseException:
        print("   Mirror linking failed", file=sys.stderr)
        mir = {}

    print("\n✅ Maintenance complete", file=sys.stderr)

    # Output summary
    print(
        json.dumps(
            {
                "chambers": classify.get("classified", {}),
                "tagged": tags.get("files_tagged", 0),
                "decayed": decay.get("decayed", 0),
                "mirrors_linked": mir.get("linked", 0),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            indent=2,
        )
    )


def cmd_migrate(args):
    """Migrate legacy nautilus databases to new location."""
    from .migrate_db import migrate_database

    dry_run = "--dry-run" in args
    verbose = "--verbose" in args or dry_run

    result = migrate_database(dry_run=dry_run, verbose=verbose)
    print(json.dumps(result, indent=2))


def cmd_chambers(args):
    """Pass through to chambers module (classify, promote, crystallize, status)."""
    subprocess.run(
        [sys.executable, "-m", "core.nautilus.chambers"] + args,
        cwd=get_workspace().parent,  # emergence repo root
    )


# === Main ===

COMMANDS = {
    "search": cmd_search,
    "status": cmd_status,
    "maintain": cmd_maintain,
    "migrate": cmd_migrate,
    "chambers": cmd_chambers,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("🐚 Nautilus Memory Palace")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        print("\nUsage:")
        print(
            "  nautilus search <query> [--n 5] [--context TAG]"
            " [--chamber atrium,corridor] [--verbose]"
        )
        print("  nautilus status")
        print("  nautilus maintain [--register-recent]")
        print("  nautilus migrate [--dry-run] [--verbose]")
        print("  nautilus chambers <promote|crystallize|status> [--dry-run]")
        print("\nExamples:")
        print('  nautilus search "project nautilus" --verbose')
        print('  nautilus search "budget issue" --n 10 --context work --chamber atrium,corridor')
        print("  nautilus maintain --register-recent")
        print("  nautilus chambers promote --dry-run")
        sys.exit(1)

    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
