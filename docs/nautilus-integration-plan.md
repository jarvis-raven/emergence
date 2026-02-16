# Nautilus Integration Plan - Emergence v0.3.0

## Overview

Move Nautilus memory architecture from `tools/nautilus/` into Emergence core module.

## Goals

1. ✅ Make Nautilus a first-class Emergence component
2. ✅ Portable - no hardcoded paths (works for all agents)
3. ✅ Nightly build covers all current functionality
4. ✅ Backward compatible CLI

## File Structure

### Current (tools/nautilus/)

```
tools/nautilus/
├── nautilus.py      # Main CLI
├── chambers.py      # Temporal layers (atrium/corridor/vault)
├── doors.py         # Context filtering
├── gravity.py       # Importance scoring
├── mirrors.py       # Multi-granularity access
└── gravity.db       # SQLite database
```

### Target (core/nautilus/)

```
core/nautilus/
├── __init__.py      # Module exports
├── __main__.py      # CLI entry point
├── cli.py           # Command handlers
├── chambers.py      # (moved)
├── doors.py         # (moved)
├── gravity.py       # (moved)
├── mirrors.py       # (moved)
└── config.py        # Path resolution
```

## Hardcoded Path Audit

### Current state:

- ✅ nautilus.py, chambers.py, doors.py, mirrors.py - Already use `OPENCLAW_WORKSPACE` env variable
- ❌ gravity.py - **CRITICAL**: `DB_PATH = Path(__file__).parent / "gravity.db"` (hardcoded next to script)

### Changes needed:

**gravity.py (CRITICAL):**

```python
# OLD (hardcoded next to script)
DB_PATH = Path(__file__).parent / "gravity.db"

# NEW (state directory)
from .config import get_state_dir
DB_PATH = get_state_dir() / "nautilus" / "gravity.db"
```

**All other files:**

```python
# Already good! Uses env variable:
WORKSPACE = Path(os.environ.get('OPENCLAW_WORKSPACE', str(Path(__file__).parent.parent.parent)))

# Will change to:
from .config import get_workspace
WORKSPACE = get_workspace()
```

## Configuration (emergence.json)

Add nautilus section:

```json
{
  "nautilus": {
    "enabled": true,
    "gravity_db": "~/.openclaw/state/nautilus/gravity.db",
    "memory_dir": "memory",
    "auto_classify": true,
    "decay_interval_hours": 168
  }
}
```

## CLI Integration

### New commands:

```bash
emergence nautilus search <query>       # Full pipeline search
emergence nautilus status               # System status
emergence nautilus maintain             # Run maintenance
emergence nautilus classify <file>      # Classify into chambers
emergence nautilus gravity <file>       # Show gravity score
```

### Implementation:

```python
# core/nautilus/cli.py
def cmd_search(args):
    """Search with full Nautilus pipeline."""
    # ...existing logic, but use config paths

def cmd_maintain(args):
    """Run nightly maintenance."""
    # ...existing logic
```

## Nightly Build Updates

### Current setup (Jarvis):

**2:30am Nautilus maintenance cron:**

```bash
# Register new/modified files
find memory/ -name '*.md' -mtime -1 -type f | \
  while read f; do python3 tools/nautilus/gravity.py record-write "$f"; done

# Run maintenance
python3 tools/nautilus/nautilus.py maintain
```

**3:00am Overnight Maintenance cron:**

- Does NOT currently call nautilus (runs separately at 2:30)
- Could be consolidated

### New setup (post-integration):

**Option A: Keep separate 2:30am cron**

```bash
# Simplified - emergence handles everything
cd ~/.openclaw/workspace/projects/emergence && \
python3 -m core.cli nautilus maintain --register-recent
```

**Option B: Consolidate into 3:00am cron**
Add to the "Overnight Maintenance" message:

```
3a. NAUTILUS MAINTENANCE
   - Run: emergence nautilus maintain --register-recent
   - Log chamber counts and gravity updates
```

**Recommendation:** Option A (keep separate) because:

- Nautilus maintenance can be heavy (shouldn't delay other nightly tasks)
- Clear separation of concerns
- 2:30am runs before 3:00am (nautilus prepares, nightly build uses)

### Cron update command for Jarvis:

```bash
openclaw cron update 7eed0170-6ca5-4d3d-88b4-f2a995897a44 \
  --message "NAUTILUS MAINTENANCE (nightly, 2:30am)

Run full nautilus maintenance via Emergence CLI.

python3 -m core.cli nautilus maintain --register-recent --verbose

This keeps gravity scores fresh and chambers classified.
Reply NO_REPLY unless there's an error."
```

## Migration Steps

### Phase 1: Code Migration

1. Create `core/nautilus/` directory
2. Copy all .py files from `tools/nautilus/`
3. Add `__init__.py` with exports
4. Add `__main__.py` for CLI entry point
5. Create `config.py` with path resolution

### Phase 2: Path Portability

1. Audit each file for hardcoded paths
2. Replace with config-based resolution
3. Add fallback logic for backward compatibility
4. Test with different workspace locations

### Phase 3: CLI Wiring

1. Add `nautilus` subcommand to `core/cli.py`
2. Wire up all nautilus commands
3. Add help text and examples
4. Test all commands

### Phase 4: Nightly Build Integration

1. Update nightly maintenance cron message
2. Test maintenance runs correctly
3. Verify gravity.db location handling
4. Check chamber classification works

### Phase 5: Database Migration

1. Move gravity.db to `~/.openclaw/state/nautilus/`
2. Add migration logic for existing databases
3. Update all references to new location

### Phase 6: Testing

1. Test on clean install (no existing nautilus)
2. Test with existing nautilus setup (migration)
3. Verify all commands work
4. Check nightly maintenance completes

### Phase 7: Documentation

1. Update README with nautilus commands
2. Add migration guide for existing users
3. Document configuration options
4. Add examples to docs/

## Breaking Changes

### For existing Jarvis installation:

- Nautilus cron job needs update (2:30am job)
- gravity.db will move location (auto-migrate on first run)
- `tools/nautilus/` becomes deprecated (but keep for safety)

### Migration notice:

```
⚠️ Nautilus has been integrated into Emergence v0.3.0

Your existing nautilus setup will be migrated automatically:
- gravity.db → ~/.openclaw/state/nautilus/gravity.db
- Update cron: emergence nautilus maintain

Old tools/nautilus/ is safe to remove after v0.3.0 install.
```

## Success Criteria

- [ ] All nautilus commands work via `emergence nautilus ...`
- [ ] No hardcoded paths (respects config)
- [ ] Nightly maintenance runs successfully
- [ ] Existing gravity.db migrates cleanly
- [ ] Chamber classification still works
- [ ] Search pipeline produces same results
- [ ] New agents can install and use immediately
- [ ] Documentation complete
- [ ] Tests pass

## Timeline

**v0.3.0-alpha** (2-3 days):

- Code migration
- Path portability fixes
- Basic CLI working

**v0.3.0-beta** (2-3 days):

- Nightly build integration
- Database migration
- Testing

**v0.3.0** (1 day):

- Documentation
- Release to PyPI
- Update my installation

## Notes

- Keep `tools/nautilus/` around for a few versions (safety)
- Nightly cron update is CRITICAL for my setup
- Test chamber promotion logic thoroughly
- Gravity scores must persist across migration
- Consider making nautilus optional (enabled=false)?
