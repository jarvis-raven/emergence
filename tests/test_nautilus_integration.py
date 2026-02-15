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


@pytest.fixture
def temp_workspace(tmp_path, monkeypatch):
    """Create a temporary workspace with test structure.

    Uses environment variables instead of direct patching to avoid
    import timing issues (functions already imported before patch).
    """
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

    # Create state directory for nautilus
    state_dir = tmp_path / "state" / "nautilus"
    state_dir.mkdir(parents=True)

    # Create config file with nautilus settings
    config_path = workspace / "emergence.json"
    config_data = {
        "nautilus": {
            "enabled": True,
            "memory_dir": "memory",
            "nightly_enabled": True,
            "nightly_hour": 2,
            "nightly_minute": 30,
        },
        "paths": {"workspace": str(workspace)},
    }
    config_path.write_text(json.dumps(config_data, indent=2))

    # Set environment variables to override config resolution
    # CRITICAL: Must happen BEFORE any nautilus imports!
    monkeypatch.setenv("OPENCLAW_WORKSPACE", str(workspace))
    monkeypatch.setenv("OPENCLAW_STATE_DIR", str(state_dir))

    # Initialize the gravity database with correct schema
    # Do this BEFORE clearing module cache to ensure schema exists
    import sqlite3

    db_file = state_dir / "gravity.db"
    db = sqlite3.connect(str(db_file))
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS gravity (
            path TEXT NOT NULL,
            line_start INTEGER DEFAULT 0,
            line_end INTEGER DEFAULT 0,
            access_count INTEGER DEFAULT 0,
            reference_count INTEGER DEFAULT 0,
            explicit_importance REAL DEFAULT 0.0,
            last_accessed_at TEXT,
            last_written_at TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            superseded_by TEXT DEFAULT NULL,
            tags TEXT DEFAULT '[]',
            context_tags TEXT DEFAULT '[]',
            chamber TEXT DEFAULT 'atrium',
            promoted_at TEXT,
            source_chunk TEXT,
            PRIMARY KEY (path, line_start, line_end)
        )
    """
    )
    db.execute(
        """
        CREATE TABLE IF NOT EXISTS access_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT NOT NULL,
            line_start INTEGER DEFAULT 0,
            line_end INTEGER DEFAULT 0,
            accessed_at TEXT NOT NULL,
            context TEXT DEFAULT '{}'
        )
    """
    )
    db.commit()
    db.close()

    # Now clear and reimport nautilus modules to pick up environment variables
    import sys

    nautilus_modules = [k for k in sys.modules.keys() if k.startswith("nautilus")]
    for mod_name in nautilus_modules:
        del sys.modules[mod_name]

    # Import fresh with correct environment
    from nautilus import config

    # Verify environment was picked up correctly
    assert config.get_workspace() == workspace
    assert config.get_state_dir() == state_dir
    assert config.get_gravity_db_path() == db_file

    yield workspace


class TestSessionHooks:
    """Test Issue #65: Session Hook - Auto-record memory accesses."""

    def test_record_access_read(self, temp_workspace):
        """Test recording a file read."""
        from nautilus.session_hooks import record_access
        from nautilus import gravity

        result = record_access("memory/test1.md", access_type="read", async_mode=False)
        assert result is True

        # Verify it was recorded in gravity DB
        db = gravity.get_db()
        row = db.execute("SELECT * FROM gravity WHERE path = ?", ("memory/test1.md",)).fetchone()
        assert row is not None
        assert row["access_count"] > 0
        assert row["last_accessed_at"] is not None
        db.close()

    def test_record_access_write(self, temp_workspace):
        """Test recording a file write."""
        from nautilus.session_hooks import record_access
        from nautilus import gravity

        result = record_access("memory/test2.md", access_type="write", async_mode=False)
        assert result is True

        # Verify it was recorded
        db = gravity.get_db()
        row = db.execute("SELECT * FROM gravity WHERE path = ?", ("memory/test2.md",)).fetchone()
        assert row is not None
        assert row["last_written_at"] is not None
        db.close()

    def test_batch_record_accesses(self, temp_workspace):
        """Test batch recording multiple files."""
        from nautilus.session_hooks import batch_record_accesses
        from nautilus import gravity

        files = ["memory/test1.md", "memory/test2.md"]
        count = batch_record_accesses(files, access_type="read")
        assert count == 2

        # Verify both were recorded
        db = gravity.get_db()
        for f in files:
            row = db.execute("SELECT * FROM gravity WHERE path = ?", (f,)).fetchone()
            assert row is not None
        db.close()

    def test_register_recent_writes(self, temp_workspace):
        """Test registering recently modified files."""
        from nautilus.session_hooks import register_recent_writes

        # Touch a file to make it recent
        test_file = temp_workspace / "memory" / "recent.md"
        test_file.write_text("# Recent file")

        result = register_recent_writes(hours=1)
        assert result.get("registered", 0) > 0
        assert result.get("recent_files", 0) > 0

    def test_skip_non_markdown(self, temp_workspace):
        """Test that non-markdown files are skipped."""
        from nautilus.session_hooks import record_access

        # Create a non-.md file
        txt_file = temp_workspace / "memory" / "test.txt"
        txt_file.write_text("Not markdown")

        result = record_access("memory/test.txt", async_mode=False)
        assert result is False

    def test_skip_nonexistent_file(self, temp_workspace):
        """Test that nonexistent files are skipped."""
        from nautilus.session_hooks import record_access

        result = record_access("memory/nonexistent.md", async_mode=False)
        assert result is False

    def test_on_file_read_hook(self, temp_workspace):
        """Test the on_file_read hook."""
        from nautilus.session_hooks import on_file_read

        with patch("nautilus.session_hooks.record_access") as mock_record:
            on_file_read("memory/test1.md", session_id="test-session")
            mock_record.assert_called_once_with(
                "memory/test1.md",
                access_type="read",
                session_context="test-session",
                async_mode=True,
            )

    def test_on_file_write_hook(self, temp_workspace):
        """Test the on_file_write hook."""
        from nautilus.session_hooks import on_file_write

        with patch("nautilus.session_hooks.record_access") as mock_record:
            on_file_write("memory/test2.md", session_id="test-session")
            mock_record.assert_called_once_with(
                "memory/test2.md",
                access_type="write",
                session_context="test-session",
                async_mode=True,
            )


