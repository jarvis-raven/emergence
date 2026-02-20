# Nautilus Integration Test Fix - v0.4.0

## Summary

Fixed integration test harness in `tests/test_nautilus_integration.py` by refactoring the `temp_workspace` fixture to use environment variables and pre-initialize the database schema.

## Problem Diagnosed

The original fixture attempted to use `monkeypatch.setattr()` to patch config functions, but this failed due to import timing:

1. **Direct imports**: `session_hooks.py` does `from .config import get_gravity_db_path`, creating a direct reference before patches could be applied
2. **Module imports**: `gravity.py` does `from . import config`, accessing functions via module namespace
3. **Timing**: Patches were applied AFTER imports had already captured function references

Additionally, `_record_access_sync()` catches all exceptions silently, so when the database schema didn't exist, tests appeared to succeed but no data was written.

## Solution Implemented

Refactored `temp_workspace` fixture in `tests/test_nautilus_integration.py`:

1. **Environment variables**: Set `OPENCLAW_WORKSPACE` and `OPENCLAW_STATE_DIR` which `config.py` checks FIRST
2. **Schema initialization**: Create database tables directly before module imports to ensure they exist
3. **Module cache clearing**: Remove all `nautilus.*` modules from `sys.modules` to force fresh imports with new environment
4. **Lazy imports**: Move imports from module level into individual test methods to avoid timing issues

## Changes Made

- **File modified**: `tests/test_nautilus_integration.py`
- **Production code**: Zero changes (test-only fix)
- **Key changes**:
  - Fixture creates SQLite schema directly before module imports
  - Uses environment variables instead of monkeypatch
  - Clears module cache to force reimport with correct environment
  - Moves imports into test methods instead of module-level

## Test Results

```
✅ Unit tests: 8/8 passing
✅ Integration tests: 18/18 passing
✅ Total: 26/26 passing
```

## Verification Commands

```bash
# Integration tests only
cd ~/projects/emergence && python3 -m pytest tests/test_nautilus_integration.py -v

# Unit tests only
cd ~/projects/emergence && python3 -m pytest tests/test_nautilus.py -v

# Both together
cd ~/projects/emergence && python3 -m pytest tests/test_nautilus.py tests/test_nautilus_integration.py -v
```

## Technical Details

The fix exploits the fact that `nautilus/config.py` already supports environment variables as the highest-priority configuration source:

```python
def get_workspace() -> Path:
    # 1. Environment variable (HIGHEST PRIORITY)
    if ENV_WORKSPACE in os.environ:
        return Path(os.environ[ENV_WORKSPACE])
    # 2. Config file
    # 3. Inferred from package location
    # 4. Current directory
```

By setting these variables before imports and clearing the module cache, we ensure all code paths use the test workspace without any monkeypatching.

## Commits Ready For

This fix is ready to be committed with message:

```
fix: Nautilus integration test harness using environment variables

- Replace monkeypatch with environment variables (OPENCLAW_WORKSPACE, OPENCLAW_STATE_DIR)
- Pre-initialize SQLite schema before module imports
- Clear module cache to force fresh imports
- Move imports into test methods to avoid timing issues
- All 18 integration tests now passing (was 3 failed, 15 passed)
- Unit tests still passing (8/8)

Fixes #65, #66 test infrastructure
```
