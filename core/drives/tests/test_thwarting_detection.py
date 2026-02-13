"""Tests for thwarting detection logic (Issue #41).

Tests cover:
- Detection of thwarted drives (≥3 triggers OR ≥150% pressure)
- Thwarting status reporting
- Finding all thwarted drives in state
- Message formatting
- Integration with drive engine
"""

import pytest
from datetime import datetime, timezone

from ..models import (
    Drive,
    DriveState,
    create_default_state,
    ensure_drive_defaults,
)
from ..engine import (
    satisfy_drive,
    mark_drive_triggered,
    bump_drive,
    tick_all_drives,
)
from ..thwarting import (
    is_thwarted,
    get_thwarting_status,
    get_thwarted_drives,
    format_thwarting_message,
    get_thwarting_emoji,
)


class TestIsThwarted:
    """Test is_thwarted() detection function."""
    
    def test_not_thwarted_normal_state(self):
        """Normal drive state should not be thwarted."""
        drive = {
            "pressure": 10.0,
            "threshold": 20.0,
            "thwarting_count": 0,
        }
        assert is_thwarted(drive) is False
    
    def test_not_thwarted_single_trigger(self):
        """Single trigger should not be thwarted."""
        drive = {
            "pressure": 15.0,
            "threshold": 20.0,
            "thwarting_count": 1,
        }
        assert is_thwarted(drive) is False
    
    def test_not_thwarted_two_triggers(self):
        """Two triggers should not be thwarted."""
        drive = {
            "pressure": 15.0,
            "threshold": 20.0,
            "thwarting_count": 2,
        }
        assert is_thwarted(drive) is False
    
    def test_thwarted_three_triggers(self):
        """Three consecutive triggers should be thwarted."""
        drive = {
            "pressure": 10.0,
            "threshold": 20.0,
            "thwarting_count": 3,
        }
        assert is_thwarted(drive) is True
    
    def test_thwarted_many_triggers(self):
        """Multiple triggers should remain thwarted."""
        drive = {
            "pressure": 10.0,
            "threshold": 20.0,
            "thwarting_count": 5,
        }
        assert is_thwarted(drive) is True
    
    def test_thwarted_extreme_pressure(self):
        """Pressure ≥150% should be thwarted."""
        drive = {
            "pressure": 30.0,  # 150% of 20
            "threshold": 20.0,
            "thwarting_count": 0,
        }
        assert is_thwarted(drive) is True
    
    def test_thwarted_very_high_pressure(self):
        """Pressure >150% should be thwarted."""
        drive = {
            "pressure": 40.0,  # 200% of 20
            "threshold": 20.0,
            "thwarting_count": 0,
        }
        assert is_thwarted(drive) is True
    
    def test_not_thwarted_below_150_percent(self):
        """Pressure just below 150% should not be thwarted."""
        drive = {
            "pressure": 29.0,  # 145% of 20
            "threshold": 20.0,
            "thwarting_count": 0,
        }
        assert is_thwarted(drive) is False
    
    def test_thwarted_combined_conditions(self):
        """Both high triggers and high pressure should be thwarted."""
        drive = {
            "pressure": 35.0,
            "threshold": 20.0,
            "thwarting_count": 4,
        }
        assert is_thwarted(drive) is True


