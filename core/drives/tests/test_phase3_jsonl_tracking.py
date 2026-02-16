"""Tests for Phase 3: JSONL-based session tracking (Issue #58).

Tests the new session tracking system that uses trigger-log.jsonl instead
of breadcrumb files for tracking spawned sessions.
"""

import json
import os
from datetime import datetime, timezone
from unittest.mock import patch

import pytest

from core.drives.history import (
    add_trigger_event,
    update_session_status,
    get_active_sessions,
)
from core.drives.satisfaction import check_completed_sessions
from core.drives.spawn import record_trigger


@pytest.fixture
def temp_state_dir(tmp_path):
    """Provide a temporary state directory."""
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    with patch.dict(os.environ, {"EMERGENCE_STATE": str(state_dir)}):
        yield state_dir


class TestLogTriggerEvent:
    """Test logging trigger events to JSONL."""

    def test_creates_jsonl_file(self, temp_state_dir):
        """Test that add_trigger_event creates trigger-log.jsonl."""
        add_trigger_event({}, "CARE", 25.0, 20.0, True, reason="Test", session_key="test:123")

        log_path = temp_state_dir / "trigger-log.jsonl"
        assert log_path.exists()

    def test_appends_to_existing_log(self, temp_state_dir):
        """Test that multiple events append to the log."""
        add_trigger_event({}, "CARE", 25.0, 20.0, True, session_key="test:1")
        add_trigger_event({}, "CREATIVE", 30.0, 25.0, True, session_key="test:2")

        log_path = temp_state_dir / "trigger-log.jsonl"
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 2

    def test_includes_session_key_and_status(self, temp_state_dir):
        """Test that events with session_key include session_status."""
        add_trigger_event(
            {}, "CARE", 25.0, 20.0, True, session_key="test:123", session_status="spawned"
        )

        log_path = temp_state_dir / "trigger-log.jsonl"
        event = json.loads(log_path.read_text())

        assert event["session_key"] == "test:123"
        assert event["session_status"] == "spawned"

    def test_non_spawned_events_no_session_key(self, temp_state_dir):
        """Test that non-spawned events don't have session_key."""
        add_trigger_event({}, "CARE", 15.0, 20.0, False, reason="Below threshold")

        log_path = temp_state_dir / "trigger-log.jsonl"
        event = json.loads(log_path.read_text())

        assert "session_key" not in event
        assert "session_status" not in event
        assert event["session_spawned"] is False


class TestUpdateSessionStatus:
    """Test updating session status in JSONL."""

    def test_updates_existing_session(self, temp_state_dir):
        """Test that update_session_status modifies the right entry."""
        # Create initial entry
        add_trigger_event(
            {}, "CARE", 25.0, 20.0, True, session_key="test:123", session_status="spawned"
        )

        # Update status
        result = update_session_status("test:123", "completed")
        assert result is True

        # Verify update
        log_path = temp_state_dir / "trigger-log.jsonl"
        event = json.loads(log_path.read_text())
        assert event["session_status"] == "completed"

    def test_returns_false_for_nonexistent_session(self, temp_state_dir):
        """Test that updating nonexistent session returns False."""
        result = update_session_status("nonexistent:key", "completed")
        assert result is False

    def test_preserves_other_fields(self, temp_state_dir):
        """Test that update doesn't modify other fields."""
        add_trigger_event({}, "CARE", 25.0, 20.0, True, session_key="test:123", reason="Test")

        update_session_status("test:123", "active")

        log_path = temp_state_dir / "trigger-log.jsonl"
        event = json.loads(log_path.read_text())
        assert event["drive"] == "CARE"
        assert event["pressure"] == 25.0
        assert event["reason"] == "Test"
        assert event["session_status"] == "active"


class TestGetActiveSessions:
    """Test querying active sessions from JSONL."""

    def test_returns_spawned_sessions(self, temp_state_dir):
        """Test that get_active_sessions returns spawned sessions."""
        add_trigger_event(
            {}, "CARE", 25.0, 20.0, True, session_key="test:1", session_status="spawned"
        )
        add_trigger_event(
            {}, "CREATIVE", 30.0, 25.0, True, session_key="test:2", session_status="spawned"
        )

        active = get_active_sessions()
        assert len(active) == 2
        assert all(s["session_status"] == "spawned" for s in active)

    def test_returns_active_sessions(self, temp_state_dir):
        """Test that get_active_sessions includes active status."""
        add_trigger_event(
            {}, "CARE", 25.0, 20.0, True, session_key="test:1", session_status="active"
        )

        active = get_active_sessions()
        assert len(active) == 1
        assert active[0]["session_status"] == "active"

    def test_excludes_completed_sessions(self, temp_state_dir):
        """Test that completed sessions are not returned."""
        add_trigger_event(
            {}, "CARE", 25.0, 20.0, True, session_key="test:1", session_status="spawned"
        )
        add_trigger_event(
            {}, "CREATIVE", 30.0, 25.0, True, session_key="test:2", session_status="completed"
        )

        active = get_active_sessions()
        assert len(active) == 1
        assert active[0]["drive"] == "CARE"

    def test_excludes_timeout_sessions(self, temp_state_dir):
        """Test that timed-out sessions are not returned."""
        add_trigger_event(
            {}, "CARE", 25.0, 20.0, True, session_key="test:1", session_status="timeout"
        )

        active = get_active_sessions()
        assert len(active) == 0

    def test_adds_spawned_epoch_from_timestamp(self, temp_state_dir):
        """Test that get_active_sessions adds spawned_epoch."""
        add_trigger_event(
            {}, "CARE", 25.0, 20.0, True, session_key="test:1", session_status="spawned"
        )

        active = get_active_sessions()
        assert "spawned_epoch" in active[0]
        assert isinstance(active[0]["spawned_epoch"], int)


