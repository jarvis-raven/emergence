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
  python -m core.nautilus gravity record-access <path> [--lines START:END]
  python -m core.nautilus gravity record-write <path>
  python -m core.nautilus gravity boost <path> [--amount N]
  python -m core.nautilus gravity decay
  python -m core.nautilus gravity score <path> [--lines START:END]
  python -m core.nautilus gravity top [--n 10]
  python -m core.nautilus gravity stats
  python -m core.nautilus gravity rerank --json <results_json>
"""

import sqlite3
import json
import sys
import os
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List, Tuple

from . import config
from .logging_config import get_logger
from .db_utils import safe_connect, with_retry, commit_with_retry, DatabaseError

# Setup logging
logger = get_logger("gravity")

# Configuration
DECAY_RATE = 0.05  # Mass lost per day since last write
RECENCY_HALF_LIFE = 14  # Days for recency factor to halve
AUTHORITY_BOOST = 0.3  # Bonus multiplier for recently-written chunks
MASS_CAP = 100.0  # Prevent runaway accumulation


@with_retry
def _add_column_if_missing(db: sqlite3.Connection, table: str, column: str, col_type: str) -> None:
    """
    Add a column to a table if it doesn't exist.
    
    Args:
        db: Database connection
        table: Table name
        column: Column name to add
        col_type: SQL type of the column
        
    Raises:
        DatabaseError: If column cannot be added
    """
    try:
        db.execute(f"SELECT {column} FROM {table} LIMIT 1")
        logger.debug(f"Column {column} already exists in {table}")
    except sqlite3.OperationalError:
        # Column doesn't exist, add it
        try:
            db.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}")
            commit_with_retry(db)
            logger.info(f"Added column {column} to {table}")
        except DatabaseError:
            raise
        except sqlite3.Error as e:
            logger.error(f"Failed to add column {column} to {table}: {e}")
            raise DatabaseError(f"Cannot add column {column} to {table}: {e}") from e


def get_db_path() -> Path:
    """
    Get the gravity database path (with migration support).
    
    Returns:
        Path object for the gravity database.
    """
    config.migrate_legacy_db()  # Auto-migrate if needed
    return config.get_gravity_db_path()


def get_db() -> sqlite3.Connection:
    """
    Get or create the gravity database.
    
    Returns:
        SQLite database connection with schema initialized.
        
    Raises:
        DatabaseError: If database cannot be created or accessed.
    """
    db_path = get_db_path()
    
    try:
        db_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        logger.error(f"Could not create database directory {db_path.parent}: {e}")
        raise DatabaseError(
            f"Cannot create database directory: {db_path.parent}\n"
            f"Check permissions and ensure parent directories exist."
        ) from e
    
    try:
        db = safe_connect(db_path, timeout=10.0)
        logger.debug(f"Connected to gravity database: {db_path}")
        
        # Main gravity table
        db.execute("""
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
                context_tags TEXT DEFAULT '[]',
                chamber TEXT DEFAULT 'atrium',
                promoted_at TEXT,
                source_chunk TEXT,
                PRIMARY KEY (path, line_start, line_end)
            )
        """)
        
        # Add columns that might be missing from legacy databases
        _add_column_if_missing(db, "gravity", "tags", "TEXT DEFAULT '[]'")
        _add_column_if_missing(db, "gravity", "context_tags", "TEXT DEFAULT '[]'")
        _add_column_if_missing(db, "gravity", "chamber", "TEXT DEFAULT 'atrium'")
        _add_column_if_missing(db, "gravity", "promoted_at", "TEXT")
        _add_column_if_missing(db, "gravity", "source_chunk", "TEXT")
        
        # Access log table
        db.execute("""
            CREATE TABLE IF NOT EXISTS access_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL,
                line_start INTEGER DEFAULT 0,
                line_end INTEGER DEFAULT 0,
                accessed_at TEXT DEFAULT (datetime('now')),
                query TEXT DEFAULT NULL,
                score REAL DEFAULT NULL
            )
        """)
        
        # Mirrors table (for phase 4)
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
        
        # Indexes
        db.execute("CREATE INDEX IF NOT EXISTS idx_gravity_path ON gravity(path)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_gravity_chamber ON gravity(chamber)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_access_log_path ON access_log(path)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_mirrors_event ON mirrors(event_key)")
        db.execute("CREATE INDEX IF NOT EXISTS idx_mirrors_path ON mirrors(path)")
        
        commit_with_retry(db)
        logger.debug("Database schema initialized successfully")
        return db
        
    except DatabaseError:
        # Already logged and formatted
        raise
    except sqlite3.Error as e:
        logger.error(f"Database schema initialization error: {e}")
        raise DatabaseError(f"Failed to initialize database schema: {e}") from e


def now_iso() -> str:
    """
    Get current time in ISO format.
    
    Returns:
        ISO-formatted timestamp string.
    """
    return datetime.now(timezone.utc).isoformat()


def days_since(iso_str: Optional[str]) -> float:
    """
    Calculate days since an ISO timestamp.
    
    Args:
        iso_str: ISO-formatted timestamp string, or None
        
    Returns:
        Number of days since the timestamp (999 if None or invalid).
    """
    if not iso_str:
        return 999.0  # Never written/accessed = very old
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        delta = datetime.now(timezone.utc) - dt
        return max(0.0, delta.total_seconds() / 86400)
    except (ValueError, TypeError) as e:
        logger.warning(f"Invalid timestamp {iso_str}: {e}")
        return 999.0


def compute_effective_mass(row: sqlite3.Row) -> float:
    """
    Compute effective mass with stale-authority mitigations.
    
    Formula:
        base_mass = (access_count × 0.3) + (reference_count × 0.5) + explicit_importance
        recency_factor = 1 / (1 + days_since_last_write × DECAY_RATE)
        authority_boost = AUTHORITY_BOOST if written in last 48h else 0
        effective_mass = min(base_mass × recency_factor + authority_boost, MASS_CAP)
    
    Args:
        row: SQLite row with gravity data
        
    Returns:
        Computed effective mass score.
    """
    access_count = row['access_count'] or 0
    reference_count = row['reference_count'] or 0
    explicit_importance = row['explicit_importance'] or 0.0
    
    base_mass = (access_count * 0.3) + (reference_count * 0.5) + explicit_importance
    
    # Recency factor based on write date (not access date)
    days_written = days_since(row['last_written_at'])
    recency_factor = 1.0 / (1.0 + days_written * DECAY_RATE)
    
    # Authority boost for recently-written content (last 48h)
    authority = AUTHORITY_BOOST if days_written < 2.0 else 0.0
    
    effective_mass = min(base_mass * recency_factor + authority, MASS_CAP)
    logger.debug(f"Computed mass for {row['path']}: {effective_mass:.3f} "
                f"(base={base_mass:.1f}, recency={recency_factor:.3f}, authority={authority:.3f})")
    return effective_mass


def gravity_score_modifier(effective_mass: float) -> float:
    """
    Convert effective mass to a score multiplier.
    
    Returns a value >= 1.0 that multiplies the base similarity score.
    
    - At mass 0: modifier = 1.0 (no change)
    - At mass 5: modifier ≈ 1.18
    - At mass 20: modifier ≈ 1.30
    - At mass 100: modifier ≈ 1.46
    
    Args:
        effective_mass: The computed effective mass value
        
    Returns:
        Score multiplier (>= 1.0).
    """
    modifier = 1.0 + 0.1 * math.log(1.0 + effective_mass)
    logger.debug(f"Gravity modifier for mass {effective_mass:.3f}: {modifier:.3f}")
    return modifier


# === Commands ===

def cmd_record_access(args: List[str]) -> Dict[str, Any]:
    """
    Record that a memory chunk was accessed (retrieved by search).
    
    Args:
        args: Command arguments [path, --lines START:END, --query Q, --score S]
        
    Returns:
        Dictionary with access information.
    """
    if not args:
        logger.error("No path provided to record-access")
        print("Usage: gravity record-access <path> [--lines START:END] [--query Q] [--score S]", file=sys.stderr)
        sys.exit(1)
    
    path = args[0]
    line_start, line_end = 0, 0
    query, score = None, None
    
    i = 1
    while i < len(args):
        if args[i] == '--lines' and i + 1 < len(args):
            try:
                parts = args[i+1].split(':')
                line_start = int(parts[0])
                line_end = int(parts[1]) if len(parts) > 1 else line_start
            except (ValueError, IndexError) as e:
                logger.warning(f"Invalid line range {args[i+1]}: {e}")
            i += 2
        elif args[i] == '--query' and i + 1 < len(args):
            query = args[i+1]
            i += 2
        elif args[i] == '--score' and i + 1 < len(args):
            try:
                score = float(args[i+1])
            except ValueError as e:
                logger.warning(f"Invalid score {args[i+1]}: {e}")
            i += 2
        else:
            i += 1
    
    try:
        db = get_db()
        now = now_iso()
        
        # Upsert gravity record
        db.execute("""
            INSERT INTO gravity (path, line_start, line_end, access_count, last_accessed_at, last_written_at)
            VALUES (?, ?, ?, 1, ?, ?)
            ON CONFLICT(path, line_start, line_end) DO UPDATE SET
                access_count = access_count + 1,
                last_accessed_at = ?
        """, (path, line_start, line_end, now, now, now))
        
        # Log access
        db.execute("""
            INSERT INTO access_log (path, line_start, line_end, query, score)
            VALUES (?, ?, ?, ?, ?)
        """, (path, line_start, line_end, query, score))
        
        commit_with_retry(db)
        
        row = db.execute("""
            SELECT * FROM gravity WHERE path = ? AND line_start = ? AND line_end = ?
        """, (path, line_start, line_end)).fetchone()
        
        if row:
            mass = compute_effective_mass(row)
            result = {
                "path": path,
                "lines": f"{line_start}:{line_end}",
                "access_count": row['access_count'],
                "effective_mass": round(mass, 3),
                "modifier": round(gravity_score_modifier(mass), 3)
            }
            logger.info(f"Recorded access to {path}:{line_start}:{line_end} (count={row['access_count']})")
        else:
            logger.warning(f"Failed to find row after insert for {path}")
            result = {"error": "Row not found after insert"}
        
        print(json.dumps(result))
        db.close()
        return result
        
    except sqlite3.Error as e:
        logger.error(f"Database error in record_access: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_record_write(args: List[str]) -> Dict[str, Any]:
    """
    Record that a memory file was written/updated.
    
    Args:
        args: Command arguments [path]
        
    Returns:
        Dictionary with write information.
    """
    if not args:
        logger.error("No path provided to record-write")
        print("Usage: gravity record-write <path>", file=sys.stderr)
        sys.exit(1)
    
    path = args[0]
    
    try:
        db = get_db()
        now = now_iso()
        
        # Update all chunks for this path
        updated = db.execute("""
            UPDATE gravity SET last_written_at = ? WHERE path = ?
        """, (now, path)).rowcount
        
        # If no existing records, create one for the whole file
        if updated == 0:
            db.execute("""
                INSERT INTO gravity (path, line_start, line_end, last_written_at)
                VALUES (?, 0, 0, ?)
            """, (path, now))
            updated = 1
        
        commit_with_retry(db)
        result = {"path": path, "updated_chunks": updated, "written_at": now}
        logger.info(f"Recorded write to {path} ({updated} chunks updated)")
        print(json.dumps(result))
        db.close()
        return result
        
    except DatabaseError as e:
        logger.error(f"Database error in record_write: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        logger.error(f"Unexpected database error in record_write: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_boost(args: List[str]) -> Dict[str, Any]:
    """
    Explicitly boost a memory's importance.
    
    Args:
        args: Command arguments [path, --amount N, --lines START:END]
        
    Returns:
        Dictionary with boost information.
    """
    if not args:
        logger.error("No path provided to boost")
        print("Usage: gravity boost <path> [--amount N] [--lines START:END]", file=sys.stderr)
        sys.exit(1)
    
    path = args[0]
    amount = 2.0
    line_start, line_end = 0, 0
    
    i = 1
    while i < len(args):
        if args[i] == '--amount' and i + 1 < len(args):
            try:
                amount = float(args[i+1])
            except ValueError as e:
                logger.warning(f"Invalid amount {args[i+1]}: {e}")
            i += 2
        elif args[i] == '--lines' and i + 1 < len(args):
            try:
                parts = args[i+1].split(':')
                line_start = int(parts[0])
                line_end = int(parts[1]) if len(parts) > 1 else line_start
            except (ValueError, IndexError) as e:
                logger.warning(f"Invalid line range {args[i+1]}: {e}")
            i += 2
        else:
            i += 1
    
    try:
        db = get_db()
        now = now_iso()
        
        db.execute("""
            INSERT INTO gravity (path, line_start, line_end, explicit_importance, last_written_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(path, line_start, line_end) DO UPDATE SET
                explicit_importance = explicit_importance + ?,
                last_written_at = ?
        """, (path, line_start, line_end, amount, now, amount, now))
        
        commit_with_retry(db)
        
        row = db.execute("""
            SELECT * FROM gravity WHERE path = ? AND line_start = ? AND line_end = ?
        """, (path, line_start, line_end)).fetchone()
        
        if row:
            mass = compute_effective_mass(row)
            result = {
                "path": path,
                "explicit_importance": row['explicit_importance'],
                "effective_mass": round(mass, 3),
                "modifier": round(gravity_score_modifier(mass), 3)
            }
            logger.info(f"Boosted {path}:{line_start}:{line_end} by {amount} (total importance={row['explicit_importance']})")
        else:
            result = {"error": "Row not found after boost"}
        
        print(json.dumps(result))
        db.close()
        return result
        
    except sqlite3.Error as e:
        logger.error(f"Database error in boost: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_decay(args: List[str]) -> Dict[str, Any]:
    """
    Apply nightly decay — reduce gravity on stale memories.
    
    Args:
        args: Command arguments (currently unused)
        
    Returns:
        Dictionary with decay statistics.
    """
    try:
        db = get_db()
        
        rows = db.execute("SELECT *, rowid FROM gravity").fetchall()
        decayed = 0
        
        logger.info(f"Starting decay on {len(rows)} records")
        
        for row in rows:
            days_written = days_since(row['last_written_at'])
            days_accessed = days_since(row['last_accessed_at'])
            
            # If not accessed in 30+ days AND not written in 14+ days,
            # reduce explicit importance by 10%
            if days_accessed > 30 and days_written > 14 and (row['explicit_importance'] or 0) > 0.1:
                new_importance = max(0, row['explicit_importance'] * 0.9)
                db.execute("""
                    UPDATE gravity SET explicit_importance = ?
                    WHERE path = ? AND line_start = ? AND line_end = ?
                """, (new_importance, row['path'], row['line_start'], row['line_end']))
                decayed += 1
        
        commit_with_retry(db)
        
        total = len(rows)
        result = {
            "total_records": total,
            "decayed": decayed,
            "timestamp": now_iso()
        }
        logger.info(f"Decay complete: {decayed}/{total} records decayed")
        print(json.dumps(result))
        db.close()
        
        return result
        
    except DatabaseError as e:
        logger.error(f"Database error in decay: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        logger.error(f"Unexpected database error in decay: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_score(args: List[str]) -> Dict[str, Any]:
    """
    Get the gravity score for a specific path.
    
    Args:
        args: Command arguments [path, --lines START:END]
        
    Returns:
        Dictionary with score information.
    """
    if not args:
        logger.error("No path provided to score")
        print("Usage: gravity score <path> [--lines START:END]", file=sys.stderr)
        sys.exit(1)
    
    path = args[0]
    line_start, line_end = 0, 0
    
    i = 1
    while i < len(args):
        if args[i] == '--lines' and i + 1 < len(args):
            try:
                parts = args[i+1].split(':')
                line_start = int(parts[0])
                line_end = int(parts[1]) if len(parts) > 1 else line_start
            except (ValueError, IndexError) as e:
                logger.warning(f"Invalid line range {args[i+1]}: {e}")
            i += 2
        else:
            i += 1
    
    try:
        db = get_db()
        
        # Try exact match first, then path-level
        row = db.execute("""
            SELECT * FROM gravity WHERE path = ? AND line_start = ? AND line_end = ?
        """, (path, line_start, line_end)).fetchone()
        
        if not row:
            # Try any chunk from this file
            row = db.execute("SELECT * FROM gravity WHERE path = ? LIMIT 1", (path,)).fetchone()
        
        if not row:
            result = {"path": path, "effective_mass": 0, "modifier": 1.0, "exists": False}
            logger.debug(f"No gravity record found for {path}")
        else:
            mass = compute_effective_mass(row)
            result = {
                "path": row['path'],
                "lines": f"{row['line_start']}:{row['line_end']}",
                "access_count": row['access_count'],
                "reference_count": row['reference_count'],
                "explicit_importance": row['explicit_importance'],
                "days_since_write": round(days_since(row['last_written_at']), 1),
                "days_since_access": round(days_since(row['last_accessed_at']), 1),
                "effective_mass": round(mass, 3),
                "modifier": round(gravity_score_modifier(mass), 3),
                "superseded_by": row['superseded_by'],
                "exists": True
            }
            logger.debug(f"Retrieved score for {path}: mass={mass:.3f}")
        
        print(json.dumps(result))
        db.close()
        return result
        
    except sqlite3.Error as e:
        logger.error(f"Database error in score: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_top(args: List[str]) -> List[Dict[str, Any]]:
    """
    Show highest-gravity memories.
    
    Args:
        args: Command arguments [--n N]
        
    Returns:
        List of top-ranked memory chunks.
    """
    n = 10
    if args and args[0] == '--n' and len(args) > 1:
        try:
            n = int(args[1])
        except ValueError as e:
            logger.warning(f"Invalid n value {args[1]}: {e}")
    
    try:
        db = get_db()
        rows = db.execute("SELECT * FROM gravity ORDER BY access_count DESC").fetchall()
        
        results = []
        for row in rows:
            mass = compute_effective_mass(row)
            results.append({
                "path": row['path'],
                "lines": f"{row['line_start']}:{row['line_end']}",
                "access_count": row['access_count'],
                "explicit_importance": row['explicit_importance'],
                "effective_mass": round(mass, 3),
                "modifier": round(gravity_score_modifier(mass), 3),
                "days_since_write": round(days_since(row['last_written_at']), 1),
                "superseded_by": row['superseded_by']
            })
        
        # Sort by effective mass
        results.sort(key=lambda x: x['effective_mass'], reverse=True)
        results = results[:n]
        
        logger.info(f"Retrieved top {len(results)} gravity entries")
        print(json.dumps(results, indent=2))
        db.close()
        return results
        
    except sqlite3.Error as e:
        logger.error(f"Database error in top: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_rerank(args: List[str]) -> List[Dict[str, Any]]:
    """
    Re-rank memory_search results using gravity scores.
    
    Expects JSON array of results with {path, startLine, endLine, score, snippet}.
    Outputs same array with adjusted scores and gravity metadata.
    
    Args:
        args: Command arguments [--json <json_string>]
        
    Returns:
        Re-ranked list of results.
    """
    json_str = None
    i = 0
    while i < len(args):
        if args[i] == '--json' and i + 1 < len(args):
            json_str = args[i+1]
            i += 2
        else:
            i += 1
    
    if not json_str:
        # Try stdin
        if not sys.stdin.isatty():
            json_str = sys.stdin.read()
        else:
            logger.error("No JSON input provided to rerank")
            print("Usage: gravity rerank --json '<results>' or pipe JSON via stdin", file=sys.stderr)
            sys.exit(1)
    
    try:
        results = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON input: {e}")
        print(f"Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)
    
    try:
        db = get_db()
        now = now_iso()
        
        reranked = []
        for r in results:
            path = r.get('path', '')
            start = r.get('startLine', 0)
            end = r.get('endLine', 0)
            base_score = r.get('score', 0)
            
            # Look up gravity
            row = db.execute("""
                SELECT * FROM gravity WHERE path = ? AND line_start = ? AND line_end = ?
            """, (path, start, end)).fetchone()
            
            if not row:
                # Try file-level match
                row = db.execute("SELECT * FROM gravity WHERE path = ? LIMIT 1", (path,)).fetchone()
            
            if row:
                mass = compute_effective_mass(row)
                modifier = gravity_score_modifier(mass)
                is_superseded = row['superseded_by'] is not None
                
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
            entry['original_score'] = base_score
            entry['score'] = round(adjusted_score, 4)
            entry['gravity'] = {
                "effective_mass": round(mass, 3),
                "modifier": round(modifier, 3),
                "superseded": is_superseded
            }
            reranked.append(entry)
            
            # Record access
            try:
                db.execute("""
                    INSERT INTO gravity (path, line_start, line_end, access_count, last_accessed_at)
                    VALUES (?, ?, ?, 1, ?)
                    ON CONFLICT(path, line_start, line_end) DO UPDATE SET
                        access_count = access_count + 1,
                        last_accessed_at = ?
                """, (path, start, end, now, now))
            except sqlite3.Error as e:
                logger.warning(f"Failed to record access for {path}: {e}")
        
        commit_with_retry(db)
        db.close()
        
        # Sort by adjusted score
        reranked.sort(key=lambda x: x['score'], reverse=True)
        logger.info(f"Re-ranked {len(reranked)} results")
        print(json.dumps(reranked, indent=2))
        return reranked
        
    except DatabaseError as e:
        logger.error(f"Database error in rerank: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)
    except sqlite3.Error as e:
        logger.error(f"Unexpected database error in rerank: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_stats(args: List[str]) -> Dict[str, Any]:
    """
    Show database statistics.
    
    Args:
        args: Command arguments (currently unused)
        
    Returns:
        Dictionary with database statistics.
    """
    try:
        db = get_db()
        
        total = db.execute("SELECT COUNT(*) FROM gravity").fetchone()[0]
        total_accesses = db.execute("SELECT COUNT(*) FROM access_log").fetchone()[0]
        superseded = db.execute("SELECT COUNT(*) FROM gravity WHERE superseded_by IS NOT NULL").fetchone()[0]
        
        # Top 5 most accessed
        top = db.execute("""
            SELECT path, line_start, line_end, access_count, explicit_importance
            FROM gravity ORDER BY access_count DESC LIMIT 5
        """).fetchall()
        
        # Recent accesses
        recent = db.execute("""
            SELECT path, query, score, accessed_at
            FROM access_log ORDER BY id DESC LIMIT 5
        """).fetchall()
        
        db_path = config.get_gravity_db_path()
        db_size = db_path.stat().st_size if db_path.exists() else 0
        
        result = {
            "total_chunks": total,
            "total_accesses": total_accesses,
            "superseded_chunks": superseded,
            "db_path": str(db_path),
            "db_size_bytes": db_size,
            "top_accessed": [dict(r) for r in top],
            "recent_accesses": [dict(r) for r in recent]
        }
        
        logger.info(f"Database stats: {total} chunks, {total_accesses} total accesses")
        print(json.dumps(result, indent=2, default=str))
        db.close()
        return result
        
    except sqlite3.Error as e:
        logger.error(f"Database error in stats: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


def cmd_supersede(args: List[str]) -> Dict[str, Any]:
    """
    Mark a chunk as superseded by a newer one.
    
    Args:
        args: Command arguments [old_path, new_path]
        
    Returns:
        Dictionary with supersession information.
    """
    if len(args) < 2:
        logger.error("Insufficient arguments for supersede")
        print("Usage: gravity supersede <old_path> <new_path> [--lines OLD_START:END NEW_START:END]", file=sys.stderr)
        sys.exit(1)
    
    old_path = args[0]
    new_path = args[1]
    
    try:
        db = get_db()
        updated = db.execute("""
            UPDATE gravity SET superseded_by = ? WHERE path = ?
        """, (new_path, old_path)).rowcount
        
        db.commit()
        result = {"old_path": old_path, "new_path": new_path, "updated": updated}
        logger.info(f"Marked {old_path} as superseded by {new_path} ({updated} records)")
        print(json.dumps(result))
        db.close()
        return result
        
    except sqlite3.Error as e:
        logger.error(f"Database error in supersede: {e}")
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)


# === Main ===

COMMANDS = {
    'record-access': cmd_record_access,
    'record-write': cmd_record_write,
    'boost': cmd_boost,
    'decay': cmd_decay,
    'score': cmd_score,
    'top': cmd_top,
    'rerank': cmd_rerank,
    'stats': cmd_stats,
    'supersede': cmd_supersede,
}


def main() -> None:
    """Main entry point for gravity command."""
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(f"Usage: python -m core.nautilus gravity <command> [args]")
        print(f"Commands: {', '.join(COMMANDS.keys())}")
        sys.exit(1)
    
    cmd = sys.argv[1]
    logger.info(f"Executing gravity command: {cmd}")
    COMMANDS[cmd](sys.argv[2:])


if __name__ == '__main__':
    # Logging already configured by logging_config module
    main()
