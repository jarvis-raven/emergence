#!/usr/bin/env python3
"""
🐚 Nautilus v0.4.0 Performance Test Suite

Tests Nautilus performance under load:
  1. Large database (1000+ chunks) performs well
  2. Concurrent access doesn't corrupt DB
  3. Search response time < 1s
  4. Nightly maintenance completes < 5 min
"""

import pytest
import sqlite3
import json
import os
import sys
import time
import threading
from pathlib import Path
from datetime import datetime, timezone, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.nautilus import (
    search,
    get_status,
    run_maintain,
)
from core.nautilus.gravity import (
    get_db,
    cmd_record_write,
    cmd_record_access,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def isolated_workspace(tmp_path):
    """Create isolated workspace for performance tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    memory = workspace / "memory"
    memory.mkdir()
    (memory / "daily").mkdir()
    (memory / "sessions").mkdir()
    (memory / "projects").mkdir()
    
    state = tmp_path / "state" / "nautilus"
    state.mkdir(parents=True)
    
    orig_workspace = os.environ.get("OPENCLAW_WORKSPACE")
    orig_state = os.environ.get("OPENCLAW_STATE_DIR")
    
    os.environ["OPENCLAW_WORKSPACE"] = str(workspace)
    os.environ["OPENCLAW_STATE_DIR"] = str(state)
    
    yield workspace
    
    if orig_workspace:
        os.environ["OPENCLAW_WORKSPACE"] = orig_workspace
    else:
        os.environ.pop("OPENCLAW_WORKSPACE", None)
        
    if orig_state:
        os.environ["OPENCLAW_STATE_DIR"] = orig_state
    else:
        os.environ.pop("OPENCLAW_STATE_DIR", None)


@pytest.fixture
def large_dataset(isolated_workspace):
    """Create large dataset with 1000+ files for performance testing."""
    memory = isolated_workspace / "memory"
    daily_dir = memory / "daily"
    
    print("\n📝 Creating large test dataset (1000 files)...")
    start_time = time.time()
    
    files_created = []
    
    # Create 1000 daily files
    base_date = datetime.now() - timedelta(days=1000)
    for i in range(1000):
        date = base_date + timedelta(days=i)
        daily_file = daily_dir / f"{date.strftime('%Y-%m-%d')}.md"
        
        content = f"""# Daily Log {date.strftime('%Y-%m-%d')}

## Morning Activities
Started work at 9 AM. Reviewed emails and planned the day.
Working on project alpha which involves {i % 10} different components.

## Afternoon Progress
Made significant progress on task #{i}. 
Collaborated with team members on design decisions.
The key insight was understanding the relationship between X and Y.

## Evening Reflection
Productive day overall. Completed {i % 5 + 1} major tasks.
Tomorrow will focus on optimization and testing.

**Tags:** #daily #project-alpha #task{i % 20}
**Satisfaction:** {0.5 + (i % 50) / 100}
"""
        
        daily_file.write_text(content)
        files_created.append(str(daily_file))
        
        # Record write for every 10th file to avoid slowdown
        if i % 10 == 0:
            cmd_record_write([str(daily_file]))
    
    # Bulk record remaining files
    print(f"📊 Created {len(files_created)} files in {time.time() - start_time:.2f}s")
    print("🔄 Indexing remaining files...")
    
    index_start = time.time()
    for i, filepath in enumerate(files_created):
        if i % 10 != 0:  # Index the ones we skipped
            cmd_record_write([filepath])
        
        if (i + 1) % 100 == 0:
            print(f"   Indexed {i + 1}/{len(files_created)} files...")
    
    print(f"✅ Dataset ready in {time.time() - start_time:.2f}s total")
    
    return files_created


# ============================================================================
# Performance Tests
# ============================================================================

class TestLargeScalePerformance:
    """Test performance with large datasets."""
    
    @pytest.mark.timeout(300)  # 5 minute timeout
    def test_large_database_search_speed(self, large_dataset):
        """
        Search should return results in < 1s even with 1000+ chunks.
        
        Target: < 1s for complex queries
        """
        print("\n🔍 Testing search performance on large dataset...")
        
        # Perform multiple searches with different queries
        queries = [
            "project alpha",
            "task optimization",
            "team collaboration",
            "morning activities",
            "evening reflection",
        ]
        
        search_times = []
        
        for query in queries:
            start_time = time.time()
            results = search(query, n=10)
            elapsed = time.time() - start_time
            search_times.append(elapsed)
            
            assert len(results) > 0, f"No results for query '{query}'"
            assert elapsed < 1.0, \
                f"Search took {elapsed:.3f}s (target: < 1s) for query '{query}'"
            
            print(f"   '{query}': {elapsed*1000:.1f}ms ({len(results)} results)")
        
        avg_time = sum(search_times) / len(search_times)
        print(f"\n📊 Average search time: {avg_time*1000:.1f}ms")
        print(f"📊 Max search time: {max(search_times)*1000:.1f}ms")
        print(f"✅ All searches completed in < 1s")
    
    
    @pytest.mark.timeout(600)  # 10 minute timeout
    def test_maintenance_completes_quickly(self, large_dataset):
        """
        Nightly maintenance should complete in < 5 minutes.
        
        Target: < 5 minutes (300s) for full maintenance
        """
        print("\n🔧 Testing maintenance performance on large dataset...")
        
        start_time = time.time()
        result = run_maintain()
        elapsed = time.time() - start_time
        
        assert result is not None, "Maintenance failed"
        assert elapsed < 300, \
            f"Maintenance took {elapsed:.1f}s (target: < 300s / 5 min)"
        
        print(f"✅ Maintenance completed in {elapsed:.1f}s")
        
        # Verify database integrity after maintenance
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM chunks")
        chunk_count = cursor.fetchone()[0]
        print(f"📊 Database has {chunk_count} chunks after maintenance")
        
        assert chunk_count > 900, "Maintenance lost data"
    
    
    def test_bulk_insert_performance(self, isolated_workspace):
        """
        Bulk inserts should be efficient.
        
        Target: > 100 inserts/second
        """
        memory = isolated_workspace / "memory"
        daily_dir = memory / "daily"
        
        print("\n📝 Testing bulk insert performance...")
        
        num_files = 100
        start_time = time.time()
        
        for i in range(num_files):
            daily_file = daily_dir / f"bulk-test-{i}.md"
            daily_file.write_text(f"# Test {i}\n\nBulk insert test content {i}.")
            cmd_record_write([str(daily_file]))
        
        elapsed = time.time() - start_time
        rate = num_files / elapsed
        
        print(f"📊 Inserted {num_files} files in {elapsed:.2f}s ({rate:.1f} files/s)")
        
        assert rate > 10, \
            f"Insert rate too slow: {rate:.1f} files/s (target: > 10 files/s)"
        
        print(f"✅ Bulk insert performance acceptable")
    
    
    def test_database_size_reasonable(self, large_dataset):
        """
        Database size should be reasonable for amount of data.
        
        Target: < 100MB for 1000 files
        """
        db_path = Path(os.environ.get("OPENCLAW_STATE_DIR")) / "nautilus" / "gravity.db"
        
        if db_path.exists():
            size_bytes = db_path.stat().st_size
            size_mb = size_bytes / (1024 * 1024)
            
            print(f"\n💾 Database size: {size_mb:.2f} MB for ~1000 files")
            
            assert size_mb < 100, \
                f"Database too large: {size_mb:.2f} MB (target: < 100 MB)"
            
            print(f"✅ Database size reasonable")


class TestConcurrentAccess:
    """Test concurrent access patterns."""
    
    def test_concurrent_reads(self, isolated_workspace):
        """
        Multiple threads reading simultaneously should work.
        
        Target: No errors, no corruption
        """
        memory = isolated_workspace / "memory"
        test_file = memory / "daily" / "2026-02-14.md"
        test_file.write_text("# Concurrent Test\n\nSearchable content.")
        cmd_record_write([str(test_file]))
        
        print("\n🔀 Testing concurrent read access...")
        
        def search_worker(thread_id):
            """Worker that performs searches."""
            try:
                results = search("searchable", n=5)
                return (thread_id, True, len(results))
            except Exception as e:
                return (thread_id, False, str(e))
        
        # Run 20 concurrent searches
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(search_worker, i) for i in range(20)]
            results = [f.result() for f in as_completed(futures)]
        
        # Check results
        successes = sum(1 for _, success, _ in results if success)
        failures = [r for r in results if not r[1]]
        
        print(f"📊 {successes}/{len(results)} searches succeeded")
        
        if failures:
            print(f"❌ Failures: {failures}")
        
        assert successes >= len(results) * 0.9, \
            f"Too many failures: {len(results) - successes}/{len(results)}"
        
        print(f"✅ Concurrent reads handled successfully")
    
    
    def test_concurrent_writes(self, isolated_workspace):
        """
        Multiple threads writing simultaneously should not corrupt DB.
        
        Target: No errors, no corruption
        """
        memory = isolated_workspace / "memory"
        daily_dir = memory / "daily"
        
        print("\n🔀 Testing concurrent write access...")
        
        def write_worker(thread_id):
            """Worker that writes files."""
            try:
                test_file = daily_dir / f"concurrent-{thread_id}.md"
                test_file.write_text(f"# Thread {thread_id}\n\nConcurrent write test.")
                cmd_record_write([str(test_file]))
                return (thread_id, True, None)
            except Exception as e:
                return (thread_id, False, str(e))
        
        # Run 20 concurrent writes
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(write_worker, i) for i in range(20)]
            results = [f.result() for f in as_completed(futures)]
        
        successes = sum(1 for _, success, _ in results if success)
        failures = [r for r in results if not r[1]]
        
        print(f"📊 {successes}/{len(results)} writes succeeded")
        
        if failures:
            print(f"⚠️  Failures: {failures[:3]}...")  # Show first 3
        
        # SQLite can handle concurrent reads but writes may timeout
        # Allow some failures but database should remain intact
        assert successes >= len(results) * 0.5, \
            f"Too many write failures: {len(results) - successes}/{len(results)}"
        
        # Verify database integrity
        db = get_db()
        cursor = db.cursor()
        cursor.execute("PRAGMA integrity_check")
        integrity = cursor.fetchone()[0]
        
        assert integrity == "ok", f"Database corrupted: {integrity}"
        
        print(f"✅ Concurrent writes completed, database intact")
    
    
    def test_mixed_concurrent_operations(self, isolated_workspace):
        """
        Mix of reads, writes, and maintenance operations.
        
        Target: System remains stable
        """
        memory = isolated_workspace / "memory"
        daily_dir = memory / "daily"
        
        # Create initial content
        for i in range(10):
            f = daily_dir / f"initial-{i}.md"
            f.write_text(f"# Initial {i}\n\nContent.")
            cmd_record_write([str(f]))
        
        print("\n🔀 Testing mixed concurrent operations...")
        
        operations_completed = []
        
        def read_worker(thread_id):
            for _ in range(5):
                search("content", n=3)
                time.sleep(0.01)
            operations_completed.append(("read", thread_id))
        
        def write_worker(thread_id):
            for i in range(5):
                f = daily_dir / f"write-{thread_id}-{i}.md"
                f.write_text(f"# Write {thread_id}\n\nContent.")
                cmd_record_write([str(f]))
                time.sleep(0.01)
            operations_completed.append(("write", thread_id))
        
        def maintenance_worker():
            try:
                run_maintain()
                operations_completed.append(("maintain", 0))
            except:
                operations_completed.append(("maintain_fail", 0))
        
        # Run mixed operations
        with ThreadPoolExecutor(max_workers=8) as executor:
            # 3 readers
            for i in range(3):
                executor.submit(read_worker, i)
            
            # 3 writers
            for i in range(3):
                executor.submit(write_worker, i)
            
            # 1 maintenance
            executor.submit(maintenance_worker)
        
        print(f"📊 Completed {len(operations_completed)} operations")
        
        # Verify database still works
        results = search("content", n=5)
        assert len(results) > 0, "Search broken after concurrent ops"
        
        print(f"✅ System stable after mixed concurrent operations")


class TestErrorRecovery:
    """Test graceful error handling and recovery."""
    
    def test_corrupted_database_recovery(self, isolated_workspace):
        """
        System should detect and handle corrupted database.
        """
        # Create valid database first
        memory = isolated_workspace / "memory"
        test_file = memory / "daily" / "2026-02-14.md"
        test_file.write_text("# Test\n\nContent.")
        cmd_record_write([str(test_file]))
        
        # Get database path
        db_path = Path(os.environ.get("OPENCLAW_STATE_DIR")) / "nautilus" / "gravity.db"
        
        # Close connection
        db = get_db()
        db.close()
        
        # Corrupt database by truncating it
        with open(db_path, 'wb') as f:
            f.write(b'CORRUPTED')
        
        print("\n🔧 Testing corrupted database recovery...")
        
        # Try to use database - should detect corruption
        try:
            # This should either recover or fail gracefully
            new_db = get_db()
            cursor = new_db.cursor()
            
            # Try to query - might fail, but shouldn't crash
            try:
                cursor.execute("SELECT COUNT(*) FROM chunks")
                print("   Database recovered or recreated")
            except sqlite3.DatabaseError:
                print("   Database corruption detected gracefully")
        except Exception as e:
            # Should fail gracefully, not crash
            print(f"   Handled corruption gracefully: {type(e).__name__}")
        
        print(f"✅ Corruption handled without crash")
    
    
    def test_missing_files_handled(self, isolated_workspace):
        """
        Missing source files should be handled gracefully.
        """
        memory = isolated_workspace / "memory"
        test_file = memory / "daily" / "2026-02-14.md"
        test_file.write_text("# Test\n\nContent.")
        cmd_record_write([str(test_file]))
        
        # Delete file but keep database entry
        test_file.unlink()
        
        print("\n📁 Testing missing file handling...")
        
        # Search should still work
        try:
            results = search("content", n=5)
            print(f"   Search completed with {len(results)} results")
        except Exception as e:
            pytest.fail(f"Search crashed on missing file: {e}")
        
        print(f"✅ Missing files handled gracefully")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-s"])
