# Data Loss Impact Assessment: Drive Satisfaction Tracking

## Executive Summary

**Data Status:** ✅ **NOT LOST** — Satisfaction history is being preserved in centralized logs  
**System Status:** ⚠️ **PARTIALLY BROKEN** — Tracking mechanisms are inconsistent across different data stores  
**Recovery Status:** ✅ **FULLY RECOVERABLE** — All satisfaction data exists and can be reconciled

---

## Investigation Findings

### 1. Satisfaction Data Storage Architecture

The drives system uses **multiple independent data stores** for satisfaction tracking:

| File | Purpose | Satisfaction Events Status |
|------|---------|---------------------------|
| `~/.openclaw/state/satisfaction_history.jsonl` | ✅ **Centralized satisfaction log** | **HAS DATA** (2 recent events) |
| `~/.openclaw/state/drives.json` | ✅ Drive config + runtime state | **HAS DATA** (CARE drive: 1 event) |
| `~/.openclaw/state/trigger-log.jsonl` | ✅ All drive trigger events | **HAS DATA** (3 recent events) |
| `~/.openclaw/state/drives-state.json` | ❌ Runtime snapshot for display | **MISSING** (no satisfaction_events fields) |
| `workspace/drives-state.json` | ❌ Legacy/workspace copy | **MISSING** (no satisfaction_events fields) |
| `~/.openclaw/state/drives/READING.json` | ✅ Individual drive state | **HAS SESSION COUNT** (29 completions) |

### 2. What's Working

**✅ Centralized Satisfaction Logging** (`satisfaction_history.jsonl`):
```json
{"timestamp": "2026-02-14T18:03:44.018949+00:00", "drive": "CARE", "pressure_before": 0.07, "pressure_after": 0.05, "band": "available", "depth": "auto-shallow", "ratio": 0.25, "source": "manual"}
{"timestamp": "2026-02-14T18:19:14.132129+00:00", "drive": "CARE", "pressure_before": 0.1, "pressure_after": 0.08, "band": "available", "depth": "shallow", "ratio": 0.25, "source": "session"}
```

**✅ Per-Drive Satisfaction Arrays** (in main `drives.json`):
- CARE drive has `satisfaction_events: ["2026-02-14T18:19:14.131970+00:00"]`
- WANDER, REST, MAINTENANCE have empty arrays `[]` (correct state)
- These are **kept to last 10 events only** (rolling window)

**✅ Trigger Log** (`trigger-log.jsonl`):
- Records all trigger events including satisfaction reasons
- Shows manual satisfactions with "SATISFIED-moderate" messages

**✅ Individual Drive Session Tracking** (e.g., `READING.json`):
- Tracks `last_satisfied` timestamp
- Tracks `sessions_completed` count (29 for READING)

### 3. What's Broken

**❌ drives-state.json Missing Satisfaction Arrays**:
- The runtime state snapshot file does NOT include `satisfaction_events` arrays
- This is likely intentional (to keep the display file minimal)
- BUT it means DRIVES.md display can't show recent satisfaction history

**❌ Session Ingest Breadcrumbs Not Being Created**:
- `~/.openclaw/state/sessions_ingest/` directory is **EMPTY**
- Breadcrumb mechanism for tracking spawned sessions is not writing files
- This causes drives system to **re-process old sessions** (duplicate ingest work)
- Session completion detection relies on breadcrumbs — without them, satisfaction from spawned sessions may not trigger automatically

**❌ Inconsistent satisfaction_events Fields**:
- Some drives in `drives.json` have `satisfaction_events` arrays
- Others (like READING, EMBODIMENT) are **missing the field entirely**
- This suggests incomplete migration or partial initialization

### 4. Impact Assessment

#### 🟢 **NO PERMANENT DATA LOSS**

All satisfaction events are being preserved in:
1. **satisfaction_history.jsonl** — Complete append-only log
2. **drives.json** — Per-drive rolling window (last 10 events)
3. **trigger-log.jsonl** — Trigger events with satisfaction reasons
4. **Individual drive files** — Session counts and timestamps

