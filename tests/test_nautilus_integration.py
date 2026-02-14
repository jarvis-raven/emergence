"""
Tests for Nautilus v0.4.0 Beta integration (Issues #65, #66).

Tests:
- Session hooks: Auto-record memory accesses
- Nightly maintenance: Daemon integration
"""

import pytest
import sys
import os
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

# Add core to path
sys.path.insert(0, str(Path(__file__).parent.parent / "core"))

from nautilus import session_hooks, nightly, config
from nautilus.session_hooks import (
    record_access,
    batch_record_accesses,
    register_recent_writes,
    on_file_read,
    on_file_write,
)
from nautilus.nightly import (
    run_nightly_maintenance,
    should_run_maintenance,
)
from drives.nightly_check import (
    should_run_nautilus_nightly,
    load_nightly_state,
    save_nightly_state,
    mark_nautilus_run,
)


@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    """Create a temporary workspace with test structure."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    
    # Create memory directory
    memory = workspace / "memory"
    memory.mkdir()
    
    # Create some test files
    (memory / "test1.md").write_text("# Test 1\nSome content")
    (memory / "test2.md").write_text("# Test 2\nMore content")
    
    daily = memory / "daily"
    daily.mkdir()
    (daily / "2026-02-14.md").write_text("# Daily note")
    
    # Create .emergence state directory
    emergence = workspace / ".emergence"
    emergence.mkdir()
    state_dir = emergence / "state"
    state_dir.mkdir()
    
    # Create nautilus state dir
    nautilus_dir = state_dir / "nautilus"
    nautilus_dir.mkdir(parents=True)
    
    # Create config
    cfg = {
        "enabled": True,
        "gravity_db": str(nautilus_dir / "gravity.db"),
        "memory_dir": "memory",
        "nightly_enabled": True,
        "nightly_hour": 2,
        "nightly_minute": 30,
    }
    
    # Monkeypatch config functions
    monkeypatch.setattr('nautilus.config.get_workspace', lambda: workspace)
    monkeypatch.setattr('nautilus.config.get_config', lambda: cfg)
    monkeypatch.setattr('nautilus.config.get_db_path', lambda: nautilus_dir / "gravity.db")
    
    # Also patch in session_hooks module
    monkeypatch.setattr('nautilus.session_hooks.get_workspace', lambda: workspace)
    monkeypatch.setattr('nautilus.session_hooks.get_db_path', lambda: nautilus_dir / "gravity.db")
    
    # Initialize gravity DB
    from nautilus import gravity
    db = gravity.get_db()
    db.close()
    
    yield workspace


class TestSessionHooks:
    """Test Issue #65: Session Hook - Auto-record memory accesses."""
    
    def test_record_access_read(self, temp_workspace):
        """Test recording a file read."""
        result = record_access("memory/test1.md", access_type="read", async_mode=False)
        assert result is True
        
        # Verify it was recorded in gravity DB
        from nautilus import gravity
        db = gravity.get_db()
        row = db.execute("SELECT * FROM gravity WHERE path = ?", ("memory/test1.md",)).fetchone()
        assert row is not None
        assert row['access_count'] > 0
        assert row['last_accessed_at'] is not None
        db.close()
    
    def test_record_access_write(self, temp_workspace):
        """Test recording a file write."""
        result = record_access("memory/test2.md", access_type="write", async_mode=False)
        assert result is True
        
        # Verify it was recorded
        from nautilus import gravity
        db = gravity.get_db()
        row = db.execute("SELECT * FROM gravity WHERE path = ?", ("memory/test2.md",)).fetchone()
        assert row is not None
        assert row['last_written_at'] is not None
        db.close()
    
    def test_batch_record_accesses(self, temp_workspace):
        """Test batch recording multiple files."""
        files = ["memory/test1.md", "memory/test2.md"]
        count = batch_record_accesses(files, access_type="read")
        assert count == 2
        
        # Verify both were recorded
        from nautilus import gravity
        db = gravity.get_db()
        for f in files:
            row = db.execute("SELECT * FROM gravity WHERE path = ?", (f,)).fetchone()
            assert row is not None
        db.close()
    
    def test_register_recent_writes(self, temp_workspace):
        """Test registering recently modified files."""
        # Touch a file to make it recent
        test_file = temp_workspace / "memory" / "recent.md"
        test_file.write_text("# Recent file")
        
        result = register_recent_writes(hours=1)
        assert result.get("registered", 0) > 0
        assert result.get("recent_files", 0) > 0
    
    def test_skip_non_markdown(self, temp_workspace):
        """Test that non-markdown files are skipped."""
        # Create a non-.md file
        txt_file = temp_workspace / "memory" / "test.txt"
        txt_file.write_text("Not markdown")
        
        result = record_access("memory/test.txt", async_mode=False)
        assert result is False
    
    def test_skip_nonexistent_file(self, temp_workspace):
        """Test that nonexistent files are skipped."""
        result = record_access("memory/nonexistent.md", async_mode=False)
        assert result is False
    
    def test_on_file_read_hook(self, temp_workspace):
        """Test the on_file_read hook."""
        with patch('nautilus.session_hooks.record_access') as mock_record:
            on_file_read("memory/test1.md", session_id="test-session")
            mock_record.assert_called_once_with(
                "memory/test1.md",
                access_type="read",
                session_context="test-session",
                async_mode=True
            )
    
    def test_on_file_write_hook(self, temp_workspace):
        """Test the on_file_write hook."""
        with patch('nautilus.session_hooks.record_access') as mock_record:
            on_file_write("memory/test2.md", session_id="test-session")
            mock_record.assert_called_once_with(
                "memory/test2.md",
                access_type="write",
                session_context="test-session",
                async_mode=True
            )


