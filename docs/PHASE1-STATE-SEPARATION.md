# Phase 1 State Separation (Issues #55, #59, #60)

## Overview

Phase 1 of the state duplication cleanup separates static drive configuration from runtime state. This reduces duplication identified in issue #33 and improves maintainability.

## Changes

### Before (Single File)

Previously, all drive data was stored in `drives.json`:

```json
{
  "version": "1.0",
  "last_updated": "2026-02-09T18:39:19.699459+00:00",
  "drives": {
    "CARE": {
      "name": "CARE",
      "description": "...",
      "prompt": "...",
      "threshold": 25.0,
      "rate_per_hour": 2.0,
      "pressure": 0.0,              // Runtime state mixed with config
      "satisfaction_events": [],    // Runtime state mixed with config
      ...
    }
  },
  "triggered_drives": []  // Changed every tick when drives trigger
}
```

**Problems:**
- Runtime state (pressure, triggered_drives) mixed with static config
- File changes every daemon tick even if config unchanged
- Harder to version control (git diffs show state changes)
- `triggered_drives` and `last_updated` change frequently

### After (Split Files)

Now separated into two files:

**drives.json** (static configuration):
```json
{
  "version": "1.1",
  "drives": {
    "CARE": {
      "name": "CARE",
      "description": "...",
      "prompt": "...",
      "threshold": 25.0,
      "rate_per_hour": 2.0,
      "category": "core",
      "created_by": "system",
      ...
    }
  }
}
```

**drives-state.json** (runtime state):
```json
{
  "version": "1.1",
  "last_tick": "2026-02-09T18:39:19.699459+00:00",
  "drives": {
    "CARE": {
      "pressure": 0.0,
      "satisfaction_events": [],
      "last_triggered": null,
      ...
    }
  },
  "triggered_drives": []
}
```

## Implementation

### Issue #55: Separate Static Config from Runtime State

**Static config fields** (in drives.json):
- `name`, `description`, `prompt`
- `threshold`, `thresholds`, `rate_per_hour`, `max_rate`
- `category`, `created_by`, `created_at`
- `discovered_during`, `activity_driven`
- `min_interval_seconds`, `base_drive`, `aspects`
- `gated_until`

**Runtime state fields** (in drives-state.json):
- `pressure`, `status`
- `satisfaction_events`, `last_triggered`
- `valence`, `thwarting_count`
- `last_emergency_spawn`, `session_count_since`

### Issue #59: Move triggered_drives to Runtime State

The `triggered_drives` list moves from `drives.json` to `drives-state.json` because:
- Changes every time a drive triggers or is satisfied
- Not part of static configuration
- Runtime state that tracks current trigger queue

### Issue #60: Move last_tick to Runtime State

The `last_tick` (formerly `last_updated`) timestamp moves to `drives-state.json` because:
- Updated every daemon tick
- Pure runtime state, not configuration
- No reason to pollute config file with timestamp updates

## Benefits

1. **Cleaner version control**: drives.json only changes when configuration actually changes
2. **Smaller config file**: ~15-20% size reduction in drives.json
3. **Better separation of concerns**: Clear distinction between "what the drives are" vs "what state they're in"
4. **Easier config management**: Can edit drives.json without worrying about losing runtime state
5. **Foundation for future work**: Enables Phase 2 consolidation work

## Size Impact

Typical reduction (3-drive example):
- Original drives.json: 1,838 bytes
- New drives.json: 1,558 bytes (85% of original, **280 bytes saved**)
- New drives-state.json: 384 bytes

The config file is now ~15% smaller and changes much less frequently.

## Migration

### Automatic Migration

The migration script automatically splits existing drives.json:

```bash
# Dry run (shows what would happen)
python3 scripts/migrate_phase1_state_separation.py --dry-run .emergence/state

# Run migration
python3 scripts/migrate_phase1_state_separation.py .emergence/state
```

The script:
1. Creates a backup: `drives.json.pre-phase1-migration`
2. Splits drives.json into drives.json + drives-state.json
3. Preserves all existing data
4. Validates the migration

### Backward Compatibility

The code automatically handles both formats:
- **New format**: Loads from drives.json + drives-state.json
- **Legacy format**: Loads from drives.json alone (if drives-state.json missing)
- **Save**: Always saves to split format

This means:
- Existing installations work without migration
- Migration is non-breaking
- Can roll back by deleting drives-state.json and restoring backup

## Testing

Run the test suite to verify:

```bash
# All tests should pass
python3 -m pytest core/drives/tests/ -v

# Verify drives status command works
python3 -m core.drives.cli status
```

Expected: 507 tests pass, drives status displays correctly.

## Files Changed

- `core/drives/state.py`: Updated load/save logic for split files
- `scripts/migrate_phase1_state_separation.py`: Migration script (new)
- `docs/PHASE1-STATE-SEPARATION.md`: This documentation (new)

## Next Steps

Phase 2 (future work) will consolidate duplicate drives and further optimize state structure. See issue #33 for full roadmap.

## Rollback

If needed, rollback by:

1. Stop the daemon: `emergence daemon stop`
2. Delete the split files: `rm .emergence/state/drives-state.json`
3. Restore backup: `mv .emergence/state/drives.json.pre-phase1-migration .emergence/state/drives.json`
4. Restart daemon: `emergence daemon start`

The code will automatically detect and load the legacy format.