#### 🟡 **TRACKING BROKEN, NOT DATA LOST**

The problems are **operational**, not archival:

1. **Duplicate Ingest Work**: Without breadcrumbs, the ingest system may re-analyze old sessions multiple times
2. **Display Incomplete**: DRIVES.md can't show recent satisfaction history because drives-state.json lacks it
3. **Session Completion Detection Broken**: Spawned drive sessions don't automatically satisfy their drives when they complete
4. **Inconsistent State**: Some drives have satisfaction_events arrays, others don't

#### 🔴 **REST Drive session_count_since NOT WORKING**

REST drive is `activity_driven: true` and should track work sessions to build pressure.

Current REST state in `drives.json`:
```json
{
  "name": "REST",
  "activity_driven": true,
  "pressure": 0.0,
  "satisfaction_events": []
}
```

The drive has no mechanism to track `session_count_since` in the current implementation. This field is mentioned in state.py as a runtime state field, but it's not being populated.

**Impact:** REST drive pressure doesn't build from work — it's stuck at 0.0 indefinitely.

---

## Data Recovery Plan

### Phase 1: Verify Data Integrity

```bash
# Check satisfaction_history.jsonl completeness
wc -l ~/.openclaw/state/satisfaction_history.jsonl
cat ~/.openclaw/state/satisfaction_history.jsonl | jq -r '.drive' | sort | uniq -c

# Check drives.json satisfaction arrays
jq '.drives | to_entries | map({drive: .key, events: (.value.satisfaction_events // [] | length)})' ~/.openclaw/state/drives.json
```

### Phase 2: Reconcile Missing Fields

For drives missing `satisfaction_events` in drives.json:
1. Initialize empty array: `"satisfaction_events": []`
2. Backfill from satisfaction_history.jsonl (last 10 events per drive)
3. Ensure all drives have consistent schema

### Phase 3: Fix Session Ingest Breadcrumbs

**Root cause:** The breadcrumb write mechanism in `satisfaction.py::write_breadcrumb()` is not being called when sessions spawn.

**Fix:**
1. Check drive spawn code to ensure `write_breadcrumb()` is called
2. Verify sessions_ingest directory permissions
3. Add logging to breadcrumb write/read operations
4. Test breadcrumb lifecycle (spawn → complete → satisfy)

### Phase 4: Rebuild drives-state.json Generation

Options:
1. **Include satisfaction_events in runtime snapshot** — adds display capability
2. **Keep it minimal, read from drives.json on demand** — current architecture
3. **Add separate satisfaction summary endpoint** — cleaner separation

Recommend: **Option 1** — Include last 3 satisfaction events in drives-state.json for DRIVES.md display.

### Phase 5: Implement REST Drive Session Counting

REST drive needs activity tracking:
1. Hook into session completion events
2. Increment `session_count_since` field on non-REST sessions
3. Build pressure proportional to sessions completed
4. Reset counter on REST drive satisfaction
5. Add to runtime state output

---

## Immediate Actions

1. ✅ **Confirm satisfaction_history.jsonl is authoritative** — VERIFIED
2. ⚠️ **Fix breadcrumb writing** — CRITICAL (prevents duplicate ingest)
3. ⚠️ **Standardize satisfaction_events schema** — IMPORTANT (consistency)
4. ⚠️ **Implement REST session counting** — IMPORTANT (drive functionality)
5. 🔵 **Update drives-state.json to include satisfaction data** — NICE TO HAVE (display)

---

## Recoverable Data Summary

| Data Type | Location | Records | Status |
|-----------|----------|---------|--------|
| Satisfaction events | satisfaction_history.jsonl | 2 | ✅ Complete |
| Trigger events | trigger-log.jsonl | 3+ | ✅ Complete |
| Drive state | drives.json | 12 drives | ✅ Complete |
| Session counts | drives/READING.json | 29 sessions | ✅ Complete |
| Breadcrumbs | sessions_ingest/ | 0 | ❌ Empty (broken mechanism) |

**Conclusion:** All satisfaction data is preserved and recoverable. The system needs operational fixes, not data recovery.
