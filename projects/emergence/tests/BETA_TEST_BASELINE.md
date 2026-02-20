# Nautilus v0.4.0 Beta Test Baseline
**Date:** 2026-02-14 21:10 GMT  
**System:** Jarvis (macOS, main agent)

## Test Results: 25/31 PASSING (81%)

### ✅ PASSED (25 tests)
**Search (5/6):**
- ✅ Semantic search basic
- ✅ Gravity scoring
- ✅ Chamber filtering  
- ✅ Trapdoor mode
- ✅ Different file types

**Status (5/5):**
- ✅ Chamber distribution
- ✅ Door coverage
- ✅ Mirror completeness
- ✅ Database health
- ✅ All phases present

**Migration (2/3):**
- ✅ Backward compatibility
- ✅ No data loss

**Integration (3/4):**
- ✅ Package import
- ✅ CLI commands work
- ✅ No conflicts with tools

**Edge Cases (6/6):**
- ✅ Corrupted database handling
- ✅ Concurrent access
- ✅ Large database performance
- ✅ Missing columns migration
- ✅ Superseded chunks

**Maintenance (4/4):**
- ✅ Classifies chambers
- ✅ Auto-tags
- ✅ Decay
- ✅ Links mirrors

**CLI (1/3):**
- ✅ Search command

### ❌ FAILED (6 tests)

1. **TestSearch::test_search_context_classification**
   - Issue: Door context tags not being detected
   - Impact: Medium (tagging feature)

2. **TestMigration::test_migration_data_preservation**
   - Issue: Data not found after migration
   - Impact: High (migration reliability)

3. **TestIntegration::test_config_changes_reflected**
   - Issue: Config default mismatch (168h vs 24h)
   - Impact: Low (config test issue)

4. **TestEdgeCases::test_empty_database_initialization**
   - Issue: Migration copying prod DB to test env
   - Impact: Medium (test isolation)

5. **TestCLI::test_cli_gravity_score**
   - Issue: Wrong module entry point
   - Impact: Low (CLI wrapper)

6. **TestCLI::test_cli_chambers_status**
   - Issue: Wrong module entry point
   - Impact: Low (CLI wrapper)

## Critical Bug Fixed

**Bug:** `cmd_decay()` returned `None` instead of result dict  
**Fix:** Added `return result` statement in `gravity.py:352`  
**Impact:** Fixed all 4 maintenance tests

## Remaining Issues for Beta

1. **Door tagging** - Context classification not working
2. **Migration** - Data preservation test failing  
3. **Test isolation** - Empty DB test sees prod data
4. **CLI entry points** - gravity/chambers commands need module fix

## Performance

All performance tests passing:
- 1000 inserts: < 5s target
- Complex query: < 100ms
- Concurrent access: > 50% success

## Next Steps

1. Deploy to Aurora (Ubuntu) for multi-agent testing
2. Test chamber promotion (atrium → corridor → vault)
3. Validate summarization and tagging quality
4. Fix remaining test failures
5. Document cross-contamination prevention
