# Emergence Test Suite

Comprehensive testing for the Emergence AI framework, with focus on Nautilus v0.4.0 alpha validation.

## Test Structure

```
tests/
├── __init__.py
├── test_nautilus_alpha.py    # Alpha release validation suite
└── README.md                  # This file
```

## Running Tests

### All Tests
```bash
pytest tests/ -v
```

### Specific Test Categories
```bash
# Search tests
pytest tests/test_nautilus_alpha.py::TestSearch -v

# Status tests
pytest tests/test_nautilus_alpha.py::TestStatus -v

# Migration tests
pytest tests/test_nautilus_alpha.py::TestMigration -v

# Integration tests
pytest tests/test_nautilus_alpha.py::TestIntegration -v

# Edge cases
pytest tests/test_nautilus_alpha.py::TestEdgeCases -v
```

### Individual Tests
```bash
pytest tests/test_nautilus_alpha.py::TestSearch::test_search_semantic_basic -v
```

### With Coverage
```bash
pytest tests/ --cov=core.nautilus --cov-report=html
```

## Test Categories

### 🔍 Search Testing (`TestSearch`)
- **Semantic search**: Validates full pipeline search functionality
- **Gravity scoring**: Tests importance-weighted ranking
- **Chamber filtering**: Validates temporal layer filtering (atrium/corridor/vault)
- **Context classification**: Tests query context detection
- **File type coverage**: Tests daily, session, project, and summary files
- **Trapdoor mode**: Validates context bypass functionality

### 📊 Status Testing (`TestStatus`)
- **Chamber distribution**: Validates reporting of memory distribution across chambers
- **Door coverage**: Tests tag coverage metrics
- **Mirror completeness**: Validates link completeness reporting
- **Database health**: Tests health indicators and diagnostics
- **Phase reporting**: Validates all four phases are reported

### 🔄 Migration Testing (`TestMigration`)
- **Data preservation**: Ensures migration preserves all records
- **Backward compatibility**: Tests old schema handling
- **No data loss**: Validates complete migration without loss
- **Column migration**: Tests automatic schema updates

### 🔌 Integration Testing (`TestIntegration`)
- **Package imports**: Validates emergence package integration
- **Config changes**: Tests configuration propagation
- **CLI commands**: Validates CLI functionality from emergence namespace
- **No conflicts**: Tests coexistence with legacy tools

### ⚠️ Edge Cases (`TestEdgeCases`)
- **Empty database**: Tests initialization with no data
- **Corrupted database**: Validates graceful error handling
- **Concurrent access**: Tests thread safety with WAL mode
- **Large scale**: Performance benchmarks with 1000+ files
- **Missing columns**: Tests automatic schema migration
- **Superseded chunks**: Validates handling of replaced content

### 🛠️ Maintenance Testing (`TestMaintenance`)
- **Chamber classification**: Tests automatic file classification
- **Auto-tagging**: Validates context tag assignment
- **Gravity decay**: Tests time-based importance decay
- **Mirror linking**: Tests automatic summary linking

### 💻 CLI Testing (`TestCLI`)
- **Search command**: Tests `emergence nautilus search`
- **Gravity command**: Tests `emergence nautilus gravity`
- **Chambers command**: Tests `emergence nautilus chambers`
- **Status command**: Tests `emergence nautilus status`

## Test Fixtures

### `temp_workspace`
Creates isolated temporary workspace with proper directory structure:
- `memory/daily/` - Daily logs
- `memory/sessions/` - Session notes
- `memory/projects/` - Project documentation
- `memory/corridors/` - Weekly/monthly summaries
- `memory/vaults/` - Crystallized knowledge
- `state/nautilus/` - Database storage

### `sample_memories`
Generates sample memory files covering all file types and chambers.

### `populated_db`
Creates pre-populated gravity database with realistic test data including access counts, chambers, tags, and timestamps.

## Performance Benchmarks

The test suite includes performance benchmarks:

- **Bulk insert**: 1000 records < 5 seconds
- **Complex queries**: < 100ms
- **Concurrent access**: 10 threads successfully accessing database

Results are printed during test execution:
```
📊 Performance Benchmarks:
   1000 inserts: 0.523s (1912 ops/s)
   Complex query: 0.003s
```

## Requirements

```bash
pip install pytest pytest-timeout
```

Optional for coverage:
```bash
pip install pytest-cov
```

## CI/CD Integration

For continuous integration, run:
```bash
pytest tests/ --tb=short --maxfail=3
```

## Alpha Release Validation Checklist

- [ ] All search tests passing
- [ ] All status tests passing
- [ ] All migration tests passing
- [ ] All integration tests passing
- [ ] All edge case tests passing
- [ ] Performance benchmarks within acceptable ranges
- [ ] CLI commands functional
- [ ] No regression in existing functionality

## Known Limitations

- **Search tests**: Require `openclaw memory search` to be functional
- **CLI tests**: Require emergence package to be properly installed
- **Concurrency tests**: May have timing-dependent behavior

## Contributing

When adding new tests:
1. Add to appropriate test class
2. Use descriptive test names (`test_feature_behavior`)
3. Include docstrings explaining what's being tested
4. Use fixtures for common setup
5. Assert specific, meaningful conditions
6. Document any external dependencies

## Debugging Failed Tests

Verbose output:
```bash
pytest tests/test_nautilus_alpha.py::test_name -vv -s
```

Show local variables on failure:
```bash
pytest tests/test_nautilus_alpha.py::test_name -l
```

Drop into debugger on failure:
```bash
pytest tests/test_nautilus_alpha.py::test_name --pdb
```

## Contact

For test failures or questions about the test suite, check the issue tracker or contact the Nautilus team.
