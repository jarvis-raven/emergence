"""Session spawning for drive triggers.

This module bridges the interoception system with the OpenClaw runtime,
spawning isolated sessions when drive pressures exceed thresholds.
"""

import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from .models import DriveState


def detect_openclaw_path() -> Optional[str]:
    """Detect the full path to the openclaw binary.
    
    Search order:
    1. Config-specified path (drives.openclaw_path)
    2. shutil.which('openclaw') - searches PATH
    3. Common npm global bin directories
    
    Returns:
        Full path to openclaw binary, or None if not found
        
    Examples:
        >>> path = detect_openclaw_path()
        >>> path is not None or "openclaw not installed"
        True
    """
    # Try shutil.which first (searches PATH)
    openclaw_bin = shutil.which("openclaw")
    if openclaw_bin:
        return openclaw_bin
    
    # Fallback: check common npm global bin locations
    common_paths = [
        Path.home() / ".npm-global" / "bin" / "openclaw",
        Path.home() / ".nvm" / "current" / "bin" / "openclaw",  # nvm active version
        Path.home() / ".nvm" / "versions" / "node" / "*" / "bin" / "openclaw",  # nvm fallback
        Path("/usr/local/bin/openclaw"),
        Path.home() / ".local" / "bin" / "openclaw",
    ]
    
    for path in common_paths:
        # Handle glob patterns for nvm
        if "*" in str(path):
            from glob import glob
            matches = glob(str(path))
            if matches:
                return matches[0]  # Use first match
        elif path.exists() and os.access(path, os.X_OK):
            return str(path)
    
    return None


def is_quiet_hours(config: dict) -> bool:
    """Check if current time is within configured quiet hours.
    
    Quiet hours prevent session spawning but pressure still accumulates.
    Supports overnight ranges (e.g., [23, 7] for 23:00-07:00).
    
    Args:
        config: Configuration dict with drives.quiet_hours as [start, end]
        
    Returns:
        True if currently within quiet hours
        
    Examples:
        >>> config = {"drives": {"quiet_hours": [23, 7]}}
        >>> # At 2 AM, returns True
        >>> # At 14:00 (2 PM), returns False
    """
    quiet_hours = config.get("drives", {}).get("quiet_hours", [23, 7])
    if not quiet_hours or len(quiet_hours) != 2:
        return False
    
    start_hour, end_hour = quiet_hours
    current_hour = datetime.now().hour
    
    # Handle overnight quiet hours (e.g., 23:00-07:00)
    if start_hour > end_hour:
        return current_hour >= start_hour or current_hour < end_hour
    else:
        # Same-day quiet hours (e.g., 01:00-05:00)
        return start_hour <= current_hour < end_hour


def check_cooldown(state: DriveState, drive_name: str, cooldown_minutes: int) -> bool:
    """Check if drive is within cooldown period from last trigger.
    
    Args:
        state: Current drive state with trigger_log
        drive_name: Name of drive to check
        cooldown_minutes: Minimum minutes between triggers
        
    Returns:
        True if drive is in cooldown (should not trigger)
        
    Examples:
        >>> state = {"trigger_log": [{"drive": "CARE", "timestamp": "2026-02-07T14:00:00+00:00"}]}
        >>> # If current time is 14:15 and cooldown is 30:
        >>> check_cooldown(state, "CARE", 30)  # Returns True (in cooldown)
    """
    trigger_log = state.get("trigger_log", [])
    
    for entry in reversed(trigger_log):
        if entry.get("drive") == drive_name:
            try:
                last_trigger = datetime.fromisoformat(entry["timestamp"])
                # Ensure timezone-aware comparison
                if last_trigger.tzinfo is None:
                    last_trigger = last_trigger.replace(tzinfo=timezone.utc)
                
                now = datetime.now(timezone.utc)
                minutes_since = (now - last_trigger).total_seconds() / 60
                return minutes_since < cooldown_minutes
            except (ValueError, TypeError):
                # Invalid timestamp format, treat as no cooldown
                return False
    
    return False  # No previous trigger


