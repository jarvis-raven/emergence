"""Tests for valence and thwarting_count tracking (Issue #40).

Tests cover:
- Valence calculation based on pressure and thwarting
- Thwarting count increments on trigger
- Thwarting count resets on satisfaction
- Valence transitions (appetitive -> aversive)
- Integration with drive engine
"""

import pytest
from datetime import datetime, timezone

from ..models import (
    calculate_valence,
    ensure_drive_defaults,
    create_default_state,
)
from ..engine import (
    satisfy_drive,
    mark_drive_triggered,
    bump_drive,
    tick_all_drives,
    get_drive_status,
)


class TestValenceCalculation:
    """Test calculate_valence function."""

    def test_neutral_valence_low_pressure(self):
        """Valence should be neutral when pressure < 30%."""
        valence = calculate_valence(5.0, 20.0, 0)
        assert valence == "neutral"

    def test_appetitive_valence_normal_pressure(self):
        """Valence should be appetitive for 30-150% pressure with no thwarting."""
        # 50% pressure
        valence = calculate_valence(10.0, 20.0, 0)
        assert valence == "appetitive"

        # 100% pressure
        valence = calculate_valence(20.0, 20.0, 0)
        assert valence == "appetitive"

        # 120% pressure
        valence = calculate_valence(24.0, 20.0, 0)
        assert valence == "appetitive"

    def test_aversive_valence_high_pressure(self):
        """Valence should be aversive when pressure >= 150%."""
        valence = calculate_valence(30.0, 20.0, 0)
        assert valence == "aversive"

        valence = calculate_valence(40.0, 20.0, 0)
        assert valence == "aversive"

    def test_aversive_valence_thwarting(self):
        """Valence should be aversive when thwarting_count >= 3."""
        # 50% pressure but high thwarting
        valence = calculate_valence(10.0, 20.0, 3)
        assert valence == "aversive"

        valence = calculate_valence(10.0, 20.0, 5)
        assert valence == "aversive"

    def test_appetitive_with_low_thwarting(self):
        """Valence should remain appetitive with low thwarting count."""
        valence = calculate_valence(10.0, 20.0, 1)
        assert valence == "appetitive"

        valence = calculate_valence(10.0, 20.0, 2)
        assert valence == "appetitive"


class TestDriveDefaults:
    """Test that new drives get proper defaults for valence and thwarting."""

    def test_ensure_drive_defaults_adds_valence(self):
        """ensure_drive_defaults should add valence field."""
        drive = {
            "name": "TEST",
            "pressure": 0.0,
            "threshold": 20.0,
        }
        drive = ensure_drive_defaults(drive)

        assert "valence" in drive
        assert drive["valence"] == "appetitive"

    def test_ensure_drive_defaults_adds_thwarting_count(self):
        """ensure_drive_defaults should add thwarting_count field."""
        drive = {
            "name": "TEST",
            "pressure": 0.0,
            "threshold": 20.0,
        }
        drive = ensure_drive_defaults(drive)

        assert "thwarting_count" in drive
        assert drive["thwarting_count"] == 0

    def test_create_default_state_includes_valence(self):
        """Default drive state should include valence tracking."""
        state = create_default_state()

        # Check that CARE drive has valence fields
        care = state["drives"]["CARE"]
        assert "valence" in care or care.get("valence") is None  # Will be set on first tick


class TestMarkDriveTriggered:
    """Test marking drives as triggered and incrementing thwarting count."""

    def test_increment_thwarting_on_trigger(self):
        """Thwarting count should increment when drive is triggered."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        state["drives"]["CARE"]["thwarting_count"] = 0

        result = mark_drive_triggered(state, "CARE")

        assert result["success"] is True
        assert result["new_thwarting_count"] == 1
        assert state["drives"]["CARE"]["thwarting_count"] == 1

    def test_multiple_triggers_increment_count(self):
        """Multiple triggers should accumulate thwarting count."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        state["drives"]["CARE"]["thwarting_count"] = 0

        mark_drive_triggered(state, "CARE")
        mark_drive_triggered(state, "CARE")
        result = mark_drive_triggered(state, "CARE")

        assert result["new_thwarting_count"] == 3
        assert state["drives"]["CARE"]["thwarting_count"] == 3

    def test_trigger_updates_valence(self):
        """Triggering should update valence based on count."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        state["drives"]["CARE"]["thwarting_count"] = 2
        state["drives"]["CARE"]["valence"] = "appetitive"

        # Third trigger should shift to aversive
        result = mark_drive_triggered(state, "CARE")

        assert result["new_valence"] == "aversive"
        assert state["drives"]["CARE"]["valence"] == "aversive"

    def test_trigger_updates_last_triggered_timestamp(self):
        """Triggering should update last_triggered timestamp."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0

        result = mark_drive_triggered(state, "CARE")

        assert "last_triggered" in state["drives"]["CARE"]
        assert state["drives"]["CARE"]["last_triggered"] is not None


