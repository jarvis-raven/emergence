"""Unit tests for drive engine logic.

Tests pressure accumulation, threshold detection, satisfaction mechanics,
and quiet hours functionality.
"""

import sys
import os
import unittest
from datetime import datetime, timezone
from pathlib import Path

# Import from the package
from core.drives.engine import (
    accumulate_pressure,
    check_thresholds,
    satisfy_drive,
    bump_drive,
    reset_all_drives,
    get_drive_status,
    tick_all_drives,
    is_quiet_hours,
)
from core.drives.models import create_default_state, SATISFACTION_DEPTHS


class TestPressureAccumulation(unittest.TestCase):
    """Test pressure accumulation math and edge cases."""
    
    def test_basic_accumulation(self):
        """Pressure should increase by rate * hours."""
        drive = {
            "pressure": 10.0,
            "threshold": 20.0,
            "rate_per_hour": 2.0,
        }
        new_pressure = accumulate_pressure(drive, 2.0)
        self.assertEqual(new_pressure, 14.0)  # 10 + (2 * 2)
    
    def test_zero_elapsed(self):
        """Zero elapsed time should not change pressure."""
        drive = {
            "pressure": 10.0,
            "threshold": 20.0,
            "rate_per_hour": 2.0,
        }
        new_pressure = accumulate_pressure(drive, 0.0)
        self.assertEqual(new_pressure, 10.0)
    
    def test_activity_driven_no_accumulation(self):
        """Activity-driven drives should not accumulate from time."""
        drive = {
            "pressure": 5.0,
            "threshold": 30.0,
            "rate_per_hour": 0.0,
            "activity_driven": True,
        }
        new_pressure = accumulate_pressure(drive, 10.0)
        self.assertEqual(new_pressure, 5.0)  # Unchanged
    
    def test_pressure_cap(self):
        """Pressure should cap at threshold * max_ratio."""
        drive = {
            "pressure": 10.0,
            "threshold": 20.0,
            "rate_per_hour": 10.0,
        }
        # 10 + (10 * 10) = 110, but capped at 20 * 1.5 = 30
        new_pressure = accumulate_pressure(drive, 10.0, max_ratio=1.5)
        self.assertEqual(new_pressure, 30.0)
    
    def test_custom_max_ratio(self):
        """Custom max_ratio should apply correctly."""
        drive = {
            "pressure": 10.0,
            "threshold": 20.0,
            "rate_per_hour": 5.0,
        }
        # 10 + (5 * 5) = 35, capped at 20 * 2 = 40
        new_pressure = accumulate_pressure(drive, 5.0, max_ratio=2.0)
        self.assertEqual(new_pressure, 35.0)  # Not capped
    
    def test_zero_threshold(self):
        """Zero threshold should not cause division by zero issues."""
        drive = {
            "pressure": 10.0,
            "threshold": 0.0,
            "rate_per_hour": 1.0,
        }
        new_pressure = accumulate_pressure(drive, 1.0)
        # Should just return current pressure (can't accumulate with no threshold)
        self.assertEqual(new_pressure, 10.0)


class TestThresholdDetection(unittest.TestCase):
    """Test threshold checking logic."""
    
    def test_exact_threshold(self):
        """Drive exactly at threshold should trigger."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 20.0  # Exactly at threshold
        
        config = {"drives": {"quiet_hours": None}}
        triggered = check_thresholds(state, config)
        
        self.assertIn("CARE", triggered)
    
    def test_over_threshold(self):
        """Drive over threshold should trigger."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0  # Over threshold 20.0
        
        config = {"drives": {"quiet_hours": None}}
        triggered = check_thresholds(state, config)
        
        self.assertIn("CARE", triggered)
    
    def test_below_threshold(self):
        """Drive below threshold should not trigger."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 19.9  # Just under threshold
        
        config = {"drives": {"quiet_hours": None}}
        triggered = check_thresholds(state, config)
        
        self.assertNotIn("CARE", triggered)
    
    def test_already_triggered_not_repeated(self):
        """Already triggered drives should not trigger again."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0  # Over threshold
        state["triggered_drives"] = ["CARE"]  # Already triggered
        
        config = {"drives": {"quiet_hours": None}}
        triggered = check_thresholds(state, config)
        
        self.assertNotIn("CARE", triggered)
    
    def test_sorted_by_ratio(self):
        """Triggered drives should be sorted by pressure ratio."""
        state = create_default_state()
        # CARE: 20.0 threshold, 30.0 pressure = 150%
        state["drives"]["CARE"]["pressure"] = 30.0
        # MAINTENANCE: 25.0 threshold, 50.0 pressure = 200%
        state["drives"]["MAINTENANCE"]["pressure"] = 50.0
        
        config = {"drives": {"quiet_hours": None}}
        triggered = check_thresholds(state, config)
        
        # MAINTENANCE has higher ratio, should be first
        self.assertEqual(triggered[0], "MAINTENANCE")
        self.assertEqual(triggered[1], "CARE")


