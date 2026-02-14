"""
Nautilus Session Hooks - Auto-track memory accesses

Integrates with OpenClaw session lifecycle to automatically register
file reads and writes in the Nautilus gravity database.

Usage:
    # Register a file read
    record_access("memory/daily/2026-02-14.md", access_type="read")
    
    # Register a file write
    record_access("memory/MEMORY.md", access_type="write")
    
    # Batch register multiple files
    batch_record_accesses(["file1.md", "file2.md"], access_type="read")
"""

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Literal, Optional
import asyncio
import logging

from .config import get_db_path, get_workspace
from . import gravity

# Configure logging
logger = logging.getLogger("nautilus.session_hooks")


def record_access(
    file_path: str,
    access_type: Literal["read", "write"] = "read",
    session_context: Optional[str] = None,
    async_mode: bool = True
) -> bool:
    """Record a file access in the gravity database.
    
    Args:
        file_path: Path to file (relative to workspace or absolute)
        access_type: Type of access ("read" or "write")
        session_context: Optional session identifier/context
        async_mode: If True, run asynchronously (non-blocking)
        
    Returns:
        True if recorded successfully, False otherwise
    """
    try:
        workspace = get_workspace()
        
        # Normalize path to be relative to workspace
        path = Path(file_path)
        if path.is_absolute():
            try:
                path = path.relative_to(workspace)
            except ValueError:
                # Path not under workspace, skip
                logger.debug(f"Skipping {file_path}: not under workspace")
                return False
        
        # Convert to string for DB
        rel_path = str(path)
        
        # Skip non-markdown files for now (could expand later)
        if not rel_path.endswith('.md'):
            return False
        
        # Skip if file doesn't exist
        full_path = workspace / rel_path
        if not full_path.exists():
            logger.debug(f"Skipping {rel_path}: file doesn't exist")
            return False
        
        if async_mode:
            # Fire and forget in background
            try:
                asyncio.create_task(_record_access_async(rel_path, access_type, session_context))
            except RuntimeError:
                # No event loop, fall back to sync
                _record_access_sync(rel_path, access_type, session_context)
        else:
            _record_access_sync(rel_path, access_type, session_context)
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to record access for {file_path}: {e}")
        return False


def _record_access_sync(rel_path: str, access_type: str, session_context: Optional[str]) -> None:
    """Synchronous implementation of record access."""
    try:
        db_path = get_db_path()
        db = sqlite3.connect(str(db_path))
        db.row_factory = sqlite3.Row
        
        now = datetime.now(timezone.utc).isoformat()
        
        # Ensure file is registered in gravity table
        row = db.execute("SELECT * FROM gravity WHERE path = ?", (rel_path,)).fetchone()
        
        if not row:
            # Register new file
            workspace = get_workspace()
            full_path = workspace / rel_path
            
            chamber = "atrium"  # New files start in atrium
            tags = "[]"
            
            db.execute(
                """INSERT INTO gravity 
                   (path, chamber, access_count, reference_count, explicit_importance,
                    last_accessed_at, last_written_at, superseded_by, tags, created_at)
                   VALUES (?, ?, 0, 0, 0.0, ?, ?, NULL, ?, ?)""",
                (rel_path, chamber, now, now, tags, now)
            )
        
        # Update access tracking
        if access_type == "write":
            db.execute(
                """UPDATE gravity 
                   SET last_written_at = ?, access_count = access_count + 1
                   WHERE path = ?""",
                (now, rel_path)
            )
        else:  # read
            db.execute(
                """UPDATE gravity 
                   SET last_accessed_at = ?, access_count = access_count + 1
                   WHERE path = ?""",
                (now, rel_path)
            )
        
        # Log access
        context_json = f'{{"session": "{session_context}"}}' if session_context else "{}"
        db.execute(
            """INSERT INTO access_log (path, accessed_at, context)
               VALUES (?, ?, ?)""",
            (rel_path, now, context_json)
        )
        
        db.commit()
        db.close()
        
        logger.debug(f"Recorded {access_type} access: {rel_path}")
        
    except Exception as e:
        logger.error(f"Sync record access failed for {rel_path}: {e}")


async def _record_access_async(rel_path: str, access_type: str, session_context: Optional[str]) -> None:
    """Asynchronous implementation of record access."""
    # Run the sync version in a thread pool to avoid blocking
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _record_access_sync, rel_path, access_type, session_context)


