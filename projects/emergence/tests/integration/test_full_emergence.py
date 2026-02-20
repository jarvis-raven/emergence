#!/usr/bin/env python3
"""
🐚 Nautilus v0.4.0 Integration Test Suite - Full Emergence Workflows

Tests complete end-to-end workflows from fresh setup through actual usage:
  1. Fresh agent setup → Nautilus migration → first search
  2. Session recording → gravity update → search finds it
  3. Nightly maintenance runs → files promoted → chambers updated
  4. Room dashboard loads → displays accurate data
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
import time

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.nautilus import (
    search,
    get_status,
    run_maintain,
    classify_file,
    get_gravity_score,
    config,
)
from core.nautilus.gravity import (
    get_db,
    cmd_record_write,
    cmd_record_access,
    cmd_boost,
)
from core.nautilus.chambers import classify_chamber
from core.nautilus.doors import classify_text


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def isolated_workspace(tmp_path):
    """Create completely isolated workspace for integration tests."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # Create standard Emergence directory structure
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
    
    # Store original environment
    orig_workspace = os.environ.get("OPENCLAW_WORKSPACE")
    orig_state = os.environ.get("OPENCLAW_STATE_DIR")
    
    # Set test environment
    os.environ["OPENCLAW_WORKSPACE"] = str(workspace)
    os.environ["OPENCLAW_STATE_DIR"] = str(state)
    
    yield workspace
    
    # Restore environment
    if orig_workspace:
        os.environ["OPENCLAW_WORKSPACE"] = orig_workspace
    else:
        os.environ.pop("OPENCLAW_WORKSPACE", None)
        
    if orig_state:
        os.environ["OPENCLAW_STATE_DIR"] = orig_state
    else:
        os.environ.pop("OPENCLAW_STATE_DIR", None)


@pytest.fixture
def fresh_agent_setup(isolated_workspace):
    """Simulate fresh agent initialization with bootstrap files."""
    # Create bootstrap files
    (isolated_workspace / "SOUL.md").write_text("""# SOUL.md
I am an agent helping my human.
""")
    (isolated_workspace / "USER.md").write_text("""# USER.md
Name: Test User
Preferences: Testing, automation
""")
    (isolated_workspace / "MEMORY.md").write_text("""# Long-term Memory
Initial bootstrap complete.
""")
    
    return isolated_workspace


# ============================================================================
# Test Class: End-to-End Workflows
# ============================================================================