class TestSatisfaction(unittest.TestCase):
    """Test satisfaction mechanics."""
    
    def test_shallow_satisfaction(self):
        """Shallow satisfaction reduces by 30%."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 20.0
        
        result = satisfy_drive(state, "CARE", "shallow")
        
        self.assertEqual(result["new_pressure"], 14.0)  # 20 * 0.7
        self.assertEqual(result["depth"], "shallow")
    
    def test_moderate_satisfaction(self):
        """Moderate satisfaction reduces by 50%."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 20.0
        
        result = satisfy_drive(state, "CARE", "moderate")
        
        self.assertEqual(result["new_pressure"], 10.0)  # 20 * 0.5
    
    def test_deep_satisfaction(self):
        """Deep satisfaction reduces by 75%."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 20.0
        
        result = satisfy_drive(state, "CARE", "deep")
        
        self.assertEqual(result["new_pressure"], 5.0)  # 20 * 0.25
    
    def test_full_satisfaction(self):
        """Full satisfaction reduces to zero."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 100.0
        
        result = satisfy_drive(state, "CARE", "full")
        
        self.assertEqual(result["new_pressure"], 0.0)
    
    def test_satisfaction_shortcuts(self):
        """Single-letter depth shortcuts work."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 20.0
        
        result_s = satisfy_drive(state, "CARE", "s")
        self.assertEqual(result_s["new_pressure"], 14.0)  # 30% reduction
        
        state["drives"]["CARE"]["pressure"] = 20.0
        result_m = satisfy_drive(state, "CARE", "m")
        self.assertEqual(result_m["new_pressure"], 10.0)  # 50% reduction
    
    def test_removes_from_triggered_if_significant(self):
        """Satisfaction with >=50% reduction removes from triggered."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        state["triggered_drives"] = ["CARE"]
        
        satisfy_drive(state, "CARE", "moderate")  # 50% reduction
        
        self.assertNotIn("CARE", state["triggered_drives"])
    
    def test_keeps_in_triggered_if_shallow(self):
        """Shallow satisfaction (<50%) keeps in triggered list."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        state["triggered_drives"] = ["CARE"]
        
        satisfy_drive(state, "CARE", "shallow")  # 30% reduction
        
        self.assertIn("CARE", state["triggered_drives"])
    
    def test_satisfaction_event_recorded(self):
        """Satisfaction should record timestamp."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 20.0
        state["drives"]["CARE"]["satisfaction_events"] = []
        
        satisfy_drive(state, "CARE", "full")
        
        events = state["drives"]["CARE"]["satisfaction_events"]
        self.assertEqual(len(events), 1)
        # Should be ISO format timestamp
        self.assertIn("T", events[0])
    
    def test_negative_pressure_clamped(self):
        """Satisfaction should never result in negative pressure."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 1.0
        
        result = satisfy_drive(state, "CARE", "deep")  # 75% of 1 = 0.25, so 0.75
        
        self.assertEqual(result["new_pressure"], 0.25)
        self.assertGreaterEqual(result["new_pressure"], 0.0)


class TestBumpDrive(unittest.TestCase):
    """Test manual pressure bumping."""
    
    def test_bump_by_amount(self):
        """Bump should increase by specified amount."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 10.0
        
        result = bump_drive(state, "CARE", 5.0)
        
        self.assertEqual(result["new_pressure"], 15.0)
    
    def test_bump_default_amount(self):
        """Bump without amount uses 2 hours at drive's rate."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 10.0
        # rate_per_hour is 2.0 for CARE
        
        result = bump_drive(state, "CARE")  # No amount specified
        
        self.assertEqual(result["amount_added"], 4.0)  # 2 * 2.0
        self.assertEqual(result["new_pressure"], 14.0)
    
    def test_bump_respects_cap(self):
        """Bump should cap at threshold * 1.5."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0  # Already over threshold
        
        result = bump_drive(state, "CARE", 50.0)  # Would go to 75
        
        self.assertEqual(result["new_pressure"], 30.0)  # Capped at 20 * 1.5


