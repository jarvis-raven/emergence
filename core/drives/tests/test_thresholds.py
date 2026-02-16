"""Unit tests for graduated threshold system.

Tests threshold configuration, backward compatibility, status labels,
and per-drive vs global threshold settings.
"""

import unittest

# Import from the package
from core.drives.models import (
    get_drive_thresholds,
    get_threshold_label,
    create_default_state,
)
from core.drives.engine import (
    check_thresholds,
    get_drive_status,
)
from core.drives.config import DEFAULT_THRESHOLDS


class TestGraduatedThresholds(unittest.TestCase):
    """Test graduated threshold configuration and resolution."""

    def test_default_thresholds_structure(self):
        """DEFAULT_THRESHOLDS should have all five levels."""
        self.assertIn("available", DEFAULT_THRESHOLDS)
        self.assertIn("elevated", DEFAULT_THRESHOLDS)
        self.assertIn("triggered", DEFAULT_THRESHOLDS)
        self.assertIn("crisis", DEFAULT_THRESHOLDS)
        self.assertIn("emergency", DEFAULT_THRESHOLDS)

        # Check ordering
        self.assertLess(DEFAULT_THRESHOLDS["available"], DEFAULT_THRESHOLDS["elevated"])
        self.assertLess(DEFAULT_THRESHOLDS["elevated"], DEFAULT_THRESHOLDS["triggered"])
        self.assertLess(DEFAULT_THRESHOLDS["triggered"], DEFAULT_THRESHOLDS["crisis"])
        self.assertLess(DEFAULT_THRESHOLDS["crisis"], DEFAULT_THRESHOLDS["emergency"])

    def test_default_thresholds_values(self):
        """DEFAULT_THRESHOLDS should match specification."""
        self.assertEqual(DEFAULT_THRESHOLDS["available"], 0.30)
        self.assertEqual(DEFAULT_THRESHOLDS["elevated"], 0.75)
        self.assertEqual(DEFAULT_THRESHOLDS["triggered"], 1.0)
        self.assertEqual(DEFAULT_THRESHOLDS["crisis"], 1.5)
        self.assertEqual(DEFAULT_THRESHOLDS["emergency"], 2.0)

    def test_get_drive_thresholds_with_global(self):
        """Global thresholds should apply to drive's base threshold."""
        drive = {"threshold": 20.0}
        global_thresholds = DEFAULT_THRESHOLDS.copy()

        thresholds = get_drive_thresholds(drive, global_thresholds)

        self.assertEqual(thresholds["available"], 6.0)  # 20 * 0.30
        self.assertEqual(thresholds["elevated"], 15.0)  # 20 * 0.75
        self.assertEqual(thresholds["triggered"], 20.0)  # 20 * 1.0
        self.assertEqual(thresholds["crisis"], 30.0)  # 20 * 1.5
        self.assertEqual(thresholds["emergency"], 40.0)  # 20 * 2.0

    def test_get_drive_thresholds_per_drive_override(self):
        """Drive-specific thresholds override global config."""
        drive = {
            "threshold": 20.0,
            "thresholds": {
                "available": 5.0,
                "elevated": 12.0,
                "triggered": 18.0,
                "crisis": 28.0,
                "emergency": 35.0,
            },
        }
        global_thresholds = DEFAULT_THRESHOLDS.copy()

        thresholds = get_drive_thresholds(drive, global_thresholds)

        # Should use drive-specific values, not global
        self.assertEqual(thresholds["available"], 5.0)
        self.assertEqual(thresholds["elevated"], 12.0)
        self.assertEqual(thresholds["triggered"], 18.0)

    def test_get_drive_thresholds_backward_compat(self):
        """Single threshold without global config uses default ratios."""
        drive = {"threshold": 20.0}

        thresholds = get_drive_thresholds(drive, None)

        # Should apply default ratios to base threshold
        self.assertEqual(thresholds["triggered"], 20.0)  # 20 * 1.0
        self.assertEqual(thresholds["elevated"], 15.0)  # 20 * 0.75
        self.assertEqual(thresholds["available"], 6.0)  # 20 * 0.30