class TestNightlyIntegration:
    """Test Issue #66: Nightly Build Integration."""

    def test_should_run_maintenance_enabled(self, temp_workspace):
        """Test maintenance check when enabled."""
        from nautilus.nightly import should_run_maintenance

        cfg = {
            "enabled": True,
            "nightly_enabled": True,
        }
        assert should_run_maintenance(cfg) is True

    def test_should_run_maintenance_disabled(self, temp_workspace):
        """Test maintenance check when disabled."""
        from nautilus.nightly import should_run_maintenance

        cfg = {
            "enabled": False,
        }
        assert should_run_maintenance(cfg) is False

    def test_run_nightly_maintenance_disabled(self, temp_workspace):
        """Test nightly maintenance when Nautilus is disabled."""
        from nautilus.nightly import run_nightly_maintenance

        with patch("nautilus.nightly.get_nautilus_config", return_value={"enabled": False}):
            result = run_nightly_maintenance(verbose=False)
            assert result["enabled"] is False
            assert len(result["errors"]) > 0
            assert any("disabled" in err.lower() for err in result["errors"])

    @patch("nautilus.nightly.subprocess.run")
    def test_run_nightly_maintenance_success(self, mock_run, temp_workspace):
        """Test successful nightly maintenance run."""
        from nautilus.nightly import run_nightly_maintenance

        # Mock subprocess calls to return success
        mock_run.return_value = MagicMock(
            returncode=0, stdout=json.dumps({"classified": {"atrium": 5, "corridor": 3}}), stderr=""
        )

        with patch("nautilus.config.get_nautilus_config", return_value={"enabled": True}):
            with patch(
                "nautilus.session_hooks.register_recent_writes", return_value={"registered": 10}
            ):
                result = run_nightly_maintenance(verbose=False)

                assert result["enabled"] is True
                assert len(result["errors"]) == 0
                assert "register_recent" in result["steps"]

    def test_nightly_state_persistence(self, temp_workspace):
        """Test that nightly state is saved and loaded correctly."""
        from drives.nightly_check import load_nightly_state, mark_nautilus_run

        cfg = {"paths": {"workspace": str(temp_workspace)}}

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
        from drives.nightly_check import should_run_nautilus_nightly

        cfg = {
            "nautilus": {
                "enabled": True,
                "nightly_enabled": True,
                "nightly_hour": 2,
                "nightly_minute": 30,
            },
            "paths": {"workspace": str(temp_workspace)},
        }

        # Simulate a recent run
        state = {"last_nautilus_run": datetime.now(timezone.utc).isoformat()}

        should_run, reason = should_run_nautilus_nightly(cfg, state)
        assert should_run is False
        assert "ago" in reason

    def test_should_run_nautilus_nightly_preferred_time(self, temp_workspace):
        """Test that nightly maintenance runs during preferred time window."""
        from drives.nightly_check import should_run_nautilus_nightly

        now = datetime.now(timezone.utc)

        cfg = {
            "nautilus": {
                "enabled": True,
                "nightly_enabled": True,
                "nightly_hour": now.hour,
                "nightly_minute": now.minute,
            },
            "paths": {"workspace": str(temp_workspace)},
        }

        # Simulate a run from yesterday
        yesterday = now - timedelta(days=1)
        state = {"last_nautilus_run": yesterday.isoformat()}

        should_run, reason = should_run_nautilus_nightly(cfg, state)
        assert should_run is True
        assert "preferred window" in reason

    def test_should_run_nautilus_nightly_outside_window(self, temp_workspace):
        """Test that nightly maintenance doesn't run outside preferred time."""
        from drives.nightly_check import should_run_nautilus_nightly

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
            "paths": {"workspace": str(temp_workspace)},
        }

        # Simulate a run from yesterday
        yesterday = now - timedelta(days=1)
        state = {"last_nautilus_run": yesterday.isoformat()}

        should_run, reason = should_run_nautilus_nightly(cfg, state)
        assert should_run is False
        assert "Outside preferred window" in reason


class TestDaemonIntegration:
    """Test daemon integration points."""

    def test_nautilus_import_available(self, temp_workspace):
        """Test that Nautilus can be imported in daemon context."""
        try:
            from nautilus.nightly import run_nightly_maintenance

            assert callable(run_nightly_maintenance)
        except ImportError:
            pytest.fail("Nautilus nightly module not importable")

    def test_daemon_nightly_check_import(self, temp_workspace):
        """Test that nightly check module can be imported in daemon context."""
        try:
            from drives.nightly_check import should_run_nautilus_nightly

            assert callable(should_run_nautilus_nightly)
        except ImportError:
            pytest.fail("Nightly check module not importable")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
