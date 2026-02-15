# Nautilus v0.4.0 Beta - Core Integration

**Status:** ✅ Complete  
**Date:** 2026-02-14  
**Issues:** #65, #66

## Summary

Successfully integrated Nautilus memory system into Emergence's runtime with automatic memory tracking and nightly maintenance.

## Deliverables

### Issue #65: Session Hooks ✅

**File:** `core/nautilus/session_hooks.py`

Auto-records file accesses during sessions without manual registration:

```python
from core.nautilus.session_hooks import record_access, on_file_read, on_file_write

# Record a file read
record_access("memory/daily/2026-02-14.md", access_type="read")

# Record a file write
record_access("memory/MEMORY.md", access_type="write")

# Batch register multiple files
batch_record_accesses(["file1.md", "file2.md"], access_type="read")

# Find and register recent writes
register_recent_writes(hours=24)
```

**Features:**
- ✅ Async/sync modes (non-blocking by default)
- ✅ Automatic gravity DB registration
- ✅ Access logging with session context
- ✅ Batch operations for efficiency
- ✅ Auto-skip non-markdown files
- ✅ Workspace-relative path handling

**Integration hooks:**
- `on_file_read(file_path, session_id)` - Hook for read events
- `on_file_write(file_path, session_id)` - Hook for write events
- `on_session_start(session_id, session_type)` - Session lifecycle hook
- `on_session_end(session_id, files_accessed)` - Session lifecycle hook

### Issue #66: Nightly Maintenance ✅

**Files:**
- `core/nautilus/nightly.py` - Maintenance pipeline
- `core/drives/nightly_check.py` - Scheduler integration
- `core/drives/daemon.py` - Daemon integration (updated)

**Maintenance Pipeline:**

```bash
# Manual run
python3 -m core.nautilus.nightly --verbose --register-recent

# Via daemon (automatic)
# Runs at preferred time (default: 2:30 AM)
```

**Steps executed:**
1. **Register recent writes** - Files modified in last 24h
2. **Classify chambers** - atrium → corridor → vault
3. **Auto-tag contexts** - Apply semantic tags
4. **Apply gravity decay** - Recency decay for untouched memories
5. **Promote memories** - Chamber advancement (if available)
6. **Link mirrors** - Multi-granularity indexing