class TestThresholdLabels(unittest.TestCase):
    """Test threshold label calculation."""

    def test_available_label(self):
        """Pressure below 'available' threshold."""
        thresholds = {
            "available": 6.0,
            "elevated": 15.0,
            "triggered": 20.0,
            "crisis": 30.0,
            "emergency": 40.0,
        }

        label = get_threshold_label(5.0, thresholds)
        self.assertEqual(label, "available")

    def test_elevated_label(self):
        """Pressure at/above 'elevated', below 'triggered'."""
        thresholds = {
            "available": 6.0,
            "elevated": 15.0,
            "triggered": 20.0,
            "crisis": 30.0,
            "emergency": 40.0,
        }

        # At elevated boundary
        self.assertEqual(get_threshold_label(15.0, thresholds), "elevated")

        # Between elevated and triggered
        self.assertEqual(get_threshold_label(18.0, thresholds), "elevated")

        # Just below triggered
        self.assertEqual(get_threshold_label(19.9, thresholds), "elevated")

    def test_triggered_label(self):
        """Pressure at/above 'triggered', below 'crisis'."""
        thresholds = {
            "available": 6.0,
            "elevated": 15.0,
            "triggered": 20.0,
            "crisis": 30.0,
            "emergency": 40.0,
        }

        # At triggered boundary
        self.assertEqual(get_threshold_label(20.0, thresholds), "triggered")

        # Between triggered and crisis
        self.assertEqual(get_threshold_label(25.0, thresholds), "triggered")

    def test_crisis_label(self):
        """Pressure at/above 'crisis', below 'emergency'."""
        thresholds = {
            "available": 6.0,
            "elevated": 15.0,
            "triggered": 20.0,
            "crisis": 30.0,
            "emergency": 40.0,
        }

        # At crisis boundary
        self.assertEqual(get_threshold_label(30.0, thresholds), "crisis")

        # Between crisis and emergency
        self.assertEqual(get_threshold_label(35.0, thresholds), "crisis")

    def test_emergency_label(self):
        """Pressure at/above 'emergency'."""
        thresholds = {
            "available": 6.0,
            "elevated": 15.0,
            "triggered": 20.0,
            "crisis": 30.0,
            "emergency": 40.0,
        }

        # At emergency boundary
        self.assertEqual(get_threshold_label(40.0, thresholds), "emergency")

        # Well above emergency
        self.assertEqual(get_threshold_label(50.0, thresholds), "emergency")


class TestCheckThresholdsWithGraduated(unittest.TestCase):
    """Test threshold checking with graduated system."""

    def test_triggers_at_triggered_level(self):
        """Drive at 'triggered' threshold should trigger."""
        state = create_default_state()
        config = {
            "drives": {
                "quiet_hours": None,
                "thresholds": DEFAULT_THRESHOLDS.copy(),
            }
        }

        # CARE base threshold is 20.0, so triggered = 20.0 * 1.0 = 20.0
        state["drives"]["CARE"]["pressure"] = 20.0

        triggered = check_thresholds(state, config)

        self.assertIn("CARE", triggered)

    def test_no_trigger_at_elevated(self):
        """Drive at 'elevated' (75%) should not trigger."""
        state = create_default_state()
        config = {
            "drives": {
                "quiet_hours": None,
                "thresholds": DEFAULT_THRESHOLDS.copy(),
            }
        }

        # CARE base threshold is 20.0, so elevated = 20.0 * 0.75 = 15.0
        state["drives"]["CARE"]["pressure"] = 15.0

        triggered = check_thresholds(state, config)

        self.assertNotIn("CARE", triggered)

    def test_triggers_at_crisis(self):
        """Drive at 'crisis' (150%) should trigger (it's > triggered)."""
        state = create_default_state()
        config = {
            "drives": {
                "quiet_hours": None,
                "thresholds": DEFAULT_THRESHOLDS.copy(),
            }
        }

        # CARE base threshold is 20.0, so crisis = 20.0 * 1.5 = 30.0
        state["drives"]["CARE"]["pressure"] = 30.0

        triggered = check_thresholds(state, config)

        self.assertIn("CARE", triggered)

    def test_per_drive_threshold_override(self):
        """Drive-specific thresholds override global."""
        state = create_default_state()

        # Custom thresholds for CARE
        state["drives"]["CARE"]["thresholds"] = {
            "available": 5.0,
            "elevated": 12.0,
            "triggered": 18.0,  # Lower than default 20.0
            "crisis": 28.0,
            "emergency": 35.0,
        }

        config = {
            "drives": {
                "quiet_hours": None,
                "thresholds": DEFAULT_THRESHOLDS.copy(),
            }
        }

        # Pressure at 18.0 should trigger with custom threshold
        state["drives"]["CARE"]["pressure"] = 18.0

        triggered = check_thresholds(state, config)

        self.assertIn("CARE", triggered)


