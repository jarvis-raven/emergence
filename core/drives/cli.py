"""CLI entry point for the Emergence drive engine.

Provides a human-facing interface to the interoception system with
commands for checking status, satisfying drives, viewing history, etc.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# Import from the drive engine modules
from .config import load_config, get_state_path, find_config, ensure_config_example
from .state import load_state, save_state, StateLock, get_hours_since_tick
from .runtime_state import load_runtime_state, save_runtime_state, extract_runtime_state
from .engine import (
    tick_all_drives,
    check_thresholds,
    satisfy_drive,
    bump_drive,
    reset_all_drives,
    get_drive_status,
    is_quiet_hours,
)
from .utils import fuzzy_match, get_ambiguous_matches, format_pressure_bar
from .history import read_trigger_log, filter_log_entries
from .defaults import ensure_core_drives, load_core_drives
from .daemon import daemon_status, start_daemon, stop_daemon
from .spawn import spawn_session, record_trigger
from .platform import (
    detect_platform,
    install_platform,
    uninstall_platform,
    get_install_status,
)
from .thwarting import (
    is_thwarted,
    get_thwarting_status,
    get_thwarted_drives,
    format_thwarting_message,
    get_thwarting_emoji,
)


# --- Constants ---
VERSION = "1.0.0"
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_USAGE = 2

# --- Status Indicators ---
INDICATOR_NORMAL = "▫"      # <75%
INDICATOR_ELEVATED = "⚡"    # 75-99%
INDICATOR_OVER = "🔥"       # >=100%
INDICATOR_TRIGGERED = "⏸"   # Triggered, awaiting satisfaction

# --- Colors for terminal output ---
COLOR_RESET = "\033[0m"
COLOR_CORE = "\033[36m"      # Cyan for core drives
COLOR_DISCOVERED = "\033[33m"  # Yellow for discovered drives
COLOR_LATENT = "\033[90m"    # Gray for latent drives
COLOR_BUDGET_LOW = "\033[32m"   # Green
COLOR_BUDGET_MED = "\033[33m"   # Yellow
COLOR_BUDGET_HIGH = "\033[31m"  # Red
COLOR_DIM = "\033[90m"
COLOR_WARNING = "\033[33m"      # Yellow for warnings


# --- Helper Functions ---

def get_indicator(status: str) -> str:
    """Get the visual indicator for a drive status."""
    return {
        "normal": INDICATOR_NORMAL,
        "elevated": INDICATOR_ELEVATED,
        "over_threshold": INDICATOR_OVER,
        "triggered": INDICATOR_TRIGGERED,
    }.get(status, INDICATOR_NORMAL)


def get_state_and_config(args) -> tuple:
    """Load state and config, handling errors appropriately."""
    config_path = getattr(args, 'config', None)
    config = load_config(Path(config_path) if config_path else None)
    state_path = get_state_path(config)
    
    # Ensure state directory exists
    state_path.parent.mkdir(parents=True, exist_ok=True)
    
    state = load_state(state_path)
    
    # Ensure core drives exist
    ensure_core_drives(state)
    
    return state, config, state_path


def get_runtime_state_and_config(args) -> tuple:
    """Load lightweight runtime state and config.
    
    This loads only drives-state.json (pressure, threshold, status)
    without the full descriptions, prompts, and history from drives.json.
    Use this for regular status checks to prevent context bloat.
    
    Returns:
        Tuple of (runtime_state, config, runtime_state_path)
    """
    config_path = getattr(args, 'config', None)
    config = load_config(Path(config_path) if config_path else None)
    
    # Get runtime state path (drives-state.json, not drives.json)
    state_dir = Path(get_state_path(config)).parent
    runtime_state_path = state_dir / "drives-state.json"
    
    # Ensure state directory exists
    runtime_state_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Load lightweight runtime state
    runtime_state = load_runtime_state(runtime_state_path)
    
    return runtime_state, config, runtime_state_path


def save_with_lock(state_path: Path, state: dict) -> bool:
    """Save state with advisory locking."""
    with StateLock(state_path, timeout=5.0) as lock:
        if not lock.acquired:
            print("⚠ State file locked by another process", file=sys.stderr)
            return False
        save_state(state_path, state)
        return True


def fuzzy_find_drive(drive_name: str, state: dict) -> Optional[str]:
    """Find a drive by fuzzy matching, with error output if not found."""
    drives = state.get("drives", {})
    normalized = fuzzy_match(drive_name, list(drives.keys()))
    
    if normalized:
        return normalized
    
    # Check for ambiguous matches
    ambiguous = get_ambiguous_matches(drive_name, list(drives.keys()))
    
    if len(ambiguous) == 1:
        return ambiguous[0]
    
    if len(ambiguous) > 1:
        print(f"✗ Ambiguous drive name: \"{drive_name}\"", file=sys.stderr)
        print(f"  Matches: {', '.join(ambiguous)}", file=sys.stderr)
        return None
    
    # No match at all
    available = ", ".join(sorted(drives.keys()))
    print(f"✗ Unknown drive: {drive_name}", file=sys.stderr)
    
    # Suggest closest match
    for candidate in drives.keys():
        if candidate.lower().startswith(drive_name.lower()[:2]):
            print(f"  Did you mean: {candidate}?", file=sys.stderr)
            break
    
    print(f"  Available drives: {available}", file=sys.stderr)
    return None


def get_pending_reviews_path(config: dict) -> Path:
    """Get path to pending reviews file."""
    state_dir = config.get("paths", {}).get("state", ".emergence/state")
    workspace = config.get("paths", {}).get("workspace", ".")
    return Path(workspace) / state_dir / "pending-reviews.json"


def load_pending_reviews(config: dict) -> list:
    """Load pending drive consolidation reviews."""
    reviews_path = get_pending_reviews_path(config)
    if not reviews_path.exists():
        return []
    try:
        with open(reviews_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def get_budget_info(config: dict, state: dict) -> dict:
    """Calculate budget information for display.
    
    If budget is disabled (drives.budget.enabled = false), returns
    a minimal dict with enabled=False for callers to skip display.
    """
    drives_config = config.get("drives", {})
    budget_config = drives_config.get("budget", {})
    
    if not budget_config.get("enabled", True):
        return {"enabled": False, "daily_spend": 0.0, "daily_limit": 0.0, "percent_used": 0.0}
    
    daily_limit = budget_config.get("daily_limit", 50.0)
    cost_per_trigger = budget_config.get("cost_per_trigger", 2.50)
    
    # Calculate daily spend from trigger log
    trigger_log = state.get("trigger_log", [])
    today = datetime.now(timezone.utc).date()
    
    daily_spend = 0.0
    for entry in trigger_log:
        ts_str = entry.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str)
            if ts.date() == today and entry.get("session_spawned"):
                daily_spend += cost_per_trigger
        except (ValueError, TypeError):
            continue
    
    # Calculate projected costs
    drives = state.get("drives", {})
    active_drives = {k: v for k, v in drives.items() if v.get("status") != "latent"}
    
    # Estimate triggers per day based on drive rates and thresholds
    total_triggers_per_day = 0.0
    for name, drive in active_drives.items():
        rate = drive.get("rate_per_hour", 0.0)
        threshold = drive.get("threshold", 20.0)
        if rate > 0 and threshold > 0:
            # Time to trigger = threshold / rate hours
            # Triggers per day = 24 / time_to_trigger
            time_to_trigger = threshold / rate
            triggers_per_day = 24.0 / time_to_trigger if time_to_trigger > 0 else 0
            total_triggers_per_day += triggers_per_day
    
    projected_daily_cost = total_triggers_per_day * cost_per_trigger
    projected_monthly_cost = projected_daily_cost * 30
    
    return {
        "daily_limit": daily_limit,
        "daily_spend": daily_spend,
        "percent_used": (daily_spend / daily_limit * 100) if daily_limit > 0 else 0,
        "projected_triggers_per_day": total_triggers_per_day,
        "projected_daily_cost": projected_daily_cost,
        "projected_monthly_cost": projected_monthly_cost,
        "cost_per_trigger": cost_per_trigger,
    }


def get_cooldown_status(state: dict, config: dict) -> dict:
    """Get cooldown status for display."""
    cooldown_minutes = config.get("drives", {}).get("cooldown_minutes", 30)
    trigger_log = state.get("trigger_log", [])
    
    if not trigger_log:
        return {"ready": True, "last_trigger_ago": None, "ready_in_minutes": 0}
    
    # Find last triggered session
    last_trigger = None
    for entry in reversed(trigger_log):
        if entry.get("session_spawned"):
            last_trigger = entry
            break
    
    if not last_trigger:
        return {"ready": True, "last_trigger_ago": None, "ready_in_minutes": 0}
    
    ts_str = last_trigger.get("timestamp", "")
    try:
        last_ts = datetime.fromisoformat(ts_str)
        now = datetime.now(timezone.utc)
        minutes_ago = int((now - last_ts).total_seconds() / 60)
        
        ready_in = max(0, cooldown_minutes - minutes_ago)
        
        return {
            "ready": ready_in <= 0,
            "last_trigger_ago": minutes_ago,
            "ready_in_minutes": ready_in,
            "cooldown_minutes": cooldown_minutes,
        }
    except (ValueError, TypeError):
        return {"ready": True, "last_trigger_ago": None, "ready_in_minutes": 0}


def find_graduation_candidates(state: dict) -> list:
    """Find aspects that have >50% pressure dominance and could graduate."""
    candidates = []
    drives = state.get("drives", {})
    
    for name, drive in drives.items():
        aspects = drive.get("aspects", [])
        if not aspects:
            continue
        
        # Check satisfaction history for aspect dominance
        # This is a simplified check - in production would analyze breakdown
        # For now, check if drive has many satisfactions suggesting rich activity
        satisfaction_events = drive.get("satisfaction_events", [])
        if len(satisfaction_events) >= 10:
            # Check if the drive has been around for 14+ days
            created_at = drive.get("created_at", "")
            if created_at:
                try:
                    created = datetime.fromisoformat(created_at)
                    now = datetime.now(timezone.utc)
                    days_old = (now - created).days
                    if days_old >= 14:
                        for aspect in aspects:
                            candidates.append({
                                "aspect": aspect,
                                "parent_drive": name,
                                "satisfactions": len(satisfaction_events),
                                "days_old": days_old,
                            })
                except (ValueError, TypeError):
                    continue
    
    return candidates


def format_time_ago(minutes: int) -> str:
    """Format minutes ago into human readable string."""
    if minutes < 1:
        return "just now"
    elif minutes == 1:
        return "1m ago"
    elif minutes < 60:
        return f"{minutes}m ago"
    elif minutes < 120:
        return "1h ago"
    else:
        hours = minutes // 60
        return f"{hours}h ago"


def format_time_remaining(minutes: int) -> str:
    """Format remaining minutes into human readable string."""
    if minutes <= 0:
        return "Ready"
    elif minutes < 60:
        return f"Ready in {minutes}m"
    else:
        hours = minutes // 60
        mins = minutes % 60
        if mins == 0:
            return f"Ready in {hours}h"
        return f"Ready in {hours}h {mins}m"


def format_elapsed_time(hours: float) -> str:
    """Format elapsed hours into human readable string."""
    if hours < 1:
        minutes = int(hours * 60)
        return f"{minutes}m elapsed"
    elif hours < 24:
        return f"{hours:.1f}h elapsed"
    else:
        days = hours / 24
        return f"{days:.1f}d elapsed"


def get_elapsed_since_last_satisfaction(drive: dict) -> Optional[float]:
    """Get hours elapsed since last satisfaction event."""
    events = drive.get("satisfaction_events", [])
    if not events:
        return None
    
    last = events[-1]
    try:
        ts = datetime.fromisoformat(last)
        now = datetime.now(timezone.utc)
        hours = (now - ts).total_seconds() / 3600
        return hours
    except (ValueError, TypeError):
        return None


# --- Command Implementations ---

def cmd_status(args) -> int:
    """Show drive status with pressure bars."""
    # Use lightweight runtime state for status display (prevents context bloat)
    # This loads drives-state.json (pressure/threshold only) not drives.json (full config)
    runtime_state, config, runtime_state_path = get_runtime_state_and_config(args)
    
    drives = runtime_state.get("drives", {})
    
    # Get triggered drives from full state (needed for status display)
    # This is a quick load just for triggered status
    try:
        full_state_path = runtime_state_path.parent / "drives.json"
        if full_state_path.exists():
            with open(full_state_path, 'r') as f:
                full_state = json.load(f)
            triggered = set(full_state.get("triggered_drives", []))
        else:
            triggered = set()
    except (IOError, json.JSONDecodeError):
        triggered = set()
    
    show_latent = getattr(args, 'show_latent', False)
    show_latent = getattr(args, 'show_latent', False)
    
    # Get last tick info from runtime state
    last_tick_str = runtime_state.get("last_tick", "")
    try:
        last_tick = datetime.fromisoformat(last_tick_str)
        now = datetime.now(timezone.utc)
        mins_ago = int((now - last_tick).total_seconds() / 60)
        updated_text = format_time_ago(mins_ago)
    except (ValueError, TypeError):
        updated_text = "unknown"
    
    # Check if JSON output requested
    if getattr(args, 'json', False):
        output = {
            "last_updated": last_tick_str,
            "drives": [],
            "triggered": list(triggered),
            "quiet_hours_active": is_quiet_hours(config),
        }
        for name, drive in drives.items():
            pressure = drive.get("pressure", 0.0)
            threshold = drive.get("threshold", 1.0)
            ratio = pressure / threshold if threshold > 0 else 0.0
            
            if name in triggered:
                status = "triggered"
            elif ratio >= 1.0:
                status = "over_threshold"
            elif ratio >= 0.75:
                status = "elevated"
            else:
                status = "normal"
            
            # Runtime state only has pressure, threshold, status
            # Category/aspects come from full drives.json (not loaded for context bloat prevention)
            output["drives"].append({
                "name": name,
                "pressure": round(pressure, 2),
                "threshold": threshold,
                "ratio": round(ratio, 2),
                "status": status,
                "category": "unknown",  # Not available in runtime state
                "aspects": [],  # Not available in runtime state
                "status_field": None,  # Not available in runtime state
            })
        
        # Add budget and reviews info (use full_state for budget info)
        try:
            budget = get_budget_info(config, full_state)
        except:
            budget = {"daily_spend": 0.0, "daily_limit": 50.0, "percent_used": 0.0}
        output["budget"] = budget
        output["pending_reviews"] = len(load_pending_reviews(config))
        
        print(json.dumps(output, indent=2))
        return EXIT_SUCCESS
    
    # Load full state only for budget/cooldown info (not for basic drive display)
    # This prevents loading full drive config (descriptions, prompts, history) into context
    try:
        full_state_path = runtime_state_path.parent / "drives.json"
        if full_state_path.exists():
            full_state = load_state(full_state_path)
        else:
            full_state = runtime_state  # Fallback to runtime state
    except:
        full_state = runtime_state
    
    # Get additional info for display (these need full state)
    budget_info = get_budget_info(config, full_state)
    cooldown_info = get_cooldown_status(full_state, config)
    pending_reviews = load_pending_reviews(config)
    graduation_candidates = find_graduation_candidates(full_state)
    
    # Header
    print(f"🧠 Drive Status (updated {updated_text})")
    
    # Budget line with color (skip if disabled)
    if budget_info.get("enabled", True) is not False:
        percent = budget_info["percent_used"]
        if percent >= 90:
            budget_color = COLOR_BUDGET_HIGH
        elif percent >= 75:
            budget_color = COLOR_BUDGET_MED
        else:
            budget_color = COLOR_BUDGET_LOW
        
        print(f"Budget: {budget_color}${budget_info['daily_spend']:.2f} / ${budget_info['daily_limit']:.2f} daily ({percent:.0f}%){COLOR_RESET}")
        
        # Warn if using default cost estimate
        if budget_info.get("cost_per_trigger") == 2.50:
            print(f"{COLOR_WARNING}  ⚠️  Using default cost estimate ($2.50/trigger). For accurate tracking,")
            print(f"     set 'cost_per_trigger' in emergence.json drives.budget config.{COLOR_RESET}")
    else:
        print(f"Budget: {COLOR_BUDGET_LOW}unlimited (subscription){COLOR_RESET}")
    
    # Cooldown line
    if cooldown_info["last_trigger_ago"] is not None:
        last_trigger_text = format_time_ago(cooldown_info["last_trigger_ago"])
        if cooldown_info["ready"]:
            print(f"Cooldown: {COLOR_BUDGET_LOW}Ready{COLOR_RESET} (last trigger {last_trigger_text})")
        else:
            ready_text = format_time_remaining(cooldown_info["ready_in_minutes"])
            print(f"Cooldown: {COLOR_BUDGET_MED}{ready_text}{COLOR_RESET} (last trigger {last_trigger_text})")
    else:
        print(f"Cooldown: {COLOR_BUDGET_LOW}Ready{COLOR_RESET}")
    
    print("─" * 52)
    
    # Separate drives by status (runtime state only has pressure/threshold/status)
    # Core vs discovered distinction requires full drives.json (not loaded to prevent bloat)
    active_drives = []
    latent_drives = []
    
    for name, drive in drives.items():
        drive_status = drive.get("status")
        
        if drive_status == "latent":
            latent_drives.append((name, drive))
        else:
            active_drives.append((name, drive))
    
    # Active Drives section (core vs discovered not distinguishable in runtime state)
    if active_drives:
        print(f"\n{COLOR_CORE}Active Drives:{COLOR_RESET}")
        for name, drive in sorted(active_drives, key=lambda x: x[0]):
            _print_drive_line(name, drive, triggered, cooldown_info)
    
    # Thwarted Drives section (issue #41)
    thwarted_drives = get_thwarted_drives(full_state, config)
    if thwarted_drives:
        print(f"\n{COLOR_BUDGET_HIGH}⚠️  Thwarted Drives:{COLOR_RESET} {len(thwarted_drives)}")
        for thw in thwarted_drives[:5]:  # Show up to 5
            drive_name = thw["name"]
            msg = format_thwarting_message(drive_name, thw)
            print(f"  {COLOR_BUDGET_HIGH}⚠{COLOR_RESET} {msg}")
        if len(thwarted_drives) > 5:
            print(f"  ... and {len(thwarted_drives) - 5} more")
        print(f"    {COLOR_DIM}These drives need immediate attention or investigation{COLOR_RESET}")
        print(f"    {COLOR_DIM}Use 'drives satisfy <name> deep' or 'full' for relief{COLOR_RESET}")
    
    # Pending Reviews section
    if pending_reviews:
        print(f"\n{COLOR_BUDGET_MED}Pending Reviews:{COLOR_RESET} {len(pending_reviews)}")
        for review in pending_reviews[:3]:  # Show up to 3
            new_drive = review.get("new_drive", "Unknown")
            similar = review.get("similar_drives", [])
            similar_names = [s.get("name", "?") for s in similar[:2]]
            print(f"  → {new_drive} - Similar to {', '.join(similar_names)}")
        if len(pending_reviews) > 3:
            print(f"  ... and {len(pending_reviews) - 3} more")
        print(f"    {COLOR_DIM}Run: drives review{COLOR_RESET}")
    
    # Latent Drives section (if --show-latent)
    if show_latent and latent_drives:
        print(f"\n{COLOR_LATENT}Latent Drives:{COLOR_RESET}")
        for name, drive in sorted(latent_drives, key=lambda x: x[0]):
            reason = drive.get("latent_reason", "Consolidated as aspect")
            print(f"  ○ {name} - {reason}")
            parent = drive.get("aspect_of")
            if parent:
                print(f"    {COLOR_DIM}Part of: {parent}{COLOR_RESET}")
    
    # Graduation Candidates section
    if graduation_candidates:
        print(f"\n{COLOR_BUDGET_MED}Graduation Candidates:{COLOR_RESET}")
        for candidate in graduation_candidates[:3]:
            aspect = candidate["aspect"]
            parent = candidate["parent_drive"]
            sats = candidate["satisfactions"]
            days = candidate["days_old"]
            print(f"  ↑ {aspect} ({parent}) - {sats} satisfactions, {days} days")
        if len(graduation_candidates) > 3:
            print(f"  ... and {len(graduation_candidates) - 3} more")
    
    # Footer separator and projection
    print("─" * 52)
    
    triggers = budget_info["projected_triggers_per_day"]
    daily_cost = budget_info["projected_daily_cost"]
    monthly_cost = budget_info["projected_monthly_cost"]
    
    print(f"Projected: ~{triggers:.0f} triggers/day (~${daily_cost:.0f}/day, ${monthly_cost:.0f}/month)")
    
    # Show triggered drives alert
    if triggered:
        print()
        triggered_list = ", ".join(sorted(triggered))
        print(f"{COLOR_BUDGET_HIGH}⏸ Triggered & waiting: {triggered_list}{COLOR_RESET}")
        print(f"   Use 'emergence drives satisfy <name>' to reset after addressing.")
    
    # Show quiet hours
    if is_quiet_hours(config):
        quiet_start, quiet_end = config.get("drives", {}).get("quiet_hours", [23, 7])
        print(f"\n{COLOR_DIM}ℹ Quiet hours active ({quiet_start:02d}:00-{quiet_end:02d}:00) — triggers queued{COLOR_RESET}")
    
    return EXIT_SUCCESS


def _print_drive_line(name: str, drive: dict, triggered: set, cooldown_info: dict) -> None:
    """Print a single drive line with status indicator and pressure bar."""
    from .models import get_drive_thresholds, get_threshold_label
    
    pressure = drive.get("pressure", 0.0)
    threshold = drive.get("threshold", 1.0)
    ratio = pressure / threshold if threshold > 0 else 0.0
    
    # Get threshold band
    thresholds = get_drive_thresholds(drive)
    band = get_threshold_label(pressure, thresholds)
    
    # Determine status
    if name in triggered:
        status = "triggered"
    elif ratio >= 1.0:
        status = "over_threshold"
    elif ratio >= 0.75:
        status = "elevated"
    else:
        status = "normal"
    
    indicator = get_indicator(status)
    pct = int(ratio * 100)
    
    # Pad name to 14 chars
    name_padded = name.ljust(14)
    
    # Build pressure bar (20 chars wide)
    width = 20
    display_ratio = min(ratio, 1.5)
    filled = int(display_ratio * width)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    
    # Band-based color coding
    band_colors = {
        "available": COLOR_DIM,
        "elevated": COLOR_BUDGET_LOW,
        "triggered": COLOR_BUDGET_MED,
        "crisis": COLOR_BUDGET_HIGH,
        "emergency": COLOR_BUDGET_HIGH,
    }
    band_color = band_colors.get(band, "")
    
    # Thwarting and valence indicator (issue #41)
    thwarting_status = get_thwarting_status(drive)
    valence_indicator = get_thwarting_emoji(thwarting_status)
    
    # Status text with band info
    if status == "triggered":
        status_text = f"{COLOR_BUDGET_HIGH}Triggered{COLOR_RESET} ({band_color}{band}{COLOR_RESET})"
    elif status == "over_threshold":
        remaining = cooldown_info.get("ready_in_minutes", 0)
        if remaining > 0:
            status_text = f"{format_time_remaining(remaining)} ({band_color}{band}{COLOR_RESET})"
        else:
            status_text = f"{COLOR_BUDGET_HIGH}Over threshold{COLOR_RESET} ({band_color}{band}{COLOR_RESET})"
    elif status == "elevated":
        elapsed = get_elapsed_since_last_satisfaction(drive)
        if elapsed is not None:
            status_text = f"{format_elapsed_time(elapsed)} ({band_color}{band}{COLOR_RESET})"
        else:
            status_text = f"{format_time_remaining(int((1.0 - ratio) * threshold / drive.get('rate_per_hour', 1.0) * 60))} ({band_color}{band}{COLOR_RESET})"
    else:
        if drive.get("activity_driven"):
            status_text = f"Activity-driven ({band_color}{band}{COLOR_RESET})"
        else:
            elapsed = get_elapsed_since_last_satisfaction(drive)
            if elapsed is not None:
                status_text = f"{format_elapsed_time(elapsed)} ({band_color}{band}{COLOR_RESET})"
            else:
                status_text = f"({band_color}{band}{COLOR_RESET})"
    
    print(f"  {indicator} {name_padded} [{bar}] {pct}%  {valence_indicator} {status_text}")
    
    # Show aspects if present
    aspects = drive.get("aspects", [])
    if aspects:
        aspects_str = ", ".join(aspects)
        print(f"     {COLOR_DIM}({len(aspects)} aspect{'s' if len(aspects) > 1 else ''}: {aspects_str}){COLOR_RESET}")


def cmd_review(args) -> int:
    """Review pending drive consolidation decisions."""
    state, config, state_path = get_state_and_config(args)
    
    pending_reviews = load_pending_reviews(config)
    
    if not pending_reviews:
        print("✓ No pending reviews — all caught up!")
        return EXIT_SUCCESS
    
    # If specific drive specified, show just that one
    drive_name = getattr(args, 'drive', None)
    if drive_name:
        review = None
        for r in pending_reviews:
            if r.get("new_drive", "").upper() == drive_name.upper():
                review = r
                break
        
        if not review:
            print(f"✗ No pending review found for: {drive_name}")
            print(f"   Pending reviews: {', '.join(r.get('new_drive', '?') for r in pending_reviews)}")
            return EXIT_ERROR
        
        # Show single review with irreducibility test
        _show_irreducibility_test(review)
        return EXIT_SUCCESS
    
    # Show all pending reviews
    print(f"⚖️  Pending Drive Reviews ({len(pending_reviews)})")
    print("=" * 52)
    
    for i, review in enumerate(pending_reviews, 1):
        new_drive = review.get("new_drive", "Unknown")
        similar = review.get("similar_drives", [])
        discovered_at = review.get("discovered_at", "unknown")
        
        print(f"\n{i}. {new_drive}")
        print(f"   Discovered: {discovered_at[:10] if discovered_at != 'unknown' else 'unknown'}")
        print(f"   Similar to:")
        for s in similar:
            sim_name = s.get("name", "?")
            sim_score = s.get("similarity", 0)
            print(f"      • {sim_name} (similarity: {sim_score:.2f})")
        
        print(f"\n   Actions:")
        print(f"      drives review {new_drive.lower()}  # View irreducibility test")
        print(f"      drives merge {new_drive.lower()} --into DRIVE  # Merge as aspect")
        print(f"      drives keep {new_drive.lower()}  # Keep as distinct drive")
    
    print("\n" + "=" * 52)
    print(f"Run 'drives review <name>' to see the irreducibility test for a specific drive")
    
    return EXIT_SUCCESS


def _show_irreducibility_test(review: dict) -> None:
    """Display the irreducibility test prompt for a review."""
    new_drive = review.get("new_drive", "Unknown")
    new_desc = review.get("description", "No description")
    similar = review.get("similar_drives", [])
    
    print(f"\n🧠 Irreducibility Test: {new_drive}")
    print("=" * 60)
    print(f"\nNew drive discovered: {new_drive}")
    print(f"Description: {new_desc}")
    
    if similar:
        print(f"\nThis seems related to existing drive(s):")
        for s in similar[:3]:
            sim_name = s.get("name", "?")
            sim_desc = s.get("description", "No description")
            sim_score = s.get("similarity", 0)
            print(f"\n  • {sim_name} (similarity: {sim_score:.2f})")
            print(f"    Description: {sim_desc}")
    
    print("\n" + "-" * 60)
    print("\nIRREDUCIBILITY TEST:")
    print()
    
    if similar:
        primary = similar[0].get("name", "existing drive")
        print(f"Ask yourself: 'Can I fully satisfy {new_drive} by satisfying {primary}?'")
        print()
        print("Test both directions:")
        print(f"  1. Does satisfying {primary} always satisfy {new_drive}?")
        print(f"  2. Does satisfying {new_drive} always satisfy {primary}?")
        print()
        print("If YES to either → ASPECT (merge into existing drive)")
        print("If NO to both → DISTINCT (keep as separate drive)")
        print()
        print("What makes this drive irreducible (if it is)?")
        print("What unique satisfaction does it provide?")
    
    print("\n" + "-" * 60)
    print("\nDECISION:")
    print()
    print(f"  [ ] DISTINCT - Keep {new_drive} as a separate drive")
    if similar:
        primary = similar[0].get("name", "existing drive")
        print(f"  [ ] ASPECT - Merge {new_drive} into {primary}")
    print()
    print("Commands:")
    print(f"  drives keep {new_drive.lower()}     # Mark as distinct")
    if similar:
        primary = similar[0].get("name", "existing drive")
        print(f"  drives merge {new_drive.lower()} --into {primary}  # Merge as aspect")


def cmd_satisfy(args) -> int:
    """Satisfy a drive (reduce pressure) with auto-scaling or explicit depth."""
    from .satisfaction import calculate_satisfaction_depth
    
    state, config, state_path = get_state_and_config(args)
    
    if not args.name:
        print("✗ Usage: drives satisfy <drive_name> [depth]", file=sys.stderr)
        return EXIT_USAGE
    
    drive_name = fuzzy_find_drive(args.name, state)
    if not drive_name:
        return EXIT_ERROR
    
    drive = state["drives"][drive_name]
    old_pressure = drive.get("pressure", 0.0)
    threshold = drive.get("threshold", 1.0)
    
    if old_pressure == 0.0:
        print(f"ℹ {drive_name} is already at 0.0 — nothing to satisfy")
        return EXIT_SUCCESS
    
    # Determine depth - use auto-scaling if not specified
    depth_arg = getattr(args, 'depth', None)
    auto_scaled = False
    band_name = None
    
    if depth_arg:
        # Explicit depth provided - normalize it
        depth_map = {
            's': 'shallow', 'shallow': 'shallow',
            'm': 'moderate', 'moderate': 'moderate',
            'd': 'deep', 'deep': 'deep',
            'f': 'full', 'full': 'full',
        }
        depth = depth_map.get(depth_arg.lower(), depth_arg.lower())
    else:
        # No depth provided - use auto-scaling based on pressure and threshold bands
        from .models import get_drive_thresholds
        auto_scaled = True
        thresholds = get_drive_thresholds(drive, config.get("drives", {}).get("thresholds"))
        band_name, depth_label, reduction_ratio = calculate_satisfaction_depth(
            old_pressure, threshold, thresholds
        )
        
        # Map auto-scaled reductions to standard depth names for satisfy_drive()
        # We'll manually apply the custom reduction ratio
        depth = depth_label
    
    # Apply satisfaction (custom reduction for auto-scaled, standard for explicit)
    if auto_scaled:
        # Manual pressure reduction with auto-scaled ratio
        from .models import get_drive_thresholds
        from .satisfaction import log_satisfaction
        thresholds = get_drive_thresholds(drive, config.get("drives", {}).get("thresholds"))
        band_name, _, reduction_ratio = calculate_satisfaction_depth(old_pressure, threshold, thresholds)
        new_pressure = max(0.0, old_pressure * (1.0 - reduction_ratio))
        drive["pressure"] = new_pressure
        
        # Record satisfaction event
        if "satisfaction_events" not in drive:
            drive["satisfaction_events"] = []
        
        now = datetime.now(timezone.utc).isoformat()
        drive["satisfaction_events"].append(now)
        drive["satisfaction_events"] = drive["satisfaction_events"][-10:]
        
        # Remove from triggered list if reduction is significant (>= 50%)
        if reduction_ratio >= 0.5 and drive_name in state.get("triggered_drives", []):
            state["triggered_drives"].remove(drive_name)
        
        # Log satisfaction history
        log_satisfaction(
            drive_name=drive_name,
            pressure_before=old_pressure,
            pressure_after=new_pressure,
            band=band_name,
            depth=depth,
            ratio=reduction_ratio,
            source="manual"
        )
        
        result = {
            "success": True,
            "drive": drive_name,
            "old_pressure": old_pressure,
            "new_pressure": new_pressure,
            "reduction_ratio": reduction_ratio,
            "depth": depth,
            "band": band_name,
        }
    else:
        # Use standard satisfy_drive() for explicit depths
        try:
            result = satisfy_drive(state, drive_name, depth)
        except ValueError as e:
            print(f"✗ {e}", file=sys.stderr)
            return EXIT_ERROR
    
    # Save state
    if not save_with_lock(state_path, state):
        return EXIT_ERROR

    # !!! FIX: Update and save runtime state as well !!!
    # Reload runtime state to ensure consistency, then update it
    # Use the same args so config and state path resolution is consistent
    runtime_state, _config_dummy, runtime_state_path = get_runtime_state_and_config(args)
    
    # Update attributes in runtime_state specific to satisfaction
    if drive_name in runtime_state.get("drives", {}):
        new_pressure_val = state["drives"][drive_name].get("pressure", 0.0)
        runtime_state["drives"][drive_name]["pressure"] = new_pressure_val
        runtime_state["drives"][drive_name]["status"] = "idle" if new_pressure_val <= 0 else "building"
        if drive_name in runtime_state.get("triggered", []):
            runtime_state["triggered"] = [d for d in runtime_state["triggered"] if d != drive_name]
    
    save_runtime_state(runtime_state_path, runtime_state)
    # !!! END FIX !!!
    
    new_pressure = result["new_pressure"]
    reduction = result["reduction_ratio"]
    reduction_pct = int(reduction * 100)
    
    # Display results with auto-scaling info if applicable
    pressure_pct = int((old_pressure / threshold) * 100) if threshold > 0 else 0
    
    if auto_scaled:
        band_display = result.get("band", "unknown")
        print(f"✓ {drive_name} satisfied ({old_pressure:.1f} → {new_pressure:.1f}) [band: {band_display}]")
        print(f"  Pressure reduced by {reduction_pct}% (auto-scaled: {band_display} threshold)")
    else:
        print(f"✓ {drive_name} satisfied ({old_pressure:.1f} → {new_pressure:.1f}) [{depth}]")
        print(f"  Pressure reduced by {reduction_pct}%")
    
    # Show next steps if not fully satisfied
    if new_pressure > 0.0:
        if auto_scaled:
            print(f"  For more relief, use explicit depth: 'drives satisfy {drive_name.lower()} deep' or 'full'")
        elif depth not in ('full', 'f'):
            remaining = "deep" if depth in ('shallow', 'moderate') else "full"
            print(f"  Use 'drives satisfy {drive_name.lower()} {remaining}' for more reduction")
    
    # Show triggered status
    if drive_name in state.get("triggered_drives", []):
        print(f"  Still in triggered list — reduction not sufficient")
    else:
        if old_pressure >= threshold:  # Was over threshold
            print(f"  Removed from triggered drives list")
    
    return EXIT_SUCCESS


def cmd_bump(args) -> int:
    """Bump a drive (increase pressure)."""
    state, config, state_path = get_state_and_config(args)
    
    if not args.name:
        print("✗ Usage: drives bump <drive_name> [amount]", file=sys.stderr)
        return EXIT_USAGE
    
    drive_name = fuzzy_find_drive(args.name, state)
    if not drive_name:
        return EXIT_ERROR
    
    # Get amount if specified
    amount = None
    if hasattr(args, 'amount') and args.amount is not None:
        try:
            amount = float(args.amount)
        except (ValueError, TypeError):
            print(f"✗ Invalid amount: {args.amount}", file=sys.stderr)
            return EXIT_USAGE
    
    drive = state["drives"][drive_name]
    old_pressure = drive.get("pressure", 0.0)
    rate = drive.get("rate_per_hour", 0.0)
    
    try:
        result = bump_drive(state, drive_name, amount)
    except ValueError as e:
        print(f"✗ {e}", file=sys.stderr)
        return EXIT_ERROR
    
    # Save state
    if not save_with_lock(state_path, state):
        return EXIT_ERROR
    
    new_pressure = result["new_pressure"]
    amount_added = result["amount_added"]
    
    print(f"⬆ {drive_name}: {old_pressure:.1f} → {new_pressure:.1f} (+{amount_added:.1f})")
    
    if amount is None:
        print(f"  Added 2 hours worth of pressure (rate: {rate}/hour)")
    
    threshold = drive.get("threshold", 1.0)
    if new_pressure >= threshold:
        print(f"  Now at {int(new_pressure/threshold*100)}% — will trigger on next tick")
    
    # Log reason if provided
    reason = getattr(args, 'reason', None)
    if reason:
        print(f"  Reason logged: {reason}")
    
    return EXIT_SUCCESS


def cmd_reset(args) -> int:
    """Reset all drives to zero."""
    state, config, state_path = get_state_and_config(args)
    
    triggered_count = len(state.get("triggered_drives", []))
    
    # Confirm unless --force
    if not getattr(args, 'force', False):
        print("⚠ This will reset ALL drives to 0.0")
        print("  This cannot be undone.")
        print()
        
        try:
            response = input("Reset all drives? [y/N] ")
        except (EOFError, KeyboardInterrupt):
            print()
            print("Cancelled — no changes made")
            return EXIT_SUCCESS
        
        if response.lower().strip() != 'y':
            print("Cancelled — no changes made")
            return EXIT_SUCCESS
    
    result = reset_all_drives(state)
    
    # Save state
    if not save_with_lock(state_path, state):
        return EXIT_ERROR
    
    print(f"✓ All drives reset to 0.0")
    if triggered_count > 0:
        print(f"  {triggered_count} triggered drive{'s' if triggered_count > 1 else ''} cleared")
    
    return EXIT_SUCCESS


def cmd_log(args) -> int:
    """Show trigger/satisfaction history."""
    state, config, state_path = get_state_and_config(args)
    
    # Get number of entries (default 20)
    n = 20
    if hasattr(args, 'n') and args.n is not None:
        try:
            n = int(args.n)
        except (ValueError, TypeError):
            pass
    
    # Read log entries
    trigger_log = state.get("trigger_log", [])
    
    if not trigger_log:
        print("ℹ No trigger log yet. Events will appear here once drives trigger.")
        return EXIT_SUCCESS
    
    # Filter by drive if specified
    drive_filter = getattr(args, 'drive', None)
    if drive_filter:
        trigger_log = [e for e in trigger_log if e.get("drive", "").lower() == drive_filter.lower()]
        if not trigger_log:
            print(f"ℹ No events found for drive: {drive_filter}")
            return EXIT_SUCCESS
    
    # Filter by time if specified
    since_filter = getattr(args, 'since', None)
    if since_filter:
        trigger_log = filter_log_entries(trigger_log, since=since_filter)
    
    # Get last n entries
    trigger_log = trigger_log[-n:]
    
    print(f"📋 Last {len(trigger_log)} trigger events:")
    print("─" * 52)
    
    for entry in trigger_log:
        ts_str = entry.get("timestamp", "")
        try:
            ts = datetime.fromisoformat(ts_str)
            ts_formatted = ts.strftime("%Y-%m-%d %H:%M")
        except (ValueError, TypeError):
            ts_formatted = ts_str[:16] if ts_str else "unknown"
        
        drive = entry.get("drive", "UNKNOWN")
        pressure = entry.get("pressure", 0.0)
        threshold = entry.get("threshold", 1.0)
        
        event_type = "TRIGGERED"
        if "satisfied" in entry.get("reason", "").lower():
            event_type = "SATISFIED"
        elif entry.get("session_spawned"):
            event_type = "TRIGGERED → spawned session"
        
        print(f"{ts_formatted}  {drive:12} {pressure:.1f}/{threshold:.0f}   {event_type}")
    
    return EXIT_SUCCESS


def cmd_tick(args) -> int:
    """Run a manual tick (update pressures and check triggers)."""
    state, config, state_path = get_state_and_config(args)
    
    dry_run = getattr(args, 'dry_run', False)
    verbose = getattr(args, 'verbose', False)
    
    hours_elapsed = get_hours_since_tick(state)
    
    if dry_run:
        print(f"[DRY RUN] Would update drives after {hours_elapsed:.2f}h")
    else:
        print(f"[{datetime.now().strftime('%H:%M')}] Updated drives after {hours_elapsed:.2f}h")
    
    # Run tick
    changes = tick_all_drives(state, config)
    
    # Show changes
    for name, (old, new) in changes.items():
        drive = state["drives"][name]
        threshold = drive.get("threshold", 1.0)
        old_pct = int((old / threshold) * 100) if threshold > 0 else 0
        new_pct = int((new / threshold) * 100) if threshold > 0 else 0
        
        delta = new - old
        if verbose:
            rate = drive.get("rate_per_hour", 0.0)
            print(f"  {name}: {old:.1f} → {new:.1f} (+{delta:.1f}) [rate: {rate}/hour]")
        else:
            print(f"  {name}: {old:.1f}/{threshold:.0f} ({old_pct}%) → {new:.1f}/{threshold:.0f} ({new_pct}%)")
    
    if not changes:
        if verbose:
            print("  No pressure changes (all drives up to date)")
    
    # Check for triggers
    triggered = check_thresholds(state, config, respect_quiet_hours=True)
    
    if triggered:
        for name in triggered:
            drive = state["drives"][name]
            pressure = drive.get("pressure", 0.0)
            threshold = drive.get("threshold", 1.0)
            
            if dry_run:
                print(f"\n[DRY RUN] Would trigger: {name}")
            else:
                prompt = drive.get("prompt", f"Your {name} drive triggered. Address this need.")
                print(f"\n[{datetime.now().strftime('%H:%M')}] 🔥 {name} triggered at {pressure:.1f}/{threshold:.0f}")
                
                # Actually spawn the session
                spawned = spawn_session(name, prompt, config, pressure, threshold)
                
                if spawned:
                    print(f"  ✓ Spawned session via OpenClaw")
                else:
                    print(f"  ✗ Failed to spawn session — will retry next tick")
                
                # Record the trigger event
                record_trigger(state, name, pressure, threshold, spawned)
                
                # Add to triggered drives (even if spawn failed — prevents spam)
                if name not in state.get("triggered_drives", []):
                    state["triggered_drives"].append(name)
    else:
        if verbose:
            print("\n  No drives triggered")
        # Find closest to threshold
        closest_name = None
        closest_ratio = 0.0
        for name, drive in state.get("drives", {}).items():
            if name in state.get("triggered_drives", []):
                continue
            pressure = drive.get("pressure", 0.0)
            threshold = drive.get("threshold", 1.0)
            ratio = pressure / threshold if threshold > 0 else 0.0
            if ratio > closest_ratio:
                closest_ratio = ratio
                closest_name = name
        
        if closest_name and closest_ratio < 1.0:
            remaining_pct = int((1.0 - closest_ratio) * 100)
            print(f"\n  Closest: {closest_name} at {int(closest_ratio*100)}% (need {remaining_pct}% more)")
    
    # Check quiet hours
    if is_quiet_hours(config):
        quiet_start, quiet_end = config.get("drives", {}).get("quiet_hours", [23, 7])
        print(f"\n  ℹ Quiet hours active ({quiet_start:02d}:00-{quiet_end:02d}:00)")
        print(f"    Pressures updated but no sessions spawned")
    
    # Save state if not dry run
    if not dry_run:
        if not save_with_lock(state_path, state):
            return EXIT_ERROR
    
    return EXIT_SUCCESS


def cmd_list(args) -> int:
    """List all drives with metadata."""
    state, config, state_path = get_state_and_config(args)
    
    drives = state.get("drives", {})
    
    # Filter by category if specified
    category_filter = getattr(args, 'category', None)
    if category_filter:
        drives = {k: v for k, v in drives.items() if v.get("category") == category_filter}
    
    if not drives:
        print("ℹ No drives found")
        return EXIT_SUCCESS
    
    # JSON output
    if getattr(args, 'json', False):
        output = []
        for name, drive in sorted(drives.items()):
            output.append({
                "name": name,
                "category": drive.get("category", "unknown"),
                "threshold": drive.get("threshold", 0.0),
                "rate_per_hour": drive.get("rate_per_hour", 0.0),
                "activity_driven": drive.get("activity_driven", False),
                "description": drive.get("description", ""),
            })
        print(json.dumps(output, indent=2))
        return EXIT_SUCCESS
    
    # Table output
    print(f"{'NAME':<14} {'CATEGORY':<12} {'THRESH':<8} {'RATE':<10} {'ACTIVITY':<10} DESCRIPTION")
    print("─" * 90)
    
    for name, drive in sorted(drives.items()):
        category = drive.get("category", "unknown")
        threshold = drive.get("threshold", 0.0)
        rate = drive.get("rate_per_hour", 0.0)
        activity = "yes" if drive.get("activity_driven") else "—"
        rate_str = f"{rate}/hr" if rate > 0 else "—"
        desc = drive.get("description", "")[:40]
        
        print(f"{name:<14} {category:<12} {threshold:<8.0f} {rate_str:<10} {activity:<10} {desc}")
    
    return EXIT_SUCCESS


def cmd_show(args) -> int:
    """Show detailed info for a single drive."""
    state, config, state_path = get_state_and_config(args)
    
    if not args.name:
        print("✗ Usage: drives show <drive_name>", file=sys.stderr)
        return EXIT_USAGE
    
    drive_name = fuzzy_find_drive(args.name, state)
    if not drive_name:
        return EXIT_ERROR
    
    status = get_drive_status(state, drive_name)
    if not status:
        print(f"✗ Drive not found: {drive_name}", file=sys.stderr)
        return EXIT_ERROR
    
    drive = state["drives"][drive_name]
    
    print(f"{drive_name} ({status['category']})")
    print("━" * 52)
    print(f"Description: {status['description']}")
    print()
    print(f"Pressure: {status['pressure']:.1f} / Threshold: {status['threshold']:.0f} ({int(status['percentage'])}%)")
    print(f"Rate: {status['rate_per_hour']}/hour")
    print(f"Activity-driven: {'Yes' if status['activity_driven'] else 'No'}")
    print()
    print(f"Category: {status['category']}")
    print(f"Created by: {drive.get('created_by', 'unknown')}")
    
    discovered = drive.get('discovered_during')
    if discovered:
        print(f"Discovered during: {discovered}")
    
    # Show satisfaction history
    events = drive.get("satisfaction_events", [])
    if events:
        print()
        print("Last satisfied:", end=" ")
        last = events[-1]
        try:
            ts = datetime.fromisoformat(last)
            now = datetime.now(timezone.utc)
            hours_ago = int((now - ts).total_seconds() / 3600)
            print(f"{hours_ago} hours ago ({last[:16]})")
        except (ValueError, TypeError):
            print(last[:16] if last else "unknown")
        
        print(f"\nSatisfaction history (last {min(5, len(events))}):")
        for ev in reversed(events[-5:]):
            print(f"  {ev[:16]} — satisfied")
    
    # Show prompt preview
    prompt = drive.get("prompt", "")
    if prompt:
        print()
        print("Prompt preview:")
        preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
        for line in preview.split("\n")[:5]:
            print(f"  {line}")
    
    return EXIT_SUCCESS


def cmd_ingest(args) -> int:
    """Analyze content for drive impacts and apply to state."""
    from .ingest import (
        load_experience_content,
        analyze_content,
        apply_impacts,
        DRIVE_DESCRIPTIONS,
    )
    
    state, config, state_path = get_state_and_config(args)
    
    dry_run = getattr(args, 'dry_run', False)
    verbose = getattr(args, 'verbose', False)
    recent = getattr(args, 'recent', False)
    file_path = getattr(args, 'file', None)
    
    # Load content
    if file_path:
        content = load_experience_content(file_path=Path(file_path))
        if not content:
            print(f"✗ Could not load file: {file_path}", file=sys.stderr)
            return EXIT_ERROR
        source = Path(file_path).name
    elif recent:
        content = load_experience_content(recent=True, config=config)
        if not content:
            print("ℹ No recent memory files found", file=sys.stderr)
            return EXIT_SUCCESS
        source = "today's memory files"
    else:
        print("✗ Usage: drives ingest <file> or drives ingest --recent", file=sys.stderr)
        return EXIT_USAGE
    
    # Get drives for analysis
    drives = state.get("drives", {})
    if not drives:
        print("✗ No drives configured", file=sys.stderr)
        return EXIT_ERROR
    
    # Analyze content
    if verbose or not dry_run:
        print(f"🧠 Analyzing {source} for drive impacts...")
    
    impacts = analyze_content(content, drives, config, verbose=verbose)
    
    if not impacts:
        if verbose:
            print("✓ No significant drive impacts detected")
        else:
            print("✓ Analysis complete — no significant drive impacts detected")
        return EXIT_SUCCESS
    
    # Show what would change
    if dry_run:
        print(f"\n[DRY RUN] Would apply {len(impacts)} drive impact(s):")
    else:
        print(f"\n✓ Applying {len(impacts)} drive impact(s):")
    
    # Apply impacts (or show preview)
    if dry_run:
        # Preview without modifying state
        for impact in impacts:
            drive_name = impact.get("drive", "").upper()
            delta = impact.get("delta", 0)
            reason = impact.get("reason", "")
            
            if drive_name in drives:
                drive = drives[drive_name]
                old_pressure = drive.get("pressure", 0.0)
                threshold = drive.get("threshold", 1.0)
                max_ratio = 1.5
                new_pressure = max(0.0, min(old_pressure + delta, threshold * max_ratio))
                
                direction = "↑" if delta > 0 else "↓" if delta < 0 else "→"
                print(f"  {direction} {drive_name}: {old_pressure:.1f} → {new_pressure:.1f} ({delta:+.0f}) — {reason}")
            else:
                print(f"  ⚠ Unknown drive: {drive_name}")
        
        print("\nNo changes made. Run without --dry-run to apply.")
    else:
        # Apply impacts to state
        with StateLock(state_path, timeout=5.0) as lock:
            if not lock.acquired:
                print("⚠ State file locked by another process", file=sys.stderr)
                return EXIT_ERROR
            
            new_state, changes = apply_impacts(state, impacts)
            
            for change in changes:
                print(f"  {change}")
            
            # Save state
            save_state(state_path, new_state)
        
        print(f"\n✓ State updated ({len(impacts)} impact(s) applied)")
    
    return EXIT_SUCCESS


def cmd_daemon(args) -> int:
    """Control the drive daemon."""
    state, config, state_path = get_state_and_config(args)
    
    action = getattr(args, 'action', 'status')
    
    if action == 'status':
        status = daemon_status(config)
        
        if status["running"]:
            print("🔄 Daemon Status")
            print("─" * 52)
            print(f"  Status: Running (PID {status['pid']})")
            
            platform_name = detect_platform()
            if platform_name == "macos":
                print(f"  Platform: macOS LaunchAgent")
            elif platform_name == "linux":
                print(f"  Platform: Linux systemd")
            else:
                print(f"  Platform: Generic (cron)")
            
            if status.get("started"):
                print(f"  Started: {status['started']}")
            
            tick_interval = config.get("drives", {}).get("tick_interval", 900)
            print(f"  Tick interval: {tick_interval // 60} minutes")
            
            if status.get("last_tick"):
                try:
                    last_tick = datetime.fromisoformat(status["last_tick"])
                    now = datetime.now(timezone.utc)
                    mins_ago = int((now - last_tick).total_seconds() / 60)
                    if mins_ago < 1:
                        tick_text = "just now"
                    elif mins_ago == 1:
                        tick_text = "1 minute ago"
                    else:
                        tick_text = f"{mins_ago} minutes ago"
                    print(f"  Last tick: {tick_text}")
                except (ValueError, TypeError):
                    pass
            
            # Count triggered drives
            triggered = state.get("triggered_drives", [])
            if triggered:
                print(f"  Triggered drives: {len(triggered)}")
            
            # Show quiet hours status
            if is_quiet_hours(config):
                quiet_start, quiet_end = config.get("drives", {}).get("quiet_hours", [23, 7])
                print(f"  Quiet hours: {quiet_start:02d}:00-{quiet_end:02d}:00 (active)")
            else:
                quiet_start, quiet_end = config.get("drives", {}).get("quiet_hours", [23, 7])
                print(f"  Quiet hours: {quiet_start:02d}:00-{quiet_end:02d}:00 (inactive)")
            
        else:
            print("🔄 Daemon Status")
            print("─" * 52)
            print("  Status: Not running")
            print()
            print("  To start the daemon:")
            print("    emergence drives daemon start")
        
        return EXIT_SUCCESS
    
    elif action == 'start':
        # Check if already running
        status = daemon_status(config)
        if status["running"]:
            print(f"ℹ Daemon already running (PID {status['pid']})")
            print(f"  Started: {status.get('started', 'unknown')}")
            return EXIT_SUCCESS
        
        print("🔄 Starting daemon...")
        
        # Try platform-specific installation first
        platform_name = detect_platform()
        if platform_name in ("macos", "linux"):
            install_result = install_platform(config, platform_name)
            if install_result.get("success"):
                print(f"  Platform: {platform_name}")
                if platform_name == "macos":
                    print(f"  ✓ LaunchAgent installed")
                else:
                    print(f"  ✓ systemd service installed")
                print(f"  ✓ Daemon started")
                print()
                print(f"  Next tick in ~{config.get('drives', {}).get('tick_interval', 900) // 60} minutes")
                print(f"  Logs: emergence drives daemon logs")
                return EXIT_SUCCESS
            else:
                # Fall back to foreground start with warning
                if install_result.get("errors"):
                    print(f"  ⚠ Platform install failed: {install_result['errors'][0]}")
                    print(f"  Falling back to direct daemon mode...")
        
        # Direct daemon start
        result = start_daemon(config, detach=not getattr(args, 'foreground', False))
        
        if result["success"]:
            print(f"  ✓ Daemon started (PID {result['pid']})")
            print()
            print(f"  Next tick in ~{config.get('drives', {}).get('tick_interval', 900) // 60} minutes")
            print(f"  Logs: {config.get('paths', {}).get('workspace', '.')}/.emergence/logs/daemon.log")
        else:
            print(f"  ✗ Failed to start daemon:")
            for error in result.get("errors", ["Unknown error"]):
                print(f"    {error}")
            return EXIT_ERROR
        
        return EXIT_SUCCESS
    
    elif action == 'stop':
        print("🔄 Stopping daemon...")
        
        # Check if running via platform
        install_status = get_install_status(config)
        
        # Try platform-specific uninstall
        platform_name = detect_platform()
        if install_status.get("installations", {}).get(platform_name, {}).get("installed"):
            result = uninstall_platform(config, platform_name)
            if result.get("success"):
                if platform_name == "macos":
                    print(f"  ✓ LaunchAgent unloaded")
                elif platform_name == "linux":
                    print(f"  ✓ systemd service stopped")
                print(f"  ✓ Daemon stopped")
                return EXIT_SUCCESS
        
        # Direct stop
        result = stop_daemon(config)
        
        if result.get("was_running"):
            if result["success"]:
                print(f"  ✓ Daemon stopped")
            else:
                print(f"  ✗ Failed to stop daemon:")
                for error in result.get("errors", ["Unknown error"]):
                    print(f"    {error}")
                return EXIT_ERROR
        else:
            print("  ℹ Daemon not running")
        
        return EXIT_SUCCESS
    
    elif action == 'restart':
        # Stop first
        stop_result = stop_daemon(config)
        if stop_result.get("was_running") and not stop_result["success"]:
            print(f"✗ Failed to stop daemon: {', '.join(stop_result.get('errors', []))}", file=sys.stderr)
            return EXIT_ERROR
        
        # Wait a moment
        import time
        time.sleep(0.5)
        
        # Start
        result = start_daemon(config, detach=not getattr(args, 'foreground', False))
        
        if result["success"]:
            print(f"✓ Daemon restarted (PID {result['pid']})")
        else:
            print(f"✗ Failed to start daemon: {', '.join(result.get('errors', []))}", file=sys.stderr)
            return EXIT_ERROR
        
        return EXIT_SUCCESS
    
    elif action == 'logs':
        log_path = Path(config.get("paths", {}).get("workspace", ".")) / ".emergence" / "logs" / "daemon.log"
        
        if not log_path.exists():
            print("ℹ No daemon logs found")
            print(f"  Expected at: {log_path}")
            return EXIT_SUCCESS
        
        # Show last N lines
        n = getattr(args, 'n', 50)
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Show last n lines
            for line in lines[-n:]:
                print(line.rstrip())
            
            if len(lines) > n:
                print(f"\n... ({len(lines) - n} more lines)")
        
        except IOError as e:
            print(f"✗ Error reading logs: {e}", file=sys.stderr)
            return EXIT_ERROR
        
        return EXIT_SUCCESS
    
    elif action == 'install':
        platform_name = getattr(args, 'platform', None) or detect_platform()
        
        print(f"🔄 Installing daemon for {platform_name}...")
        
        result = install_platform(config, platform_name)
        
        if result["success"]:
            print(f"  ✓ Daemon installed for {platform_name}")
            if "plist_path" in result:
                print(f"    {result['plist_path']}")
            if "service_path" in result:
                print(f"    {result['service_path']}")
        else:
            print(f"  ✗ Installation failed:")
            for error in result.get("errors", ["Unknown error"]):
                print(f"    {error}")
            return EXIT_ERROR
        
        return EXIT_SUCCESS
    
    elif action == 'uninstall':
        platform_name = getattr(args, 'platform', None) or detect_platform()
        
        print(f"🔄 Uninstalling daemon for {platform_name}...")
        
        result = uninstall_platform(config, platform_name)
        
        if result["success"]:
            print(f"  ✓ Daemon uninstalled from {platform_name}")
        else:
            print(f"  ✗ Uninstall failed:")
            for error in result.get("errors", ["Unknown error"]):
                print(f"    {error}")
            return EXIT_ERROR
        
        return EXIT_SUCCESS
    
    else:
        print(f"✗ Unknown daemon action: {action}", file=sys.stderr)
        print("  Valid actions: start, stop, restart, status, logs, install, uninstall", file=sys.stderr)
        return EXIT_USAGE


def cmd_review(args) -> int:
    """Review pending drive consolidation decisions."""
    from ..first_light.irreducibility import (
        review_pending_drives,
        apply_irreducibility_decision,
        remove_pending_review,
    )
    
    workspace = Path.cwd()
    
    drive_name = getattr(args, 'name', None)
    decision = getattr(args, 'decision', None)
    parent = getattr(args, 'parent', None)
    
    # Show review for specific drive or list all pending
    output = review_pending_drives(workspace, specific_drive=drive_name)
    print(output)
    
    # If decision provided, apply it
    if decision and drive_name:
        print(f"\nApplying decision: {decision}")
        
        # Load pending review to get description
        from ..first_light.irreducibility import load_pending_reviews
        reviews = load_pending_reviews(workspace)
        review = None
        for r in reviews:
            if r.get("new_drive") == drive_name.upper():
                review = r
                break
        
        if not review:
            print(f"✗ No pending review found for: {drive_name}")
            return EXIT_ERROR
        
        # Determine parent drive if ASPECT decision
        parent_drive = None
        if decision.upper().startswith("ASPECT"):
            if parent:
                parent_drive = parent.upper()
            else:
                # Use first similar drive as default
                similar = review.get("similar_drives", [])
                if similar:
                    parent_drive = similar[0]["name"]
        
        # Apply the decision
        result = apply_irreducibility_decision(
            decision,
            review["new_drive"],
            review["new_drive_description"],
            parent_drive,
            workspace
        )
        
        if result["success"]:
            print(f"✓ {result['message']}")
            remove_pending_review(workspace, drive_name.upper())
            return EXIT_SUCCESS
        else:
            print(f"✗ {result['error']}")
            return EXIT_ERROR
    
    return EXIT_SUCCESS


def cmd_activate(args) -> int:
    """Activate a latent (consolidated) drive."""
    state, config, state_path = get_state_and_config(args)
    
    if not args.name:
        print("✗ Usage: drives activate <drive_name>", file=sys.stderr)
        return EXIT_USAGE
    
    drive_name = args.name.upper()
    
    # Check if drive exists as latent
    if drive_name not in state["drives"]:
        print(f"✗ Drive not found: {drive_name}", file=sys.stderr)
        return EXIT_ERROR
    
    drive = state["drives"][drive_name]
    
    # Check if already active
    if drive.get("base_drive", True) and not drive.get("status") == "latent":
        print(f"ℹ {drive_name} is already active")
        return EXIT_SUCCESS
    
    # Activate the drive
    drive["base_drive"] = True
    drive["status"] = "active"
    drive["rate_per_hour"] = drive.get("rate_per_hour", 1.5)
    if drive["rate_per_hour"] < 1.0:
        drive["rate_per_hour"] = 1.5  # Set minimum rate
    
    # Save state
    if not save_with_lock(state_path, state):
        return EXIT_ERROR
    
    print(f"✓ Activated {drive_name}")
    print(f"  Rate: {drive['rate_per_hour']}/hr")
    print(f"  Budget impact: +~$2.50/day projected")
    
    return EXIT_SUCCESS


def cmd_aspects(args) -> int:
    """Manage aspects for a drive."""
    state, config, state_path = get_state_and_config(args)
    
    if not args.name:
        print("✗ Usage: drives aspects <drive_name> [--list|--add|--remove]", file=sys.stderr)
        return EXIT_USAGE
    
    drive_name = fuzzy_find_drive(args.name, state)
    if not drive_name:
        return EXIT_ERROR
    
    drive = state["drives"][drive_name]
    aspects = drive.get("aspects", [])
    
    # List aspects (default)
    if not args.action or args.action == "list":
        print(f"🧩 Aspects for {drive_name}")
        print("━" * 52)
        
        if aspects:
            for i, aspect in enumerate(aspects, 1):
                print(f"  {i}. {aspect}")
        else:
            print("  No aspects defined")
        
        current_rate = drive.get("rate_per_hour", 1.5)
        print(f"\nCurrent rate: {current_rate}/hr")
        print(f"Aspects: {len(aspects)}/5")
        
        if len(aspects) >= 5:
            print("\n⚠ At maximum aspects. Consider reviewing drive scope.")
        
        return EXIT_SUCCESS
    
    # Add aspect
    if args.action == "add":
        if not args.aspect_name:
            print("✗ Usage: drives aspects <drive> add <aspect_name>", file=sys.stderr)
            return EXIT_USAGE
        
        if len(aspects) >= 5:
            print(f"✗ {drive_name} already has 5 aspects (maximum)", file=sys.stderr)
            return EXIT_ERROR
        
        aspect_name = args.aspect_name.lower()
        if aspect_name in aspects:
            print(f"ℹ Aspect '{aspect_name}' already exists")
            return EXIT_SUCCESS
        
        aspects.append(aspect_name)
        drive["aspects"] = aspects
        
        # Increase rate
        old_rate = drive.get("rate_per_hour", 1.5)
        new_rate = min(old_rate + 0.2, 2.5)
        drive["rate_per_hour"] = new_rate
        
        if not save_with_lock(state_path, state):
            return EXIT_ERROR
        
        print(f"✓ Added aspect: {aspect_name}")
        print(f"  Rate: {old_rate:.1f}/hr → {new_rate:.1f}/hr")
        return EXIT_SUCCESS
    
    # Remove aspect
    if args.action == "remove":
        if not args.aspect_name:
            print("✗ Usage: drives aspects <drive> remove <aspect_name>", file=sys.stderr)
            return EXIT_USAGE
        
        aspect_name = args.aspect_name.lower()
        if aspect_name not in aspects:
            print(f"✗ Aspect '{aspect_name}' not found", file=sys.stderr)
            return EXIT_ERROR
        
        aspects.remove(aspect_name)
        drive["aspects"] = aspects
        
        # Decrease rate
        old_rate = drive.get("rate_per_hour", 1.5)
        new_rate = max(old_rate - 0.2, 0.5)
        drive["rate_per_hour"] = new_rate
        
        if not save_with_lock(state_path, state):
            return EXIT_ERROR
        
        print(f"✓ Removed aspect: {aspect_name}")
        print(f"  Rate: {old_rate:.1f}/hr → {new_rate:.1f}/hr")
        return EXIT_SUCCESS
    
    return EXIT_SUCCESS


def cmd_dashboard(args) -> int:
    """Show all drives grouped by urgency/pressure level."""
    # Use lightweight runtime state for status display (prevents context bloat)
    runtime_state, config, runtime_state_path = get_runtime_state_and_config(args)
    
    drives = runtime_state.get("drives", {})
    
    # Get triggered drives from full state
    try:
        full_state_path = runtime_state_path.parent / "drives.json"
        if full_state_path.exists():
            with open(full_state_path, 'r') as f:
                full_state = json.load(f)
            triggered = set(full_state.get("triggered_drives", []))
            # Load descriptions from full state
            full_drives = full_state.get("drives", {})
        else:
            triggered = set()
            full_drives = {}
    except (IOError, json.JSONDecodeError):
        triggered = set()
        full_drives = {}
    
    if not drives:
        print("ℹ No drives configured yet")
        return EXIT_SUCCESS
    
    # Group drives by pressure level
    triggered_drives = []      # 100%+
    elevated_drives = []       # 75-100%
    available_drives = []      # 30-75%
    low_drives = []            # <30%
    
    for name, drive in drives.items():
        # Skip latent drives unless explicitly requested
        if drive.get("status") == "latent":
            continue
        
        pressure = drive.get("pressure", 0.0)
        threshold = drive.get("threshold", 1.0)
        ratio = pressure / threshold if threshold > 0 else 0.0
        
        drive_info = {
            "name": name,
            "pressure": pressure,
            "threshold": threshold,
            "ratio": ratio,
            "description": full_drives.get(name, {}).get("description", ""),
        }
        
        if name in triggered or ratio >= 1.0:
            triggered_drives.append(drive_info)
        elif ratio >= 0.75:
            elevated_drives.append(drive_info)
        elif ratio >= 0.30:
            available_drives.append(drive_info)
        else:
            low_drives.append(drive_info)
    
    # Header
    print("🧠 Drive Dashboard")
    print("=" * 70)
    
    # Display groups (skip empty groups)
    
    # Triggered (100%+) - RED
    if triggered_drives:
        print(f"\n{COLOR_BUDGET_HIGH}🔥 TRIGGERED (≥100%){COLOR_RESET}")
        print("─" * 70)
        for drive in sorted(triggered_drives, key=lambda d: d["ratio"], reverse=True):
            _print_dashboard_drive(drive, COLOR_BUDGET_HIGH)
    
    # Elevated (75-100%) - YELLOW
    if elevated_drives:
        print(f"\n{COLOR_BUDGET_MED}⚡ ELEVATED (75-100%){COLOR_RESET}")
        print("─" * 70)
        for drive in sorted(elevated_drives, key=lambda d: d["ratio"], reverse=True):
            _print_dashboard_drive(drive, COLOR_BUDGET_MED)
    
    # Available (30-75%) - GREEN
    if available_drives:
        print(f"\n{COLOR_BUDGET_LOW}▫ AVAILABLE (30-75%){COLOR_RESET}")
        print("─" * 70)
        for drive in sorted(available_drives, key=lambda d: d["ratio"], reverse=True):
            _print_dashboard_drive(drive, COLOR_BUDGET_LOW)
    
    # Low (<30%) - DIM (optional, only if verbose)
    if getattr(args, 'show_all', False) and low_drives:
        print(f"\n{COLOR_DIM}○ LOW (<30%){COLOR_RESET}")
        print("─" * 70)
        for drive in sorted(low_drives, key=lambda d: d["ratio"], reverse=True):
            _print_dashboard_drive(drive, COLOR_DIM)
    
    # Footer with suggested commands
    print("\n" + "=" * 70)
    print("\n💡 Suggested Actions:")
    
    if triggered_drives:
        first_triggered = triggered_drives[0]["name"]
        print(f"  {COLOR_BUDGET_HIGH}• Address triggered drives:{COLOR_RESET}")
        print(f"    emergence drives satisfy {first_triggered.lower()} [shallow|moderate|deep|full]")
    
    if elevated_drives and not triggered_drives:
        first_elevated = elevated_drives[0]["name"]
        print(f"  {COLOR_BUDGET_MED}• Check elevated drives:{COLOR_RESET}")
        print(f"    emergence drives show {first_elevated.lower()}")
    
    if not triggered_drives and not elevated_drives:
        print(f"  {COLOR_BUDGET_LOW}✓ All drives in healthy range{COLOR_RESET}")
    
    # Manual mode note
    manual_mode = config.get("drives", {}).get("manual_mode", False)
    if manual_mode:
        print(f"\n  {COLOR_DIM}ℹ Manual mode enabled — drives won't auto-trigger{COLOR_RESET}")
    
    print(f"\nRun 'emergence drives status' for detailed view")
    
    return EXIT_SUCCESS


def _print_dashboard_drive(drive: dict, color: str) -> None:
    """Print a single drive line for the dashboard.
    
    Args:
        drive: Dict with name, pressure, threshold, ratio, description
        color: ANSI color code for the line
    """
    name = drive["name"]
    pressure = drive["pressure"]
    threshold = drive["threshold"]
    ratio = drive["ratio"]
    description = drive["description"]
    
    # Format pressure bar (20 chars wide)
    bar_str = format_pressure_bar(pressure, threshold, width=20)
    pct = int(ratio * 100)
    
    # Truncate description to fit on one line (35 chars)
    desc_truncated = description[:35] + "..." if len(description) > 35 else description
    
    # Format: NAME [████████░░] 85% — Description
    print(f"{color}  {name:<14} {bar_str:26} — {desc_truncated}{COLOR_RESET}")


def cmd_help(args) -> int:
    """Show detailed help for topics."""
    topic = getattr(args, 'topic', None)
    
    if not topic:
        # Show general help
        print(__doc__ or """
