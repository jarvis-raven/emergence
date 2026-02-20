# Investigation: satisfaction_events Missing from drives-state.json

**Date:** 2026-02-14  
**Issue:** satisfaction_events arrays are being dropped from drives-state.json after Phase 1 state separation

## Root Cause

**Two conflicting systems are writing to drives-state.json:**

1. **NEW (Phase 1, commit abccfa1):** `state.py` split logic
   - Uses `split_drive_config_and_state()` to separate RUNTIME_STATE_FIELDS (including `satisfaction_events`) from config
   - Writes drives-state.json correctly WITH satisfaction_events
   - Called first in daemon tick cycle (line 291)

2. **OLD (commit c50fb76):** `runtime_state.py` lightweight extraction
   - Uses `extract_runtime_state()` which only extracts: pressure, threshold, status, description, last_triggered
   - **Does NOT include satisfaction_events** (see runtime_state.py:91-114)
   - Writes drives-state.json WITHOUT satisfaction_events
   - Called second in daemon tick cycle (line 300) - **overwrites Phase 1 state**

## Timeline

1. **Feb 11 (7df041e):** Created `runtime_state.py` for read-only display purposes (avoid context bloat)
2. **Feb 12 (c50fb76):** Wired runtime_state into daemon write path (mistake - meant for reading only)
3. **Feb 14 (abccfa1):** Phase 1 added proper state.py split logic, but didn't remove old runtime_state write

## Evidence

### Test confirming bug:
```bash
$ python3 -c "
from core.drives.runtime_state import extract_runtime_state
full_state = {
    'drives': {
        'PLAY': {
            'pressure': 5.0,
            'satisfaction_events': ['2026-02-14T07:00:00+00:00']
        }
    }
}
runtime = extract_runtime_state(full_state)
print('Has satisfaction_events?', 'satisfaction_events' in runtime['drives']['PLAY'])
"
Has satisfaction_events? False
```

### Daemon flow (daemon.py:291-302):
```python
# Line 291: Phase 1 split - CORRECT (includes satisfaction_events)
save_state(state_path, state)

# Lines 296-302: Old runtime extraction - BUG (drops satisfaction_events)  
runtime_state = extract_runtime_state(state)
runtime_path = state_path.parent / "drives-state.json"
save_runtime_state(runtime_path, runtime_state)  # OVERWRITES CORRECT STATE
```

### RUNTIME_STATE_FIELDS definition (state.py:48-57):
```python
RUNTIME_STATE_FIELDS = {
    "pressure",
    "status",
    "satisfaction_events",  # ← Defined here
    "last_triggered",
    "valence",
    "thwarting_count",
    "last_emergency_spawn",
    "session_count_since",
}
```

### DriveRuntimeState TypedDict (runtime_state.py:14-28):
```python
class DriveRuntimeState(TypedDict, total=False):
    pressure: float
    threshold: float
    status: str
    description: Optional[str]
    last_triggered: Optional[str]
    # ← satisfaction_events NOT HERE
```

## Impact

- `satisfaction_events` is written correctly by `save_state()`, then immediately overwritten without it
- This causes ingest to re-process old sessions (e.g., 07:00 PLAY session re-analyzed at 18:00)
- Session deduplication fails because satisfaction_events array is always empty

## Proposed Fix

**Option 1 (Recommended - Architectural Fix):**

Remove the redundant `save_runtime_state()` call from daemon.py (lines 296-302).

**Why:**
- The Phase 1 `save_state()` already writes drives-state.json correctly
- `runtime_state.py` was originally designed for read-only display (context optimization)
- Having two writers creates maintenance burden and bugs like this

**Changes:**
```diff
--- a/core/drives/daemon.py
+++ b/core/drives/daemon.py
@@ -291,13 +291,6 @@ def run_tick_cycle(state: dict, config: dict, state_path: Path, log_path: Path)
             save_state(state_path, state)
         except Exception as e:
             result["errors"].append(f"Failed to save state: {e}")
             write_log(log_path, f"State save error: {e}", "ERROR")
-        
-        # Write lightweight runtime state (drives-state.json)
-        try:
-            runtime_state = extract_runtime_state(state)
-            runtime_path = state_path.parent / "drives-state.json"
-            save_runtime_state(runtime_path, runtime_state)
-        except Exception as e:
-            write_log(log_path, f"Runtime state write error: {e}", "WARN")
     
     return result
```

**Option 2 (Band-aid Fix):**

Add `satisfaction_events` to `extract_runtime_state()` and `DriveRuntimeState`.

**Why NOT recommended:**
- Keeps duplication
- Defeats original purpose of runtime_state.py (lightweight for display)
- Will cause similar bugs in future when new RUNTIME_STATE_FIELDS are added

## Verification Plan

After fix:
1. Apply patch to daemon.py
2. Restart daemon
3. Trigger PLAY drive satisfaction
4. Check drives-state.json:
   ```bash
   grep -A5 "PLAY" ~/.openclaw/state/drives-state.json | grep satisfaction_events
   ```
5. Should see: `"satisfaction_events": ["2026-02-14T18:XX:XX+00:00"]`
6. Verify ingest doesn't re-process the session

## Files Modified

- `~/projects/emergence/core/drives/daemon.py` (remove lines 296-302)

## Related Issues

- Issue #55: Separate drives config from runtime state (Phase 1)
- Issue #59: Move triggered_drives to drives-state.json  
- Issue #60: Move last_tick to drives-state.json
- PR #76: Phase 1 implementation (commit abccfa1)