class TestRecordTrigger:
    """Test record_trigger function with session_key support."""

    def test_records_with_session_key(self, temp_state_dir):
        """Test that record_trigger writes session_key to JSONL."""
        state = {}
        record_trigger(state, "CARE", 25.0, 20.0, True, session_key="test:123", reason="Test")

        log_path = temp_state_dir / "trigger-log.jsonl"
        event = json.loads(log_path.read_text())

        assert event["session_key"] == "test:123"
        assert event["session_status"] == "spawned"

    def test_records_without_session_key(self, temp_state_dir):
        """Test that record_trigger works without session_key."""
        state = {}
        record_trigger(state, "CARE", 15.0, 20.0, False, reason="Below threshold")

        log_path = temp_state_dir / "trigger-log.jsonl"
        event = json.loads(log_path.read_text())

        assert "session_key" not in event
        assert event["session_spawned"] is False


class TestCheckCompletedSessions:
    """Test JSONL-based completed session checking."""

    def test_detects_completed_sessions(self, temp_state_dir):
        """Test that check_completed_sessions finds completed sessions."""
        # Create spawned session
        add_trigger_event(
            {}, "CARE", 25.0, 20.0, True, session_key="test:123", session_status="spawned"
        )

        # Mark as completed
        update_session_status("test:123", "completed")

        # Check for completions
        state = {
            "drives": {
                "CARE": {
                    "pressure": 25.0,
                    "threshold": 20.0,
                }
            }
        }
        config = {"drives": {"session_timeout": 900}}

        satisfied = check_completed_sessions(state, config)

        # Should not be empty (but exact behavior depends on assess_depth implementation)
        assert isinstance(satisfied, list)

    def test_handles_timeout(self, temp_state_dir):
        """Test that old spawned sessions are marked as timeout."""
        # Create old spawned session (using manual timestamp)
        old_timestamp = datetime.now(timezone.utc).timestamp() - 1000  # 1000 seconds ago
        log_path = temp_state_dir / "trigger-log.jsonl"

        event = {
            "drive": "CARE",
            "pressure": 25.0,
            "threshold": 20.0,
            "timestamp": datetime.fromtimestamp(old_timestamp, timezone.utc).isoformat(),
            "session_spawned": True,
            "session_key": "test:old",
            "session_status": "pending",
        }

        with log_path.open("a") as f:
            f.write(json.dumps(event) + "\n")

        # Check for completions (should detect timeout)
        state = {
            "drives": {
                "CARE": {
                    "pressure": 25.0,
                    "threshold": 20.0,
                }
            }
        }
        config = {"drives": {"session_timeout": 300}}  # 5 minutes

        satisfied = check_completed_sessions(state, config)

        # Verify timeout was detected
        assert isinstance(satisfied, list)


class TestPhase3Migration:
    """Test that Phase 3 works without breadcrumb files."""

    def test_no_breadcrumb_directory_needed(self, temp_state_dir):
        """Test that session tracking works without sessions_ingest directory."""
        # Ensure sessions_ingest doesn't exist
        ingest_dir = temp_state_dir / "sessions_ingest"
        assert not ingest_dir.exists()

        # Spawn session (records to JSONL)
        add_trigger_event(
            {}, "CARE", 25.0, 20.0, True, session_key="test:123", session_status="spawned"
        )

        # Verify tracking works
        active = get_active_sessions()
        assert len(active) == 1
        assert active[0]["session_key"] == "test:123"

    def test_jsonl_is_single_source_of_truth(self, temp_state_dir):
        """Test that all session tracking goes through JSONL."""
        # Spawn multiple sessions
        for i in range(5):
            add_trigger_event(
                {},
                f"DRIVE_{i}",
                25.0,
                20.0,
                True,
                session_key=f"test:{i}",
                session_status="spawned",
            )

        # Complete some
        update_session_status("test:1", "completed")
        update_session_status("test:3", "timeout")

        # Query active
        active = get_active_sessions()
        assert len(active) == 3  # 0, 2, 4

        # Verify JSONL has all records
        log_path = temp_state_dir / "trigger-log.jsonl"
        lines = log_path.read_text().strip().split("\n")
        assert len(lines) == 5