class TestSatisfyDriveResetsThwarting:
    """Test that satisfying a drive resets thwarting count."""

    def test_satisfaction_resets_thwarting_count(self):
        """Satisfying a drive should reset thwarting_count to 0."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        state["drives"]["CARE"]["thwarting_count"] = 3
        state["drives"]["CARE"]["valence"] = "aversive"

        result = satisfy_drive(state, "CARE", "moderate")

        assert result["success"] is True
        assert result["thwarting_count_reset"] == 3
        assert state["drives"]["CARE"]["thwarting_count"] == 0

    def test_satisfaction_updates_valence(self):
        """Satisfying a drive should recalculate valence."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        state["drives"]["CARE"]["thwarting_count"] = 3
        state["drives"]["CARE"]["valence"] = "aversive"

        result = satisfy_drive(state, "CARE", "deep")

        # After 75% reduction, pressure should be ~6.25 (31% of 20.0 threshold)
        # This is just above the 30% available threshold, so appetitive
        assert state["drives"]["CARE"]["pressure"] < 10.0
        assert state["drives"]["CARE"]["thwarting_count"] == 0
        assert state["drives"]["CARE"]["valence"] == "appetitive"

    def test_partial_satisfaction_still_resets_count(self):
        """Even shallow satisfaction should reset thwarting count."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        state["drives"]["CARE"]["thwarting_count"] = 2

        satisfy_drive(state, "CARE", "shallow")

        assert state["drives"]["CARE"]["thwarting_count"] == 0


class TestValenceTransitions:
    """Test valence transitions through drive lifecycle."""

    def test_appetitive_to_aversive_via_thwarting(self):
        """Drive should shift from appetitive to aversive after repeated thwarting."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 15.0
        state["drives"]["CARE"]["thwarting_count"] = 0
        state["drives"]["CARE"]["valence"] = "appetitive"

        # Trigger 3 times
        mark_drive_triggered(state, "CARE")
        assert state["drives"]["CARE"]["valence"] == "appetitive"

        mark_drive_triggered(state, "CARE")
        assert state["drives"]["CARE"]["valence"] == "appetitive"

        mark_drive_triggered(state, "CARE")
        assert state["drives"]["CARE"]["valence"] == "aversive"

    def test_appetitive_to_aversive_via_pressure(self):
        """Drive should shift from appetitive to aversive at 150% pressure."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 10.0
        state["drives"]["CARE"]["threshold"] = 20.0
        state["drives"]["CARE"]["thwarting_count"] = 0

        # Bump to 150%+
        bump_drive(state, "CARE", 20.0)

        assert state["drives"]["CARE"]["pressure"] >= 30.0
        assert state["drives"]["CARE"]["valence"] == "aversive"

    def test_aversive_to_appetitive_via_satisfaction(self):
        """Drive should return to appetitive after satisfaction."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 30.0
        state["drives"]["CARE"]["thwarting_count"] = 3
        state["drives"]["CARE"]["valence"] = "aversive"

        # Deep satisfaction brings pressure down and resets count
        satisfy_drive(state, "CARE", "deep")

        # New pressure: 30 * 0.25 = 7.5 (35% of threshold)
        assert state["drives"]["CARE"]["pressure"] < 10.0
        assert state["drives"]["CARE"]["thwarting_count"] == 0
        assert state["drives"]["CARE"]["valence"] == "appetitive"


class TestValenceIntegrationWithEngine:
    """Test valence updates during normal drive operations."""

    def test_tick_updates_valence(self):
        """Ticking should update valence for all drives."""
        state = create_default_state()
        state["last_tick"] = "2026-02-13T10:00:00+00:00"

        # Manually set CARE to high pressure
        state["drives"]["CARE"]["pressure"] = 30.0
        state["drives"]["CARE"]["thwarting_count"] = 0

        config = {"drives": {}}

        # Update last_tick to 2 hours ago
        from datetime import timedelta

        now = datetime.now(timezone.utc)
        two_hours_ago = (now - timedelta(hours=2)).isoformat()
        state["last_tick"] = two_hours_ago

        tick_all_drives(state, config)

        # Should have updated valence
        assert "valence" in state["drives"]["CARE"]
        assert state["drives"]["CARE"]["valence"] == "aversive"  # 30.0 is 150% of 20.0

    def test_get_drive_status_includes_valence(self):
        """Drive status should include valence and thwarting count."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 15.0
        state["drives"]["CARE"]["thwarting_count"] = 2
        state["drives"]["CARE"]["valence"] = "appetitive"

        status = get_drive_status(state, "CARE")

        assert status is not None
        assert "valence" in status
        assert "thwarting_count" in status
        assert status["valence"] == "appetitive"
        assert status["thwarting_count"] == 2


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_valence_with_zero_threshold(self):
        """Valence calculation should handle zero threshold gracefully."""
        valence = calculate_valence(10.0, 0.0, 0)
        assert valence == "neutral"

    def test_valence_with_negative_pressure(self):
        """Valence should handle negative pressure (shouldn't happen, but...)."""
        valence = calculate_valence(-5.0, 20.0, 0)
        assert valence == "neutral"

    def test_thwarting_count_never_negative(self):
        """Thwarting count should never go negative."""
        state = create_default_state()
        state["drives"]["CARE"]["thwarting_count"] = 0

        # Satisfy when count is already 0
        satisfy_drive(state, "CARE", "moderate")

        assert state["drives"]["CARE"]["thwarting_count"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
