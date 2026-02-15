"""
🐚 Nautilus — Memory Palace Architecture for Emergence v0.4.0

A four-phase memory system:
  Phase 1: Gravity — Importance-weighted scoring
  Phase 2: Chambers — Temporal layers (atrium/corridor/vault)  
  Phase 3: Doors — Context-aware pre-filtering
  Phase 4: Mirrors — Multi-granularity indexing

Usage:
    from core.nautilus import search, get_status, run_maintain
    
    # Full pipeline search
    results = search("project details", n=5)
    
    # System status
    info = get_status()
    
    # Run maintenance
    result = run_maintain()

Configuration:
    ~/.openclaw/emergence.json:
    {
        "nautilus": {
            "enabled": true,
            "gravity_db": "~/.openclaw/state/nautilus/gravity.db",
            "memory_dir": "memory",
            "auto_classify": true,
            "decay_interval_hours": 168
        }
    }
"""

__version__ = "0.4.0"
__all__ = [
    # Main API
    "search",
    "get_status", 
    "run_maintain",
    "classify_file",
    "get_gravity_score",
    "nautilus_info",
    
    # Configuration
    "config",
    "get_workspace",
    "get_state_dir",
    "get_gravity_db_path",
    
    # Submodules
    "gravity_module",
    "chambers",
    "doors", 
    "mirrors",
]

# Import config first (no dependencies)
from . import config
from .config import (
    get_workspace,
    get_state_dir,
    get_gravity_db_path,
    get_memory_dir,
    is_auto_classify_enabled,
)

# Import submodules for direct access
from . import gravity as gravity_module
from . import chambers
from . import doors
from . import mirrors

# Import search pipeline
from .search import run_full_search as search

# Convenience function for classifying a file
from .chambers import classify_chamber as classify_file

# Import for API wrapper functions
from . import gravity as _gravity
from . import chambers as _chambers
from . import doors as _doors
from . import mirrors as _mirrors


def get_status():
    """Get full Nautilus system status."""
    import sqlite3
    
    # Get gravity stats
    db = _gravity.get_db()
    
    total_chunks = db.execute("SELECT COUNT(*) FROM gravity").fetchone()[0]
    total_accesses = db.execute("SELECT COUNT(*) FROM access_log").fetchone()[0]
    superseded = db.execute("SELECT COUNT(*) FROM gravity WHERE superseded_by IS NOT NULL").fetchone()[0]
    tagged = db.execute("SELECT COUNT(*) FROM gravity WHERE tags != '[]' AND tags IS NOT NULL").fetchone()[0]
    
    db.close()
    
    # Get chamber distribution
    chambers_data = _chambers.cmd_status([])
    
    # Get mirrors stats
    mirrors_data = _mirrors.cmd_stats([])
    
    # Get config info
    workspace = config.get_workspace()
    state_dir = config.get_state_dir()
    db_path = config.get_gravity_db_path()
    
    return {
        "nautilus": {
            "phase_1_gravity": {
                "total_chunks": total_chunks,
                "total_accesses": total_accesses,
                "superseded": superseded,
                "tagged": tagged,
                "coverage": f"{tagged}/{total_chunks}" if total_chunks else "0/0"
            },
            "phase_2_chambers": chambers_data.get("chambers", {}),
            "phase_3_doors": {
                "patterns_defined": 11,  # From doors.py CONTEXT_PATTERNS
            },
            "phase_4_mirrors": mirrors_data,
            "config": {
                "workspace": str(workspace),
                "state_dir": str(state_dir),
                "gravity_db": str(db_path),
                "db_exists": db_path.exists()
            }
        }
    }


def run_maintain(register_recent=False, verbose=False):
    """Run all Nautilus maintenance tasks."""
    from datetime import datetime, timezone
    
    args = []
    if verbose:
        args.append("--verbose")
    if register_recent:
        args.append("--register-recent")
    
    # Step 1: Register recently modified files
    if register_recent:
        import subprocess
        workspace = config.get_workspace()
        memory_dir = config.get_memory_dir()
        
        if memory_dir.exists():
            try:
                result = subprocess.run(
                    ["find", str(memory_dir), "-name", "*.md", "-mtime", "-1", "-type", "f"],
                    capture_output=True, text=True, timeout=30
                )
                recent_files = [f for f in result.stdout.strip().split("\n") if f]
                
                for filepath in recent_files:
                    try:
                        rel_path = str(Path(filepath).relative_to(workspace))
                        _gravity.cmd_record_write([rel_path])
                    except ValueError:
                        pass  # File not in workspace
            except Exception:
                pass
    
    # Step 2: Classify chambers
    classify_result = _chambers.cmd_classify([])
    
    # Step 3: Auto-tag contexts
    tag_result = _doors.cmd_auto_tag([])
    
    # Step 4: Run gravity decay
    decay_result = _gravity.cmd_decay([])
    
    # Step 5: Auto-link mirrors
    link_result = _mirrors.cmd_auto_link([])
    
    return {
        "chambers": classify_result.get("classified", {}),
        "tagged": tag_result.get("files_tagged", 0),
        "decayed": decay_result.get("decayed", 0),
        "mirrors_linked": link_result.get("linked", 0),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def get_gravity_score(filepath, line_start=0, line_end=0):
    """Get the gravity score for a specific file."""
    args = [filepath]
    if line_start or line_end:
        args.extend(["--lines", f"{line_start}:{line_end}"])
    
    import io
    from contextlib import redirect_stdout
    
    f = io.StringIO()
    with redirect_stdout(f):
        _gravity.cmd_score(args)
    
    import json
    return json.loads(f.getvalue())


def nautilus_info():
    """Return information about the nautilus system."""
    return {
        "name": "Nautilus Memory Palace",
        "version": __version__,
        "phases": [
            {"id": 1, "name": "Gravity", "description": "Importance-weighted scoring"},
            {"id": 2, "name": "Chambers", "description": "Temporal memory layers"},
            {"id": 3, "name": "Doors", "description": "Context-aware filtering"},
            {"id": 4, "name": "Mirrors", "description": "Multi-granularity indexing"},
        ],
        "workspace": str(get_workspace()),
        "state_dir": str(get_state_dir()),
        "gravity_db": str(get_gravity_db_path()),
    }
