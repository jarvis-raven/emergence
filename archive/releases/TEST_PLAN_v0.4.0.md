# v0.4.0 PyPI Package Testing Plan

**For:** Dan (pre-upload verification)
**Package:** emergence-ai v0.4.0
**Date:** 2026-02-15

---

## Pre-Build Checklist

Before building the package, verify:

- [ ] Version is `0.4.0` in `pyproject.toml`
- [ ] Version is `0.4.0` in `core/__init__.py`
- [ ] Version is `0.4.0` in `core/nautilus/__init__.py` (as `0.4.0-beta`)
- [ ] `core.nautilus` is listed in `[tool.setuptools] packages` in `pyproject.toml`
- [ ] CHANGELOG.md has comprehensive v0.4.0 entry
- [ ] RELEASE_NOTES_v0.4.0.md exists and is complete
- [ ] All tests pass: `pytest tests/`
- [ ] No uncommitted changes: `git status`

---

## Step 1: Build Package

### Build Command

```bash
cd ~/projects/emergence
python -m build
```

**Note:** If `build` module not installed:

```bash
pip install --upgrade build
```

### Expected Output

```
Successfully built emergence-ai-0.4.0.tar.gz and emergence_ai-0.4.0-py3-none-any.whl
```

### Verify Build Artifacts

```bash
ls -lh dist/
```

Should show:

```
emergence-ai-0.4.0.tar.gz
emergence_ai-0.4.0-py3-none-any.whl
```

---

## Step 2: Verify Package Contents

### Check Source Distribution

```bash
tar -tzf dist/emergence-ai-0.4.0.tar.gz | head -20
```

**Expected:** Should include top-level files:

- `emergence-ai-0.4.0/pyproject.toml`
- `emergence-ai-0.4.0/README.md`
- `emergence-ai-0.4.0/LICENSE`
- `emergence-ai-0.4.0/CHANGELOG.md`

### Check Nautilus Module Inclusion

```bash
tar -tzf dist/emergence-ai-0.4.0.tar.gz | grep "core/nautilus"
```

**Expected output (all files present):**

```
emergence-ai-0.4.0/core/nautilus/__init__.py
emergence-ai-0.4.0/core/nautilus/__main__.py
emergence-ai-0.4.0/core/nautilus/chambers.py
emergence-ai-0.4.0/core/nautilus/config.py
emergence-ai-0.4.0/core/nautilus/db_utils.py
emergence-ai-0.4.0/core/nautilus/doors.py
emergence-ai-0.4.0/core/nautilus/gravity.py
emergence-ai-0.4.0/core/nautilus/logging_config.py
emergence-ai-0.4.0/core/nautilus/migrate_db.py
emergence-ai-0.4.0/core/nautilus/mirrors.py
emergence-ai-0.4.0/core/nautilus/nautilus_cli.py
emergence-ai-0.4.0/core/nautilus/nightly.py
emergence-ai-0.4.0/core/nautilus/session_hooks.py
```

**Count files:**

```bash
tar -tzf dist/emergence-ai-0.4.0.tar.gz | grep "core/nautilus.*\.py$" | wc -l
```

**Expected:** 13 Python files

### Check Other Core Modules

```bash
tar -tzf dist/emergence-ai-0.4.0.tar.gz | grep "core/" | grep -E "(drives|memory|dream_engine|first_light|aspirations)" | head -10
```

**Expected:** All core modules present (drives, memory, dream_engine, first_light, aspirations)

### Check Wheel Contents

```bash
unzip -l dist/emergence_ai-0.4.0-py3-none-any.whl | grep "core/nautilus"
```

**Expected:** Same nautilus files as in source distribution

---

## Step 3: Test Installation in Clean Environment

### Create Test Environment

```bash
cd ~/projects/emergence
python -m venv test_env_v040
source test_env_v040/bin/activate
```

**Windows:**

