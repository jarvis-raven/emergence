"""Tests for the file-based drive satisfaction system and manual satisfaction."""

import json
import os
import time
from unittest.mock import patch

import pytest

from core.drives.satisfaction import (
    assess_depth,
    check_completed_sessions,
    calculate_satisfaction_depth,
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


@pytest.mark.skip(
    reason="Breadcrumb system removed in Phase 3 - use test_phase3_jsonl_tracking.py instead"
)
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


@pytest.mark.skip(
    reason="Breadcrumb system removed in Phase 3 - assess_depth now uses trigger log entries"
)
class TestAssessDepth:
    def test_timed_out(self):
        bc = {"timed_out": True, "spawned_epoch": 0, "timeout_seconds": 300}
        band, depth, ratio = assess_depth(bc)
        assert depth == "shallow"
        assert band == "session-error"

    def test_very_old_session(self):
        bc = {"spawned_epoch": 1, "timeout_seconds": 300}  # epoch 1 = ancient
        band, depth, ratio = assess_depth(bc)
        assert depth == "shallow"
        assert band == "session-error"

    def test_normal_completion(self):
        bc = {"spawned_epoch": time.time() - 60, "timeout_seconds": 300}
        # Low pressure (5/20 = 25%) -> below available -> shallow
        band, depth, ratio = assess_depth(bc, pressure=5.0)
        assert depth == "shallow"
        assert ratio == 0.25

    def test_deep_with_file_writes(self):
        bc = {"spawned_epoch": time.time() - 60, "timeout_seconds": 300}
        # High pressure (25/20 = 125%) -> triggered -> deep
        band, depth, ratio = assess_depth(bc, pressure=25.0)
        assert depth == "deep"
        assert ratio == 0.75


@pytest.mark.skip(
    reason="Breadcrumb system removed in Phase 3 - use test_phase3_jsonl_tracking.py instead"
)
class TestIsSessionComplete:
    def test_young_session_unknown_without_breadcrumb(self):
        # Spawned 30 seconds ago, no completion breadcrumb — unknown
        assert _is_session_complete("CREATIVE", "key", 300, time.time() - 30) is None

    def test_past_timeout_plus_buffer_is_complete(self):
        # Spawned 400 seconds ago, timeout 300 — past timeout+60
        assert _is_session_complete("CREATIVE", "key", 300, time.time() - 400) is True

    def test_within_timeout_is_unknown(self):
        # Spawned 3 minutes ago, timeout 600 — still within timeout
        result = _is_session_complete("CREATIVE", "key", 600, time.time() - 180)
        assert result is None

    def test_between_timeout_and_buffer_is_unknown(self):
        # Spawned 11 minutes ago, timeout 1800 — within timeout, no breadcrumb
        assert _is_session_complete("CREATIVE", "key", 1800, time.time() - 660) is None

    def test_completion_breadcrumb_detected(self, temp_ingest_dir):
        # Write a completion breadcrumb
        from core.drives.satisfaction import write_completion

        with patch.dict(os.environ, {"EMERGENCE_STATE": str(temp_ingest_dir.parent)}):
            write_completion("TEST", "agent:main:cron:test-key")
            # Should detect as complete immediately
            assert (
                _is_session_complete("TEST", "agent:main:cron:test-key", 900, time.time() - 5)
                is True
            )


@pytest.mark.skip(reason="Breadcrumb system removed in Phase 3 - file checking no longer used")
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


@pytest.mark.skip(
    reason="Breadcrumb system removed in Phase 3 - use test_phase3_jsonl_tracking.py instead"
)
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
            "drives": {"CREATIVE": {"pressure": 20.0, "threshold": 20, "rate_per_hour": 4}},
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


class TestCalculateSatisfactionDepth:
    """Tests for auto-scaled satisfaction depth calculation (issue #38 - band-based)."""

    def test_0_to_30_percent_shallow(self):
        """Below 30% (available band): 25% reduction"""
        # 25% pressure (5/20) - below available threshold
        band, depth, reduction = calculate_satisfaction_depth(5.0, 20.0)
        assert depth == "auto-shallow"
        assert reduction == 0.25
        assert band in ("below-available", "available")

        # 15% pressure (3/20)
        band, depth, reduction = calculate_satisfaction_depth(3.0, 20.0)
        assert depth == "auto-shallow"
        assert reduction == 0.25

    def test_30_to_75_percent_moderate(self):
        """30-75% (available band): 25% reduction"""
        # 50% pressure (10/20) - available
        band, depth, reduction = calculate_satisfaction_depth(10.0, 20.0)
        assert depth == "auto-shallow"
        assert reduction == 0.25
        assert band == "available"

        # 60% pressure (12/20)
        band, depth, reduction = calculate_satisfaction_depth(12.0, 20.0)
        assert depth == "auto-shallow"
        assert reduction == 0.25

    def test_75_to_100_percent_deep(self):
        """75-100% (elevated band): 50% reduction"""
        # 75% pressure (15/20) - elevated
        band, depth, reduction = calculate_satisfaction_depth(15.0, 20.0)
        assert depth == "auto-moderate"
        assert reduction == 0.50
        assert band == "elevated"

        # 90% pressure (18/20)
        band, depth, reduction = calculate_satisfaction_depth(18.0, 20.0)
        assert depth == "auto-moderate"
        assert reduction == 0.50

        # Exactly 100% (20/20) - now in triggered band (100-150%)
        band, depth, reduction = calculate_satisfaction_depth(20.0, 20.0)
        assert depth == "auto-deep"
        assert reduction == 0.75
        assert band == "triggered"

    def test_100_to_150_percent_deep_75(self):
        """100-150% (triggered band): 75% reduction"""
        # 110% pressure (22/20) - triggered
        band, depth, reduction = calculate_satisfaction_depth(22.0, 20.0)
        assert depth == "auto-deep"
        assert reduction == 0.75
        assert band == "triggered"

        # 125% pressure (25/20)
        band, depth, reduction = calculate_satisfaction_depth(25.0, 20.0)
        assert depth == "auto-deep"
        assert reduction == 0.75

    def test_150_plus_percent_full(self):
        """150%+ (crisis/emergency): 90% reduction"""
        # 150% pressure (30/20) - crisis
        band, depth, reduction = calculate_satisfaction_depth(30.0, 20.0)
        assert depth == "auto-full"
        assert reduction == 0.90
        assert band in ("crisis", "emergency")

        # 200% pressure (40/20)
        band, depth, reduction = calculate_satisfaction_depth(40.0, 20.0)
        assert depth == "auto-full"
        assert reduction == 0.90

    def test_edge_case_zero_threshold(self):
        """Handle invalid threshold gracefully"""
        band, depth, reduction = calculate_satisfaction_depth(10.0, 0.0)
        assert depth == "auto-moderate"
        assert reduction == 0.50

    def test_edge_case_zero_pressure(self):
        """Zero pressure should still calculate (below available)"""
        band, depth, reduction = calculate_satisfaction_depth(0.0, 20.0)
        # Below available band gets 25% shallow
        assert reduction == 0.25

    def test_boundary_conditions(self):
        """Test exact boundary values"""
        # Exactly 30% - should be available (25% reduction)
        band, depth, reduction = calculate_satisfaction_depth(6.0, 20.0)
        assert depth == "auto-shallow"
        assert reduction == 0.25

        # Just below 75% - should be available (25% reduction)
        band, depth, reduction = calculate_satisfaction_depth(14.99, 20.0)
        assert depth == "auto-shallow"
        assert reduction == 0.25

        # Exactly 150% - should be crisis/emergency (90% reduction)
        band, depth, reduction = calculate_satisfaction_depth(30.0, 20.0)
        assert depth == "auto-full"
        assert reduction == 0.90


class TestDriveStateSyncOnSatisfaction:
    """Tests for Issue #84: drives satisfy must sync drives-state.json"""

    def test_satisfy_syncs_drives_state_json(self, tmp_path):
        """Verify that drives-state.json is updated when a drive is satisfied"""
        from core.drives.state import save_state, load_drive_state
        from core.drives.engine import satisfy_drive
        from core.drives.models import create_default_state

        # Set up state paths
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        drives_json_path = state_dir / "drives.json"
        drives_state_json_path = state_dir / "drives-state.json"

        # Create initial state with a drive that has high pressure
        state = create_default_state()
        state["drives"]["CREATIVE"] = {
            "name": "CREATIVE",
            "description": "Test drive",
            "pressure": 25.0,
            "threshold": 20.0,
            "rate_per_hour": 2.0,
            "status": "triggered",
        }
        state["triggered_drives"] = ["CREATIVE"]

        # Save initial state
        save_state(drives_json_path, state)

        # Verify initial state was saved to both files
        assert drives_json_path.exists()
        assert drives_state_json_path.exists()

        # Load drives-state.json and verify initial pressure
        runtime_state_before = load_drive_state(drives_state_json_path)
        assert runtime_state_before["drives"]["CREATIVE"]["pressure"] == 25.0
        assert runtime_state_before["drives"]["CREATIVE"]["status"] == "triggered"
        assert "CREATIVE" in runtime_state_before.get("triggered_drives", [])

        # Satisfy the drive (50% reduction for moderate depth)
        satisfy_drive(state, "CREATIVE", "moderate")

        # Save state (this should update both drives.json and drives-state.json)
        save_state(drives_json_path, state)

        # Reload drives-state.json and verify it was updated
        runtime_state_after = load_drive_state(drives_state_json_path)

        # Verify pressure was reduced (25.0 * 0.5 = 12.5)
        assert runtime_state_after["drives"]["CREATIVE"]["pressure"] == 12.5

        # Verify drive was removed from triggered list (since reduction >= 50%)
        assert "CREATIVE" not in runtime_state_after.get("triggered_drives", [])

        # Note: The status field is preserved from the original state during save_state.
        # The key fix for #84 is that pressure and triggered_drives are synced correctly.

    def test_satisfy_preserves_other_drive_state(self, tmp_path):
        """Verify that satisfying one drive doesn't affect others in drives-state.json"""
        from core.drives.state import save_state, load_drive_state
        from core.drives.engine import satisfy_drive
        from core.drives.models import create_default_state

        # Set up state paths
        state_dir = tmp_path / "state"
        state_dir.mkdir()
        drives_json_path = state_dir / "drives.json"
        drives_state_json_path = state_dir / "drives-state.json"

        # Create state with multiple drives
        state = create_default_state()
        state["drives"]["CREATIVE"] = {
            "name": "CREATIVE",
            "pressure": 25.0,
            "threshold": 20.0,
            "rate_per_hour": 2.0,
        }
        state["drives"]["CARE"] = {
            "name": "CARE",
            "pressure": 15.0,
            "threshold": 20.0,
            "rate_per_hour": 1.5,
        }

        # Save initial state
        save_state(drives_json_path, state)

        # Satisfy only CREATIVE
        satisfy_drive(state, "CREATIVE", "deep")
        save_state(drives_json_path, state)

        # Reload and verify CARE was not affected
        runtime_state = load_drive_state(drives_state_json_path)
        assert runtime_state["drives"]["CARE"]["pressure"] == 15.0
        assert runtime_state["drives"]["CREATIVE"]["pressure"] == 6.25  # 25.0 * 0.25

    def test_satisfy_with_zero_pressure_threshold(self, tmp_path):
        """Edge case: satisfy a drive that's already at zero or has unusual values"""
        from core.drives.state import save_state, load_drive_state
        from core.drives.engine import satisfy_drive
        from core.drives.models import create_default_state

        state_dir = tmp_path / "state"
        state_dir.mkdir()
        drives_json_path = state_dir / "drives.json"
        drives_state_json_path = state_dir / "drives-state.json"

        state = create_default_state()
        state["drives"]["TEST"] = {
            "name": "TEST",
            "pressure": 0.0,
            "threshold": 20.0,
            "rate_per_hour": 1.0,
        }

        save_state(drives_json_path, state)
        satisfy_drive(state, "TEST", "moderate")
        save_state(drives_json_path, state)

        runtime_state = load_drive_state(drives_state_json_path)
        assert runtime_state["drives"]["TEST"]["pressure"] == 0.0
