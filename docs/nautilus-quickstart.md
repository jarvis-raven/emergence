# Nautilus Quick Start Guide

## Installation

Nautilus v0.4.0 Beta is already integrated into Emergence. No installation needed!

## Configuration

**Edit `emergence.json`:**

```json
{
  "nautilus": {
    "enabled": true,
    "nightly_enabled": true,
    "nightly_hour": 2,
    "nightly_minute": 30
  }
}
```

## Usage

### 1. Automatic Session Tracking (Coming Soon)

When OpenClaw adds session events, file tracking will be automatic. For now:

```python
from core.nautilus.session_hooks import register_recent_writes

# Register files modified in last 24 hours
result = register_recent_writes(hours=24)
print(f"Registered {result['registered']} files")
```

### 2. Manual File Tracking

```python
from core.nautilus.session_hooks import record_access

# Track a file read
record_access("memory/daily/2026-02-14.md", access_type="read")

# Track a file write
record_access("MEMORY.md", access_type="write")
```

### 3. Nightly Maintenance

**Automatic (via daemon):**
```bash
# Already running if daemon is active
# Check logs: ~/.openclaw/workspace/.emergence/logs/daemon.log
```

**Manual:**
```bash
python3 -m core.nautilus.nightly --verbose --register-recent
```

### 4. Search with Nautilus

```bash
# Full pipeline: gravity + chambers + doors + mirrors
emergence nautilus search "project timeline" --verbose

# Show system status
emergence nautilus status

# Run maintenance manually
emergence nautilus maintain --register-recent
```

## Common Tasks

### Check What's Tracked

```python
from core.nautilus import gravity

db = gravity.get_db()
count = db.execute("SELECT COUNT(*) FROM gravity").fetchone()[0]
print(f"{count} files tracked")
db.close()
```

### View Recent Activity

```python
from core.nautilus import gravity

db = gravity.get_db()
recent = db.execute("""
    SELECT path, last_accessed_at, access_count 
    FROM gravity 
    ORDER BY last_accessed_at DESC 
    LIMIT 10
""").fetchall()

for row in recent:
    print(f"{row['path']}: {row['access_count']} accesses")
db.close()
```

### Force Nightly Maintenance

```python
from core.nautilus.nightly import run_nightly_maintenance

result = run_nightly_maintenance(
    register_recent=True,
    recent_hours=24,
    verbose=True
)

print(f"Summary: {result['summary']}")
```

## Troubleshooting

### Maintenance Not Running

1. Check if enabled: `grep nautilus emergence.json`
2. Check time window: Default is 2:30 AM ±30 min
3. Check daemon logs: `tail ~/.openclaw/workspace/.emergence/logs/daemon.log`

### Files Not Being Tracked

1. Ensure files are `.md` (only markdown tracked)
2. Check they're in workspace: Must be under `~/.openclaw/workspace`
3. Run manual registration: `register_recent_writes(hours=24)`

### Database Issues

```bash
# Check database location
ls -lh ~/.openclaw/state/nautilus/gravity.db

# View schema
sqlite3 ~/.openclaw/state/nautilus/gravity.db ".schema"

# Check table counts
sqlite3 ~/.openclaw/state/nautilus/gravity.db "SELECT COUNT(*) FROM gravity"
```

## Configuration Reference

| Option | Default | Description |
|--------|---------|-------------|
| `enabled` | `true` | Enable Nautilus |
| `nightly_enabled` | `true` | Enable nightly maintenance |
| `nightly_hour` | `2` | Preferred hour (0-23) |
| `nightly_minute` | `30` | Preferred minute (0-59) |
| `gravity_db` | `~/.openclaw/state/nautilus/gravity.db` | DB path |
| `memory_dir` | `"memory"` | Memory directory |
| `decay_rate` | `0.05` | Gravity decay rate |
| `recency_half_life_days` | `14` | Recency decay half-life |

## API Reference

### Session Hooks

```python
from core.nautilus.session_hooks import (
    record_access,
    batch_record_accesses,
    register_recent_writes,
    on_file_read,
    on_file_write,
)

# Record single access
record_access("path/to/file.md", access_type="read", async_mode=False)

# Batch record
batch_record_accesses(["file1.md", "file2.md"], access_type="read")

# Register recent writes
result = register_recent_writes(hours=24)

# Lifecycle hooks (for OpenClaw integration)
on_file_read("file.md", session_id="session-123")
on_file_write("file.md", session_id="session-123")
```

### Nightly Maintenance

```python
from core.nautilus.nightly import (
    run_nightly_maintenance,
    should_run_maintenance,
)

# Run full maintenance
result = run_nightly_maintenance(
    register_recent=True,
    recent_hours=24,
    verbose=False
)

# Check if should run
config = {"enabled": True, "nightly_enabled": True}
should_run = should_run_maintenance(config)
```

### Scheduler

```python
from core.drives.nightly_check import (
    should_run_nautilus_nightly,
    load_nightly_state,
    mark_nautilus_run,
)

# Check scheduling
config = {...}
state = load_nightly_state(config)
should_run, reason = should_run_nautilus_nightly(config, state)

# Mark completed
mark_nautilus_run(config, state)
```

## Examples

### Custom Tracking Script

```python
#!/usr/bin/env python3
"""Track all session files."""

from pathlib import Path
from core.nautilus.session_hooks import batch_record_accesses

workspace = Path.home() / ".openclaw" / "workspace"
memory = workspace / "memory"

# Find all markdown files
md_files = [str(f.relative_to(workspace)) for f in memory.rglob("*.md")]

# Register them
count = batch_record_accesses(md_files, access_type="read")
print(f"Tracked {count} files")
```

### Check Maintenance Status

```python
#!/usr/bin/env python3
"""Show nightly maintenance status."""

from core.drives.nightly_check import load_nightly_state
from datetime import datetime

config = {"paths": {"workspace": "~/.openclaw/workspace"}}
state = load_nightly_state(config)

last_run = state.get("last_nautilus_run")
if last_run:
    dt = datetime.fromisoformat(last_run)
    print(f"Last run: {dt.strftime('%Y-%m-%d %H:%M')}")
else:
    print("Never run")
```

## Next Steps

1. **Enable daemon** - Nautilus nightly maintenance runs automatically
2. **Wait for OpenClaw integration** - Session tracking will be automatic
3. **Use search** - `emergence nautilus search "query"` for gravity-ranked results

## Resources

- Full guide: `docs/nautilus-v0.4.0-integration.md`
- Integration summary: `INTEGRATION_SUMMARY.md`
- Tests: `tests/test_nautilus_integration.py`