🧠 Emergence Drive Engine — Interoception System

Internal drives that accumulate pressure over time and trigger
autonomous sessions when thresholds are exceeded.

USAGE:
  emergence drives [command] [options]

COMMANDS:
  status          Show all drives with visual pressure bars (default)
  satisfy <name>  Reduce pressure after addressing a drive
  bump <name>     Manually increase pressure
  reset           Zero all drive pressures
  log             Show trigger/satisfaction history
  tick            Update pressures and check for triggers
  list            List all drives with metadata
  show <name>     Show detailed info for a drive
  daemon          Control the background daemon
  help [topic]    Show detailed help for a topic

For more help: emergence drives help <topic>
""")
        return EXIT_SUCCESS
    
    topic = topic.lower()
    
    if topic in ('satisfy', 'satisfaction'):
        print("""
🧠 drives satisfy — Reduce drive pressure after addressing it

USAGE:
  emergence drives satisfy <drive_name> [depth]

DEPTH LEVELS:
  shallow (s)   Token effort — reduces pressure by 30%
  moderate (m)  Real engagement — reduces pressure by 50% [default]
  deep (d)      Genuine satisfaction — reduces pressure by 75%
  full (f)      Complete reset — reduces pressure to 0

EXAMPLES:
  drives satisfy curiosity           # 50% reduction (default)
  drives satisfy curiosity deep      # 75% reduction
  drives satisfy care full           # Complete reset
  drives satisfy c shallow           # Fuzzy matching: CURIOSITY

