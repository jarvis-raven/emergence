# Nautilus v0.4.0 Alpha Testing Guide

This document describes the alpha testing process for Nautilus Memory Palace integration.

## Quick Start

```bash
# Install dependencies
pip install pytest pytest-timeout

# Run all alpha tests
cd projects/emergence
pytest tests/test_nautilus_alpha.py -v

# Or use the convenience script
./tests/run_alpha_tests.sh
```

## Test Coverage

The alpha test suite validates:

✅ **Search Functionality** (6 tests)
- Semantic search pipeline
- Gravity-based ranking
- Chamber filtering (atrium/corridor/vault)
- Context classification (doors)
- Multi-file-type search
- Trapdoor mode

✅ **Status Reporting** (5 tests)
- Chamber distribution metrics
- Tag coverage statistics
- Mirror link completeness
- Database health indicators
- All four phases reporting

✅ **Migration** (3 tests)
- Data preservation during migration
- Backward compatibility with old schemas
- Zero data loss validation

✅ **Integration** (4 tests)
- Import from emergence package
- Configuration propagation
- CLI command functionality
- No conflicts with legacy tools

✅ **Edge Cases** (6 tests)
- Empty database initialization
- Corrupted database handling
- Concurrent access (thread safety)
- Large-scale performance (1000+ files)
- Schema migration (missing columns)
- Superseded chunk handling

✅ **Maintenance** (4 tests)
- Auto chamber classification
- Context auto-tagging
- Gravity decay
- Mirror auto-linking

✅ **CLI** (3 tests)
- Search command
- Gravity command
- Chambers command

**Total: 31 comprehensive tests**

## Performance Benchmarks

Expected performance on modern hardware:

| Operation | Target | Measured |
|-----------|--------|----------|
| Bulk insert (1000 records) | < 5s | ~0.5s |
| Complex query | < 100ms | ~3ms |
| Concurrent threads (10) | ≥50% success | ~90% |

## Running Specific Test Categories

```bash
# Search tests only
pytest tests/test_nautilus_alpha.py::TestSearch -v

# Status tests only
pytest tests/test_nautilus_alpha.py::TestStatus -v

# Migration tests only
pytest tests/test_nautilus_alpha.py::TestMigration -v

# Integration tests only
pytest tests/test_nautilus_alpha.py::TestIntegration -v

# Edge cases only
pytest tests/test_nautilus_alpha.py::TestEdgeCases -v
```

## Running Individual Tests

```bash
pytest tests/test_nautilus_alpha.py::TestSearch::test_search_semantic_basic -v
```

## Test Output

### Successful Test
```
tests/test_nautilus_alpha.py::TestSearch::test_search_semantic_basic PASSED [10%]
```

### Failed Test
```
tests/test_nautilus_alpha.py::TestSearch::test_search_semantic_basic FAILED [10%]

FAILED tests/test_nautilus_alpha.py::TestSearch::test_search_semantic_basic
AssertionError: expected 'query' in result
```

### Performance Output
```
📊 Performance Benchmarks:
   1000 inserts: 0.523s (1912 ops/s)
   Complex query: 0.003s
```

## Test Fixtures

Tests use isolated temporary workspaces to avoid affecting production data:

- `temp_workspace` - Clean environment for each test
- `sample_memories` - Pre-populated memory files
- `populated_db` - Pre-loaded gravity database

## Known Test Dependencies

Some tests have external dependencies:

1. **Search tests**: Require `openclaw memory search` CLI
2. **CLI tests**: Require emergence package installed
3. **Migration tests**: May create temporary files

If dependencies are missing, tests will either skip or fail gracefully.

## Debugging Failed Tests

### Verbose Output
```bash
pytest tests/test_nautilus_alpha.py::test_name -vv -s
```

### Show Local Variables
```bash
pytest tests/test_nautilus_alpha.py::test_name -l
```

### Drop into Debugger
```bash
pytest tests/test_nautilus_alpha.py::test_name --pdb
```

### Run with Coverage
```bash
pytest tests/test_nautilus_alpha.py --cov=core.nautilus --cov-report=html
# Open htmlcov/index.html in browser
```

## Alpha Validation Checklist

Before declaring v0.4.0 alpha ready:

- [ ] All 31 tests passing
- [ ] Performance benchmarks within targets
- [ ] No regressions in existing functionality
- [ ] Migration script tested on real data
- [ ] CLI commands functional from emergence namespace
- [ ] Documentation complete
- [ ] Edge cases handled gracefully

## CI/CD Integration

For automated testing:

```bash
# Run all tests with fail-fast
pytest tests/test_nautilus_alpha.py --tb=short --maxfail=3

# Generate JUnit XML for CI
pytest tests/test_nautilus_alpha.py --junit-xml=test-results.xml

# Generate coverage report
pytest tests/test_nautilus_alpha.py --cov=core.nautilus --cov-report=xml
```

## Adding New Tests

When adding tests:

1. Choose appropriate test class (TestSearch, TestStatus, etc.)
2. Use descriptive names: `test_feature_behavior`
3. Add docstring explaining what's tested
4. Use fixtures for setup
5. Make assertions specific and meaningful
6. Update this document

Example:
```python
def test_new_feature(self, temp_workspace, populated_db):
    """Test that new feature works correctly."""
    result = new_feature_function()
    assert result.status == "success"
    assert len(result.items) > 0
```

## Troubleshooting

### Tests fail with "database locked"
- Ensure no other processes are using the test database
- Check that WAL mode is enabled (automatic in `get_db()`)

### Tests fail with "module not found"
- Ensure you're running from `projects/emergence/` directory
- Check that `core.nautilus` package is in Python path

### Tests timeout
- Increase timeout in pytest.ini
- Check for infinite loops or hanging operations

### Performance tests fail
- Machine may be slower than expected
- Adjust thresholds in test_large_database_performance

## Support

For issues with the test suite:
1. Check this document
2. Review test output carefully
3. Try running tests individually
4. Check pytest version compatibility
5. Open issue with full test output

## Test Maintenance

Tests should be:
- ✅ Run before each commit
- ✅ Run in CI/CD pipeline
- ✅ Updated when features change
- ✅ Kept independent and isolated
- ✅ Fast enough for frequent runs

Target: Full test suite < 60 seconds
