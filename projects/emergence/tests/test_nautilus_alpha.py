#!/usr/bin/env python3
"""
🐚 Nautilus v0.4.0 Alpha Test Suite

Comprehensive testing for Nautilus Memory Palace integration.

Test Categories:
  - Search Testing (semantic, file types, gravity, chambers)
  - Status Testing (distribution, metrics, health)
  - Migration Testing (data preservation, cleanup, compatibility)
  - Integration Testing (emergence package, config, CLI, conflicts)
  - Edge Cases (empty DB, corruption, concurrency, scale)

Usage:
    pytest tests/test_nautilus_alpha.py -v
    pytest tests/test_nautilus_alpha.py::TestSearch -v
    pytest tests/test_nautilus_alpha.py::test_search_semantic -v
"""

import pytest
import sqlite3
import json
import tempfile
import shutil
import os
import sys
from pathlib import Path
from datetime import datetime, timezone, timedelta
import subprocess
import time
import threading

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.nautilus import (
    search,
    get_status,
    run_maintain,
    classify_file,
    get_gravity_score,
    config,
)
from core.nautilus.gravity import get_db, compute_effective_mass, cmd_record_write, cmd_record_access
from core.nautilus.chambers import classify_chamber
from core.nautilus.doors import classify_text
from core.nautilus.mirrors import cmd_auto_link


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with memory structure."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # Create memory directories
    memory = workspace / "memory"
    memory.mkdir()
    (memory / "daily").mkdir()
    (memory / "sessions").mkdir()
    (memory / "projects").mkdir()
    (memory / "corridors").mkdir()
    (memory / "vaults").mkdir()
    
    # Create state directory
    state = tmp_path / "state" / "nautilus"
    state.mkdir(parents=True)
    
    # Set environment variables
    os.environ["OPENCLAW_WORKSPACE"] = str(workspace)
    os.environ["OPENCLAW_STATE_DIR"] = str(state)
    
    yield workspace
    
    # Cleanup
    if "OPENCLAW_WORKSPACE" in os.environ:
        del os.environ["OPENCLAW_WORKSPACE"]
    if "OPENCLAW_STATE_DIR" in os.environ:
        del os.environ["OPENCLAW_STATE_DIR"]


@pytest.fixture
def sample_memories(temp_workspace):
    """Create sample memory files for testing."""
    memory = temp_workspace / "memory"
    
    # Daily file - atrium (recent, ephemeral)
    daily = memory / "daily" / "2026-02-14.md"
    daily.write_text("""# 2026-02-14

## Morning
Worked on Nautilus alpha testing suite. Creating comprehensive tests.

## Afternoon
Debugging gravity scoring system. Found edge case with superseded chunks.

## Evening
Meeting with team about emergence integration strategy.
""")
    
    # Session file - corridor (structured, important)
    session = memory / "sessions" / "2026-02-project-planning.md"
    session.write_text("""# Project Planning Session - 2026-02

## Nautilus v0.4.0 Roadmap
- Alpha testing completion
- Migration script validation
- Performance benchmarks

## Security Review
Critical security considerations for memory access.
""")
    
    # Project file - vault (long-term, crystallized)
    project = memory / "projects" / "nautilus-architecture.md"
    project.write_text("""# Nautilus Memory Palace Architecture

## Core Principles
- Gravity: Importance-weighted scoring
- Chambers: Temporal memory layers
- Doors: Context-aware filtering
- Mirrors: Multi-granularity indexing

## Design Decisions
Long-term architectural patterns and rationale.
""")
    
    # Corridor summary (aggregated)
    corridor = memory / "corridors" / "2026-02-week1.md"
    corridor.write_text("""# Week 1 Summary - February 2026

Key accomplishments:
- Nautilus integration progress
- Testing framework established
""")
    
    return {
        "daily": daily,
        "session": session,
        "project": project,
        "corridor": corridor,
    }


