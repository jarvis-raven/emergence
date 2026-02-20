# PyPI Release Checklist — Emergence v0.4.0 "Nautilus"

**Release Date:** TBD  
**Release Manager:** TBD  
**Package Name:** `emergence-ai`  
**Version:** 0.4.0

---

## Overview

This checklist covers the complete process for releasing Emergence v0.4.0 to PyPI. This is a **major feature release** introducing the Nautilus memory palace architecture, session hooks, nightly maintenance, and the Room web dashboard.

**⚠️ DO NOT PUBLISH TO PYPI UNTIL THIS CHECKLIST IS COMPLETE ⚠️**

---

## Pre-Release Checklist

### 1. Version Updates

- [ ] Update version in `setup.py` → `version="0.4.0"`
- [ ] Update version in `core/nautilus/__init__.py` → `__version__ = "0.4.0"`
- [ ] Update version in `README.md` header → `# Emergence v0.4.0`
- [ ] Update version in `room/README.md` if applicable
- [ ] Search for any remaining `0.3.0` references and update:
  ```bash
  grep -r "0\.3\.0" --include="*.py" --include="*.md" .
  ```

### 2. Changelog

- [ ] Create/update `CHANGELOG.md` with v0.4.0 entry
- [ ] Document all new features:
  - [ ] Nautilus memory palace (4-phase architecture)
  - [ ] Session lifecycle hooks
  - [ ] Nightly maintenance automation
  - [ ] Room web dashboard widget
  - [ ] Multi-agent deployment support
- [ ] List bug fixes:
  - [ ] `cmd_decay()` return value fix
  - [ ] Database migration improvements
  - [ ] Schema compatibility updates
- [ ] Note breaking changes (if any) - **NONE for v0.4.0**
- [ ] Add migration notes from 0.3.0
- [ ] Include performance improvements
- [ ] Add deprecation warnings (if any)

### 3. Testing

#### Unit Tests
- [ ] All tests passing locally:
  ```bash
  cd projects/emergence
  python3 -m pytest tests/ -v
  ```
- [ ] Expected: 31+ tests passing (Nautilus alpha + beta tests)
- [ ] No regressions in existing functionality
- [ ] Performance benchmarks met:
  - [ ] 1000 inserts < 5s
  - [ ] Complex queries < 100ms
  - [ ] Concurrent access >50% success

#### Integration Tests
- [ ] CLI commands work:
  ```bash
  python3 -m core.cli nautilus status
  python3 -m core.cli nautilus search "test"
  python3 -m core.cli nautilus maintain
  ```
- [ ] Python API works:
  ```python
  from core.nautilus import search, get_status, run_maintain
  results = search("test query")
  status = get_status()
  ```
- [ ] Room dashboard starts and responds:
  ```bash
  cd room && python3 server.py
  # Test http://localhost:5000
  ```

#### Fresh Install Test
- [ ] Create fresh virtual environment:
  ```bash
  python3 -m venv /tmp/emergence-test
  source /tmp/emergence-test/bin/activate
  ```
- [ ] Install from source:
  ```bash
  pip install -e .
  ```
- [ ] Verify imports work:
  ```python
  import core.nautilus
  from core.nautilus import search
  ```
- [ ] Run basic commands
- [ ] Deactivate and remove test env

#### Migration Test
- [ ] Test upgrade from v0.3.0:
  - [ ] Create v0.3.0 database
  - [ ] Run v0.4.0 code against it
  - [ ] Verify auto-migration works
  - [ ] Check data preservation
  - [ ] Validate new columns added

#### Platform Testing
- [ ] Test on macOS (if available)
- [ ] Test on Linux (Ubuntu/Debian)
- [ ] Test on Windows (if applicable)
- [ ] Verify paths work across platforms

### 4. Documentation

#### README.md
- [ ] Updated with v0.4.0 features
- [ ] Nautilus section complete and accurate
- [ ] Installation instructions current
- [ ] Quick start examples work
- [ ] Links valid (no 404s)
- [ ] Badges updated (version, tests, license)
- [ ] Screenshots current (if applicable)

