#!/usr/bin/env python3
"""Migration script for Phase 1 state separation (issues #55, #59, #60).

Splits drives.json into:
- drives.json: Static configuration only
- drives-state.json: Runtime state (pressure, triggered_drives, last_tick)

This migration implements:
- Issue #55: Separate drives config from runtime state
- Issue #59: Move triggered_drives to drives-state.json
- Issue #60: Move last_tick to drives-state.json

Usage:
    python3 scripts/migrate_phase1_state_separation.py [state_dir]
    
    If state_dir not provided, uses .emergence/state
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timezone


# Static config fields that belong in drives.json
STATIC_CONFIG_FIELDS = {
    "name",
    "description",
    "prompt",
    "threshold",
    "thresholds",
    "rate_per_hour",
    "max_rate",
    "category",
    "created_by",
    "created_at",
    "discovered_during",
    "activity_driven",
    "min_interval_seconds",
    "base_drive",
    "aspects",
    "gated_until",
}

# Runtime state fields that belong in drives-state.json
RUNTIME_STATE_FIELDS = {
    "pressure",
    "status",
    "satisfaction_events",
    "last_triggered",
    "valence",
    "thwarting_count",
    "last_emergency_spawn",
    "session_count_since",
}


def split_drive(drive: dict) -> tuple[dict, dict]:
    """Split a drive dict into config and runtime state."""
    config = {}
    state = {}
    
    for key, value in drive.items():
        if key in STATIC_CONFIG_FIELDS:
            config[key] = value
        elif key in RUNTIME_STATE_FIELDS:
            state[key] = value
        else:
            # Unknown field - keep in config for safety
            config[key] = value
    
    return config, state


def migrate_state_dir(state_dir: Path, dry_run: bool = False) -> dict:
    """Migrate drives.json in the given directory.
    
    Args:
        state_dir: Directory containing drives.json
        dry_run: If True, don't write files, just report
        
    Returns:
        Dict with migration statistics
    """
    drives_json = state_dir / "drives.json"
    drives_state_json = state_dir / "drives-state.json"
    
    stats = {
        "drives_found": 0,
        "config_fields_moved": 0,
        "runtime_fields_moved": 0,
        "triggered_drives_moved": False,
        "last_tick_moved": False,
        "success": False,
    }
    
    # Check if already migrated
    if drives_state_json.exists():
        print(f"⚠️  drives-state.json already exists in {state_dir}")
        print("   Migration may have already run. Use --force to re-migrate.")
        return stats
    
    # Check if source exists
    if not drives_json.exists():
        print(f"❌ drives.json not found in {state_dir}")
        return stats
    
    # Load existing drives.json
    try:
        with open(drives_json, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"❌ Error reading drives.json: {e}")
        return stats
    
    # Create backup
    if not dry_run:
        backup_path = drives_json.with_suffix(".json.pre-phase1-migration")
        print(f"📦 Creating backup: {backup_path.name}")
        with open(backup_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    # Split drives
    config_drives = {}
    state_drives = {}
    
    for name, drive in data.get("drives", {}).items():
        stats["drives_found"] += 1
        drive_config, drive_state = split_drive(drive)
        config_drives[name] = drive_config
        state_drives[name] = drive_state
        
        stats["config_fields_moved"] += len(drive_config)
        stats["runtime_fields_moved"] += len(drive_state)
    
    # Build new structures
    config = {
        "version": data.get("version", "1.1"),
        "drives": config_drives
    }
    
    # Handle both last_tick and last_updated (legacy field name)
    last_tick = data.get("last_tick") or data.get("last_updated")
    if not last_tick:
        last_tick = datetime.now(timezone.utc).isoformat()
    
    state = {
        "version": data.get("version", "1.1"),
        "last_tick": last_tick,
        "drives": state_drives,
        "triggered_drives": data.get("triggered_drives", [])
    }
    
    if "triggered_drives" in data:
        stats["triggered_drives_moved"] = True
    if "last_tick" in data or "last_updated" in data:
        stats["last_tick_moved"] = True
    
    # Show what will change
    print(f"\n📊 Migration Summary for {state_dir}:")
    print(f"   Drives found: {stats['drives_found']}")
    print(f"   Config fields per drive: ~{stats['config_fields_moved'] // max(stats['drives_found'], 1)}")
    print(f"   Runtime fields per drive: ~{stats['runtime_fields_moved'] // max(stats['drives_found'], 1)}")
    print(f"   triggered_drives: {len(state['triggered_drives'])} items → drives-state.json")
    print(f"   last_tick: {last_tick} → drives-state.json")
    
    # Calculate size reduction
    config_size = len(json.dumps(config, indent=2))
    state_size = len(json.dumps(state, indent=2))
    original_size = len(json.dumps(data, indent=2))
    
    print(f"\n📏 Size Analysis:")
    print(f"   Original drives.json: {original_size} bytes")
    print(f"   New drives.json: {config_size} bytes ({100 * config_size // original_size}% of original)")
    print(f"   New drives-state.json: {state_size} bytes")
    print(f"   Reduction in drives.json: {original_size - config_size} bytes")
    
    # Write new files
    if dry_run:
        print("\n🔍 DRY RUN - No files written")
        print(f"\nWould write:")
        print(f"  {drives_json}")
        print(f"  {drives_state_json}")
    else:
        print(f"\n✍️  Writing new files...")
        
        # Write config
        temp_config = drives_json.with_suffix(".tmp")
        with open(temp_config, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        temp_config.rename(drives_json)
        print(f"   ✅ {drives_json.name}")
        
        # Write state
        temp_state = drives_state_json.with_suffix(".tmp")
        with open(temp_state, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
        temp_state.rename(drives_state_json)
        print(f"   ✅ {drives_state_json.name}")
        
        stats["success"] = True
        print("\n✨ Migration complete!")
    
    return stats


def main():
    """Main migration entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Migrate drives.json to Phase 1 separated structure"
    )
    parser.add_argument(
        "state_dir",
        nargs="?",
        default=".emergence/state",
        help="State directory containing drives.json (default: .emergence/state)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without writing files"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-migrate even if drives-state.json exists"
    )
    
    args = parser.parse_args()
    
    state_dir = Path(args.state_dir)
    
    if not state_dir.exists():
        print(f"❌ State directory not found: {state_dir}")
        sys.exit(1)
    
    print(f"🔄 Phase 1 State Separation Migration")
    print(f"   Issues: #55, #59, #60")
    print(f"   State dir: {state_dir}")
    print()
    
    # Check for force flag
    drives_state_json = state_dir / "drives-state.json"
    if drives_state_json.exists() and not args.force:
        print(f"⚠️  drives-state.json already exists!")
        print(f"   Use --force to re-migrate")
        sys.exit(1)
    
    stats = migrate_state_dir(state_dir, dry_run=args.dry_run)
    
    if not stats["success"] and not args.dry_run:
        sys.exit(1)


if __name__ == "__main__":
    main()
