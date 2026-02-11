"""Post-session analyzer for First Light sessions.

Parses session markdown files for drive discoveries, checks for similar drives
via Ollama embeddings, and generates pending reviews for irreducibility testing.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..drives.state import load_state, save_state
from .irreducibility import (
    find_similar_drives,
    generate_irreducibility_test,
    add_pending_review,
    load_pending_reviews,
)


# Patterns for drive discovery detection
DRIVE_DISCOVERY_PATTERNS = [
    # "New drive emerging: NAME"
    r'[Nn]ew drive emerging:?\s+\*?\*?([A-Z_][A-Z_\s]*)\*?\*?',
    # "discovered drive: NAME"
    r'[Dd]iscovered drive:?\s+\*?\*?([A-Z_][A-Z_\s]*)\*?\*?',
    # "Drive discovered: NAME"
    r'[Dd]rive discovered:?\s+\*?\*?([A-Z_][A-Z_\s]*)\*?\*?',
    # "New drive: NAME"
    r'[Nn]ew drive:?\s+\*?\*?([A-Z_][A-Z_\s]*)\*?\*?',
]


def parse_drive_discovery(session_file: Path) -> Optional[dict]:
    """Parse a First Light session file for drive discoveries.
    
    Args:
        session_file: Path to session markdown file
        
    Returns:
        Drive metadata dict if discovery found, None otherwise
    """
    content = session_file.read_text()
    
    # Try all patterns
    drive_name = None
    for pattern in DRIVE_DISCOVERY_PATTERNS:
        match = re.search(pattern, content)
        if match:
            drive_name = match.group(1).strip().upper().replace(' ', '_')
            break
    
    if not drive_name:
        return None
    
    # Extract description (look for dash/colon after drive name or in following lines)
    desc_pattern = rf'{re.escape(drive_name)}[^\n]*?[—–-]\s*([^\.\n]+)'
    desc_match = re.search(desc_pattern, content, re.IGNORECASE)
    description = desc_match.group(1).strip() if desc_match else f"Discovered during First Light exploration"
    
    # Try to find a better description in the context
    # Look for lines after the drive mention
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if drive_name.replace('_', ' ') in line or drive_name in line:
            # Check next few lines for description
            for j in range(i+1, min(i+5, len(lines))):
                next_line = lines[j].strip()
                if next_line and not next_line.startswith('#'):
                    # Use this as description if it's substantial
                    if len(next_line) > 20 and len(next_line) < 200:
                        description = next_line
                        break
            break
    
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
    from ..drives.config import get_state_path
    
    state_path = get_state_path({"paths": {"state": str(emergence_dir / "state")}})
    drives_state = load_state(state_path)
    
    if drive_meta["name"] in drives_state["drives"]:
        print(f"ℹ Drive {drive_meta['name']} already active")
        return
    
    # Create drive entry with new schema fields
    drives_state["drives"][drive_meta["name"]] = {
        "name": drive_meta["name"],
        "base_drive": True,
        "aspects": [],
        "pressure": 0.0,
        "threshold": 20.0,
        "rate_per_hour": 1.5,
        "max_rate": 2.5,
        "description": drive_meta["description"],
        "prompt": f"Your {drive_meta['name']} drive has triggered. {drive_meta['description']}",
        "category": "discovered",
        "created_by": "agent",
        "created_at": drive_meta["timestamp"],
        "satisfaction_events": [],
        "discovered_during": f"first_light_{drive_meta['session_number']}",
        "activity_driven": False,
        "last_triggered": None,
        "min_interval_seconds": 14400,  # 4 hours
    }
    
    drives_state["last_updated"] = datetime.now(timezone.utc).isoformat()
    
    save_state(state_path, drives_state)
    
    print(f"✓ Activated {drive_meta['name']} in drives.json")


def check_similarity_and_queue_review(workspace: Path, drive_meta: dict) -> bool:
    """Check if discovered drive is similar to existing ones and queue for review.
    
    Args:
        workspace: Path to workspace root
        drive_meta: Drive metadata from parse_drive_discovery
        
    Returns:
        True if similar drives found and review queued, False otherwise
    """
    from ..drives.config import get_state_path
    
    emergence_dir = workspace / ".emergence"
    state_path = get_state_path({"paths": {"state": str(emergence_dir / "state")}})
    
    if not state_path.exists():
        return False
    
    drives_state = load_state(state_path)
    existing_drives = drives_state.get("drives", {})
    
    # Skip if already exists
    if drive_meta["name"] in existing_drives:
        return False
    
    # Find similar drives
    similar = find_similar_drives(
        drive_meta["name"],
        drive_meta["description"],
        existing_drives,
        workspace
    )
    
    if similar:
        print(f"⚠ Similar drives found for {drive_meta['name']}:")
        for name, score, _ in similar[:3]:
            print(f"  • {name} (similarity: {score:.2f})")
        
        # Queue for review
        add_pending_review(
            workspace,
            drive_meta["name"],
            drive_meta["description"],
            similar,
            drive_meta["discovered_in"]
        )
        print(f"✓ Queued {drive_meta['name']} for irreducibility review")
        return True
    
    return False


def analyze_session(workspace: Path, session_file: Path, auto_activate: bool = True,
                    check_similarity: bool = True):
    """Analyze a First Light session file for discoveries.
    
    Args:
        workspace: Path to workspace root
        session_file: Path to session markdown file
        auto_activate: If True, promote discoveries to active drives immediately
        check_similarity: If True, check for similar drives and queue for review
    """
    drive_meta = parse_drive_discovery(session_file)
    
    if drive_meta:
        print(f"🔍 Found drive discovery: {drive_meta['name']}")
        
        # Always register in first-light.json
        register_discovered_drive(workspace, drive_meta, auto_activate=False)
        
        # Check for similar drives and queue for review
        if check_similarity:
            similar_found = check_similarity_and_queue_review(workspace, drive_meta)
            if not similar_found and auto_activate:
                # No similar drives found, safe to auto-activate
                activate_drive(workspace / ".emergence", drive_meta)
        elif auto_activate:
            activate_drive(workspace / ".emergence", drive_meta)
    else:
        print(f"ℹ No drive discoveries in {session_file.name}")


def analyze_recent_sessions(workspace: Path, limit: int = 5, auto_activate: bool = True,
                           check_similarity: bool = True):
    """Analyze recent First Light sessions for discoveries.
    
    Args:
        workspace: Path to workspace root
        limit: Number of recent sessions to analyze
        auto_activate: If True, promote discoveries to active drives
        check_similarity: If True, check for similar drives
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
        analyze_session(workspace, session_file, 
                       auto_activate=auto_activate, check_similarity=check_similarity)


def show_pending_reviews(workspace: Path):
    """Display all pending drive reviews.
    
    Args:
        workspace: Path to workspace root
    """
    reviews = load_pending_reviews(workspace)
    
    if not reviews:
        print("ℹ No pending drive reviews")
        return
    
    print(f"⚖️ Pending Drive Reviews ({len(reviews)}):")
    print("-" * 52)
    
    for review in reviews:
        new_drive = review.get("new_drive")
        similar = review.get("similar_drives", [])
        
        print(f"\n  • {new_drive}")
        print(f"    Description: {review.get('new_drive_description', 'N/A')[:60]}...")
        print(f"    Similar to:")
        for sim in similar[:2]:
            print(f"      - {sim['name']} ({sim['similarity']:.2f})")
    
    print("\n" + "-" * 52)
    print("Run 'drives review <name>' for irreducibility test")


def get_pending_review_count(workspace: Path) -> int:
    """Get count of pending drive reviews.
    
    Args:
        workspace: Path to workspace root
        
    Returns:
        Number of pending reviews
    """
    return len(load_pending_reviews(workspace))


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