**Daemon integration:**
- Checks preferred time window (±30 minutes)
- Rate limiting (max once per 24 hours)
- Error handling (won't crash daemon)
- Logging to `~/.openclaw/workspace/.emergence/logs/daemon.log`

## Configuration

**emergence.json:**

```json
{
  "nautilus": {
    "enabled": true,
    "gravity_db": "~/.openclaw/state/nautilus/gravity.db",
    "memory_dir": "memory",
    "auto_classify": true,
    "decay_interval_hours": 168,
    "nightly_enabled": true,
    "nightly_hour": 2,
    "nightly_minute": 30,
    "chamber_thresholds": {
      "atrium_max_age_hours": 48,
      "corridor_max_age_days": 7
    },
    "decay_rate": 0.05,
    "recency_half_life_days": 14,
    "authority_boost": 0.3,
    "mass_cap": 100.0
  }
}
```

**Config options:**

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `true` | Master enable/disable |
| `nightly_enabled` | `true` | Enable nightly maintenance |
| `nightly_hour` | `2` | Preferred hour (0-23) |
| `nightly_minute` | `30` | Preferred minute (0-59) |
| `gravity_db` | `~/.openclaw/state/nautilus/gravity.db` | Database location |
| `memory_dir` | `"memory"` | Memory directory (relative to workspace) |
| `auto_classify` | `true` | Auto-classify into chambers |
| `decay_interval_hours` | `168` | How often to run decay (weekly) |

## Tests

**File:** `tests/test_nautilus_integration.py`

**Coverage:**
- ✅ 18 new tests for v0.4.0 integration
- ✅ 8 existing Nautilus tests still passing
- ✅ **Total: 26 tests passing**

**Test categories:**
1. Session hooks (8 tests)
   - File read/write recording
   - Batch operations
   - Recent file registration
   - Non-markdown skip logic
   - Hook integration
   
2. Nightly integration (8 tests)
   - Maintenance pipeline
   - Scheduler logic
   - Rate limiting
   - Time window checking
   - State persistence
   
3. Daemon integration (2 tests)
   - Module imports
   - Cross-module compatibility

## Usage Examples

### Manual Session Tracking

```python
from core.nautilus.session_hooks import track_session_files

# Track all markdown files in workspace
result = track_session_files(session_label="manual-sweep")
print(f"Tracked {result['tracked']} files")
```

### Programmatic Maintenance

```python
from core.nautilus.nightly import run_nightly_maintenance

# Run full maintenance cycle
result = run_nightly_maintenance(
    register_recent=True,
    recent_hours=24,
    verbose=True
)

print(f"Summary: {result['summary']}")
print(f"Errors: {result['errors']}")
```

### Check Maintenance Status

```python
from core.drives.nightly_check import should_run_nautilus_nightly, load_nightly_state

config = {...}  # Your emergence config
state = load_nightly_state(config)

should_run, reason = should_run_nautilus_nightly(config, state)
print(f"Should run: {should_run} - {reason}")
```

## Integration Points

### 1. Daemon Integration

**Location:** `core/drives/daemon.py:run_tick_cycle()`

```python
# Check for nightly maintenance (outside state lock)
if NAUTILUS_AVAILABLE:
    nightly_state = load_nightly_state(config)
    should_run, reason = should_run_nautilus_nightly(config, nightly_state)
    
    if should_run:
        maint_result = run_nightly_maintenance(
            register_recent=True,
            recent_hours=24,
            verbose=False
        )
        mark_nautilus_run(config, nightly_state)
```

**Behavior:**
- Runs during daemon tick cycle (non-blocking)
- Only runs if in preferred time window
- Rate-limited to once per 24 hours
- Errors logged but don't crash daemon

### 2. Future OpenClaw Integration

When OpenClaw adds session lifecycle events, connect via:

```python
# In OpenClaw session manager
from core.nautilus.session_hooks import on_file_read, on_file_write

class SessionManager:
    def read_file(self, path):
        content = self._read_file_impl(path)
        on_file_read(path, session_id=self.session_id)
        return content
    
    def write_file(self, path, content):
        self._write_file_impl(path, content)
        on_file_write(path, session_id=self.session_id)
```

## Database Schema Updates

**gravity.db - access_log table:**

Added `context` column for session tracking:

```sql
CREATE TABLE access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    path TEXT NOT NULL,
    line_start INTEGER DEFAULT 0,
    line_end INTEGER DEFAULT 0,
    accessed_at TEXT DEFAULT (datetime('now')),
    query TEXT DEFAULT NULL,
    score REAL DEFAULT NULL,
    context TEXT DEFAULT '{}'  -- NEW: Session context JSON
)
```

## Error Handling

All maintenance steps are wrapped in try/catch blocks:

```python
try:
    classify_result = subprocess.run(...)
    result["steps"]["classify"] = classify_data
except Exception as e:
    result["errors"].append(f"Chamber classification error: {e}")
    # Continue to next step
```

**Philosophy:**
- Errors are logged but don't stop the pipeline
- Each step is independent and fault-tolerant
- Daemon continues running even if Nautilus fails

## Performance

**Session hooks:**
- Async by default (non-blocking)
- Batch operations for efficiency
- Skip non-markdown files early
- Lightweight DB operations

**Nightly maintenance:**
- Runs once per day (2:30 AM default)
- Total runtime: ~10-30 seconds (depending on memory size)
- Low CPU impact (background subprocess calls)
- WAL mode for concurrent DB access

## Migration Notes

**From standalone Nautilus:**
- Database location changed: `tools/nautilus/gravity.db` → `~/.openclaw/state/nautilus/gravity.db`
- Use `core.nautilus.migrate_db` for automatic migration
- Old cron jobs can be replaced with daemon integration

**From v0.3.x:**
- Session hooks are new in v0.4.0
- Nightly integration is new in v0.4.0
- All existing Nautilus commands still work
- Config schema is backward compatible

## Known Limitations

1. **OpenClaw session integration pending**
   - Hooks are ready but not yet called by OpenClaw
   - Manual registration via `register_recent_writes()` works as interim solution
   
2. **Chamber promotion not yet implemented**
   - Placeholder in pipeline (skipped gracefully)
   - Coming in future update

3. **Single-file granularity only**
   - Currently tracks whole files, not line ranges
   - Line-range tracking could be added later

## Future Enhancements

**v0.4.1 (planned):**
- Chamber promotion logic (atrium → corridor → vault)
- Configurable maintenance schedule (multiple times per day)
- Session analytics dashboard

**v0.5.0 (roadmap):**
- OpenClaw direct integration (session lifecycle hooks)
- Line-range tracking for large files
- Smart batching for high-frequency accesses
- Memory consolidation recommendations

## Changelog

### v0.4.0-beta (2026-02-14)

**Added:**
- Session hooks module (`session_hooks.py`)
- Nightly maintenance pipeline (`nightly.py`)
- Daemon scheduler integration (`nightly_check.py`)
- 18 new integration tests
- Configuration options for scheduling

**Changed:**
- `daemon.py` now imports and runs Nautilus maintenance
- `config.py` handles string/Path conversion
- `gravity.py` adds `context` column to access_log

**Fixed:**
- Path expansion for `~` in config
- String/Path compatibility in config loading

## References

- Integration plan: `docs/nautilus-integration-plan.md`
- Original issues: #65, #66
- Test suite: `tests/test_nautilus_integration.py`
- Config: `emergence.json`
