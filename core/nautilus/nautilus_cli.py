#!/usr/bin/env python3
"""
🐚 Nautilus — Unified Memory Palace CLI

Combines all four phases:
  Phase 1: Gravity (importance scoring)
  Phase 2: Chambers (temporal layers)
  Phase 3: Doors (context filtering)
  Phase 4: Mirrors (multi-granularity)

Primary command: `nautilus search <query>` — runs the full pipeline:
  1. Classify query context (Doors)
  2. Search with chamber awareness (Chambers)
  3. Apply gravity re-ranking (Gravity)
  4. Resolve mirrors for top results (Mirrors)

Usage:
  emergence nautilus search <query> [--n 5] [--trapdoor] [--verbose]
  emergence nautilus status          # Full system status
  emergence nautilus maintain        # Run all maintenance (classify, auto-tag, decay)
"""

import json
import sys
import subprocess
from datetime import datetime, timezone

from .config import get_workspace


def cmd_search(args):
    """Full Nautilus search pipeline."""
    if not args:
        print(
            "Usage: emergence nautilus search <query> [--n 5] [--trapdoor] [--verbose]",
            file=sys.stderr,
        )
        sys.exit(1)

    query_parts = []
    n = 5
    trapdoor = False
    verbose = False

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
        else:
            query_parts.append(args[i])
            i += 1

    query = " ".join(query_parts)

    # Step 1: Classify context (Doors)
    # Invoke via subprocess to reuse existing command implementation
    result = subprocess.run(
        [sys.executable, "-m", "core.nautilus.doors", "classify", query],
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        context = json.loads(result.stdout)
        context_tags = context.get("context_tags", [])
    except BaseException:
        context_tags = []

    if verbose:
        print(f"🚪 Context: {context_tags or 'none detected'}", file=sys.stderr)

    # Step 2: Run base memory search via OpenClaw
    try:
        result = subprocess.run(
            ["openclaw", "memory", "search", query, "--max-results", str(n * 3), "--json"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        raw_results = json.loads(result.stdout)
    except Exception as e:
        print(json.dumps({"error": f"Memory search failed: {e}"}))
        return

    if not isinstance(raw_results, list):
        raw_results = raw_results.get("results", [])

    if verbose:
        print(f"🔍 Base search: {len(raw_results)} results", file=sys.stderr)

    # Step 3: Apply gravity re-ranking
    rerank_result = subprocess.run(
        [
            sys.executable,
            "-m",
            "core.nautilus.gravity",
            "rerank",
            "--json",
            json.dumps(raw_results),
        ],
        capture_output=True,
        text=True,
        timeout=30,
    )
    try:
        reranked = json.loads(rerank_result.stdout)
        if isinstance(reranked, list):
            results = reranked
        else:
            results = raw_results
    except BaseException:
        results = raw_results

    if verbose:
        print(f"⚖️ Gravity applied: {len(results)} results re-ranked", file=sys.stderr)

    # Step 4: Context filtering (Doors) unless trapdoor
    if not trapdoor and context_tags:
        import sqlite3
        from .config import get_gravity_db_path

        db = sqlite3.connect(str(get_gravity_db_path()))
        db.row_factory = sqlite3.Row

        filtered = []
        for r in results:
            path = r.get("path", "")
            row = db.execute(
                "SELECT tags, chamber FROM gravity WHERE path = ? LIMIT 1", (path,)
            ).fetchone()

            if row and row["tags"]:
                file_tags = json.loads(row["tags"])
                overlap = len(set(context_tags) & set(file_tags))
                r["context_match"] = overlap / max(len(context_tags), 1) if overlap > 0 else 0.3
            else:
                r["context_match"] = 0.5  # Neutral for untagged

            r["chamber"] = row["chamber"] if row else "unknown"

            # Apply context bonus to score
            if r.get("context_match", 0) > 0:
                r["score"] = r.get("score", 0) * (0.8 + 0.2 * r["context_match"])
                filtered.append(r)

        db.close()
        results = sorted(filtered, key=lambda x: x.get("score", 0), reverse=True)

        if verbose:
            print(f"🚪 Context filtered: {len(results)} results", file=sys.stderr)

    # Step 5: Resolve mirrors for top results
    mirror_info = {}
    for r in results[:n]:
        path = r.get("path", "")
        mirror_result = subprocess.run(
            [sys.executable, "-m", "core.nautilus.mirrors", "resolve", path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        try:
            mir = json.loads(mirror_result.stdout)
            if mir.get("mirrors"):
                mirror_info[path] = mir
        except BaseException:
            pass

    # Truncate and output
    results = results[:n]

    output = {
        "query": query,
        "context": context_tags,
        "mode": "trapdoor" if trapdoor else ("context-filtered" if context_tags else "full"),
        "results": results,
    }

    if mirror_info:
        output["mirrors"] = mirror_info

    print(json.dumps(output, indent=2))


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


def cmd_maintain(args):
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


# === Main ===

COMMANDS = {
    "search": cmd_search,
    "status": cmd_status,
    "maintain": cmd_maintain,
    "migrate": cmd_migrate,
}


def main():
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print("🐚 Nautilus Memory Palace")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        print("\nUsage:")
        print("  emergence nautilus search <query> [--n 5] [--trapdoor] [--verbose]")
        print("  emergence nautilus status")
        print("  emergence nautilus maintain [--register-recent]")
        print("  emergence nautilus migrate [--dry-run] [--verbose]")
        print("\nExamples:")
        print('  emergence nautilus search "project nautilus" --verbose')
        print("  emergence nautilus maintain --register-recent")
        sys.exit(1)

    COMMANDS[sys.argv[1]](sys.argv[2:])


if __name__ == "__main__":
    main()
