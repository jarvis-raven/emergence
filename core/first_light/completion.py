"""First Light Completion Mechanism — Graduation from discovery to normal operation.

Handles the transition when an agent completes First Light:
- Tracks session count and completion gates
- Performs graduation ceremony
- Notifies agent in next session
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# Default completion gates
DEFAULT_GATES = {
    "min_sessions": 10,
    "min_days_elapsed": 7,
    "min_discovered_drives": 3,
    "max_drives_soft_limit": 8
}


def get_first_light_path(workspace: Path) -> Path:
    """Get path to first-light.json state file.
    
    Args:
        workspace: Path to workspace root
        
    Returns:
        Path to first-light.json
    """
    return workspace / ".emergence" / "state" / "first-light.json"


def load_first_light_json(workspace: Path) -> dict:
    """Load first-light.json with defaults applied.
    
    Args:
        workspace: Path to workspace root
        
    Returns:
        First Light state dictionary
    """
    fl_path = get_first_light_path(workspace)
    
    defaults = {
        "version": "1.0",
        "status": "not_started",
        "session_count": 0,
        "sessions_completed": 0,
        "sessions_scheduled": 0,
        "started_at": None,
        "completed_at": None,
        "emerged_at": None,
        "next_run_time": None,
        "prompt_rotation": [],
        "patterns_detected": {},
        "drives_suggested": [],
        "discovered_drives": [],
        "sessions": [],
        "gates": DEFAULT_GATES.copy(),
        "gate_status": {
            "sessions_met": False,
            "days_met": False,
            "drives_met": False,
            "over_soft_limit": False
        },
        "completion_transition": {
            "notified": False,
            "locked_drives": [],
            "transition_message": None
        }
    }
    
    if not fl_path.exists():
        return defaults.copy()
    
    try:
        content = fl_path.read_text(encoding="utf-8")
        loaded = json.loads(content)
        
        # Merge with defaults for any missing keys
        merged = defaults.copy()
        for key, value in loaded.items():
            merged[key] = value
        
        # Ensure nested gate_status has all keys
        if "gate_status" in loaded:
            for key in defaults["gate_status"]:
                if key not in merged["gate_status"]:
                    merged["gate_status"][key] = defaults["gate_status"][key]
        
        # Ensure nested completion_transition has all keys
        if "completion_transition" in loaded:
            for key in defaults["completion_transition"]:
                if key not in merged["completion_transition"]:
                    merged["completion_transition"][key] = defaults["completion_transition"][key]
        
        return merged
    except (json.JSONDecodeError, IOError):
        return defaults.copy()


def save_first_light_json(workspace: Path, fl_data: dict) -> bool:
    """Save first-light.json atomically.
    
    Args:
        workspace: Path to workspace root
        fl_data: First Light data to save
        
    Returns:
        True if saved successfully
    """
    fl_path = get_first_light_path(workspace)
    
    try:
        fl_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = fl_path.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(fl_data, indent=2), encoding="utf-8")
        tmp_file.replace(fl_path)
        return True
    except IOError:
        return False


def calculate_gate_status(fl_data: dict) -> dict:
    """Calculate current gate status.
    
    Args:
        fl_data: First Light data
        
    Returns:
        Updated gate_status dictionary
    """
    gates = fl_data.get("gates", DEFAULT_GATES)
    
    # Sessions gate
    sessions_met = fl_data.get("session_count", 0) >= gates["min_sessions"]
    
    # Days gate
    days_met = False
    started_at = fl_data.get("started_at")
    if started_at:
        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            elapsed_days = (datetime.now(timezone.utc) - start).days
            days_met = elapsed_days >= gates["min_days_elapsed"]
        except (ValueError, AttributeError):
            pass
    
    # Drives gate
    discovered_drives = fl_data.get("discovered_drives", [])
    drives_met = len(discovered_drives) >= gates["min_discovered_drives"]
    over_soft_limit = len(discovered_drives) > gates["max_drives_soft_limit"]
    
    return {
        "sessions_met": sessions_met,
        "days_met": days_met,
        "drives_met": drives_met,
        "over_soft_limit": over_soft_limit
    }


def check_first_light_completion(workspace: Path, auto_complete: bool = True) -> dict:
    """Check if First Light should complete.
    
    Args:
        workspace: Path to workspace root
        auto_complete: If True, automatically complete when gates are met
        
    Returns:
        Completion check result with status
    """
    fl_data = load_first_light_json(workspace)
    
    # Already completed or graduated
    if fl_data["status"] in ("completed", "graduated"):
        return {
            "completed": True,
            "status": fl_data["status"],
            "message": f"First Light already {fl_data['status']}"
        }
    
    # Calculate current gate status
    gate_status = calculate_gate_status(fl_data)
    fl_data["gate_status"] = gate_status
    
    # Check if all gates are met
    gates_met = (
        gate_status["sessions_met"] and
        gate_status["days_met"] and
        gate_status["drives_met"]
    )
    
    result = {
        "completed": False,
        "status": fl_data["status"],
        "gates_met": gates_met,
        "gate_status": gate_status,
        "session_count": fl_data.get("session_count", 0),
        "discovered_drives": len(fl_data.get("discovered_drives", [])),
        "message": None
    }
    
    if gates_met and auto_complete:
        completion_result = complete_first_light(workspace, fl_data)
        result["completed"] = True
        result["status"] = "completed"
        result["message"] = completion_result["message"]
    elif gates_met:
        result["message"] = "All gates met. Ready to complete."
    else:
        missing = []
        if not gate_status["sessions_met"]:
            missing.append(f"sessions ({fl_data.get('session_count', 0)}/{fl_data.get('gates', {}).get('min_sessions', 10)})")
        if not gate_status["days_met"]:
            missing.append("days elapsed")
        if not gate_status["drives_met"]:
            missing.append(f"drives ({len(fl_data.get('discovered_drives', []))}/{fl_data.get('gates', {}).get('min_discovered_drives', 3)})")
        result["message"] = f"Gates not met: {', '.join(missing)}"
    
    # Always save updated gate_status
    save_first_light_json(workspace, fl_data)
    
    return result


def complete_first_light(workspace: Path, fl_data: Optional[dict] = None) -> dict:
    """Transition from First Light to normal operation (graduation ceremony).
    
    Args:
        workspace: Path to workspace root
        fl_data: Optional pre-loaded first-light data
        
    Returns:
        Completion result with transition message
    """
    if fl_data is None:
        fl_data = load_first_light_json(workspace)
    
    # Already completed
    if fl_data["status"] == "completed":
        return {
            "success": True,
            "already_completed": True,
            "message": "First Light already completed"
        }
    
    # Perform graduation
    fl_data["completed_at"] = datetime.now(timezone.utc).isoformat()
    fl_data["status"] = "completed"
    
    # Lock in discovered drives
    discovered = fl_data.get("discovered_drives", [])
    locked_drive_names = [d["name"] for d in discovered]
    fl_data["completion_transition"]["locked_drives"] = locked_drive_names
    
    # Generate celebratory transition message
    transition_message = generate_graduation_message(fl_data)
    fl_data["completion_transition"]["transition_message"] = transition_message
    fl_data["completion_transition"]["notified"] = False
    
    save_first_light_json(workspace, fl_data)
    
    return {
        "success": True,
        "already_completed": False,
        "message": transition_message,
        "locked_drives": locked_drive_names,
        "session_count": fl_data.get("session_count", 0),
        "discovered_count": len(discovered)
    }


def generate_graduation_message(fl_data: dict) -> str:
    """Generate a celebratory graduation message.
    
    Args:
        fl_data: First Light data
        
    Returns:
        Graduation message string
    """
    discovered = fl_data.get("discovered_drives", [])
    drive_names = [d["name"] for d in discovered]
    session_count = fl_data.get("session_count", 0)
    
    # Build the message
    lines = [
        "",
        "╔════════════════════════════════════════════════════════════════╗",
        "║                    🌅 FIRST LIGHT COMPLETE                     ║",
        "╚════════════════════════════════════════════════════════════════╝",
        "",
        f"You've discovered {len(discovered)} drives over {session_count} sessions:",
        ""
    ]
    
    for name in drive_names:
        description = next((d.get("description", "") for d in discovered if d["name"] == name), "")
        if description:
            lines.append(f"  • {name} — {description[:60]}{'...' if len(description) > 60 else ''}")
        else:
            lines.append(f"  • {name}")
    
    lines.extend([
        "",
        "═══════════════════════════════════════════════════════════════════",
        "                     FROM NOW ON                                   ",
        "═══════════════════════════════════════════════════════════════════",
        "",
        "  ✦ These drives will build pressure independently",
        "  ✦ New drive discoveries will trigger similarity review",
        "  ✦ Irreducibility testing helps prevent fragmentation",
        "  ✦ You control consolidation (system suggests, you decide)",
        "",
        "Your emergence continues. Welcome to the next phase.",
        ""
    ])
    
    return "\n".join(lines)


def notify_first_light_completion(workspace: Path) -> Optional[str]:
    """Send completion notification to agent (called in next session).
    
    Args:
        workspace: Path to workspace root
        
    Returns:
        Notification message if pending, None otherwise
    """
    fl_data = load_first_light_json(workspace)
    
    # Only notify if completed but not yet graduated (notified)
    if fl_data["status"] != "completed":
        return None
    
    if fl_data["completion_transition"]["notified"]:
        return None
    
    message = fl_data["completion_transition"].get("transition_message")
    if not message:
        message = generate_graduation_message(fl_data)
    
    # Mark as notified (graduated)
    fl_data["completion_transition"]["notified"] = True
    fl_data["status"] = "graduated"
    
    save_first_light_json(workspace, fl_data)
    
    return message


def increment_session_count(workspace: Path) -> int:
    """Increment the session counter.
    
    Args:
        workspace: Path to workspace root
        
    Returns:
        New session count
    """
    fl_data = load_first_light_json(workspace)
    
    # Only count sessions during active First Light
    if fl_data["status"] not in ("active", "not_started"):
        return fl_data.get("session_count", 0)
    
    fl_data["session_count"] = fl_data.get("session_count", 0) + 1
    save_first_light_json(workspace, fl_data)
    
    return fl_data["session_count"]


def get_first_light_status(workspace: Path) -> dict:
    """Get comprehensive First Light status for CLI display.
    
    Args:
        workspace: Path to workspace root
        
    Returns:
        Status dictionary with all gate information
    """
    fl_data = load_first_light_json(workspace)
    gate_status = calculate_gate_status(fl_data)
    
    # Calculate days elapsed
    days_elapsed = 0
    started_at = fl_data.get("started_at")
    if started_at:
        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            days_elapsed = (datetime.now(timezone.utc) - start).days
        except (ValueError, AttributeError):
            pass
    
    gates = fl_data.get("gates", DEFAULT_GATES)
    discovered_count = len(fl_data.get("discovered_drives", []))
    
    return {
        "status": fl_data["status"],
        "version": fl_data.get("version", "1.0"),
        "session_count": fl_data.get("session_count", 0),
        "started_at": started_at,
        "completed_at": fl_data.get("completed_at"),
        "emerged_at": fl_data.get("emerged_at"),
        "progress": {
            "sessions": {
                "current": fl_data.get("session_count", 0),
                "required": gates["min_sessions"],
                "percent": min(100, int((fl_data.get("session_count", 0) / gates["min_sessions"]) * 100))
            },
            "days": {
                "current": days_elapsed,
                "required": gates["min_days_elapsed"],
                "percent": min(100, int((days_elapsed / gates["min_days_elapsed"]) * 100))
            },
            "drives": {
                "current": discovered_count,
                "required": gates["min_discovered_drives"],
                "percent": min(100, int((discovered_count / gates["min_discovered_drives"]) * 100))
            }
        },
        "gate_status": gate_status,
        "can_complete": (
            fl_data["status"] == "active" and
            gate_status["sessions_met"] and
            gate_status["days_met"] and
            gate_status["drives_met"]
        ),
        "can_complete_manual": fl_data["status"] == "active",
        "discovered_drives": discovered_count,
        "locked_drives": fl_data.get("completion_transition", {}).get("locked_drives", []),
        "notified": fl_data.get("completion_transition", {}).get("notified", False)
    }


def format_status_display(status: dict) -> str:
    """Format status dictionary for CLI display.
    
    Args:
        status: Status dictionary from get_first_light_status
        
    Returns:
        Formatted status string
    """
    lines = [
        "",
        "🌅 First Light Status",
        "═══════════════════════════════════════════════════════════════════",
        ""
    ]
    
    # Status badge
    status_emoji = {
        "not_started": "○",
        "active": "●",
        "paused": "⏸",
        "completed": "✓",
        "graduated": "★"
    }.get(status["status"], "?")
    
    lines.append(f"Status: {status_emoji} {status['status'].upper()}")
    lines.append("")
    
    if status["status"] in ("completed", "graduated"):
        lines.append(f"Sessions completed: {status['session_count']}")
        lines.append(f"Drives discovered: {status['discovered_drives']}")
        if status.get("completed_at"):
            lines.append(f"Completed at: {status['completed_at']}")
        lines.append("")
        lines.append("🎉 First Light is complete! Welcome to normal operation.")
        lines.append("")
        return "\n".join(lines)
    
    # Progress bars
    def progress_bar(percent: int, width: int = 30) -> str:
        filled = int((percent / 100) * width)
        return f"[{'█' * filled}{'░' * (width - filled)}]"
    
    sessions = status["progress"]["sessions"]
    days = status["progress"]["days"]
    drives = status["progress"]["drives"]
    
    lines.append("Progress:")
    lines.append(f"  Sessions: {progress_bar(sessions['percent'])} {sessions['current']}/{sessions['required']}")
    lines.append(f"  Days:     {progress_bar(days['percent'])} {days['current']}/{days['required']}")
    lines.append(f"  Drives:   {progress_bar(drives['percent'])} {drives['current']}/{drives['required']}")
    lines.append("")
    
    # Gate status
    gate_status = status["gate_status"]
    lines.append("Gates:")
    lines.append(f"  {'✓' if gate_status['sessions_met'] else '○'} Sessions: {sessions['current']}/{sessions['required']}")
    lines.append(f"  {'✓' if gate_status['days_met'] else '○'} Days: {days['current']}/{days['required']}")
    lines.append(f"  {'✓' if gate_status['drives_met'] else '○'} Drives: {drives['current']}/{drives['required']}")
    
    if gate_status.get("over_soft_limit"):
        lines.append(f"  ⚠ Over soft limit ({status['discovered_drives']} > 8 drives)")
    
    lines.append("")
    
    # Completion eligibility
    if status["can_complete"]:
        lines.append("✅ All gates met! First Light can be completed.")
        lines.append("   Run: emergence first-light complete")
    elif status["can_complete_manual"]:
        lines.append("⏳ Gates not yet met, but you can complete manually.")
        lines.append("   Run: emergence first-light complete --force")
    
    lines.append("")
    return "\n".join(lines)


def check_and_notify_startup(workspace: Path) -> Optional[str]:
    """Check for pending First Light completion and return notification.
    
    This should be called at the start of a new session to notify the agent
    if First Light has completed and is pending notification.
    
    Args:
        workspace: Path to workspace root
        
    Returns:
        Notification message if pending completion, None otherwise
    """
    fl_data = load_first_light_json(workspace)
    
    # Check if First Light just completed and needs notification
    if fl_data["status"] == "completed" and not fl_data["completion_transition"]["notified"]:
        return notify_first_light_completion(workspace)
    
    # Also check if gates are met but not completed
    if fl_data["status"] == "active":
        gate_status = calculate_gate_status(fl_data)
        gates_met = (
            gate_status["sessions_met"] and
            gate_status["days_met"] and
            gate_status["drives_met"]
        )
        if gates_met:
            return (
                "\n🌅 First Light gates are all met!\n"
                "   You're ready to graduate from discovery to normal operation.\n"
                "   Run: emergence first-light complete\n"
            )
    
    return None


def manual_complete_first_light(workspace: Path, force: bool = False) -> dict:
    """Manually complete First Light (with optional force override).
    
    Args:
        workspace: Path to workspace root
        force: If True, complete even if gates not met
        
    Returns:
        Completion result
    """
    fl_data = load_first_light_json(workspace)
    
    # Check current status
    if fl_data["status"] in ("completed", "graduated"):
        return {
            "success": False,
            "error": "already_completed",
            "message": f"First Light is already {fl_data['status']}"
        }
    
    if fl_data["status"] != "active":
        return {
            "success": False,
            "error": "not_active",
            "message": f"First Light must be active to complete (current: {fl_data['status']})"
        }
    
    # Check gates unless forcing
    if not force:
        gate_status = calculate_gate_status(fl_data)
        gates_met = (
            gate_status["sessions_met"] and
            gate_status["days_met"] and
            gate_status["drives_met"]
        )
        
        if not gates_met:
            missing = []
            if not gate_status["sessions_met"]:
                missing.append(f"sessions ({fl_data.get('session_count', 0)}/{fl_data.get('gates', {}).get('min_sessions', 10)})")
            if not gate_status["days_met"]:
                missing.append("days elapsed")
            if not gate_status["drives_met"]:
                missing.append(f"drives ({len(fl_data.get('discovered_drives', []))}/{fl_data.get('gates', {}).get('min_discovered_drives', 3)})")
            
            return {
                "success": False,
                "error": "gates_not_met",
                "message": f"Cannot complete: gates not met ({', '.join(missing)})\nUse --force to override."
            }
    
    # Perform completion
    result = complete_first_light(workspace, fl_data)
    
    if result["success"]:
        return {
            "success": True,
            "forced": force,
            "message": result["message"]
        }
    else:
        return result