def batch_record_accesses(
    file_paths: List[str],
    access_type: Literal["read", "write"] = "read",
    session_context: Optional[str] = None
) -> int:
    """Record multiple file accesses in batch.
    
    Args:
        file_paths: List of file paths
        access_type: Type of access ("read" or "write")
        session_context: Optional session identifier
        
    Returns:
        Number of files successfully recorded
    """
    success_count = 0
    
    for file_path in file_paths:
        if record_access(file_path, access_type, session_context, async_mode=False):
            success_count += 1
    
    return success_count


def track_session_files(session_label: Optional[str] = None) -> dict:
    """Track all markdown files in workspace and record as accessed.
    
    Useful for initial registration or periodic sweeps.
    
    Args:
        session_label: Optional session identifier for context
        
    Returns:
        Dictionary with statistics about what was tracked
    """
    workspace = get_workspace()
    memory_dir = workspace / "memory"
    
    if not memory_dir.exists():
        return {"error": "memory directory not found", "tracked": 0}
    
    # Find all .md files
    md_files = list(memory_dir.rglob("*.md"))
    
    # Also check identity files
    identity_files = [
        "MEMORY.md",
        "SELF.md",
        "USER.md",
        "SOUL.md",
        "AGENTS.md",
        "TOOLS.md",
        "DRIVES.md",
        "ASPIRATIONS.md",
    ]
    
    for id_file in identity_files:
        id_path = workspace / id_file
        if id_path.exists():
            md_files.append(id_path)
    
    # Convert to relative paths
    rel_paths = []
    for f in md_files:
        try:
            rel_paths.append(str(f.relative_to(workspace)))
        except ValueError:
            continue
    
    # Batch record
    tracked = batch_record_accesses(rel_paths, access_type="read", session_context=session_label)
    
    return {
        "total_files": len(md_files),
        "tracked": tracked,
        "session_label": session_label or "unlabeled",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def register_recent_writes(hours: int = 24) -> dict:
    """Find and register files modified in the last N hours.
    
    Args:
        hours: Look back this many hours
        
    Returns:
        Dictionary with registration statistics
    """
    import time
    
    workspace = get_workspace()
    memory_dir = workspace / "memory"
    
    if not memory_dir.exists():
        return {"error": "memory directory not found", "registered": 0}
    
    now = time.time()
    cutoff = now - (hours * 3600)
    
    recent_files = []
    for md_file in memory_dir.rglob("*.md"):
        try:
            mtime = md_file.stat().st_mtime
            if mtime >= cutoff:
                recent_files.append(str(md_file.relative_to(workspace)))
        except (OSError, ValueError):
            continue
    
    # Also check identity files
    identity_files = [
        "MEMORY.md", "SELF.md", "USER.md", "SOUL.md",
        "AGENTS.md", "TOOLS.md", "DRIVES.md", "ASPIRATIONS.md",
    ]
    
    for id_file in identity_files:
        id_path = workspace / id_file
        if id_path.exists():
            try:
                mtime = id_path.stat().st_mtime
                if mtime >= cutoff:
                    recent_files.append(id_file)
            except OSError:
                continue
    
    # Batch register as writes
    registered = batch_record_accesses(recent_files, access_type="write")
    
    return {
        "hours": hours,
        "recent_files": len(recent_files),
        "registered": registered,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


# OpenClaw integration hooks (to be called by OpenClaw when available)

def on_session_start(session_id: str, session_type: str = "unknown") -> None:
    """Hook called when a session starts.
    
    Args:
        session_id: Unique session identifier
        session_type: Type of session (e.g., "agent", "cli", "heartbeat")
    """
    logger.info(f"Session started: {session_id} (type: {session_type})")
    # Could initialize session-specific tracking here if needed


def on_session_end(session_id: str, files_accessed: Optional[List[str]] = None) -> None:
    """Hook called when a session ends.
    
    Args:
        session_id: Unique session identifier
        files_accessed: Optional list of files accessed during session
    """
    logger.info(f"Session ended: {session_id}")
    
    if files_accessed:
        # Record all files accessed during this session
        batch_record_accesses(files_accessed, access_type="read", session_context=session_id)


def on_file_read(file_path: str, session_id: Optional[str] = None) -> None:
    """Hook called when a file is read.
    
    Args:
        file_path: Path to file that was read
        session_id: Optional session identifier
    """
    record_access(file_path, access_type="read", session_context=session_id, async_mode=True)


def on_file_write(file_path: str, session_id: Optional[str] = None) -> None:
    """Hook called when a file is written.
    
    Args:
        file_path: Path to file that was written
        session_id: Optional session identifier
    """
    record_access(file_path, access_type="write", session_context=session_id, async_mode=True)