class TestNightlyIntegration:
    """Test Issue #66: Nightly Build Integration."""
    
    def test_should_run_maintenance_enabled(self, temp_workspace):
        """Test maintenance check when enabled."""
        cfg = {
            "enabled": True,
            "nightly_enabled": True,
        }
        assert should_run_maintenance(cfg) is True
    
    def test_should_run_maintenance_disabled(self, temp_workspace):
        """Test maintenance check when disabled."""
        cfg = {
            "enabled": False,
        }
        assert should_run_maintenance(cfg) is False
    
    def test_run_nightly_maintenance_disabled(self, temp_workspace):
        """Test nightly maintenance when Nautilus is disabled."""
        with patch('nautilus.nightly.get_config', return_value={"enabled": False}):
            result = run_nightly_maintenance(verbose=False)
            assert result["enabled"] is False
            assert len(result["errors"]) > 0
            assert any("disabled" in err.lower() for err in result["errors"])
    
    @patch('nautilus.nightly.subprocess.run')
    def test_run_nightly_maintenance_success(self, mock_run, temp_workspace):
        """Test successful nightly maintenance run."""
        # Mock subprocess calls to return success
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps({"classified": {"atrium": 5, "corridor": 3}}),
            stderr=""
        )
        
        with patch('nautilus.config.get_config', return_value={"enabled": True}):
            with patch('nautilus.session_hooks.register_recent_writes', return_value={"registered": 10}):
                result = run_nightly_maintenance(verbose=False)
                
                assert result["enabled"] is True
                assert len(result["errors"]) == 0
                assert "register_recent" in result["steps"]
    
    def test_nightly_state_persistence(self, temp_workspace):
        """Test that nightly state is saved and loaded correctly."""
        cfg = {
            "paths": {
                "workspace": str(temp_workspace)
            }
        }
        
        # Load initial state (should be empty)
        state = load_nightly_state(cfg)
        assert state.get("last_nautilus_run") is None
        
        # Mark a run
        mark_nautilus_run(cfg, state)
        assert state.get("last_nautilus_run") is not None
        
        # Reload and verify persistence
        state2 = load_nightly_state(cfg)
        assert state2.get("last_nautilus_run") == state.get("last_nautilus_run")
    
    def test_should_run_nautilus_nightly_rate_limiting(self, temp_workspace):
        """Test that nightly maintenance doesn't run more than once per day."""
        cfg = {
            "nautilus": {
                "enabled": True,
                "nightly_enabled": True,
                "nightly_hour": 2,
                "nightly_minute": 30,
            },
            "paths": {
                "workspace": str(temp_workspace)
            }
        }
        
        # Simulate a recent run
        state = {
            "last_nautilus_run": datetime.now(timezone.utc).isoformat()
        }
        
        should_run, reason = should_run_nautilus_nightly(cfg, state)
        assert should_run is False
        assert "ago" in reason
    
    def test_should_run_nautilus_nightly_preferred_time(self, temp_workspace):
        """Test that nightly maintenance runs during preferred time window."""
        now = datetime.now(timezone.utc)
        
        cfg = {
            "nautilus": {
                "enabled": True,
                "nightly_enabled": True,
                "nightly_hour": now.hour,
                "nightly_minute": now.minute,
            },
            "paths": {
                "workspace": str(temp_workspace)
            }
        }
        
        # Simulate a run from yesterday
        yesterday = now - timedelta(days=1)
        state = {
            "last_nautilus_run": yesterday.isoformat()
        }
        
        should_run, reason = should_run_nautilus_nightly(cfg, state)
        assert should_run is True
        assert "preferred window" in reason
    
    def test_should_run_nautilus_nightly_outside_window(self, temp_workspace):
        """Test that nightly maintenance doesn't run outside preferred time."""
        now = datetime.now(timezone.utc)
        
        # Set preferred time to 6 hours from now
        preferred_time = now + timedelta(hours=6)
        
        cfg = {
            "nautilus": {
                "enabled": True,
                "nightly_enabled": True,
                "nightly_hour": preferred_time.hour,
                "nightly_minute": preferred_time.minute,
            },
            "paths": {
                "workspace": str(temp_workspace)
            }
        }
        
        # Simulate a run from yesterday
        yesterday = now - timedelta(days=1)
        state = {
            "last_nautilus_run": yesterday.isoformat()
        }
        
        should_run, reason = should_run_nautilus_nightly(cfg, state)
        assert should_run is False
        assert "Outside preferred window" in reason


class TestDaemonIntegration:
    """Test daemon integration points."""
    
    def test_nautilus_import_available(self):
        """Test that Nautilus can be imported in daemon context."""
        try:
            from nautilus.nightly import run_nightly_maintenance
            assert callable(run_nightly_maintenance)
        except ImportError:
            pytest.fail("Nautilus nightly module not importable")
    
    def test_daemon_nightly_check_import(self):
        """Test that nightly check module can be imported in daemon context."""
        try:
            from drives.nightly_check import should_run_nautilus_nightly
            assert callable(should_run_nautilus_nightly)
        except ImportError:
            pytest.fail("Nightly check module not importable")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