#### API Documentation
- [ ] `core/nautilus/__init__.py` docstrings complete
- [ ] All public functions documented
- [ ] Examples included in docstrings
- [ ] Type hints present
- [ ] Parameter descriptions clear

#### User Guide
- [ ] Check if `docs/USER_GUIDE.md` exists
- [ ] Update with new features
- [ ] Add Nautilus usage examples
- [ ] Document session hooks
- [ ] Explain maintenance scheduling

#### Examples
- [ ] All code examples work:
  ```bash
  # Test each example in docs
  python3 examples/example1.py
  ```
- [ ] Examples reflect v0.4.0 API
- [ ] Output matches documentation

#### Configuration Documentation
- [ ] `emergence.json` schema documented
- [ ] All Nautilus config options explained
- [ ] Default values listed
- [ ] Environment variables documented

### 5. Package Preparation

#### setup.py Validation
- [ ] `setup.py` exists and is complete
- [ ] All required fields present:
  - [ ] name = "emergence-ai"
  - [ ] version = "0.4.0"
  - [ ] description
  - [ ] long_description (from README.md)
  - [ ] author / author_email
  - [ ] url / project_urls
  - [ ] license
  - [ ] classifiers
  - [ ] keywords
  - [ ] python_requires
- [ ] All dependencies listed in `install_requires`:
  - [ ] Check `room/requirements.txt` for Room deps
  - [ ] Verify version constraints
- [ ] Package data includes:
  - [ ] `core/nautilus/*.py`
  - [ ] `room/templates/*.html`
  - [ ] `room/static/**/*`
- [ ] Entry points defined (if applicable)
- [ ] Packages auto-discovered or explicitly listed

#### Dependency Check
- [ ] All dependencies available on PyPI
- [ ] Version constraints compatible
- [ ] No conflicting requirements
- [ ] Test with `pip check` after install
- [ ] Security audit:
  ```bash
  pip install safety
  safety check
  ```

#### Build Test
- [ ] Install build tools:
  ```bash
  pip install build twine
  ```
- [ ] Clean old builds:
  ```bash
  rm -rf dist/ build/ *.egg-info
  ```
- [ ] Build distributions:
  ```bash
  python3 -m build
  ```
- [ ] Check output:
  ```bash
  ls dist/
  # Should see:
  # emergence-ai-0.4.0.tar.gz
  # emergence-ai-0.4.0-py3-none-any.whl
  ```
- [ ] Inspect tarball contents:
  ```bash
  tar -tzf dist/emergence-ai-0.4.0.tar.gz | head -20
  ```
- [ ] Verify wheel contents:
  ```bash
  unzip -l dist/emergence-ai-0.4.0-py3-none-any.whl | head -20
  ```

#### Package Validation
- [ ] Check package metadata:
  ```bash
  twine check dist/*
  ```
- [ ] Should output: `PASSED`
- [ ] No warnings about long_description
- [ ] No missing required fields

#### Test Install from Built Package
- [ ] Create fresh virtual environment:
  ```bash
  python3 -m venv /tmp/emergence-pkg-test
  source /tmp/emergence-pkg-test/bin/activate
  ```
- [ ] Install from tarball:
  ```bash
  pip install dist/emergence-ai-0.4.0.tar.gz
  ```
- [ ] Test imports and basic functionality
- [ ] Install from wheel:
  ```bash
  pip uninstall emergence-ai -y
  pip install dist/emergence-ai-0.4.0-py3-none-any.whl
  ```
- [ ] Test again
- [ ] Deactivate and remove test env

---

## TestPyPI Upload (REQUIRED)

**Always test on TestPyPI before production PyPI!**

### 6. TestPyPI Preparation

- [ ] Create TestPyPI account: https://test.pypi.org/account/register/
- [ ] Verify email
- [ ] Generate API token:
  - Go to https://test.pypi.org/manage/account/token/
  - Create token with scope "Entire account"
  - Save token securely
