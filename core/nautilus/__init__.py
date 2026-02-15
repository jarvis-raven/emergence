"""
Nautilus Memory Palace - Emergence Integration

Four-phase memory architecture:
- Phase 1: Gravity (importance-weighted scoring)
- Phase 2: Chambers (temporal layers: atrium, corridor, vault)
- Phase 3: Doors (context-aware filtering)
- Phase 4: Mirrors (multi-granularity indexing)

v0.4.0 Beta additions:
- Session hooks: Auto-track file accesses during sessions
- Nightly maintenance: Daemon-integrated memory upkeep

Usage:
    from core.nautilus import gravity, chambers, doors, mirrors
    from core.nautilus.config import get_workspace, get_config
    from core.nautilus.session_hooks import record_access, on_file_read, on_file_write
    from core.nautilus.nightly import run_nightly_maintenance
"""

__version__ = "0.4.0-beta"

# Module exports
from . import gravity, chambers, doors, mirrors, config, session_hooks, nightly
from .config import get_workspace, get_nautilus_config, get_gravity_db_path

__all__ = [
    "gravity",
    "chambers",
    "doors",
    "mirrors",
    "config",
    "session_hooks",
    "nightly",
    "get_workspace",
    "get_nautilus_config",
    "get_gravity_db_path",
]