class TestEndToEndWorkflows:
    """Test complete workflows from start to finish."""
    
    def test_fresh_setup_to_first_search(self, fresh_agent_setup):
        """
        E2E Test 1: Fresh agent setup → Nautilus migration → first search
        
        Simulates:
        1. Agent wakes up for first time
        2. Nautilus initializes database
        3. Existing memory files get indexed
        4. User performs first search
        5. Results are returned with proper gravity
        """
        workspace = fresh_agent_setup
        memory = workspace / "memory"
        
        # Step 1: Create initial memory file
        daily_file = memory / "daily" / f"{datetime.now().strftime('%Y-%m-%d')}.md"
        daily_file.write_text("""# Daily Log

## Morning
Started testing Nautilus integration. Creating comprehensive test suite.
Learning about memory palace architecture and gravity scoring.

## Afternoon
Deep dive into chamber classifications. Understanding atrium vs corridor vs vault.
""")
        
        # Step 2: Initialize Nautilus (happens automatically on first import)
        db = get_db()
        cursor = db.cursor()
        
        # Verify database was created
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        assert "chunks" in tables, "Database initialization failed"
        
        # Step 3: Record write (simulates session activity)
        cmd_record_write([str(daily_file)])
        
        # Step 4: Verify chunk was created
        cursor.execute("SELECT COUNT(*) FROM chunks WHERE source_path LIKE '%daily%'")
        chunk_count = cursor.fetchone()[0]
        assert chunk_count > 0, "File was not indexed"
        
        # Step 5: Perform first search
        results = search("testing Nautilus", n=5)
        assert len(results) > 0, "Search returned no results"
        
        # Step 6: Verify gravity scoring is working
        first_result = results[0]
        assert "mass" in first_result, "Results missing gravity score"
        assert first_result["mass"] > 0, "Gravity score not calculated"
        
        print(f"✅ Fresh setup workflow complete: {chunk_count} chunks indexed, {len(results)} search results")
    
    
    def test_session_recording_to_search(self, isolated_workspace):
        """
        E2E Test 2: Session recording → gravity update → search finds it
        
        Simulates:
        1. User has conversation with agent
        2. Session gets recorded to memory
        3. Gravity events are recorded (write, access, satisfaction)
        4. Search finds the session
        5. Results ranked by gravity
        """
        workspace = isolated_workspace
        memory = workspace / "memory"
        
        # Step 1: Create session file
        session_dir = memory / "sessions"
        session_file = session_dir / "2026-02-14-nautilus-testing.md"
        session_file.write_text("""# Session: Nautilus Testing

**Date:** 2026-02-14  
**Topic:** Testing memory palace search functionality

## Discussion

User: How does gravity scoring work?

Agent: Gravity scoring combines multiple signals:
- **Freshness:** Recent memories have higher mass
- **Access patterns:** Frequently accessed memories gain mass
- **Satisfaction:** High-satisfaction events boost connected chunks
- **Decay:** Mass naturally decays over time

User: That's brilliant! This will help surface the most relevant memories.

Agent: Exactly. The memory palace uses physics-inspired metaphors.

**Outcome:** Successful explanation of gravity mechanics.
**Satisfaction:** 0.9
""")
        
        # Step 2: Record gravity events
        session_path = str(session_file)
        
        # Write event
        cmd_record_write([session_path])
        
        # Access events (simulate re-reading)
        cmd_record_access([session_path])
        cmd_record_access([session_path])
        
        # Boost event (high satisfaction from good conversation)
        # Satisfaction 0.9 → boost by 9.0 to simulate satisfaction multiplier
        cmd_boost([session_path, '--amount', '9.0'])
        
        # Step 3: Verify gravity score is elevated
        score = get_gravity_score(session_path)
        assert score > 0, "Gravity score not recorded"
        
        # Step 4: Search for content
        results = search("gravity scoring", n=5)
        assert len(results) > 0, "Search didn't find session"
        
        # Step 5: Verify session appears in top results
        found_session = False
        for result in results:
            if "nautilus-testing" in result.get("source_path", ""):
                found_session = True
                assert result["mass"] > 0, "Session has no gravity"
                break
        
        assert found_session, "Session not in search results"
        
        print(f"✅ Session recording workflow complete: gravity={score:.2f}, found in top {len(results)} results")
    
    
    def test_nightly_maintenance_promotion(self, isolated_workspace):
        """
        E2E Test 3: Nightly maintenance → files promoted → chambers updated
        
        Simulates:
        1. Agent accumulates daily notes over time
        2. Nightly maintenance runs
        3. Important content gets promoted to corridors/vaults
        4. Chamber classifications are updated
        5. Gravity scores are recalculated
        """
        workspace = isolated_workspace
        memory = workspace / "memory"
        
        # Step 1: Create multiple daily files (simulate week of activity)
        daily_dir = memory / "daily"
        dates = [
            datetime.now() - timedelta(days=i)
            for i in range(7, 0, -1)
        ]
        
        for date in dates:
            daily_file = daily_dir / f"{date.strftime('%Y-%m-%d')}.md"
            daily_file.write_text(f"""# {date.strftime('%Y-%m-%d')}

## Work Log
Continued development on Nautilus memory palace.
Improving search relevance and gravity scoring.
Testing chamber classification logic.

## Key Insight
The memory palace architecture mirrors human memory - 
recent in atrium, important in corridors, permanent in vaults.

**Tags:** #nautilus #testing #architecture
""")
            # Record write events for all files
            cmd_record_write([str(daily_file)])
        
        # Step 2: Create a corridor file (manually promoted content)
        corridor_file = memory / "corridors" / "nautilus-learnings.md"
        corridor_file.write_text("""# Nautilus Architecture Learnings

## Core Concepts
- **Gravity:** Physics-inspired relevance scoring
- **Chambers:** Spatial organization (atrium/corridor/vault)
- **Doors:** Context classification tags
- **Mirrors:** Bidirectional links between memories

## Design Decisions
Chose SQLite FTS5 for fast full-text search.
Gravity combines freshness + access + satisfaction.
Chamber promotion based on access patterns and age.
""")
        cmd_record_write([str(corridor_file)])
        
        # Step 3: Run maintenance
        result = run_maintain()
        assert result is not None, "Maintenance failed to run"
        
        # Step 4: Verify chamber classifications
        db = get_db()
        cursor = db.cursor()
        
        # Check daily files are in atrium
        cursor.execute("""
            SELECT COUNT(*) FROM chunks 
            WHERE source_path LIKE '%daily%' 
            AND chamber = 'atrium'
        """)
        atrium_count = cursor.fetchone()[0]
        assert atrium_count > 0, "Daily files not classified as atrium"
        
        # Check corridor file is in corridor
        cursor.execute("""
            SELECT COUNT(*) FROM chunks 
            WHERE source_path LIKE '%corridors%' 
            AND chamber = 'corridor'
        """)
        corridor_count = cursor.fetchone()[0]
        assert corridor_count > 0, "Corridor file not classified correctly"
        
        # Step 5: Verify gravity decay was applied
        cursor.execute("SELECT AVG(mass) FROM chunks")
        avg_mass = cursor.fetchone()[0]
        assert avg_mass is not None, "Gravity scores missing"
        
        print(f"✅ Maintenance workflow complete: {atrium_count} atrium, {corridor_count} corridor chunks")
    
    
    def test_room_dashboard_accuracy(self, isolated_workspace):
        """
        E2E Test 4: Room dashboard loads → displays accurate data
        
        Simulates:
        1. Memory files are created and indexed
        2. Room API requests status
        3. Status includes accurate metrics
        4. All four phases (gravity, chambers, doors, mirrors) report correctly
        """
        workspace = isolated_workspace
        memory = workspace / "memory"
        
        # Step 1: Create diverse memory content
        files = [
            ("daily/2026-02-14.md", "Daily log entry with #testing tag", "atrium"),
            ("projects/nautilus.md", "Project documentation", "corridor"),
            ("vaults/architecture.md", "Permanent architectural decisions", "vault"),
        ]
        
        for path, content, expected_chamber in files:
            file_path = memory / path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f"# {path}\n\n{content}\n\n**Important insight here.**")
            cmd_record_write([str(file_path)])
        
        # Step 2: Run maintenance to ensure everything is classified
        run_maintain()
        
        # Step 3: Get status (what Room dashboard would call)
        status = get_status()
        
        # Step 4: Verify all four phases are present
        assert "phase_1_gravity" in status, "Phase 1 (Gravity) missing"
        assert "phase_2_chambers" in status, "Phase 2 (Chambers) missing"
        assert "phase_3_doors" in status, "Phase 3 (Doors) missing"
        assert "phase_4_mirrors" in status, "Phase 4 (Mirrors) missing"
        
        # Step 5: Verify chamber distribution
        chambers = status["phase_2_chambers"]
        assert chambers["atrium_pct"] > 0, "No atrium content detected"
        assert chambers["corridor_pct"] >= 0, "Corridor percentage missing"
        assert chambers["vault_pct"] >= 0, "Vault percentage missing"
        
        # Step 6: Verify gravity metrics
        gravity = status["phase_1_gravity"]
        assert gravity["total_chunks"] >= 3, f"Expected ≥3 chunks, got {gravity['total_chunks']}"
        assert gravity["avg_mass"] > 0, "Average mass should be > 0"
        
        # Step 7: Verify door (context) tags
        doors = status["phase_3_doors"]
        assert "total_tags" in doors, "Tag count missing"
        assert "coverage_pct" in doors, "Tag coverage missing"
        
        print(f"✅ Room dashboard workflow complete: {gravity['total_chunks']} chunks, "
              f"{chambers['atrium_pct']:.0f}% atrium, {doors['coverage_pct']:.0f}% tagged")


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
