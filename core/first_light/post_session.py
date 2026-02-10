"""Post-session analyzer for First Light sessions.

Parses session markdown files for drive discoveries and registers them automatically.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..drives.state import load_state, save_state


def parse_drive_discovery(session_file: Path) -> Optional[dict]:
    """Parse a First Light session file for drive discoveries.
    
    Args:
        session_file: Path to session markdown file
        
    Returns:
        Drive metadata dict if discovery found, None otherwise
    """
    content = session_file.read_text()
    
    # Pattern 1: "New drive emerging: NAME"
    match = re.search(r'[Nn]ew drive emerging:?\s+\*?\*?([A-Z_\s]+)\*?\*?', content)
    if not match:
        # Pattern 2: "discovered drive: NAME"
        match = re.search(r'discovered drive:?\s+\*?\*?([A-Z_\s]+)\*?\*?', content)
    
    if not match:
        return None
    
    drive_name = match.group(1).strip().upper().replace(' ', '_')
    
    # Extract description (look for dash/colon after drive name)
    desc_pattern = rf'{re.escape(drive_name)}[^\n]*?[—–-]\s*([^.\n]+)'
    desc_match = re.search(desc_pattern, content, re.IGNORECASE)
    description = desc_match.group(1).strip() if desc_match else f"Discovered during First Light exploration"
    
    # Extract session number from filename
    session_num_match = re.search(r'first.*light[_-](\d+)', session_file.name, re.IGNORECASE)
    session_num = session_num_match.group(1) if session_num_match else "unknown"
    
    return {
        "name": drive_name,
        "description": description,
        "discovered_in": session_file.name,
        "session_number": session_num,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


def register_discovered_drive(workspace: Path, drive_meta: dict, auto_activate: bool = False):
    """Register a discovered drive in the system.
    
    Args:
        workspace: Path to workspace root
        drive_meta: Drive metadata from parse_drive_discovery
        auto_activate: If True, add to active drives.json immediately
    """
    emergence_dir = workspace / ".emergence"
    state_dir = emergence_dir / "state"
    
    # Load first-light.json
    fl_state_path = state_dir / "first-light.json"
    if fl_state_path.exists():
        fl_state = json.loads(fl_state_path.read_text())
    else:
        fl_state = {"discovered_drives": []}
    
    if "discovered_drives" not in fl_state:
        fl_state["discovered_drives"] = []
    
    # Check if already registered
    existing = [d for d in fl_state["discovered_drives"] if d["name"] == drive_meta["name"]]
    if existing:
        print(f"ℹ Drive {drive_meta['name']} already registered")
        return
    
    # Add to discovered_drives
    fl_state["discovered_drives"].append(drive_meta)
    fl_state_path.write_text(json.dumps(fl_state, indent=2))
    
    print(f"✓ Registered {drive_meta['name']} in first-light.json")
    
    # Auto-activate if requested
    if auto_activate:
        activate_drive(emergence_dir, drive_meta)


def activate_drive(emergence_dir: Path, drive_meta: dict):
    """Promote a discovered drive to active drives.json.
    
    Args:
        emergence_dir: Path to .emergence directory
        drive_meta: Drive metadata
    """
    state_dir = emergence_dir / "state"
    drives_state = load_state(emergence_dir)
    
    if drive_meta["name"] in drives_state["drives"]:
        print(f"ℹ Drive {drive_meta['name']} already active")
        return
    
    # Create drive entry
    drives_state["drives"][drive_meta["name"]] = {
        "name": drive_meta["name"],
        "pressure": 0.0,
        "threshold": 20.0,
        "rate_per_hour": 1.5,
        "description": drive_meta["description"],
        "prompt": f"Your {drive_meta['name']} drive has triggered. {drive_meta['description']}",
        "category": "discovered",
        "created_by": "agent",
        "created_at": drive_meta["timestamp"],
        "satisfaction_events": [],
        "discovered_during": f"first_light_{drive_meta['session_number']}",
        "activity_driven": False
    }
    
    drives_state["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    save_state(emergence_dir, drives_state)
    
    print(f"✓ Activated {drive_meta['name']} in drives.json")


def analyze_session(workspace: Path, session_file: Path, auto_activate: bool = True):
    """Analyze a First Light session file for discoveries.
    
    Args:
        workspace: Path to workspace root
        session_file: Path to session markdown file
        auto_activate: If True, promote discoveries to active drives immediately
    """
    drive_meta = parse_drive_discovery(session_file)
    
    if drive_meta:
        print(f"🔍 Found drive discovery: {drive_meta['name']}")
        register_discovered_drive(workspace, drive_meta, auto_activate=auto_activate)
    else:
        print(f"ℹ No drive discoveries in {session_file.name}")


def analyze_recent_sessions(workspace: Path, limit: int = 5, auto_activate: bool = True):
    """Analyze recent First Light sessions for discoveries.
    
    Args:
        workspace: Path to workspace root
        limit: Number of recent sessions to analyze
        auto_activate: If True, promote discoveries to active drives
    """
    sessions_dir = workspace / "memory" / "sessions"
    if not sessions_dir.exists():
        print("ℹ No sessions directory found")
        return
    
    # Find First Light sessions
    fl_sessions = sorted(
        [f for f in sessions_dir.glob("*first*light*.md")],
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )[:limit]
    
    if not fl_sessions:
        print("ℹ No First Light sessions found")
        return
    
    print(f"📊 Analyzing {len(fl_sessions)} recent First Light sessions...")
    
    for session_file in fl_sessions:
        analyze_session(workspace, session_file, auto_activate=auto_activate)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python -m core.first_light.post_session <workspace> [session_file]")
        sys.exit(1)
    
    workspace = Path(sys.argv[1])
    
    if len(sys.argv) > 2:
        # Analyze specific session
        session_file = Path(sys.argv[2])
        analyze_session(workspace, session_file)
    else:
        # Analyze recent sessions
        analyze_recent_sessions(workspace)