class TestGetThwartingStatus:
    """Test get_thwarting_status() detailed reporting."""
    
    def test_status_not_thwarted(self):
        """Status should show not thwarted for normal drive."""
        drive = {
            "pressure": 10.0,
            "threshold": 20.0,
            "thwarting_count": 0,
            "valence": "appetitive",
        }
        status = get_thwarting_status(drive)
        
        assert status["is_thwarted"] is False
        assert status["thwarting_count"] == 0
        assert status["pressure_ratio"] == 0.5
        assert status["pressure_percent"] == 50
        assert status["reason"] is None
    
    def test_status_thwarted_by_triggers(self):
        """Status should identify thwarting by consecutive triggers."""
        drive = {
            "pressure": 15.0,
            "threshold": 20.0,
            "thwarting_count": 3,
            "valence": "aversive",
        }
        status = get_thwarting_status(drive)
        
        assert status["is_thwarted"] is True
        assert status["thwarting_count"] == 3
        assert status["reason"] == "consecutive_triggers"
        assert status["valence"] == "aversive"
    
    def test_status_thwarted_by_pressure(self):
        """Status should identify thwarting by extreme pressure."""
        drive = {
            "pressure": 32.0,
            "threshold": 20.0,
            "thwarting_count": 0,
            "valence": "aversive",
        }
        status = get_thwarting_status(drive)
        
        assert status["is_thwarted"] is True
        assert status["pressure_ratio"] == 1.6
        assert status["pressure_percent"] == 160
        assert status["reason"] == "extreme_pressure"
    
    def test_status_includes_all_fields(self):
        """Status should include all expected fields."""
        drive = {
            "pressure": 25.0,
            "threshold": 20.0,
            "thwarting_count": 2,
            "valence": "appetitive",
        }
        status = get_thwarting_status(drive)
        
        assert "is_thwarted" in status
        assert "thwarting_count" in status
        assert "pressure" in status
        assert "threshold" in status
        assert "pressure_ratio" in status
        assert "pressure_percent" in status
        assert "valence" in status
        assert "reason" in status