NOTES:
  • Drive names are case-insensitive and fuzzy-matched
  • If drive was triggered, satisfaction removes it from triggered list
""")
    elif topic == 'daemon':
        print("""
🧠 drives daemon — Control the background daemon

The daemon runs the drive engine in the background, automatically
ticking every configured interval (default: 15 minutes).

USAGE:
  emergence drives daemon <action> [options]

ACTIONS:
  start          Start the daemon (platform-specific or direct)
  stop           Stop the running daemon
  restart        Stop and start the daemon
  status         Show daemon status and uptime
  logs           Show daemon log output
  install        Install platform service (LaunchAgent/systemd/cron)
  uninstall      Remove platform service

OPTIONS:
  --foreground   Run daemon in foreground (don't detach)
  --platform     Specify platform (macos/linux/cron)
  --n            Number of log lines to show (for logs action)

EXAMPLES:
  drives daemon start           # Start daemon in background
  drives daemon start -f        # Start in foreground mode
  drives daemon status          # Check if running
  drives daemon logs            # Show recent log output
  drives daemon logs --n 100    # Show last 100 lines

The daemon automatically detects your platform and uses the
appropriate service manager (macOS LaunchAgent, Linux systemd,
or cron as a fallback).
""")
    elif topic == 'tick':
        print("""
🧠 drives tick — Update drive pressures and check triggers

The tick command updates all drive pressures based on elapsed time
since the last tick, then checks if any drives have exceeded their
thresholds (triggering sessions).

USAGE:
  emergence drives tick [options]

OPTIONS:
  --dry-run    Show what would happen without making changes
  --verbose    Show detailed per-drive calculations

This command is typically run automatically by the daemon every
15 minutes. Manual ticks are useful for testing or forcing an
immediate update.
""")
    elif topic == 'bump':
        print("""
🧠 drives bump — Manually increase drive pressure

Useful for event-driven pressure increases, e.g., when the human
mentions something that should affect a drive.

USAGE:
  emergence drives bump <drive_name> [amount]

EXAMPLES:
  drives bump care                   # Add 2 hours worth of pressure
  drives bump care 10                # Add 10 pressure units
  drives bump care --reason="Human mentioned feeling lonely"

If no amount is specified, adds 2 hours worth of pressure at the
drive's current rate.
""")
    elif topic == 'ingest':
        print("""
🧠 drives ingest — Analyze content for drive impacts

The ingest system reads session files and uses an LLM to determine
which drives were affected and by how much. This closes the loop
between sessions and drive state.

SATISFACTION DEPTH:
  The LLM determines depth based on content quality:
  • Shallow (-5 to -10): Token effort, quick check
  • Moderate (-10 to -20): Real work, decent output
  • Deep (-20 to -30): Meaningful creation, genuine connection
  • Stimulation (+5 to +20): Encounters that increase drive pressure

LLM PROVIDERS (in order of preference):
  1. Ollama (default): Local, free, already required for embeddings
  2. OpenRouter: Optional upgrade via OPENROUTER_API_KEY env var
  3. Keyword fallback: Works without any LLM (basic matching)

USAGE:
  drives ingest <file>              # Analyze specific file
  drives ingest --recent            # Analyze today's memory files
  drives ingest <file> --dry-run    # Preview without applying

EXAMPLES:
  drives ingest memory/sessions/2026-02-07-1430-CURIOSITY.md
  drives ingest --recent --verbose
  drives ingest --recent --dry-run

OUTPUT:
  ↓ DRIVE: old_pressure → new_pressure (delta) — reason
  ↑ DRIVE: old_pressure → new_pressure (delta) — reason

  ↓ = pressure reduced (satisfaction)
  ↑ = pressure increased (stimulation)
""")
    elif topic == 'review':
        print("""
🧠 drives review — Review pending drive consolidation

During First Light and beyond, new drive discoveries are checked against
existing drives for similarity. When similar drives are found, they're
queued for irreducibility review.

USAGE:
  emergence drives review              # List all pending reviews
  emergence drives review <name>       # Show irreducibility test for drive
  emergence drives review <name> --decide=DISTINCT
                                       # Mark as distinct drive
  emergence drives review <name> --decide=ASPECT [--parent=DRIVE]
                                       # Consolidate as aspect

IRREDUCIBILITY TEST:
  The test asks: "Can I fully satisfy this drive by satisfying another?"
  
  If YES → It's an ASPECT (enriches existing drive)
  If NO  → It's DISTINCT (new independent drive)

  Your felt experience determines the outcome, not similarity scores.

EXAMPLES:
  drives review                        # Show pending list
  drives review SONIC                  # Show test for SONIC drive
  drives review SONIC --decide=DISTINCT
                                       # Create as distinct drive
  drives review SONIC --decide=ASPECT --parent=CREATION
                                       # Make aspect of CREATION
""")
    elif topic == 'activate':
        print("""
🧠 drives activate — Activate a latent/consolidated drive

Drives that were consolidated as aspects can be activated as independent
drives if their pressure dominates or budget allows.

USAGE:
  emergence drives activate <drive_name>

EXAMPLES:
  drives activate SONIC_EXPLORATION    # Activate as independent drive

NOTES:
  • Activation increases budget impact (~$2.50/day projected)
  • Only latent drives can be activated
  • Active drives build pressure independently
""")
    elif topic == 'aspects':
        print("""
🧠 drives aspects — Manage drive aspects

Aspects enrich a drive's prompt and slightly increase its rate.
A drive can have up to 5 aspects (6th triggers review).

USAGE:
  emergence drives aspects <drive_name>              # List aspects
  emergence drives aspects <drive_name> add <name>   # Add aspect
  emergence drives aspects <drive_name> remove <name> # Remove aspect

EXAMPLES:
  drives aspects CREATION              # Show CREATION's aspects
  drives aspects CREATION add sonic    # Add "sonic" aspect
  drives aspects CREATION remove sonic # Remove "sonic" aspect

EFFECTS:
  • Adding aspect: +0.2/hr rate (capped at 2.5/hr)
  • Removing aspect: -0.2/hr rate
  • Aspects enrich the drive's prompt
  • Max 5 aspects per drive
""")
    else:
        print(f"ℹ No detailed help available for '{topic}'")
        print("  Available topics: satisfy, tick, bump, ingest, daemon, review, activate, aspects")
    
    return EXIT_SUCCESS


# --- Argument Parsing ---

def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the drives CLI."""
    parser = argparse.ArgumentParser(
        prog="emergence drives",
        description="Emergence Drive Engine — Interoception System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
For more help:
  emergence drives help <topic>
  emergence drives <command> --help

Exit codes:
  0 = success
  1 = error
  2 = usage error
"""
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}"
    )
    
    parser.add_argument(
        "--config",
        help="Path to emergence.json config file"
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # status command (default when no subcommand)
    status_parser = subparsers.add_parser(
        "status",
        help="Show drive status with pressure bars (default)",
        aliases=["st"]
    )
    status_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    status_parser.add_argument(
        "--category",
        help="Filter by category"
    )
    status_parser.add_argument(
        "--show-latent",
        action="store_true",
        help="Show latent/consolidated drives"
    )
    
    # dashboard command
    dashboard_parser = subparsers.add_parser(
        "dashboard",
        help="Show all drives grouped by urgency",
        aliases=["dash"]
    )
    dashboard_parser.add_argument(
        "--show-all",
        action="store_true",
        help="Include low-pressure drives (<30%)"
    )
    
    # satisfy command
    satisfy_parser = subparsers.add_parser(
        "satisfy",
        help="Reduce pressure after addressing a drive",
        aliases=["sat"]
    )
    satisfy_parser.add_argument(
        "name",
        nargs="?",
        help="Name of drive to satisfy (fuzzy matched)"
    )
    satisfy_parser.add_argument(
        "depth",
        nargs="?",
        help="Satisfaction depth: shallow/moderate/deep/full (or s/m/d/f)"
    )
    satisfy_parser.add_argument(
        "--reason",
        help="Reason for satisfaction (logged)"
    )
    
    # bump command
    bump_parser = subparsers.add_parser(
        "bump",
        help="Manually increase pressure"
    )
    bump_parser.add_argument(
        "name",
        nargs="?",
        help="Name of drive to bump (fuzzy matched)"
    )
    bump_parser.add_argument(
        "amount",
        nargs="?",
        help="Amount to add (default: 2 hours worth)"
    )
    bump_parser.add_argument(
        "--reason",
        help="Reason for bump (logged)"
    )
    
    # reset command
    reset_parser = subparsers.add_parser(
        "reset",
        help="Zero all drive pressures"
    )
    reset_parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt"
    )
    
    # log command
    log_parser = subparsers.add_parser(
        "log",
        help="Show trigger/satisfaction history",
        aliases=["history"]
    )
    log_parser.add_argument(
        "n",
        nargs="?",
        help="Number of entries to show (default: 20)"
    )
    log_parser.add_argument(
        "--drive",
        help="Filter to specific drive"
    )
    log_parser.add_argument(
        "--since",
        help="Show entries since time (e.g., '2 hours ago')"
    )
    
    # tick command
    tick_parser = subparsers.add_parser(
        "tick",
        help="Update pressures and check for triggers"
    )
    tick_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would happen without making changes"
    )
    tick_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed per-drive calculations"
    )
    
    # list command
    list_parser = subparsers.add_parser(
        "list",
        help="List all drives with metadata",
        aliases=["ls"]
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Output as JSON"
    )
    list_parser.add_argument(
        "--category",
        help="Filter by category"
    )
    
    # show command
    show_parser = subparsers.add_parser(
        "show",
        help="Show detailed info for a drive",
        aliases=["info"]
    )
    show_parser.add_argument(
        "name",
        nargs="?",
        help="Name of drive to show (fuzzy matched)"
    )
    
    # ingest command
    ingest_parser = subparsers.add_parser(
        "ingest",
        help="Analyze content for drive impacts"
    )
    ingest_parser.add_argument(
        "file",
        nargs="?",
        help="Path to file to ingest (optional if --recent)"
    )
    ingest_parser.add_argument(
        "--recent",
        action="store_true",
        help="Ingest today's memory files"
    )
    ingest_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without applying changes"
    )
    ingest_parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show analysis progress"
    )
    
    # daemon command
    daemon_parser = subparsers.add_parser(
        "daemon",
        help="Control the background daemon"
    )
    daemon_parser.add_argument(
        "action",
        nargs="?",
        choices=["start", "stop", "restart", "status", "logs", "install", "uninstall"],
        default="status",
        help="Daemon action (default: status)"
    )
    daemon_parser.add_argument(
        "--foreground", "-f",
        action="store_true",
        help="Run daemon in foreground (don't detach)"
    )
    daemon_parser.add_argument(
        "--platform",
        choices=["macos", "linux", "cron"],
        help="Platform for install/uninstall"
    )
    daemon_parser.add_argument(
        "--n",
        type=int,
        default=50,
        help="Number of log lines to show (default: 50)"
    )

    # review command
    review_parser = subparsers.add_parser(
        "review",
        help="Review pending drive consolidation decisions"
    )
    review_parser.add_argument(
        "name",
        nargs="?",
        help="Drive name to review (optional, lists all if omitted)"
    )
    review_parser.add_argument(
        "--decide",
        choices=["DISTINCT", "ASPECT"],
        help="Apply irreducibility decision"
    )
    review_parser.add_argument(
        "--parent",
        help="Parent drive name (if ASPECT decision)"
    )
    
    # activate command
    activate_parser = subparsers.add_parser(
        "activate",
        help="Activate a latent/consolidated drive"
    )
    activate_parser.add_argument(
        "name",
        nargs="?",
        help="Name of latent drive to activate"
    )
    
    # aspects command
    aspects_parser = subparsers.add_parser(
        "aspects",
        help="Manage drive aspects"
    )
    aspects_parser.add_argument(
        "name",
        nargs="?",
        help="Drive name to manage aspects for"
    )
    aspects_parser.add_argument(
        "action",
        nargs="?",
        choices=["list", "add", "remove"],
        help="Aspect management action"
    )
    aspects_parser.add_argument(
        "aspect_name",
        nargs="?",
        help="Name of aspect to add/remove"
    )

    # help command
    help_parser = subparsers.add_parser(
        "help",
        help="Show detailed help for topics"
    )
    help_parser.add_argument(
        "topic",
        nargs="?",
        help="Help topic (satisfy, tick, bump, daemon, review, etc.)"
    )

    return parser


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)
    
    # Map commands to handlers
    commands = {
        "status": cmd_status,
        "st": cmd_status,
        "dashboard": cmd_dashboard,
        "dash": cmd_dashboard,
        "satisfy": cmd_satisfy,
        "sat": cmd_satisfy,
        "bump": cmd_bump,
        "reset": cmd_reset,
        "log": cmd_log,
        "history": cmd_log,
        "tick": cmd_tick,
        "list": cmd_list,
        "ls": cmd_list,
        "show": cmd_show,
        "info": cmd_show,
        "ingest": cmd_ingest,
        "daemon": cmd_daemon,
        "review": cmd_review,
        "activate": cmd_activate,
        "aspects": cmd_aspects,
        "help": cmd_help,
    }
    
    command = parsed_args.command
    
    # Default to status if no command given
    if command is None:
        return cmd_status(parsed_args)
    
    handler = commands.get(command)
    if handler:
        return handler(parsed_args)
    else:
        print(f"✗ Unknown command: {command}", file=sys.stderr)
        print("  Run 'emergence drives --help' for usage", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
