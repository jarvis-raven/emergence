# Nautilus Integration — Emergence v0.3.0

## Overview

Nautilus is now integrated into Emergence core as a first-class component.

## Structure

```
core/nautilus/
├── __init__.py      # Module exports and API
├── __main__.py      # CLI entry point (python -m core.nautilus)
├── cli.py           # Command handlers and help
├── config.py        # Path resolution (portable!)
├── search.py        # Full pipeline implementation
├── gravity.py       # Phase 1: Importance scoring
├── chambers.py      # Phase 2: Temporal layers
├── doors.py         # Phase 3: Context filtering
└── mirrors.py       # Phase 4: Multi-granularity
```

## Commands

### Main Commands

```bash
# Full pipeline search
emergence nautilus search "project status" --n 10
emergence nautilus search "security review" --trapdoor --verbose

# System status
emergence nautilus status

# Run maintenance
emergence nautilus maintain
emergence nautilus maintain --register-recent --verbose
```

### Utility Commands

```bash
# Classify files into chambers
emergence nautilus classify
emergence nautilus classify memory/2024-01-15.md

# Show gravity score
emergence nautilus gravity memory/2024-01-15.md
```

### Subcommands

```bash
# Chambers
emergence nautilus chambers status
emergence nautilus chambers promote --dry-run
emergence nautilus chambers crystallize

# Doors
emergence nautilus doors classify "query text"
emergence nautilus doors auto-tag

# Mirrors
emergence nautilus mirrors stats
emergence nautilus mirrors resolve memory/2024-01-15.md
```

## Configuration

Configuration is read from `~/.openclaw/emergence.json`:

```json
{
  "nautilus": {
    "enabled": true,
    "state_dir": "~/.openclaw/state/nautilus",
    "memory_dir": "memory",
    "auto_classify": true,
    "decay_interval_hours": 168
  }
}
```

### Path Resolution

Paths are resolved in this order:

1. **Environment variables**: `OPENCLAW_WORKSPACE`, `OPENCLAW_STATE_DIR`
2. **Config file**: `nautilus.state_dir`, `nautilus.memory_dir`
3. **Inference**: From package location or current working directory

## Database Migration

The first time you run any nautilus command, it will automatically migrate `gravity.db` from the legacy location (`tools/nautilus/`) to the new state directory (`~/.openclaw/state/nautilus/`).

## Nightly Maintenance

Update your cron job to use the new CLI:

```bash
# Old
python3 tools/nautilus/nautilus.py maintain

# New
cd /path/to/emergence && python3 -m core.cli nautilus maintain --register-recent --verbose
```

Or via the emergence command:

```bash
cd /path/to/emergence && emergence nautilus maintain --register-recent
```

## Python API

```python
from core.nautilus import search, status, maintain

# Search
results = search("query", n=10)

# Status
info = status()

# Maintain
maintain()
```

## Success Criteria

- ✅ `emergence nautilus search "query"` works
- ✅ `emergence nautilus maintain` runs
- ✅ No hardcoded paths remain
- ✅ All commands show proper help text
- ✅ Database migration works
- ✅ Ready for PR review