class TestGetThwartedDrives:
    """Test get_thwarted_drives() state scanning."""
    
    def test_no_thwarted_drives(self):
        """Should return empty list when no drives are thwarted."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 10.0
        state["drives"]["CARE"]["thwarting_count"] = 0
        
        thwarted = get_thwarted_drives(state)
        assert len(thwarted) == 0
    
    def test_one_thwarted_drive(self):
        """Should identify single thwarted drive."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 10.0
        state["drives"]["CARE"]["thwarting_count"] = 3
        
        thwarted = get_thwarted_drives(state)
        assert len(thwarted) == 1
        assert thwarted[0]["name"] == "CARE"
        assert thwarted[0]["is_thwarted"] is True
    
    def test_multiple_thwarted_drives(self):
        """Should identify all thwarted drives."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 10.0
        state["drives"]["CARE"]["thwarting_count"] = 3
        state["drives"]["MAINTENANCE"]["pressure"] = 40.0  # 160% of 25
        state["drives"]["MAINTENANCE"]["thwarting_count"] = 0
        
        thwarted = get_thwarted_drives(state)
        assert len(thwarted) == 2
        
        names = {d["name"] for d in thwarted}
        assert "CARE" in names
        assert "MAINTENANCE" in names
    
    def test_sorted_by_severity(self):
        """Should sort by thwarting count, then pressure."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 10.0
        state["drives"]["CARE"]["thwarting_count"] = 5  # Most severe
        state["drives"]["MAINTENANCE"]["pressure"] = 40.0
        state["drives"]["MAINTENANCE"]["thwarting_count"] = 3
        state["drives"]["REST"]["pressure"] = 50.0
        state["drives"]["REST"]["thwarting_count"] = 0  # Only pressure
        
        thwarted = get_thwarted_drives(state)
        assert len(thwarted) == 3
        
        # CARE should be first (highest count)
        assert thwarted[0]["name"] == "CARE"
        assert thwarted[0]["thwarting_count"] == 5
        
        # MAINTENANCE second (count 3)
        assert thwarted[1]["name"] == "MAINTENANCE"
        assert thwarted[1]["thwarting_count"] == 3
        
        # REST third (count 0, only pressure)
        assert thwarted[2]["name"] == "REST"
        assert thwarted[2]["thwarting_count"] == 0
    
    def test_mixed_thwarted_and_normal(self):
        """Should only return thwarted drives."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 30.0
        state["drives"]["CARE"]["thwarting_count"] = 3  # Thwarted
        state["drives"]["MAINTENANCE"]["pressure"] = 10.0
        state["drives"]["MAINTENANCE"]["thwarting_count"] = 1  # Not thwarted
        state["drives"]["REST"]["pressure"] = 5.0
        state["drives"]["REST"]["thwarting_count"] = 0  # Not thwarted
        
        thwarted = get_thwarted_drives(state)
        assert len(thwarted) == 1
        assert thwarted[0]["name"] == "CARE"


class TestFormatThwartingMessage:
    """Test format_thwarting_message() human-readable output."""
    
    def test_message_not_thwarted(self):
        """Should format message for non-thwarted drive."""
        status = {
            "is_thwarted": False,
            "thwarting_count": 1,
            "pressure_percent": 50,
        }
        msg = format_thwarting_message("CREATIVE", status)
        assert "not thwarted" in msg
    
    def test_message_thwarted_by_triggers(self):
        """Should format message for trigger-based thwarting."""
        status = {
            "is_thwarted": True,
            "thwarting_count": 4,
            "pressure_percent": 75,
            "reason": "consecutive_triggers",
        }
        msg = format_thwarting_message("CREATIVE", status)
        
        assert "CREATIVE" in msg
        assert "thwarted" in msg
        assert "4 triggers" in msg
        assert "no satisfaction" in msg
    
    def test_message_thwarted_by_pressure(self):
        """Should format message for pressure-based thwarting."""
        status = {
            "is_thwarted": True,
            "thwarting_count": 0,
            "pressure_percent": 180,
            "reason": "extreme_pressure",
        }
        msg = format_thwarting_message("SOCIAL", status)
        
        assert "SOCIAL" in msg
        assert "thwarted" in msg
        assert "extreme pressure" in msg
        assert "180%" in msg


class TestGetThwartingEmoji:
    """Test get_thwarting_emoji() visual indicators."""
    
    def test_emoji_not_thwarted_appetitive(self):
        """Should return → for appetitive non-thwarted."""
        status = {
            "is_thwarted": False,
            "valence": "appetitive",
            "thwarting_count": 0,
        }
        emoji = get_thwarting_emoji(status)
        assert emoji == "→"
    
    def test_emoji_not_thwarted_neutral(self):
        """Should return ○ for neutral."""
        status = {
            "is_thwarted": False,
            "valence": "neutral",
            "thwarting_count": 0,
        }
        emoji = get_thwarting_emoji(status)
        assert emoji == "○"
    
    def test_emoji_thwarted_with_count(self):
        """Should return ⚠ with count for thwarted."""
        status = {
            "is_thwarted": True,
            "valence": "aversive",
            "thwarting_count": 3,
        }
        emoji = get_thwarting_emoji(status)
        assert "⚠" in emoji
        assert "3" in emoji
    
    def test_emoji_thwarted_without_count(self):
        """Should return ⚠ for thwarted without count."""
        status = {
            "is_thwarted": True,
            "valence": "aversive",
            "thwarting_count": 0,
        }
        emoji = get_thwarting_emoji(status)
        assert emoji == "⚠"


class TestThwartingIntegrationWithEngine:
    """Test thwarting detection with drive engine operations."""
    
    def test_thwarting_after_repeated_triggers(self):
        """Drive should become thwarted after 3 triggers."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        
        # First trigger - not thwarted yet
        mark_drive_triggered(state, "CARE")
        assert is_thwarted(state["drives"]["CARE"]) is False
        
        # Second trigger - still not thwarted
        mark_drive_triggered(state, "CARE")
        assert is_thwarted(state["drives"]["CARE"]) is False
        
        # Third trigger - NOW thwarted
        mark_drive_triggered(state, "CARE")
        assert is_thwarted(state["drives"]["CARE"]) is True
        assert state["drives"]["CARE"]["thwarting_count"] == 3
    
    def test_thwarting_cleared_by_satisfaction(self):
        """Satisfaction should clear thwarting status."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        state["drives"]["CARE"]["thwarting_count"] = 4
        
        # Initially thwarted
        assert is_thwarted(state["drives"]["CARE"]) is True
        
        # Satisfy drive
        satisfy_drive(state, "CARE", "deep")
        
        # No longer thwarted
        assert is_thwarted(state["drives"]["CARE"]) is False
        assert state["drives"]["CARE"]["thwarting_count"] == 0
    
    def test_thwarting_from_extreme_pressure(self):
        """Bumping to 150%+ should trigger thwarting."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 10.0
        state["drives"]["CARE"]["threshold"] = 20.0
        
        # Not thwarted initially
        assert is_thwarted(state["drives"]["CARE"]) is False
        
        # Bump to 150%+
        bump_drive(state, "CARE", 20.0)  # Now at 30.0 (150%)
        
        # Should be thwarted
        assert is_thwarted(state["drives"]["CARE"]) is True
    
    def test_thwarted_drives_list_updates(self):
        """get_thwarted_drives should update with state changes."""
        state = create_default_state()
        
        # Initially no thwarted drives
        thwarted = get_thwarted_drives(state)
        assert len(thwarted) == 0
        
        # Trigger CARE 3 times
        state["drives"]["CARE"]["pressure"] = 25.0
        for _ in range(3):
            mark_drive_triggered(state, "CARE")
        
        # Should now have 1 thwarted drive
        thwarted = get_thwarted_drives(state)
        assert len(thwarted) == 1
        assert thwarted[0]["name"] == "CARE"
        
        # Satisfy CARE
        satisfy_drive(state, "CARE", "moderate")
        
        # Should be back to 0 thwarted drives
        thwarted = get_thwarted_drives(state)
        assert len(thwarted) == 0
    
    def test_valence_matches_thwarting_status(self):
        """Valence should be aversive when thwarted."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 15.0
        state["drives"]["CARE"]["threshold"] = 20.0
        
        # Trigger 3 times to reach thwarted state
        for _ in range(3):
            mark_drive_triggered(state, "CARE")
        
        # Should be thwarted
        assert is_thwarted(state["drives"]["CARE"]) is True
        
        # Valence should be aversive
        assert state["drives"]["CARE"]["valence"] == "aversive"
        
        # Status should reflect thwarting
        status = get_thwarting_status(state["drives"]["CARE"])
        assert status["is_thwarted"] is True
        assert status["reason"] == "consecutive_triggers"


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_thwarting_at_exactly_150_percent(self):
        """Exactly 150% pressure should be thwarted."""
        drive = {
            "pressure": 30.0,
            "threshold": 20.0,
            "thwarting_count": 0,
        }
        assert is_thwarted(drive) is True
    
    def test_thwarting_just_below_150_percent(self):
        """Just below 150% should not be thwarted."""
        drive = {
            "pressure": 29.9,
            "threshold": 20.0,
            "thwarting_count": 0,
        }
        assert is_thwarted(drive) is False
    
    def test_thwarting_with_zero_threshold(self):
        """Zero threshold should handle gracefully."""
        drive = {
            "pressure": 10.0,
            "threshold": 0.0,
            "thwarting_count": 0,
        }
        # Should not crash
        assert is_thwarted(drive) is False
    
    def test_thwarting_with_negative_pressure(self):
        """Negative pressure should not be thwarted."""
        drive = {
            "pressure": -5.0,
            "threshold": 20.0,
            "thwarting_count": 0,
        }
        assert is_thwarted(drive) is False
    
    def test_status_with_missing_fields(self):
        """Status should handle drives missing optional fields."""
        drive = {
            "pressure": 10.0,
            "threshold": 20.0,
            # Missing thwarting_count, valence
        }
        status = get_thwarting_status(drive)
        
        assert status["is_thwarted"] is False
        assert status["thwarting_count"] == 0
        # Should use default valence
        assert "valence" in status


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
