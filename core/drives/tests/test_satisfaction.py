"""Tests for the file-based drive satisfaction system."""

import json
import os
import time
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from core.drives.satisfaction import (
    get_ingest_dir,
    write_breadcrumb,
    assess_depth,
    check_completed_sessions,
    _is_session_complete,
    _check_file_writes,
)


@pytest.fixture
def temp_ingest_dir(tmp_path):
    """Provide a temporary sessions_ingest directory."""
    ingest_dir = tmp_path / "sessions_ingest"
    ingest_dir.mkdir()
    with patch.dict(os.environ, {"EMERGENCE_STATE": str(tmp_path)}):
        yield ingest_dir


@pytest.fixture
def temp_workspace(tmp_path):
    """Provide a temporary workspace for file-write checks."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    (workspace / "memory").mkdir()
    with patch.dict(os.environ, {"EMERGENCE_WORKSPACE": str(workspace)}):
        yield workspace


class TestWriteBreadcrumb:
    def test_creates_json_file(self, temp_ingest_dir):
        with patch.dict(os.environ, {"EMERGENCE_STATE": str(temp_ingest_dir.parent)}):
            path = write_breadcrumb("CREATIVE", "agent:main:cron:abc123", 300)
        
        assert path.exists()
        assert path.suffix == ".json"
        assert "CREATIVE" in path.name
    
    def test_breadcrumb_content(self, temp_ingest_dir):
        with patch.dict(os.environ, {"EMERGENCE_STATE": str(temp_ingest_dir.parent)}):
            path = write_breadcrumb("SOCIAL", "agent:main:cron:xyz", 600)
        
        data = json.loads(path.read_text())
        assert data["drive"] == "SOCIAL"
        assert data["session_key"] == "agent:main:cron:xyz"
        assert data["timeout_seconds"] == 600
        assert "spawned_at" in data
        assert "spawned_epoch" in data
    
    def test_multiple_breadcrumbs(self, temp_ingest_dir):
        with patch.dict(os.environ, {"EMERGENCE_STATE": str(temp_ingest_dir.parent)}):
            p1 = write_breadcrumb("CREATIVE", "key1", 300)
            time.sleep(0.01)  # Ensure different timestamps
            p2 = write_breadcrumb("SOCIAL", "key2", 300)
        
        assert p1 != p2
        assert len(list(temp_ingest_dir.glob("*.json"))) == 2


class TestAssessDepth:
    def test_timed_out(self):
        bc = {"timed_out": True, "spawned_epoch": 0, "timeout_seconds": 300}
        assert assess_depth(bc) == "shallow"
    
    def test_very_old_session(self):
        bc = {"spawned_epoch": 1, "timeout_seconds": 300}  # epoch 1 = ancient
        assert assess_depth(bc) == "shallow"
    
    def test_normal_completion(self):
        bc = {"spawned_epoch": time.time() - 60, "timeout_seconds": 300}
        # No file writes detected → moderate
        with patch("core.drives.satisfaction._check_file_writes", return_value=False):
            assert assess_depth(bc) == "moderate"
    
    def test_deep_with_file_writes(self):
        bc = {"spawned_epoch": time.time() - 60, "timeout_seconds": 300}
        with patch("core.drives.satisfaction._check_file_writes", return_value=True):
            assert assess_depth(bc) == "deep"


class TestIsSessionComplete:
    def test_young_session_unknown_without_breadcrumb(self):
        # Spawned 30 seconds ago, no completion breadcrumb — unknown
        assert _is_session_complete("key", 300, time.time() - 30) is None
    
    def test_past_timeout_plus_buffer_is_complete(self):
        # Spawned 400 seconds ago, timeout 300 — past timeout+60
        assert _is_session_complete("key", 300, time.time() - 400) is True
    
    def test_within_timeout_is_unknown(self):
        # Spawned 3 minutes ago, timeout 600 — still within timeout
        result = _is_session_complete("key", 600, time.time() - 180)
        assert result is None
    
    def test_between_timeout_and_buffer_is_unknown(self):
        # Spawned 11 minutes ago, timeout 1800 — within timeout, no breadcrumb
        assert _is_session_complete("key", 1800, time.time() - 660) is None
    
    def test_completion_breadcrumb_detected(self, temp_ingest_dir):
        # Write a completion breadcrumb
        from core.drives.satisfaction import write_completion
        with patch.dict(os.environ, {"EMERGENCE_STATE": str(temp_ingest_dir.parent)}):
            write_completion("TEST", "agent:main:cron:test-key")
            # Should detect as complete immediately
            assert _is_session_complete("agent:main:cron:test-key", 900, time.time() - 5) is True


class TestCheckFileWrites:
    def test_recent_file_detected(self, temp_workspace):
        # Create a file in memory dir
        mem_file = temp_workspace / "memory" / "test.md"
        mem_file.write_text("hello")
        
        assert _check_file_writes(time.time() - 60) is True
    
    def test_old_file_not_detected(self, temp_workspace):
        mem_file = temp_workspace / "memory" / "old.md"
        mem_file.write_text("old stuff")
        # Set mtime to the past
        old_time = time.time() - 3600
        os.utime(mem_file, (old_time, old_time))
        
        assert _check_file_writes(time.time() - 60) is False
    
    def test_empty_workspace(self, temp_workspace):
        assert _check_file_writes(time.time() - 60) is False


class TestCheckCompletedSessions:
    def test_empty_ingest_dir(self, temp_ingest_dir):
        state = {"drives": {}, "triggered_drives": []}
        with patch.dict(os.environ, {"EMERGENCE_STATE": str(temp_ingest_dir.parent)}):
            result = check_completed_sessions(state, {})
        assert result == []
    
    def test_satisfies_completed_session(self, temp_ingest_dir):
        # Write a breadcrumb that looks old enough to be complete
        bc = {
            "drive": "PLAY",
            "spawned_at": "2026-01-01T00:00:00+00:00",
            "spawned_epoch": 1,  # Very old
            "session_key": "agent:main:cron:test",
            "timeout_seconds": 300,
        }
        bc_path = temp_ingest_dir / "1-PLAY.json"
        bc_path.write_text(json.dumps(bc))
        
        state = {
            "drives": {
                "PLAY": {
                    "pressure": 25.0,
                    "threshold": 25,
                    "rate_per_hour": 5,
                }
            },
            "triggered_drives": ["PLAY"],
        }
        
        with patch.dict(os.environ, {"EMERGENCE_STATE": str(temp_ingest_dir.parent)}):
            result = check_completed_sessions(state, {})
        
        assert "PLAY" in result
        assert "PLAY" not in state["triggered_drives"]
        assert state["drives"]["PLAY"]["pressure"] < 25.0
        # Breadcrumb consumed
        assert not bc_path.exists()
    
    def test_skips_young_session(self, temp_ingest_dir):
        bc = {
            "drive": "CREATIVE",
            "spawned_at": "2026-02-09T15:00:00+00:00",
            "spawned_epoch": time.time() - 30,  # 30 seconds ago
            "session_key": "agent:main:cron:new",
            "timeout_seconds": 300,
        }
        bc_path = temp_ingest_dir / f"{int(time.time())}-CREATIVE.json"
        bc_path.write_text(json.dumps(bc))
        
        state = {
            "drives": {
                "CREATIVE": {"pressure": 20.0, "threshold": 20, "rate_per_hour": 4}
            },
            "triggered_drives": ["CREATIVE"],
        }
        
        with patch.dict(os.environ, {"EMERGENCE_STATE": str(temp_ingest_dir.parent)}):
            result = check_completed_sessions(state, {})
        
        assert result == []
        assert bc_path.exists()  # Not consumed
    
    def test_cleans_corrupted_breadcrumb(self, temp_ingest_dir):
        bc_path = temp_ingest_dir / "999-BROKEN.json"
        bc_path.write_text("not valid json{{{")
        
        state = {"drives": {}, "triggered_drives": []}
        with patch.dict(os.environ, {"EMERGENCE_STATE": str(temp_ingest_dir.parent)}):
            check_completed_sessions(state, {})
        
        assert not bc_path.exists()