- [ ] Configure `.pypirc`:
  ```bash
  cat > ~/.pypirc << 'EOF'
  [testpypi]
  username = __token__
  password = pypi-YOUR_TEST_TOKEN_HERE
  EOF
  chmod 600 ~/.pypirc
  ```

### 7. TestPyPI Upload

- [ ] Upload to TestPyPI:
  ```bash
  twine upload --repository testpypi dist/*
  ```
- [ ] Verify upload successful
- [ ] Check package page: https://test.pypi.org/project/emergence-ai/
- [ ] Review displayed information:
  - [ ] Version shows 0.4.0
  - [ ] Description renders correctly
  - [ ] Links work
  - [ ] Classifiers correct

### 8. TestPyPI Installation Test

- [ ] Create fresh virtual environment:
  ```bash
  python3 -m venv /tmp/emergence-testpypi
  source /tmp/emergence-testpypi/bin/activate
  ```
- [ ] Install from TestPyPI:
  ```bash
  pip install --index-url https://test.pypi.org/simple/ \
              --extra-index-url https://pypi.org/simple/ \
              emergence-ai==0.4.0
  ```
- [ ] Run smoke tests:
  ```python
  from core.nautilus import search, get_status
  print(get_status())
  ```
- [ ] Test CLI:
  ```bash
  python3 -m core.cli nautilus status
  ```
- [ ] Verify no errors
- [ ] Deactivate and remove test env

---

## Production PyPI Upload

**⚠️ POINT OF NO RETURN — Once uploaded, PyPI releases cannot be deleted! ⚠️**

### 9. Final Pre-Flight Checks

- [ ] All tests above passed
- [ ] TestPyPI version works correctly
- [ ] Documentation reviewed
- [ ] CHANGELOG.md complete
- [ ] Git status clean (no uncommitted changes)
- [ ] All changes committed to version control

### 10. PyPI Preparation

- [ ] Create PyPI account: https://pypi.org/account/register/
- [ ] Verify email
- [ ] Generate API token:
  - Go to https://pypi.org/manage/account/token/
  - Create token with scope "Entire account" (or project-scoped)
  - Save token securely
- [ ] Update `.pypirc`:
  ```bash
  cat >> ~/.pypirc << 'EOF'
  
  [pypi]
  username = __token__
  password = pypi-YOUR_PRODUCTION_TOKEN_HERE
  EOF
  ```

### 11. Production Upload

- [ ] **FINAL CHECK**: Review `dist/*` contents one more time
- [ ] Upload to PyPI:
  ```bash
  twine upload dist/*
  ```
- [ ] Verify upload successful
- [ ] Check package page: https://pypi.org/project/emergence-ai/

### 12. PyPI Package Validation

- [ ] Version shows 0.4.0
- [ ] Description renders correctly (check markdown)
- [ ] Project URLs work:
  - [ ] Homepage
  - [ ] Documentation
  - [ ] Source Code
  - [ ] Bug Tracker
- [ ] Classifiers correct
- [ ] License displayed
- [ ] Keywords appropriate

### 13. Production Installation Test

- [ ] Create fresh virtual environment:
  ```bash
  python3 -m venv /tmp/emergence-pypi-final
  source /tmp/emergence-pypi-final/bin/activate
  ```
- [ ] Install from PyPI:
  ```bash
  pip install emergence-ai==0.4.0
  ```
- [ ] Verify correct version installed:
  ```python
  import core.nautilus
  print(core.nautilus.__version__)  # Should be 0.4.0
  ```
- [ ] Run comprehensive smoke tests:
  ```python
  from core.nautilus import search, get_status, run_maintain
  
  # Test status
  status = get_status()
  assert 'nautilus' in status
  
  # Test search
  results = search("test", n=5)
  
  # Test maintenance
  result = run_maintain()
  ```
- [ ] Test CLI commands:
  ```bash
  python3 -m core.cli nautilus --help
  python3 -m core.cli nautilus status
  ```
- [ ] All tests pass
- [ ] Deactivate and remove test env

---

## Post-Release

### 14. Git Tagging