def build_session_prompt(
    drive_name: str,
    drive_prompt: str,
    pressure: float,
    threshold: float,
    config: dict
) -> str:
    """Build the complete session prompt with context and instructions.
    
    Args:
        drive_name: Name of the triggering drive
        drive_prompt: The drive's configured prompt
        pressure: Current pressure level
        threshold: Drive's threshold level
        config: Configuration dict
        
    Returns:
        Full prompt text for the spawned session
    """
    now = datetime.now(timezone.utc)
    file_date = now.strftime("%Y-%m-%d")
    file_time = now.strftime("%H%M")
    
    # Get session directory from config
    session_dir = config.get("memory", {}).get("session_dir", "memory/sessions")
    session_file = f"{session_dir}/{file_date}-{file_time}-{drive_name}.md"
    
    # Get workspace path dynamically
    # If config has _config_dir (from load_config), use it to resolve relative paths
    config_dir = Path(config.get("_config_dir", "."))
    workspace_rel = Path(config.get("paths", {}).get("workspace", "."))
    if not workspace_rel.is_absolute():
        workspace = (config_dir / workspace_rel).resolve()
    else:
        workspace = workspace_rel.resolve()
    
    # Use the same python that's running this code (handles venv correctly)
    python_path = sys.executable
    
    return f"""AUTONOMOUS SESSION (triggered by {drive_name} drive)
Pressure: {pressure:.1f}/{threshold}
Timestamp: {now.isoformat()}

{drive_prompt}

Record your session to: {session_file}

Use this format:

---
drive: {drive_name}
timestamp: {now.isoformat()}
pressure: {pressure:.1f}/{threshold}
trigger: drive
---

## Summary
One-line description of what you did.

## Details
Full content of your session...

## Artifacts
- List any files created or modified
- List any external actions (emails sent, posts made, messages sent)

IMPORTANT: When your session is complete, signal completion by running:
```
cd {workspace} && "{python_path}" -c "from core.drives.satisfaction import write_completion; write_completion('{drive_name}', 'agent:main:cron:drive-{drive_name.lower()}')"
```
This triggers instant satisfaction of your drive. Without it, satisfaction is delayed.
"""


