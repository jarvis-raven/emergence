#!/usr/bin/env python3
"""
Nautilus Database Migration Script

Merges existing Nautilus databases from legacy locations into the
new centralized state directory while preserving all data.

Usage:
  python3 -m core.nautilus.migrate_db [--dry-run] [--verbose]

Or via emergence CLI:
  emergence nautilus migrate [--dry-run] [--verbose]
"""

import sqlite3
import json
import sys
import shutil
from pathlib import Path
from datetime import datetime, timezone
from .config import get_gravity_db_path, get_legacy_db_paths, get_state_dir


def migrate_database(dry_run=False, verbose=False):
    """
    Migrate existing Nautilus databases to new location.

    Steps:
    1. Find all legacy database locations
    2. Merge data into new centralized database
    3. Preserve original databases as backups
    4. Report statistics
    """
    target_db = get_gravity_db_path()
    legacy_dbs = get_legacy_db_paths()

    if verbose:
        print(f"Target database: {target_db}", file=sys.stderr)
        print(f"Found {len(legacy_dbs)} legacy database(s)", file=sys.stderr)
        for db in legacy_dbs:
            print(f"  - {db}", file=sys.stderr)

    if not legacy_dbs:
        print("No legacy databases found to migrate.", file=sys.stderr)
        return {
            "migrated": False,
            "reason": "No legacy databases found",
            "target_db": str(target_db),
        }

    if dry_run:
        print("DRY RUN - No changes will be made", file=sys.stderr)
        return {
            "dry_run": True,
            "legacy_dbs": [str(db) for db in legacy_dbs],
            "target_db": str(target_db),
            "would_migrate": True,
        }

    # Ensure target directory exists
    target_db.parent.mkdir(parents=True, exist_ok=True)

    # If target already exists, check if we should migrate
    target_exists = target_db.exists()

    if target_exists and verbose:
        print(f"Target database already exists: {target_db}", file=sys.stderr)
        print("Will merge legacy data into existing database", file=sys.stderr)

    # Open or create target database
    target_conn = sqlite3.connect(str(target_db))
    target_conn.row_factory = sqlite3.Row
    target_conn.execute("PRAGMA journal_mode=WAL")

    # Initialize schema (gravity.py's get_db() will handle this)
    from .gravity import get_db

    get_db().close()

    stats = {
        "migrated": True,
        "target_db": str(target_db),
        "legacy_dbs": [],
        "total_records_migrated": 0,
        "total_access_logs_migrated": 0,
        "total_mirrors_migrated": 0,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Migrate each legacy database
    for legacy_db in legacy_dbs:
        if verbose:
            print(f"\nMigrating {legacy_db}...", file=sys.stderr)

        try:
            legacy_conn = sqlite3.connect(str(legacy_db))
            legacy_conn.row_factory = sqlite3.Row

            # Migrate gravity table
            gravity_records = legacy_conn.execute("SELECT * FROM gravity").fetchall()

            migrated_count = 0
            for row in gravity_records:
                # Convert row to dict for easier access
                row_dict = dict(row)

                # Insert or update (preserve newer data)
                target_conn.execute(
                    """
                    INSERT INTO gravity (
                        path, line_start, line_end, access_count, reference_count,
                        explicit_importance, last_accessed_at, last_written_at,
                        created_at, superseded_by, tags, chamber
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(path, line_start, line_end) DO UPDATE SET
                        access_count = MAX(access_count, excluded.access_count),
                        reference_count = MAX(reference_count, excluded.reference_count),
                        explicit_importance = MAX(explicit_importance, excluded.explicit_importance),
                        last_accessed_at = CASE
                            WHEN excluded.last_accessed_at > last_accessed_at
                            THEN excluded.last_accessed_at
                            ELSE last_accessed_at
                        END,
                        last_written_at = CASE
                            WHEN excluded.last_written_at > last_written_at
                            THEN excluded.last_written_at
                            ELSE last_written_at
                        END,
                        superseded_by = COALESCE(excluded.superseded_by, superseded_by),
                        tags = COALESCE(excluded.tags, tags),
                        chamber = COALESCE(excluded.chamber, chamber)
                """,
                    (
                        row_dict["path"],
                        row_dict["line_start"],
                        row_dict["line_end"],
                        row_dict["access_count"] or 0,
                        row_dict["reference_count"] or 0,
                        row_dict["explicit_importance"] or 0.0,
                        row_dict["last_accessed_at"],
                        row_dict["last_written_at"],
                        row_dict["created_at"],
                        row_dict.get("superseded_by"),
                        row_dict.get("tags", "[]"),
                        row_dict.get("chamber", "unknown"),
                    ),
                )
                migrated_count += 1

            if verbose:
                print(f"  Migrated {migrated_count} gravity records", file=sys.stderr)

            # Migrate access_log
            access_logs = legacy_conn.execute("SELECT * FROM access_log").fetchall()
            access_count = 0
            for log in access_logs:
                log_dict = dict(log)
                target_conn.execute(
                    """
                    INSERT INTO access_log (path, line_start, line_end, accessed_at, query, score)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        log_dict["path"],
                        log_dict.get("line_start", 0),
                        log_dict.get("line_end", 0),
                        log_dict["accessed_at"],
                        log_dict.get("query"),
                        log_dict.get("score"),
                    ),
                )
                access_count += 1

            if verbose:
                print(f"  Migrated {access_count} access log entries", file=sys.stderr)

            # Migrate mirrors table if it exists
            mirrors_count = 0
            try:
                mirrors = legacy_conn.execute("SELECT * FROM mirrors").fetchall()
                for mirror in mirrors:
                    mirror_dict = dict(mirror)
                    target_conn.execute(
                        """
                        INSERT OR IGNORE INTO mirrors (event_key, granularity, path, line_start, line_end, created_at)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """,
                        (
                            mirror_dict["event_key"],
                            mirror_dict["granularity"],
                            mirror_dict["path"],
                            mirror_dict.get("line_start", 0),
                            mirror_dict.get("line_end", 0),
                            mirror_dict["created_at"],
                        ),
                    )
                    mirrors_count += 1

                if verbose:
                    print(f"  Migrated {mirrors_count} mirror records", file=sys.stderr)
            except sqlite3.OperationalError:
                # Mirrors table doesn't exist in legacy DB
                pass

            legacy_conn.close()

            # Record migration stats
            stats["legacy_dbs"].append(
                {
                    "path": str(legacy_db),
                    "gravity_records": migrated_count,
                    "access_logs": access_count,
                    "mirrors": mirrors_count,
                }
            )

            stats["total_records_migrated"] += migrated_count
            stats["total_access_logs_migrated"] += access_count
            stats["total_mirrors_migrated"] += mirrors_count

            # Backup the legacy database
            backup_path = legacy_db.parent / f"{legacy_db.stem}.pre-migration-backup.db"
            if not backup_path.exists():
                shutil.copy2(legacy_db, backup_path)
                if verbose:
                    print(f"  Backed up to: {backup_path}", file=sys.stderr)

        except Exception as e:
            print(f"  ERROR migrating {legacy_db}: {e}", file=sys.stderr)
            stats["errors"] = stats.get("errors", [])
            stats["errors"].append({"db": str(legacy_db), "error": str(e)})

    target_conn.commit()
    target_conn.close()

    if verbose:
        print(f"\n✅ Migration complete!", file=sys.stderr)
        print(f"Total records migrated: {stats['total_records_migrated']}", file=sys.stderr)
        print(f"Total access logs migrated: {stats['total_access_logs_migrated']}", file=sys.stderr)
        print(f"Total mirrors migrated: {stats['total_mirrors_migrated']}", file=sys.stderr)

    return stats


def main():
    dry_run = "--dry-run" in sys.argv
    verbose = "--verbose" in sys.argv or "-v" in sys.argv

    result = migrate_database(dry_run=dry_run, verbose=verbose)
    print(json.dumps(result, indent=2))

    if result.get("migrated") or result.get("would_migrate"):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