- [ ] Tag the release commit:
  ```bash
  git tag -a v0.4.0 -m "Release v0.4.0 - Nautilus Memory Palace"
  ```
- [ ] Push tag to remote:
  ```bash
  git push origin v0.4.0
  ```
- [ ] Verify tag appears on GitHub/GitLab

### 15. GitHub Release

- [ ] Go to repository releases page
- [ ] Click "Draft a new release"
- [ ] Select tag: `v0.4.0`
- [ ] Release title: `v0.4.0 - Nautilus Memory Palace`
- [ ] Description: Copy from CHANGELOG.md
- [ ] Attach build artifacts (optional):
  - [ ] `emergence-ai-0.4.0.tar.gz`
  - [ ] `emergence-ai-0.4.0-py3-none-any.whl`
- [ ] Mark as "Latest release" (if appropriate)
- [ ] Publish release

### 16. Documentation Updates

- [ ] Update documentation website (if applicable)
- [ ] Generate API docs:
  ```bash
  # If using Sphinx, pdoc, etc.
  pdoc core.nautilus --output-dir docs/api
  ```
- [ ] Deploy updated docs
- [ ] Verify links to v0.4.0 work

### 17. Community Announcement

- [ ] Prepare announcement text
- [ ] Include:
  - [ ] What's new in 0.4.0
  - [ ] Migration notes
  - [ ] Installation instructions
  - [ ] Links to docs and changelog
- [ ] Post to community channels:
  - [ ] Project blog (if exists)
  - [ ] Discord/Slack community
  - [ ] Reddit (if applicable)
  - [ ] Twitter/social media
  - [ ] Mailing list
- [ ] Update project README badges

### 18. Deployment Documentation

- [ ] Update deployment guides for v0.4.0
- [ ] Document new configuration options
- [ ] Update Docker images (if applicable)
- [ ] Update Kubernetes configs (if applicable)
- [ ] Update systemd service files for nightly maintenance
- [ ] Document cron job changes:
  ```bash
  # Old (v0.3.0)
  0 3 * * * cd /path/to/workspace && python3 tools/nautilus/nautilus.py maintain
  
  # New (v0.4.0)
  0 3 * * * cd /path/to/workspace && python3 -m core.cli nautilus maintain --register-recent
  ```

### 19. Monitoring

- [ ] Monitor PyPI download stats
- [ ] Watch for bug reports
- [ ] Monitor issue tracker
- [ ] Check community feedback
- [ ] Review installation errors

### 20. Cleanup

- [ ] Archive old build artifacts
- [ ] Update version to 0.4.1-dev or 0.5.0-dev in development
- [ ] Create v0.4.1 milestone for bug fixes (if needed)
- [ ] Update project board
- [ ] Celebrate! 🎉

---

## Rollback Plan

If critical issues are found post-release:

1. **DO NOT DELETE PYPI RELEASE** (not allowed by PyPI)
2. Instead, release a patch version immediately:
   - v0.4.1 with critical fixes
3. Update documentation to recommend v0.4.1
4. Post warning about v0.4.0 issues
5. Mark v0.4.0 as "yanked" on PyPI (if severe):
   ```bash
   # This prevents new installs but doesn't delete
   # Requires project permissions on PyPI
   ```

---

## Quality Gates

**Do not proceed to next section unless:**

- ✅ All items in current section checked
- ✅ Tests passing
- ✅ No blocking bugs
- ✅ Documentation complete
- ✅ Peer review passed (if applicable)

---

## Sign-off

- [ ] **Pre-Release Checklist Complete** - Signed: ____________ Date: ______
- [ ] **TestPyPI Validation Complete** - Signed: ____________ Date: ______
- [ ] **Production Upload Approved** - Signed: ____________ Date: ______
- [ ] **Post-Release Tasks Complete** - Signed: ____________ Date: ______

---

## Notes

Use this section for release-specific notes, issues encountered, or deviations from the checklist.

---

**Version:** 1.0  
**Last Updated:** 2026-02-14  
**Next Review:** After v0.4.0 release
