"""CLI entry point for the Emergence drive engine.

Provides a human-facing interface to the interoception system with
commands for checking status, satisfying drives, viewing history, etc.
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Import from the drive engine modules
from .config import load_config, get_state_path, find_config, ensure_config_example
from .state import load_state, save_state, StateLock, get_hours_since_tick
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


# --- Command Implementations ---

def cmd_status(args) -> int:
    """Show drive status with pressure bars."""
    state, config, state_path = get_state_and_config(args)
    
    drives = state.get("drives", {})
    triggered = set(state.get("triggered_drives", []))
    
    # Get last tick info
    last_tick_str = state.get("last_tick", "")
    try:
        last_tick = datetime.fromisoformat(last_tick_str)
        now = datetime.now(timezone.utc)
        mins_ago = int((now - last_tick).total_seconds() / 60)
        if mins_ago < 1:
            updated_text = "just now"
        elif mins_ago == 1:
            updated_text = "1m ago"
        elif mins_ago < 60:
            updated_text = f"{mins_ago}m ago"
        else:
            hours_ago = mins_ago // 60
            updated_text = f"{hours_ago}h ago"
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
            
            output["drives"].append({
                "name": name,
                "pressure": round(pressure, 2),
                "threshold": threshold,
                "ratio": round(ratio, 2),
                "status": status,
                "category": drive.get("category", "unknown"),
            })
        print(json.dumps(output, indent=2))
        return EXIT_SUCCESS
    
    # Normal text output
    print(f"🧠 Drive Status  (updated {updated_text})")
    print("─" * 52)
    
    # Sort by category then name
    sorted_drives = sorted(drives.items(), key=lambda x: (x[1].get("category", ""), x[0]))
    
    for name, drive in sorted_drives:
        pressure = drive.get("pressure", 0.0)
        threshold = drive.get("threshold", 1.0)
        ratio = pressure / threshold if threshold > 0 else 0.0
        
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
        bar = format_pressure_bar(pressure, threshold, width=20)
        pct = int(ratio * 100)
        
        # Pad name to 14 chars
        name_padded = name.ljust(14)
        
        needs_attention = " NEEDS ATTENTION" if status in ("over_threshold", "triggered") else ""
        
        print(f"  {indicator} {name_padded} {bar}  {pressure:.1f}/{threshold:.0f} ({pct}%){needs_attention}")
    
    print("─" * 52)
    
    # Show triggered drives
    if triggered:
        triggered_list = ", ".join(sorted(triggered))
        print(f"  ⏸ Triggered & waiting: {triggered_list}")
        print(f"  Use 'emergence drives satisfy <name>' to reset after addressing.")
    
    # Show quiet hours
    if is_quiet_hours(config):
        quiet_start, quiet_end = config.get("drives", {}).get("quiet_hours", [23, 7])
        print(f"  ℹ Quiet hours active ({quiet_start:02d}:00-{quiet_end:02d}:00) — triggers queued")
    
    return EXIT_SUCCESS


def cmd_satisfy(args) -> int:
    """Satisfy a drive (reduce pressure)."""
    state, config, state_path = get_state_and_config(args)
    
    if not args.name:
        print("✗ Usage: drives satisfy <drive_name> [depth]", file=sys.stderr)
        return EXIT_USAGE
    
    drive_name = fuzzy_find_drive(args.name, state)
    if not drive_name:
        return EXIT_ERROR
    
    # Determine depth
    depth = getattr(args, 'depth', None) or "moderate"
    depth_map = {
        's': 'shallow', 'shallow': 'shallow',
        'm': 'moderate', 'moderate': 'moderate',
        'd': 'deep', 'deep': 'deep',
        'f': 'full', 'full': 'full',
    }
    depth = depth_map.get(depth.lower(), depth)
    
    drive = state["drives"][drive_name]
    old_pressure = drive.get("pressure", 0.0)
    
    if old_pressure == 0.0:
        print(f"ℹ {drive_name} is already at 0.0 — nothing to satisfy")
        return EXIT_SUCCESS
    
    try:
        result = satisfy_drive(state, drive_name, depth)
    except ValueError as e:
        print(f"✗ {e}", file=sys.stderr)
        return EXIT_ERROR
    
    # Save state
    if not save_with_lock(state_path, state):
        return EXIT_ERROR
    
    new_pressure = result["new_pressure"]
    reduction = result["reduction_ratio"]
    reduction_pct = int(reduction * 100)
    
    print(f"✓ {drive_name} satisfied ({old_pressure:.1f} → {new_pressure:.1f}) [{depth}]")
    print(f"  Pressure reduced by {reduction_pct}%")
    
    if depth not in ('full', 'f'):
        remaining = "deep" if depth in ('shallow', 'moderate') else "full"
        print(f"  Use 'drives satisfy {drive_name.lower()} {remaining}' for more reduction")
    
    if drive_name in state.get("triggered_drives", []):
        print(f"  Still in triggered list — reduction not sufficient")
    else:
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
    else:
        print(f"ℹ No detailed help available for '{topic}'")
        print("  Available topics: satisfy, tick, bump, ingest, daemon")
    
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

    # help command
    help_parser = subparsers.add_parser(
        "help",
        help="Show detailed help for topics"
    )
    help_parser.add_argument(
        "topic",
        nargs="?",
        help="Help topic (satisfy, tick, bump, daemon, etc.)"
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