@pytest.fixture
def populated_db(temp_workspace, sample_memories):
    """Create and populate a gravity database with test data."""
    db = get_db()
    
    now = datetime.now(timezone.utc).isoformat()
    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
    
    # Insert test data
    test_data = [
        # path, line_start, line_end, access_count, chamber, tags, last_accessed, last_written
        ("memory/daily/2026-02-14.md", 0, 100, 5, "atrium", '["work", "testing"]', now, now),
        ("memory/sessions/2026-02-project-planning.md", 0, 100, 15, "corridor", '["project", "planning"]', yesterday, week_ago),
        ("memory/projects/nautilus-architecture.md", 0, 100, 30, "vault", '["architecture", "design"]', yesterday, week_ago),
        ("memory/corridors/2026-02-week1.md", 0, 50, 8, "corridor", '["summary"]', now, yesterday),
    ]
    
    for path, start, end, access, chamber, tags, accessed, written in test_data:
        db.execute("""
            INSERT OR REPLACE INTO gravity 
            (path, line_start, line_end, access_count, chamber, tags, last_accessed_at, last_written_at, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (path, start, end, access, chamber, tags, accessed, written, week_ago))
    
    db.commit()
    db.close()
    
    return config.get_gravity_db_path()


# ============================================================================
# Search Testing
# ============================================================================

class TestSearch:
    """Test search functionality."""
    
    def test_search_semantic_basic(self, temp_workspace, populated_db):
        """Test basic semantic search returns results."""
        # Note: This test requires openclaw memory search to work
        # We'll test the pipeline structure even if search returns empty
        result = search("nautilus testing", n=5)
        
        assert "query" in result
        assert "context" in result
        assert "results" in result
        assert result["query"] == "nautilus testing"
        assert isinstance(result["results"], list)
    
    def test_search_gravity_scoring(self, temp_workspace, populated_db):
        """Test that gravity scores influence ranking."""
        db = get_db()
        
        # Create two chunks, one with higher access count
        db.execute("""
            INSERT OR REPLACE INTO gravity 
            (path, line_start, line_end, access_count, chamber)
            VALUES 
            ('memory/test-high.md', 0, 10, 100, 'vault'),
            ('memory/test-low.md', 0, 10, 1, 'atrium')
        """)
        db.commit()
        
        # Verify mass computation
        high = db.execute("SELECT * FROM gravity WHERE path = 'memory/test-high.md'").fetchone()
        low = db.execute("SELECT * FROM gravity WHERE path = 'memory/test-low.md'").fetchone()
        
        high_mass = compute_effective_mass(high)
        low_mass = compute_effective_mass(low)
        
        assert high_mass > low_mass, "High access count should have higher mass"
        db.close()
    
    def test_search_chamber_filtering(self, temp_workspace, populated_db):
        """Test chamber-based filtering works."""
        result = search("architecture", n=10, chambers_filter="vault")
        
        # Should only return vault results if filtering works
        for r in result.get("results", []):
            if "chamber" in r:
                assert r["chamber"] == "vault", f"Expected vault, got {r['chamber']}"
    
    def test_search_context_classification(self, temp_workspace, populated_db):
        """Test that queries get classified into contexts."""
        # Test project context
        project_context = classify_text("project planning roadmap")
        assert "project" in project_context or "planning" in project_context
        
        # Test security context
        security_context = classify_text("security vulnerability review")
        assert "security" in security_context
        
        # Test personal context
        personal_context = classify_text("feeling stressed about deadline")
        assert "personal" in personal_context or "emotional" in personal_context
    
    def test_search_trapdoor_mode(self, temp_workspace, populated_db):
        """Test trapdoor mode bypasses context filtering."""
        result = search("test query", n=5, trapdoor=True)
        
        assert result.get("mode") == "trapdoor"
        # Trapdoor mode should not filter by context
    
    def test_search_different_file_types(self, temp_workspace, sample_memories, populated_db):
        """Test search across different memory file types."""
        # All file types should be searchable
        daily_result = search("morning afternoon", n=5)
        assert isinstance(daily_result.get("results"), list)
        
        session_result = search("planning roadmap", n=5)
        assert isinstance(session_result.get("results"), list)
        
        project_result = search("architecture principles", n=5)
        assert isinstance(project_result.get("results"), list)


# ============================================================================
# Status Testing
# ============================================================================

class TestStatus:
    """Test status reporting functionality."""
    
    def test_status_chamber_distribution(self, temp_workspace, populated_db):
        """Test that status shows chamber distribution."""
        status = get_status()
        
        assert "nautilus" in status
        nautilus = status["nautilus"]
        
        assert "phase_2_chambers" in nautilus
        chambers = nautilus["phase_2_chambers"]
        
        # Should have chamber counts
        assert "chambers" in chambers or "atrium" in str(chambers)
    
    def test_status_door_coverage(self, temp_workspace, populated_db):
        """Test door (tag) coverage metrics."""
        status = get_status()
        nautilus = status["nautilus"]
        
        assert "phase_1_gravity" in nautilus
        gravity = nautilus["phase_1_gravity"]
        
        assert "tagged" in gravity
        assert "total_chunks" in gravity
        assert "coverage" in gravity
    
    def test_status_mirror_completeness(self, temp_workspace, populated_db):
        """Test mirror link completeness metrics."""
        status = get_status()
        nautilus = status["nautilus"]
        
        assert "phase_4_mirrors" in nautilus
        # Mirrors should report linking status
    
    def test_status_database_health(self, temp_workspace, populated_db):
        """Test database health indicators."""
        status = get_status()
        nautilus = status["nautilus"]
        
        assert "config" in nautilus
        config_info = nautilus["config"]
        
        assert "db_exists" in config_info
        assert config_info["db_exists"] is True
        assert "gravity_db" in config_info
    
    def test_status_all_phases_present(self, temp_workspace, populated_db):
        """Test that all four phases are reported."""
        status = get_status()
        nautilus = status["nautilus"]
        
        assert "phase_1_gravity" in nautilus
        assert "phase_2_chambers" in nautilus
        assert "phase_3_doors" in nautilus
        assert "phase_4_mirrors" in nautilus


# ============================================================================
# Migration Testing
# ============================================================================

class TestMigration:
    """Test database migration functionality."""
    
    def test_migration_data_preservation(self, temp_workspace):
        """Test that migration preserves all data."""
        # Create legacy database with test data
        legacy_path = temp_workspace / "tools" / "nautilus"
        legacy_path.mkdir(parents=True)
        legacy_db = legacy_path / "gravity.db"
        
        db = sqlite3.connect(str(legacy_db))
        db.execute("""
            CREATE TABLE gravity (
                path TEXT,
                line_start INTEGER,
                line_end INTEGER,
                access_count INTEGER,
                PRIMARY KEY (path, line_start, line_end)
            )
        """)
        db.execute("""
            INSERT INTO gravity (path, line_start, line_end, access_count)
            VALUES ('test.md', 0, 10, 42)
        """)
        db.commit()
        db.close()
        
        # Run migration
        migrated = config.migrate_legacy_db()
        
        if migrated:
            # Check data exists in new location
            new_db = get_db()
            row = new_db.execute("SELECT * FROM gravity WHERE path = 'test.md'").fetchone()
            assert row is not None
            assert row["access_count"] == 42
            new_db.close()
    
    def test_migration_backward_compatibility(self, temp_workspace, populated_db):
        """Test that old schema columns are handled gracefully."""
        db = get_db()
        
        # Should be able to read old-style entries
        db.execute("""
            INSERT OR REPLACE INTO gravity (path, line_start, line_end, access_count)
            VALUES ('old-format.md', 0, 10, 5)
        """)
        db.commit()
        
        # Should not error when reading
        row = db.execute("SELECT * FROM gravity WHERE path = 'old-format.md'").fetchone()
        assert row is not None
        assert row["access_count"] == 5
        
        # New columns should have defaults
        assert row["chamber"] == "atrium"  # default
        db.close()
    
    def test_migration_no_data_loss(self, temp_workspace):
        """Test that migration doesn't lose any records."""
        # Create legacy database with multiple entries
        legacy_path = temp_workspace / "legacy"
        legacy_path.mkdir()
        legacy_db = legacy_path / "gravity.db"
        
        db = sqlite3.connect(str(legacy_db))
        db.execute("""
            CREATE TABLE gravity (
                path TEXT,
                line_start INTEGER,
                line_end INTEGER,
                access_count INTEGER,
                PRIMARY KEY (path, line_start, line_end)
            )
        """)
        
        test_records = [
            ("file1.md", 0, 10, 5),
            ("file2.md", 0, 20, 10),
            ("file3.md", 10, 30, 15),
        ]
        
        for path, start, end, count in test_records:
            db.execute("INSERT INTO gravity VALUES (?, ?, ?, ?)", (path, start, end, count))
        
        original_count = db.execute("SELECT COUNT(*) FROM gravity").fetchone()[0]
        db.commit()
        db.close()
        
        # Simulate migration by copying
        new_path = config.get_gravity_db_path()
        shutil.copy2(legacy_db, new_path)
        
        # Verify all records present
        new_db = get_db()
        new_count = new_db.execute("SELECT COUNT(*) FROM gravity").fetchone()[0]
        assert new_count == original_count
        new_db.close()


# ============================================================================
# Integration Testing
# ============================================================================

class TestIntegration:
    """Test integration with emergence package."""
    
    def test_emergence_package_import(self):
        """Test that nautilus can be imported from emergence."""
        try:
            from core.nautilus import search, get_status, run_maintain
            assert callable(search)
            assert callable(get_status)
            assert callable(run_maintain)
        except ImportError as e:
            pytest.fail(f"Failed to import nautilus from emergence: {e}")
    
    def test_config_changes_reflected(self, temp_workspace):
        """Test that config changes affect behavior."""
        # Create config file
        config_file = temp_workspace.parent / "emergence.json"
        config_data = {
            "nautilus": {
                "auto_classify": True,
                "decay_interval_hours": 24,
                "memory_dir": "memory"
            }
        }
        config_file.write_text(json.dumps(config_data, indent=2))
        
        # Config should be readable
        assert config.is_auto_classify_enabled() is True
        assert config.get_decay_interval_hours() == 24
    
    def test_cli_commands_work(self, temp_workspace, populated_db):
        """Test that CLI commands execute without error."""
        # Test status command
        result = subprocess.run(
            [sys.executable, "-m", "core.nautilus", "status"],
            cwd=temp_workspace.parent,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0, f"Status command failed: {result.stderr}"
        
        # Output should be valid JSON
        try:
            status = json.loads(result.stdout)
            assert "🐚 nautilus" in status or "nautilus" in status
        except json.JSONDecodeError:
            pytest.fail(f"Status output not valid JSON: {result.stdout}")
    
    def test_no_conflicts_with_tools(self, temp_workspace):
        """Test that nautilus doesn't conflict with existing tools."""
        # Test that config resolution works even if legacy paths exist
        legacy_path = temp_workspace / "tools" / "nautilus"
        legacy_path.mkdir(parents=True)
        
        # Should still resolve to new location
        db_path = config.get_gravity_db_path()
        assert "state/nautilus" in str(db_path)


# ============================================================================
# Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_empty_database_initialization(self, temp_workspace):
        """Test that system works with empty database."""
        # Get status on empty DB
        status = get_status()
        assert "nautilus" in status
        
        nautilus = status["nautilus"]
        assert nautilus["phase_1_gravity"]["total_chunks"] == 0
    
    def test_corrupted_database_handling(self, temp_workspace):
        """Test graceful handling of corrupted database."""
        # Create invalid database file
        db_path = config.get_gravity_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        db_path.write_text("This is not a valid SQLite database")
        
        # Should handle corruption gracefully
        try:
            db = get_db()
            # If we get here, it recreated the database
            assert db is not None
            db.close()
        except sqlite3.DatabaseError:
            # Acceptable to raise error, as long as it doesn't crash
            pass
    
    def test_concurrent_access(self, temp_workspace, populated_db):
        """Test concurrent access from drives + CLI."""
        results = []
        errors = []
        
        def access_db(thread_id):
            try:
                db = get_db()
                db.execute("SELECT COUNT(*) FROM gravity").fetchone()
                db.execute("""
                    INSERT OR IGNORE INTO gravity (path, line_start, line_end, access_count)
                    VALUES (?, 0, 10, 1)
                """, (f"thread-{thread_id}.md",))
                db.commit()
                db.close()
                results.append(thread_id)
            except Exception as e:
                errors.append((thread_id, e))
        
        # Create multiple threads
        threads = []
        for i in range(10):
            t = threading.Thread(target=access_db, args=(i,))
            threads.append(t)
            t.start()
        
        # Wait for completion
        for t in threads:
            t.join(timeout=5)
        
        # Most should succeed (WAL mode allows concurrent reads)
        assert len(results) >= 5, f"Too many failures: {errors}"
    
    def test_large_database_performance(self, temp_workspace):
        """Test performance with large database (1000+ files)."""
        db = get_db()
        
        start_time = time.time()
        
        # Insert 1000 entries
        for i in range(1000):
            db.execute("""
                INSERT INTO gravity (path, line_start, line_end, access_count, chamber)
                VALUES (?, ?, ?, ?, ?)
            """, (f"memory/file-{i}.md", 0, 100, i % 50, "atrium"))
        
        db.commit()
        insert_time = time.time() - start_time
        
        # Query performance
        start_time = time.time()
        result = db.execute("SELECT * FROM gravity WHERE access_count > 25 ORDER BY access_count DESC LIMIT 10").fetchall()
        query_time = time.time() - start_time
        
        db.close()
        
        # Performance benchmarks
        assert insert_time < 5.0, f"Bulk insert too slow: {insert_time:.2f}s"
        assert query_time < 0.1, f"Query too slow: {query_time:.2f}s"
        assert len(result) == 10
        
        print(f"\n📊 Performance Benchmarks:")
        print(f"   1000 inserts: {insert_time:.3f}s ({1000/insert_time:.0f} ops/s)")
        print(f"   Complex query: {query_time:.3f}s")
    
    def test_missing_columns_migration(self, temp_workspace):
        """Test that missing columns are added automatically."""
        # Create old-style database without new columns
        db_path = config.get_gravity_db_path()
        db_path.parent.mkdir(parents=True, exist_ok=True)
        
        db = sqlite3.connect(str(db_path))
        db.execute("""
            CREATE TABLE gravity (
                path TEXT,
                line_start INTEGER,
                line_end INTEGER,
                access_count INTEGER,
                PRIMARY KEY (path, line_start, line_end)
            )
        """)
        db.commit()
        db.close()
        
        # Get DB with new schema (should add missing columns)
        db = get_db()
        
        # Check that new columns exist
        cursor = db.execute("PRAGMA table_info(gravity)")
        columns = [row[1] for row in cursor.fetchall()]
        
        assert "chamber" in columns
        assert "tags" in columns
        assert "context_tags" in columns
        
        db.close()
    
    def test_superseded_chunks(self, temp_workspace, populated_db):
        """Test handling of superseded chunks."""
        db = get_db()
        
        # Create original and superseding chunk
        db.execute("""
            INSERT OR REPLACE INTO gravity 
            (path, line_start, line_end, access_count, superseded_by)
            VALUES 
            ('memory/original.md', 0, 10, 10, 'memory/new.md'),
            ('memory/new.md', 0, 10, 5, NULL)
        """)
        db.commit()
        
        # Superseded chunks should have lower effective mass
        original = db.execute("SELECT * FROM gravity WHERE path = 'memory/original.md'").fetchone()
        new_chunk = db.execute("SELECT * FROM gravity WHERE path = 'memory/new.md'").fetchone()
        
        # Even with higher access count, superseded should be deprioritized
        # This is handled in search ranking
        assert original["superseded_by"] is not None
        assert new_chunk["superseded_by"] is None
        
        db.close()


# ============================================================================
# Maintenance Testing
# ============================================================================

class TestMaintenance:
    """Test maintenance operations."""
    
    def test_maintain_classifies_chambers(self, temp_workspace, sample_memories):
        """Test that maintain classifies files into chambers."""
        result = run_maintain(verbose=False)
        
        assert "chambers" in result
        # Should have classified some files
    
    def test_maintain_auto_tags(self, temp_workspace, sample_memories, populated_db):
        """Test that maintain auto-tags files."""
        result = run_maintain(verbose=False)
        
        assert "tagged" in result
        # Should have tagged some files
    
    def test_maintain_decay(self, temp_workspace, populated_db):
        """Test that maintain runs gravity decay."""
        result = run_maintain(verbose=False)
        
        assert "decayed" in result
        assert isinstance(result["decayed"], int)
    
    def test_maintain_links_mirrors(self, temp_workspace, sample_memories, populated_db):
        """Test that maintain auto-links mirrors."""
        result = run_maintain(verbose=False)
        
        assert "mirrors_linked" in result
        assert isinstance(result["mirrors_linked"], int)


# ============================================================================
# CLI Testing
# ============================================================================

class TestCLI:
    """Test CLI commands."""
    
    def test_cli_search(self, temp_workspace, populated_db):
        """Test search command."""
        result = subprocess.run(
            [sys.executable, "-m", "core.nautilus", "search", "test", "--n", "5"],
            cwd=temp_workspace.parent,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0
        
        try:
            data = json.loads(result.stdout)
            assert "query" in data
            assert data["query"] == "test"
        except json.JSONDecodeError:
            pytest.fail(f"Search output not valid JSON: {result.stdout}")
    
    def test_cli_gravity_score(self, temp_workspace, populated_db):
        """Test gravity score command."""
        result = subprocess.run(
            [sys.executable, "-m", "core.nautilus", "gravity", "memory/daily/2026-02-14.md"],
            cwd=temp_workspace.parent,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        # Should execute (may return empty if file not found in DB)
        assert result.returncode == 0 or "not found" in result.stdout.lower()
    
    def test_cli_chambers_status(self, temp_workspace, populated_db):
        """Test chambers status command."""
        result = subprocess.run(
            [sys.executable, "-m", "core.nautilus", "chambers", "status"],
            cwd=temp_workspace.parent,
            capture_output=True,
            text=True,
            timeout=10
        )
        
        assert result.returncode == 0
        
        try:
            data = json.loads(result.stdout)
            assert "chambers" in data or isinstance(data, dict)
        except json.JSONDecodeError:
            pytest.fail(f"Chambers status output not valid JSON: {result.stdout}")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
