# Nautilus Test Suite Quick Start

## Running Tests

### Run All Tests
```bash
cd projects/emergence
python3 -m pytest tests/ -v
```

### Run Specific Test Suites
```bash
# Alpha tests (31 tests)
pytest tests/test_nautilus_alpha.py -v

# Integration tests (18 tests)
pytest tests/integration/ -v

# Performance tests (10 tests)
pytest tests/performance/ -v
```

### Run Individual Tests
```bash
pytest tests/test_nautilus_alpha.py::TestSearch::test_search_semantic_basic -v
```

## Current Status

**Alpha Tests:** 23/31 passing (74%)
**Integration Tests:** Needs API fixes
**Performance Tests:** Ready to run after fixes

See `REGRESSION_TEST_REPORT.md` for full details.

## Known Issues

1. **CLI tests fail:** Module path issues with `python3 -m core.nautilus`
2. **Integration tests fail:** API compatibility (table names, return types)
3. **Some tests use production data:** Need better isolation

## Quick Fixes Needed

### Fix 1: Update table references
```python
# Change
cursor.execute("SELECT COUNT(*) FROM chunks")
# To
cursor.execute("SELECT COUNT(*) FROM gravity")
```

### Fix 2: Handle dict return from get_gravity_score
```python
# Change
score = get_gravity_score(path)
assert score > 0
# To
result = get_gravity_score(path)
score = result.get("effective_mass", 0)
assert score > 0
```

### Fix 3: Access nested status
```python
# Change
assert "phase_1_gravity" in status
# To
assert "phase_1_gravity" in status["nautilus"]
```

### Fix 4: Use cmd_boost instead of cmd_record_satisfaction
```python
# Change
cmd_record_satisfaction(path, satisfaction=0.9)
# To
cmd_boost([path, '--amount', '9.0'])
```

## Test Coverage

Run with coverage:
```bash
pytest tests/ --cov=core.nautilus --cov-report=html
open htmlcov/index.html
```

## Adding New Tests

1. Create test file in appropriate directory
2. Import from `core.nautilus`
3. Use `isolated_workspace` fixture for isolation
4. Follow naming convention: `test_feature_behavior`
5. Add docstring explaining what's tested

Example:
```python
def test_new_feature(isolated_workspace):
    """Test that new feature works correctly."""
    memory = isolated_workspace / "memory"
    # ... test code ...
    assert expected_behavior
```

## Troubleshooting

**Tests fail with "database locked":**
- Ensure no other processes using test database
- WAL mode should be automatic

**Tests fail with "module not found":**
- Run from `projects/emergence/` directory
- Check `core.nautilus` is importable

**Tests timeout:**
- Increase timeout in pytest.ini
- Check for infinite loops

## Continuous Integration

For CI/CD:
```bash
# Fail fast
pytest tests/ --tb=short --maxfail=3

# Generate reports
pytest tests/ --junit-xml=test-results.xml --cov-report=xml
```

Target: All tests passing, < 60s runtime