```cmd
python -m venv test_env_v040
test_env_v040\Scripts\activate
```

### Install from Local Package

```bash
pip install dist/emergence-ai-0.4.0.tar.gz
```

**Expected output:**

```
Successfully installed emergence-ai-0.4.0 questionary-2.0.1 rich-13.7.0 ...
```

### Verify Installation

```bash
pip show emergence-ai
```

**Expected:**

```
Name: emergence-ai
Version: 0.4.0
Summary: AI Agent Selfhood Toolkit — Internal drives, memory, and consciousness infrastructure
Home-page: https://github.com/jarvis-raven/emergence
Author: Jarvis Raven, Dan Aghili
License: MIT
...
```

---

## Step 4: Test Imports

### Test Core Imports

```bash
python -c "import core; print(f'✓ Core version: {core.__version__}')"
```

**Expected:** `✓ Core version: 0.4.0`

### Test Existing Module Imports

```bash
python << EOF
from core import drives, memory, dream_engine, first_light
print('✓ Drives module OK')
print('✓ Memory module OK')
print('✓ Dream engine module OK')
print('✓ First Light module OK')
EOF
```

**Expected:** All four success messages, no errors

### Test Nautilus Imports (Critical!)

```bash
python << EOF
from core.nautilus import gravity, chambers, doors, mirrors
print('✓ Gravity module OK')
print('✓ Chambers module OK')
print('✓ Doors module OK')
print('✓ Mirrors module OK')
EOF
```

**Expected:** All four success messages, no errors

### Test Nautilus Submodule Imports

```bash
python << EOF
from core.nautilus import config, session_hooks, nightly, db_utils, logging_config
print('✓ Config module OK')
print('✓ Session hooks OK')
print('✓ Nightly maintenance OK')
print('✓ Database utils OK')
print('✓ Logging config OK')
EOF
```

**Expected:** All five success messages, no errors

### Test Nautilus CLI Module

```bash
python -c "from core.nautilus import nautilus_cli; print('✓ Nautilus CLI module OK')"
```

**Expected:** `✓ Nautilus CLI module OK`

---

## Step 5: Test CLI Commands

### Test Main CLI

```bash
emergence --help
```

**Expected:** Help text with available commands including drives, first-light, etc.

```bash
emergence --version
```

**Expected:** Should show version (may show package version or core version)

### Test Drives CLI

```bash
emergence drives --help
```

**Expected:** Help text for drives commands

### Test Nautilus CLI (Critical!)

```bash
emergence nautilus --help
```

**Expected:** Help text showing:

```
Usage: emergence nautilus [OPTIONS] COMMAND [ARGS]...

Nautilus Memory Palace Commands

Commands:
  search       Search across memory chambers
  promote      Manually promote a file to a higher chamber
  status       Show Nautilus configuration and chamber statistics
  maintenance  Run manual maintenance cycle
```

### Test Nautilus Subcommands

```bash
emergence nautilus status
```

**Expected:** Either configuration output or error about missing config (expected in clean env)

```bash
emergence nautilus search --help
```

**Expected:** Help text for search command

---

## Step 6: Functional Testing (Optional but Recommended)

### Initialize Test Configuration

```bash
mkdir -p ~/.emergence-test
cat > ~/.emergence-test/config.json << 'EOF'
{
  "nautilus": {
    "enabled": true,
    "workspace": "~/.emergence-test/workspace",
    "db_path": "~/.emergence-test/nautilus.db"
  }
}
EOF
```

### Test Nautilus Core Functions

```bash
python << 'EOF'
import os
from pathlib import Path
from core.nautilus import gravity, chambers
from core.nautilus.config import get_config, get_workspace

# Test config loading
config = get_config()
print(f"✓ Config loaded: {config.get('nautilus', {}).get('enabled', False)}")

# Test workspace detection
workspace = get_workspace()
print(f"✓ Workspace: {workspace}")

# These would fail without full config, but imports should work
print("✓ All Nautilus core functions importable")
EOF
```