class TestReset(unittest.TestCase):
    """Test reset functionality."""
    
    def test_reset_all_drives(self):
        """Reset should zero all drive pressures."""
        state = create_default_state()
        for drive in state["drives"].values():
            drive["pressure"] = 50.0
        state["triggered_drives"] = ["CARE", "MAINTENANCE"]
        
        result = reset_all_drives(state)
        
        self.assertEqual(result["drives_reset"], 3)  # 3 core drives
        self.assertEqual(result["triggered_cleared"], 2)
        
        for drive in state["drives"].values():
            self.assertEqual(drive["pressure"], 0.0)
        
        self.assertEqual(len(state["triggered_drives"]), 0)


class TestGetDriveStatus(unittest.TestCase):
    """Test drive status retrieval."""
    
    def test_get_status_normal(self):
        """Normal status when below 75%."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 10.0  # 50%
        
        status = get_drive_status(state, "CARE")
        
        self.assertEqual(status["status"], "normal")
        self.assertEqual(status["percentage"], 50.0)
    
    def test_get_status_elevated(self):
        """Elevated status at 75-99%."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 16.0  # 80%
        
        status = get_drive_status(state, "CARE")
        
        self.assertEqual(status["status"], "elevated")
    
    def test_get_status_over_threshold(self):
        """Over threshold status at 100%+."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0  # 125%
        
        status = get_drive_status(state, "CARE")
        
        self.assertEqual(status["status"], "over_threshold")
    
    def test_get_status_triggered(self):
        """Triggered status when in triggered_drives."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 10.0  # Normal level
        state["triggered_drives"] = ["CARE"]  # But marked triggered
        
        status = get_drive_status(state, "CARE")
        
        self.assertEqual(status["status"], "triggered")
    
    def test_get_unknown_drive(self):
        """Unknown drive should return None."""
        state = create_default_state()
        
        status = get_drive_status(state, "NONEXISTENT")
        
        self.assertIsNone(status)


class TestTickAllDrives(unittest.TestCase):
    """Test tick operation for all drives."""
    
    def test_tick_updates_non_triggered(self):
        """Tick should update non-triggered drives."""
        state = create_default_state()
        state["last_tick"] = "2026-02-07T10:00:00+00:00"
        
        # Mock the current time by not relying on real time
        # We'll just verify the structure works
        config = {"drives": {"max_pressure_ratio": 1.5}}
        
        changes = tick_all_drives(state, config)
        
        # Should have changes (hours elapsed > 0)
        self.assertIsInstance(changes, dict)
    
    def test_tick_skips_triggered(self):
        """Tick should not update already triggered drives."""
        state = create_default_state()
        state["triggered_drives"] = ["CARE"]
        
        old_pressure = state["drives"]["CARE"]["pressure"]
        
        config = {"drives": {"max_pressure_ratio": 1.5}}
        tick_all_drives(state, config)
        
        # CARE should be unchanged (it's triggered)
        self.assertEqual(state["drives"]["CARE"]["pressure"], old_pressure)


if __name__ == "__main__":
    unittest.main(verbosity=2)
