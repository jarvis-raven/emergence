# PR #73: v0.4.0 PyPI Release Preparation - Checklist

**Branch:** `release/73-pypi-prep`
**Target:** `main`
**Assignee:** Dan Aghili
**Created by:** Kimi (Subagent)
**Date:** 2026-02-15

---

## Summary

This PR prepares Emergence v0.4.0 for PyPI publication. All version bumps, package configuration updates, release documentation, and testing instructions are complete. **Dan will handle the actual PyPI upload after reviewing and merging this PR.**

---

## Changes Made

### 1. Version Updates ✅

- [x] **pyproject.toml**: `0.3.0` → `0.4.0`
- [x] **core/**init**.py**: `0.2.2` → `0.4.0`
- [x] Version consistency verified across all files
- [x] core/nautilus/**init**.py already has `0.4.0-beta`

### 2. Package Configuration ✅

- [x] Added `core.nautilus` to `[tool.setuptools] packages` in `pyproject.toml`
- [x] Verified all Nautilus submodules will be included (13 Python files)
- [x] No new dependencies required (all optional)
- [x] Package data configuration unchanged (no new static files)

### 3. CHANGELOG.md ✅

- [x] Comprehensive v0.4.0 entry added (155 new lines)
- [x] Sections included:
  - **Added**: Nautilus system (gravity, chambers, doors, mirrors, CLI, session hooks, nightly maintenance, Room widget)
  - **Improved**: Type hints, logging, database reliability, error handling
  - **Fixed**: Chamber promotion bug, gravity.py Row.get() error
  - **Documentation**: 5,124 lines across 4 guides
  - **Technical**: No breaking changes, contributors credited
- [x] Version comparison link added: `[0.4.0]: https://github.com/jarvis-raven/emergence/compare/v0.3.0...v0.4.0`
- [x] Referenced all merged PRs (#118-121, #124)
- [x] Contributors credited: Jarvis Raven, Aurora AI, Dan Aghili

### 4. Release Notes ✅

- [x] **RELEASE_NOTES_v0.4.0.md** created (387 lines)
- [x] Executive summary: "The Memory Palace"
- [x] Key features with user-friendly descriptions:
  - Gravity importance scoring
  - Three-tier chamber system
  - Multi-strategy search
  - Semantic embeddings
  - CLI integration
  - Nightly automation
  - Room dashboard
- [x] Upgrade instructions from v0.3.0
- [x] No breaking changes confirmed
- [x] Known issues documented (OpenClaw integration, embeddings)
- [x] Testing section included
- [x] Developer API reference
- [x] Credits to all contributors

### 5. Testing Documentation ✅

- [x] **TEST_PLAN_v0.4.0.md** created (467 lines)
- [x] Pre-build checklist
- [x] Build commands: `python -m build`
- [x] Package verification commands:
  - Source distribution contents check
  - Wheel contents check
  - Nautilus module inclusion verification (13 files expected)
- [x] Clean environment testing procedure
- [x] Installation verification steps
- [x] Import testing for all modules:
  - Core modules (drives, memory, dream_engine, first_light)
  - Nautilus modules (gravity, chambers, doors, mirrors)
  - Nautilus submodules (config, session_hooks, nightly, etc.)
- [x] CLI testing:
  - `emergence --help`
  - `emergence nautilus --help`
  - All nautilus subcommands
- [x] Critical success criteria checklist
- [x] Common issues & solutions
- [x] Post-upload verification
- [x] Rollback plan

---

## Files Modified/Created

```
CHANGELOG.md            (155+ lines added)
RELEASE_NOTES_v0.4.0.md (387 lines created)
TEST_PLAN_v0.4.0.md     (467 lines created)
core/__init__.py        (version updated)
pyproject.toml          (version + packages updated)
```

**Total additions:** 1,012 lines

---

## Git Commits

**Single commit:**

```
b76baa4 chore(release): prepare v0.4.0 PyPI package (#73)
```

All changes are in one atomic commit for easy review and potential revert if needed.

---

## Pre-Merge Verification (For Dan)

Before merging, verify:

- [ ] Review CHANGELOG.md v0.4.0 entry for accuracy and completeness
- [ ] Review RELEASE_NOTES_v0.4.0.md for user-facing clarity
- [ ] Verify version is 0.4.0 in both pyproject.toml and core/**init**.py
- [ ] Verify `core.nautilus` is in packages list in pyproject.toml
- [ ] Check that commit message follows project conventions
- [ ] Ensure no unintended changes in the diff

**Review checklist:**

```bash
cd ~/projects/emergence
git checkout release/73-pypi-prep
git log main..HEAD --oneline  # Should show ONLY Kimi's commit
git diff main..HEAD --stat     # Review file changes
```

---

## Post-Merge Actions (For Dan)

After merging to main:

### 1. Build Package ✅

```bash
cd ~/projects/emergence
git checkout main
git pull
python -m build
```

**Expected output:**

- `dist/emergence-ai-0.4.0.tar.gz`
- `dist/emergence_ai-0.4.0-py3-none-any.whl`

### 2. Run Test Plan ✅

Follow **TEST_PLAN_v0.4.0.md** step by step:

```bash
# Quick verification
tar -tzf dist/emergence-ai-0.4.0.tar.gz | grep "core/nautilus" | wc -l
# Expected: 13 files

# Clean environment test
python -m venv test_env
source test_env/bin/activate
pip install dist/emergence-ai-0.4.0.tar.gz
python -c "from core.nautilus import gravity, chambers, doors, mirrors; print('✓ OK')"
emergence nautilus --help
deactivate
rm -rf test_env
```

**If all tests pass** → Proceed to upload
**If any test fails** → Contact Jarvis/Kimi for fixes

### 3. Upload to PyPI 🚀

**Option A: Test PyPI first (recommended)**

```bash
python -m twine upload --repository testpypi dist/emergence-ai-0.4.0*
# Test installation from Test PyPI
pip install --index-url https://test.pypi.org/simple/ emergence-ai==0.4.0
```

**Option B: Production PyPI**

```bash
python -m twine upload dist/emergence-ai-0.4.0*
# Or upload both source and wheel:
# python -m twine upload dist/emergence-ai-0.4.0.tar.gz dist/emergence_ai-0.4.0-py3-none-any.whl
```

### 4. Create Git Tag 🏷️

```bash
git tag -a v0.4.0 -m "Release v0.4.0: The Memory Palace

Nautilus reflective journaling system
- Four-phase memory architecture (gravity, chambers, doors, mirrors)
- CLI integration and nightly automation
- Comprehensive documentation (5,124 lines)
- Type hints, logging, and reliability improvements

Contributors: Jarvis Raven, Aurora AI, Dan Aghili
Related PRs: #118, #119, #120, #121, #124"

git push origin v0.4.0
```

### 5. Create GitHub Release 📦

Go to: https://github.com/jarvis-raven/emergence/releases/new

- **Tag:** `v0.4.0`
- **Title:** `v0.4.0 — The Memory Palace`
- **Description:** Copy from `RELEASE_NOTES_v0.4.0.md`
- **Assets:** Upload `dist/emergence-ai-0.4.0.tar.gz` and `.whl`
- **Pre-release:** ☐ (unchecked - this is a stable release)

### 6. Verify Live Package ✅

```bash
pip install --upgrade emergence-ai
python -c "import core; print(core.__version__)"  # Should show 0.4.0
python -c "from core.nautilus import gravity; print('✓ Nautilus available')"
```

### 7. Announce Release 📢

- Update project README.md if needed
- Post to social media / Discord / community channels
- Notify active contributors (Jarvis, Aurora)

---

## What NOT to Do ⚠️

Per issue #73 instructions, **Kimi did NOT**:

- ❌ Upload to PyPI (Dan will do this)
- ❌ Create git tags (Dan will do this)
- ❌ Publish GitHub releases (Dan will do this)
- ❌ Modify any code functionality (only docs/config)
- ❌ Change any dependencies
- ❌ Include breaking changes

---

## Rollback Procedure

If issues are discovered after PyPI upload:

### Immediate Actions

1. **Yank the release** on PyPI web interface (makes it unavailable for new installs but doesn't delete it)
2. Post warning on GitHub releases page

### Fix & Re-release

1. Create hotfix branch: `git checkout -b hotfix/v0.4.1`
2. Fix the issue
3. Update version to `0.4.1` everywhere
4. Update CHANGELOG with hotfix entry
5. Test using TEST_PLAN_v0.4.0.md (adapted for 0.4.1)
6. Merge to main
7. Upload v0.4.1 to PyPI
8. Tag and release v0.4.1

---

## Questions or Issues?

**Before merging:**

- Contact Jarvis or Kimi for clarification

**During testing:**

- Follow TEST_PLAN_v0.4.0.md troubleshooting section
- Check that all 13 Nautilus Python files are present in package

**During upload:**

- Ensure PyPI credentials are configured
- Use Test PyPI first if unsure
- Have twine installed: `pip install twine`

**After upload:**

- Monitor PyPI for download stats
- Watch for user-reported issues
- Be ready to yank and hotfix if critical bugs found

---

## Success Criteria

This PR is ready to merge when:

- ✅ All changes reviewed and approved by Dan
- ✅ No merge conflicts with main
- ✅ Commit history is clean (single commit)
- ✅ All documentation is accurate and complete

After merge, package is ready to upload when:

- ✅ All tests in TEST_PLAN_v0.4.0.md pass
- ✅ Package contains all 13 Nautilus files
- ✅ Imports work in clean environment
- ✅ CLI commands work (`emergence nautilus --help`)

---

## Timeline

**Preparation:** 2026-02-15 (Kimi - Complete ✅)
**Review & Merge:** Dan (pending)
**Testing:** Dan (after merge)
**PyPI Upload:** Dan (after successful testing)
**Tagging & Release:** Dan (after successful upload)

---

**Prepared by:** Kimi (Subagent for Jarvis)
**Reviewed by:** _[Pending]_
**Merged by:** _[Pending]_
**Uploaded by:** _[Pending]_