def spawn_via_api(
    prompt: str,
    config: dict,
    drive_name: str,
    pressure: float,
    threshold: float
) -> bool:
    """Spawn session via OpenClaw Gateway API.
    
    Args:
        prompt: The full session prompt
        config: Configuration dict
        drive_name: Name of the triggering drive
        pressure: Current pressure level
        threshold: Drive's threshold level
        
    Returns:
        True if session spawned successfully
    """
    gateway_url = os.environ.get("OPENCLAW_GATEWAY_URL", "http://localhost:54646")
    gateway_token = os.environ.get("OPENCLAW_GATEWAY_TOKEN")
    
    # Fallback: read token from file (common in LaunchAgent contexts)
    if not gateway_token:
        token_path = Path.home() / ".openclaw" / "gateway-token"
        try:
            gateway_token = token_path.read_text().strip()
        except (FileNotFoundError, IOError):
            pass
    
    if not gateway_token:
        return False
    
    # Get timeout from config
    timeout_seconds = config.get("drives", {}).get("session_timeout", 900)
    model = config.get("drives", {}).get("session_model")
    announce = config.get("drives", {}).get("announce_session", False)
    
    req_data = {
        "agent": "emergence",
        "prompt": prompt,
        "session_type": "isolated",
        "timeout_seconds": timeout_seconds,
        "delete_after_run": True,
        "metadata": {
            "drive": drive_name,
            "source": "emergence",
            "trigger": "drive",
            "pressure": pressure,
            "threshold": threshold,
        }
    }
    
    # Add optional model if specified
    if model:
        req_data["model"] = model
    
    if announce:
        req_data["announce"] = True
    
    try:
        req_json = json.dumps(req_data).encode("utf-8")
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {gateway_token}"
        }
        
        req = urllib.request.Request(
            f"{gateway_url}/v1/cron/add",
            data=req_json,
            headers=headers,
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("success", False) or result.get("id") is not None
            
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return False
    except Exception:
        return False


def spawn_via_cli(
    prompt: str,
    config: dict,
    drive_name: str,
    pressure: float,
    threshold: float
) -> bool:
    """Fallback: Spawn session via openclaw CLI.
    
    Args:
        prompt: The full session prompt
        config: Configuration dict
        drive_name: Name of the triggering drive
        pressure: Current pressure level
        threshold: Drive's threshold level
        
    Returns:
        True if session spawned successfully
    """
    timeout_seconds = config.get("drives", {}).get("session_timeout", 900)
    model = config.get("drives", {}).get("session_model")
    announce = config.get("drives", {}).get("announce_session", False)
    
    # Get openclaw binary path
    # Priority: config-specified > auto-detected > fallback to "openclaw"
    openclaw_path = config.get("drives", {}).get("openclaw_path")
    if not openclaw_path:
        openclaw_path = config.get("_openclaw_path")  # Auto-detected at daemon startup
    if not openclaw_path:
        openclaw_path = "openclaw"  # Fallback (will fail if not in PATH)
    
    # Build the cron command
    cmd = [
        openclaw_path, "cron", "add",
        "--name", f"drive-{drive_name.lower()}",
        "--at", "10s",
        "--session", "isolated",
        "--message", prompt,
        "--timeout-seconds", str(timeout_seconds),
        "--delete-after-run",
        "--no-deliver",
    ]
    
    if model:
        cmd.extend(["--model", model])
    
    if announce:
        cmd.append("--announce")
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False
    except Exception:
        return False


def spawn_session(
    drive_name: str,
    prompt: str,
    config: dict,
    pressure: float,
    threshold: float
) -> bool:
    """Spawn an OpenClaw session for a triggered drive.
    
    Primary method: OpenClaw Gateway API (HTTP)
    Fallback method: openclaw cron add CLI
    
    Args:
        drive_name: Name of the triggering drive
        prompt: The drive's configured prompt
        config: Configuration dict
        pressure: Current pressure level
        threshold: Drive's threshold level
        
    Returns:
        True if session spawned successfully (via either method)
        
    Examples:
        >>> config = {"drives": {"session_timeout": 900}}
        >>> spawn_session("CARE", "Check in with human", config, 25.0, 20.0)
        True  # (if OpenClaw is available)
    """
    full_prompt = build_session_prompt(drive_name, prompt, pressure, threshold, config)
    
    # Try CLI first (more reliable — handles its own auth)
    if spawn_via_cli(full_prompt, config, drive_name, pressure, threshold):
        _write_spawn_breadcrumb(drive_name, config)
        return True
    
    # Fallback to API
    if spawn_via_api(full_prompt, config, drive_name, pressure, threshold):
        _write_spawn_breadcrumb(drive_name, config)
        return True
    
    return False


def _write_spawn_breadcrumb(drive_name: str, config: dict) -> None:
    """Write a breadcrumb file for a successfully spawned drive session.
    
    Called after spawn_session() succeeds. The breadcrumb is picked up
    by check_completed_sessions() on subsequent ticks.
    
    Args:
        drive_name: Name of the drive that was spawned
        config: Configuration dict (for timeout)
    """
    from .satisfaction import write_breadcrumb
    
    timeout = config.get("drives", {}).get("session_timeout", 900)
    session_key = f"agent:main:cron:drive-{drive_name.lower()}"
    
    try:
        write_breadcrumb(drive_name, session_key, timeout)
    except Exception:
        pass  # Non-fatal — satisfaction will use age-based fallback


def record_trigger(
    state: DriveState,
    drive_name: str,
    pressure: float,
    threshold: float,
    spawned: bool
) -> None:
    """Record a trigger event to state.
    
    Maintains a rolling log of the last 100 trigger events.
    
    Args:
        state: Current drive state (modified in place)
        drive_name: Name of the triggered drive
        pressure: Pressure at time of trigger
        threshold: Threshold at time of trigger
        spawned: Whether a session was successfully spawned
        
    Examples:
        >>> state = {"trigger_log": []}
        >>> record_trigger(state, "CARE", 25.0, 20.0, True)
        >>> len(state["trigger_log"])
        1
    """
    entry = {
        "drive": drive_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pressure": pressure,
        "threshold": threshold,
        "session_spawned": spawned,
    }
    
    if "trigger_log" not in state:
        state["trigger_log"] = []
    
    state["trigger_log"].append(entry)
    
    # Keep only last 100 entries
    if len(state["trigger_log"]) > 100:
        state["trigger_log"] = state["trigger_log"][-100:]


def select_drive_to_trigger(state: DriveState, config: dict) -> Optional[str]:
    """Select which drive to trigger when multiple are over threshold.
    
    Selects the highest-pressure-ratio drive that:
    - Is over its threshold
    - Is not already triggered
    - Is not in cooldown period
    
    Args:
        state: Current drive state
        config: Configuration dict
        
    Returns:
        Name of drive to trigger, or None if no eligible drive
        
    Examples:
        >>> state = {
        ...     "drives": {"CARE": {"pressure": 25.0, "threshold": 20.0}},
        ...     "triggered_drives": [],
        ...     "trigger_log": []
        ... }
        >>> config = {"drives": {"cooldown_minutes": 30}}
        >>> select_drive_to_trigger(state, config)
        'CARE'
    """
    triggered = set(state.get("triggered_drives", []))
    cooldown_minutes = config.get("drives", {}).get("cooldown_minutes", 30)
    
    candidates = []
    
    for name, drive in state.get("drives", {}).items():
        # Skip already triggered
        if name in triggered:
            continue
        
        pressure = drive.get("pressure", 0.0)
        threshold = drive.get("threshold", 1.0)
        
        # Skip if not over threshold
        if threshold <= 0 or pressure < threshold:
            continue
        
        ratio = pressure / threshold
        candidates.append((name, ratio, pressure, threshold))
    
    if not candidates:
        return None
    
    # Sort by pressure ratio descending (highest first)
    candidates.sort(key=lambda x: x[1], reverse=True)
    
    # Check cooldown for candidates in order
    for name, ratio, pressure, threshold in candidates:
        if not check_cooldown(state, name, cooldown_minutes):
            return name
    
    # All candidates in cooldown
    return None


def handle_spawn_failure(
    state: DriveState,
    drive_name: str,
    error: str
) -> None:
    """Handle a failed session spawn attempt.
    
    Records the failure and adds to retry queue with backoff.
    
    Args:
        state: Current drive state (modified in place)
        drive_name: Name of the drive that failed to spawn
        error: Error message describing the failure
        
    Examples:
        >>> state = {"retry_queue": {}}
        >>> handle_spawn_failure(state, "CARE", "Connection refused")
        >>> "CARE" in state["retry_queue"]
        True
    """
    # Get current attempt count for this drive
    retry_queue = state.setdefault("retry_queue", {})
    current_entry = retry_queue.get(drive_name, {})
    attempt_count = current_entry.get("attempt_count", 0)
    
    # Calculate backoff: 5 minutes base, doubles with each attempt
    # Max 60 minutes
    backoff_minutes = min(5 * (2 ** attempt_count), 60)
    next_attempt = datetime.now(timezone.utc) + timedelta(minutes=backoff_minutes)
    
    retry_queue[drive_name] = {
        "next_attempt": next_attempt.isoformat(),
        "attempt_count": attempt_count + 1,
        "last_error": error,
    }
    
    # Also record as a failed trigger
    drive = state.get("drives", {}).get(drive_name, {})
    record_trigger(
        state,
        drive_name,
        drive.get("pressure", 0.0),
        drive.get("threshold", 1.0),
        spawned=False
    )


def tick_with_spawning(config: dict, state: DriveState) -> DriveState:
    """Run engine tick and spawn sessions for triggered drives.
    
    This is the main integration point that wires session spawning
    into the tick cycle. Updates pressures, checks thresholds,
    and spawns at most one session per tick.
    
    Args:
        config: Configuration dict
        state: Current drive state (modified in place)
        
    Returns:
        The updated state dict
        
    Examples:
        >>> config = {"drives": {"cooldown_minutes": 30, "quiet_hours": None}}
        >>> state = create_default_state()
        >>> state["drives"]["CARE"]["pressure"] = 25.0  # Over threshold
        >>> state = tick_with_spawning(config, state)
        >>> # State updated, CARE may be in triggered_drives
    """
    from .engine import tick_all_drives
    
    # Update pressures
    tick_all_drives(state, config)
    
    # Check quiet hours
    if is_quiet_hours(config):
        return state
    
    # Select drive to trigger (max 1 per tick)
    drive_name = select_drive_to_trigger(state, config)
    
    if drive_name:
        drive = state["drives"][drive_name]
        pressure = drive.get("pressure", 0.0)
        threshold = drive.get("threshold", 1.0)
        drive_prompt = drive.get("prompt", f"Your {drive_name} drive triggered.")
        
        # Attempt to spawn session
        spawned = spawn_session(
            drive_name=drive_name,
            prompt=drive_prompt,
            config=config,
            pressure=pressure,
            threshold=threshold
        )
        
        if spawned:
            # Add to triggered list
            if "triggered_drives" not in state:
                state["triggered_drives"] = []
            state["triggered_drives"].append(drive_name)
            
            # Record successful trigger
            record_trigger(state, drive_name, pressure, threshold, True)
            
            # NOTE: Do NOT auto-satisfy here. Satisfaction should only
            # happen after the jarvling completes their session and
            # actually engages with the drive. Satisfying at spawn
            # is "hollow satisfaction" — inauthenticity.
            # The jarvling runs `drives satisfy <name>` when done.
        else:
            # Handle failure
            handle_spawn_failure(state, drive_name, "Session spawn failed")
    
    # Check for completed drive sessions and auto-satisfy (file-based)
    from .satisfaction import check_completed_sessions
    satisfied = check_completed_sessions(state, config)
    if satisfied:
        import sys
        print(f"✓ Satisfied drives: {', '.join(satisfied)}", file=sys.stderr)
    
    return state


# NOTE: The old _check_completed_sessions() that polled the OpenClaw cron API
# has been removed. It never worked because jobs were cleaned up before polling.
# Satisfaction is now handled by core/drives/satisfaction.py using file-based
# breadcrumbs in sessions_ingest/. See satisfaction.py for the full flow.