class TestDriveStatusWithGraduated(unittest.TestCase):
    """Test drive status with graduated thresholds."""

    def test_status_available(self):
        """Status at 'available' level."""
        state = create_default_state()
        config = {
            "drives": {
                "thresholds": DEFAULT_THRESHOLDS.copy(),
            }
        }

        # CARE threshold is 20.0, available = 6.0
        state["drives"]["CARE"]["pressure"] = 5.0

        status = get_drive_status(state, "CARE", config)

        self.assertEqual(status["status"], "available")
        self.assertEqual(status["threshold_label"], "available")

    def test_status_elevated(self):
        """Status at 'elevated' level."""
        state = create_default_state()
        config = {
            "drives": {
                "thresholds": DEFAULT_THRESHOLDS.copy(),
            }
        }

        # CARE threshold is 20.0, elevated = 15.0
        state["drives"]["CARE"]["pressure"] = 16.0

        status = get_drive_status(state, "CARE", config)

        self.assertEqual(status["status"], "elevated")

    def test_status_triggered_by_level(self):
        """Status at 'triggered' level."""
        state = create_default_state()
        config = {
            "drives": {
                "thresholds": DEFAULT_THRESHOLDS.copy(),
            }
        }

        # CARE threshold is 20.0, triggered = 20.0
        state["drives"]["CARE"]["pressure"] = 20.0

        status = get_drive_status(state, "CARE", config)

        self.assertEqual(status["status"], "triggered")

    def test_status_crisis(self):
        """Status at 'crisis' level."""
        state = create_default_state()
        config = {
            "drives": {
                "thresholds": DEFAULT_THRESHOLDS.copy(),
            }
        }

        # CARE threshold is 20.0, crisis = 30.0
        state["drives"]["CARE"]["pressure"] = 30.0
        state["triggered_drives"] = []  # Not yet in triggered list

        status = get_drive_status(state, "CARE", config)

        self.assertEqual(status["status"], "crisis")

    def test_status_emergency(self):
        """Status at 'emergency' level."""
        state = create_default_state()
        config = {
            "drives": {
                "thresholds": DEFAULT_THRESHOLDS.copy(),
            }
        }

        # CARE threshold is 20.0, emergency = 40.0
        state["drives"]["CARE"]["pressure"] = 40.0
        state["triggered_drives"] = []

        status = get_drive_status(state, "CARE", config)

        self.assertEqual(status["status"], "emergency")

    def test_status_includes_thresholds_dict(self):
        """Status should include full thresholds dict."""
        state = create_default_state()
        config = {
            "drives": {
                "thresholds": DEFAULT_THRESHOLDS.copy(),
            }
        }

        status = get_drive_status(state, "CARE", config)

        self.assertIn("thresholds", status)
        self.assertIn("available", status["thresholds"])
        self.assertIn("elevated", status["thresholds"])
        self.assertIn("triggered", status["thresholds"])
        self.assertIn("crisis", status["thresholds"])
        self.assertIn("emergency", status["thresholds"])

    def test_status_triggered_flag_overrides_level(self):
        """If drive in triggered_drives list, status is 'triggered'."""
        state = create_default_state()
        config = {
            "drives": {
                "thresholds": DEFAULT_THRESHOLDS.copy(),
            }
        }

        # Set pressure to 'elevated' level
        state["drives"]["CARE"]["pressure"] = 16.0

        # But mark as triggered
        state["triggered_drives"] = ["CARE"]

        status = get_drive_status(state, "CARE", config)

        # Should show 'triggered' even though pressure is at 'elevated'
        self.assertEqual(status["status"], "triggered")


class TestBackwardCompatibility(unittest.TestCase):
    """Test backward compatibility with single-threshold configs."""

    def test_single_threshold_still_works(self):
        """Old configs with just 'threshold' field work."""
        state = create_default_state()

        # No graduated thresholds, just old single threshold
        state["drives"]["CARE"]["pressure"] = 20.0
        # CARE default threshold is 20.0

        config = {
            "drives": {
                "quiet_hours": None,
                # No thresholds config
            }
        }

        triggered = check_thresholds(state, config)

        # Should trigger at 100% of old threshold
        self.assertIn("CARE", triggered)

    def test_single_threshold_maps_to_triggered(self):
        """Single threshold becomes 'triggered' level."""
        drive = {"threshold": 20.0}

        thresholds = get_drive_thresholds(drive, None)

        # Single threshold 20.0 becomes triggered level
        self.assertEqual(thresholds["triggered"], 20.0)

        # Other levels calculated from default ratios
        self.assertEqual(thresholds["elevated"], 15.0)  # 20 * 0.75
        self.assertEqual(thresholds["crisis"], 30.0)  # 20 * 1.5

    def test_status_without_config(self):
        """get_drive_status works without config."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 16.0

        # No config passed
        status = get_drive_status(state, "CARE", None)

        self.assertIsNotNone(status)
        self.assertEqual(status["status"], "elevated")


class TestThresholdConfiguration(unittest.TestCase):
    """Test configuration loading and validation."""

    def test_global_thresholds_in_config(self):
        """Config can specify global thresholds."""
        config = {
            "drives": {
                "thresholds": {
                    "available": 0.25,
                    "elevated": 0.70,
                    "triggered": 1.0,
                    "crisis": 1.6,
                    "emergency": 2.2,
                }
            }
        }

        drive = {"threshold": 20.0}
        global_thresholds = config["drives"]["thresholds"]

        thresholds = get_drive_thresholds(drive, global_thresholds)

        self.assertEqual(thresholds["available"], 5.0)  # 20 * 0.25
        self.assertEqual(thresholds["elevated"], 14.0)  # 20 * 0.70
        self.assertEqual(thresholds["crisis"], 32.0)  # 20 * 1.6

    def test_partial_global_thresholds(self):
        """Partial global thresholds fill from defaults."""
        # This test documents current behavior - may want to improve
        config = {
            "drives": {
                "thresholds": {
                    "triggered": 1.0,
                    "crisis": 1.8,
                }
            }
        }

        drive = {"threshold": 20.0}
        global_thresholds = config["drives"]["thresholds"]

        # Currently just uses what's there
        thresholds = get_drive_thresholds(drive, global_thresholds)

        self.assertEqual(thresholds["triggered"], 20.0)
        self.assertEqual(thresholds["crisis"], 36.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