**Expected:** No import errors (functional errors expected without full setup)

---

## Step 7: Cleanup Test Environment

```bash
deactivate
rm -rf test_env_v040
rm -rf ~/.emergence-test  # If created
```

---

## Step 8: Test Wheel Installation (Alternative)

Repeat Steps 3-6 but install the wheel instead:

```bash
python -m venv test_env_wheel
source test_env_wheel/bin/activate
pip install dist/emergence_ai-0.4.0-py3-none-any.whl
# ... run same tests ...
deactivate
rm -rf test_env_wheel
```

---

## Critical Success Criteria

Before uploading to PyPI, ALL of these must pass:

- [ ] Package builds without errors
- [ ] Source distribution (.tar.gz) contains all 13 nautilus .py files
- [ ] Wheel (.whl) contains all 13 nautilus .py files
- [ ] Clean venv installation succeeds
- [ ] `pip show emergence-ai` shows version 0.4.0
- [ ] Core version check shows 0.4.0
- [ ] All existing modules import successfully (drives, memory, etc.)
- [ ] All Nautilus modules import successfully (gravity, chambers, doors, mirrors)
- [ ] `emergence --help` works
- [ ] `emergence nautilus --help` works and shows nautilus commands
- [ ] No import errors when testing individual Nautilus submodules

---

## Common Issues & Solutions

### Issue: `ModuleNotFoundError: No module named 'core.nautilus'`

**Cause:** Nautilus not included in package
**Check:** Verify `core.nautilus` in `pyproject.toml` packages list
**Fix:** Add to packages list and rebuild

### Issue: `emergence nautilus` command not found

**Cause:** CLI integration not working
**Check:** Verify `core.nautilus.nautilus_cli` exists in package
**Fix:** Check package contents with `tar -tzf`

### Issue: Import works but submodules fail

**Cause:** **init**.py not properly exporting modules
**Check:** `core/nautilus/__init__.py` has all imports
**Fix:** Verify `__all__` list and imports in `__init__.py`

### Issue: Version mismatch

**Cause:** Version not updated in all files
**Check:** `pyproject.toml`, `core/__init__.py`, `core/nautilus/__init__.py`
**Fix:** Update all version strings to 0.4.0

---

## Post-Upload Verification (After PyPI)

Once uploaded to PyPI, test the live package:

```bash
python -m venv test_pypi
source test_pypi/bin/activate
pip install emergence-ai==0.4.0
python -c "from core.nautilus import gravity; print('✓ PyPI package OK')"
emergence nautilus --help
deactivate
rm -rf test_pypi
```

---

## Upload Commands (For Dan Only)

**Test PyPI (recommended first):**

```bash
python -m twine upload --repository testpypi dist/*
```

**Production PyPI:**

```bash
python -m twine upload dist/*
```

**Note:** Requires PyPI credentials configured in `~/.pypirc` or via environment variables.

---

## Rollback Plan

If issues discovered after upload:

1. **Yank the release** on PyPI (makes it unavailable for new installs)
2. Fix issues in code
3. Bump to v0.4.1
4. Re-test using this plan
5. Upload v0.4.1

**To yank:**

```bash
# Via PyPI web interface: https://pypi.org/project/emergence-ai/0.4.0/
# Or via API (requires authentication)
```

---

## Questions Before Upload?

- Does everything in the "Critical Success Criteria" section pass?
- Are all 13 Nautilus Python files present in the package?
- Does `emergence nautilus --help` work in clean environment?
- Have you tested both .tar.gz and .whl installations?

If YES to all → ✅ Safe to upload
If NO to any → ❌ Debug and re-test

---

**Prepared by:** Kimi (Subagent)
**For:** Dan Aghili
**Date:** 2026-02-15
**Package:** emergence-ai v0.4.0
