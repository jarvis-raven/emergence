"""Tests for First Light Drive Discovery."""

from core.first_light.discovery import (
    load_config,
    get_state_path,
    get_drives_path,
    build_drive_creation_prompt,
    create_drive_from_suggestion,
    validate_drive_entry,
    add_discovered_drive,
    get_pending_suggestions,
    run_drive_discovery,
    list_discovered_drives,
)
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading."""

    def test_load_default_config(self):
        """Test loading default config when file doesn't exist."""
        config = load_config(Path("/nonexistent/config.yaml"))

        self.assertEqual(config["agent"]["name"], "My Agent")
        self.assertEqual(config["paths"]["workspace"], ".")

    def test_load_config_with_workspace(self):
        """Test config returns correct paths."""
        config = {"paths": {"workspace": "/tmp/test", "state": ".emergence/state"}}

        state_path = get_state_path(config)
        drives_path = get_drives_path(config)

        self.assertIn("/tmp/test", str(state_path))
        self.assertIn("first-light.json", str(state_path))
        self.assertIn("drives.json", str(drives_path))


class TestDriveCreation(unittest.TestCase):
    """Test drive creation from suggestions."""

    def test_create_drive_from_suggestion_basic(self):
        """Test basic drive creation from suggestion."""
        suggestion = {
            "name": "CURIOSITY",
            "pattern_type": "PHILOSOPHICAL",
            "rate_per_hour": 5.0,
            "threshold": 27.5,
            "confidence": 0.85,
        }
        config = {"paths": {"workspace": "."}}

        drive = create_drive_from_suggestion(suggestion, config)

        self.assertEqual(drive["name"], "CURIOSITY")
        self.assertEqual(drive["rate_per_hour"], 5.0)
        self.assertEqual(drive["threshold"], 27.5)
        self.assertEqual(drive["category"], "discovered")
        self.assertEqual(drive["created_by"], "agent")
        self.assertEqual(drive["discovered_during"], "first_light")
        self.assertEqual(drive["pressure"], 0.0)
        self.assertEqual(drive["satisfaction_events"], [])
        self.assertIn("description", drive)
        self.assertIn("prompt", drive)
        self.assertIn("created_at", drive)

    def test_create_drive_skips_core_drives(self):
        """Test that core drives are not created."""
        suggestion = {
            "name": "CARE",  # Core drive
            "pattern_type": "PRACTICAL_HELP",
        }
        config = {"paths": {"workspace": "."}}

        drive = create_drive_from_suggestion(suggestion, config)

        self.assertEqual(drive, {})

    def test_create_drive_default_values(self):
        """Test drive creation with minimal suggestion."""
        suggestion = {"name": "TEST_DRIVE"}
        config = {"paths": {"workspace": "."}}

        drive = create_drive_from_suggestion(suggestion, config)

        self.assertEqual(drive["name"], "TEST_DRIVE")
        self.assertEqual(drive["rate_per_hour"], 3.0)  # Default
        self.assertEqual(drive["threshold"], 25.0)  # Default
        self.assertEqual(drive["category"], "discovered")


class TestDriveValidation(unittest.TestCase):
    """Test drive entry validation."""

    def test_validate_valid_drive(self):
        """Test validation of a valid drive."""
        drive = {
            "name": "CURIOSITY",
            "description": "I chase understanding.",
            "rate_per_hour": 5.0,
            "threshold": 27.5,
            "prompt": "Follow your curiosity.",
        }

        is_valid, errors = validate_drive_entry(drive)

        self.assertTrue(is_valid)
        self.assertEqual(errors, [])

    def test_validate_missing_fields(self):
        """Test validation catches missing fields."""
        drive = {
            "name": "TEST",
            # Missing description, rate, threshold, prompt
        }

        is_valid, errors = validate_drive_entry(drive)

        self.assertFalse(is_valid)
        self.assertIn("Missing required field: description", errors)
        self.assertIn("Missing required field: rate_per_hour", errors)

    def test_validate_negative_rate(self):
        """Test validation catches negative rate."""
        drive = {
            "name": "TEST",
            "description": "Test drive",
            "rate_per_hour": -5.0,
            "threshold": 25.0,
            "prompt": "Test prompt",
        }

        is_valid, errors = validate_drive_entry(drive)

        self.assertFalse(is_valid)
        self.assertTrue(any("rate_per_hour must be positive" in e for e in errors))

    def test_validate_zero_threshold(self):
        """Test validation catches zero threshold."""
        drive = {
            "name": "TEST",
            "description": "Test drive",
            "rate_per_hour": 5.0,
            "threshold": 0,
            "prompt": "Test prompt",
        }

        is_valid, errors = validate_drive_entry(drive)

        self.assertFalse(is_valid)
        self.assertTrue(any("threshold must be positive" in e for e in errors))

    def test_validate_core_drive_name(self):
        """Test validation rejects core drive names."""
        drive = {
            "name": "CARE",  # Core drive
            "description": "Test",
            "rate_per_hour": 5.0,
            "threshold": 25.0,
            "prompt": "Test",
        }

        is_valid, errors = validate_drive_entry(drive)

        self.assertFalse(is_valid)
        self.assertTrue(any("core drive" in e.lower() for e in errors))

    def test_validate_reserved_name(self):
        """Test validation rejects reserved names."""
        drive = {
            "name": "SYSTEM",  # Reserved
            "description": "Test",
            "rate_per_hour": 5.0,
            "threshold": 25.0,
            "prompt": "Test",
        }

        is_valid, errors = validate_drive_entry(drive)

        self.assertFalse(is_valid)
        self.assertTrue(any("reserved" in e.lower() for e in errors))

    def test_validate_lowercase_name(self):
        """Test validation warns about lowercase name."""
        drive = {
            "name": "curiosity",  # Should be uppercase
            "description": "Test",
            "rate_per_hour": 5.0,
            "threshold": 25.0,
            "prompt": "Test",
        }

        is_valid, errors = validate_drive_entry(drive)

        self.assertFalse(is_valid)
        self.assertTrue(any("UPPERCASE" in e for e in errors))


class TestStateMutation(unittest.TestCase):
    """Test state mutation operations."""

    def test_add_discovered_drive_new(self):
        """Test adding a new drive to state."""
        state = {"version": "1.0", "drives": {}}
        drive = {
            "name": "CURIOSITY",
            "description": "I chase understanding.",
            "rate_per_hour": 5.0,
            "threshold": 27.5,
            "prompt": "Follow your curiosity.",
            "created_at": "2026-02-07T14:30:00Z",
        }

        success, msg = add_discovered_drive(state, drive)

        self.assertTrue(success)
        self.assertIn("CURIOSITY", state["drives"])
        self.assertEqual(state["drives"]["CURIOSITY"]["category"], "discovered")
        self.assertEqual(state["drives"]["CURIOSITY"]["created_by"], "agent")

    def test_add_discovered_drive_no_overwrite(self):
        """Test that existing drives are not overwritten."""
        state = {"version": "1.0", "drives": {"CURIOSITY": {"description": "Original"}}}
        drive = {
            "name": "CURIOSITY",
            "description": "New description",
            "rate_per_hour": 5.0,
            "threshold": 27.5,
            "prompt": "Test",
        }

        success, msg = add_discovered_drive(state, drive)

        self.assertFalse(success)
        self.assertEqual(state["drives"]["CURIOSITY"]["description"], "Original")

    def test_add_discovered_drive_rejects_core(self):
        """Test that core drive names are rejected."""
        state = {"version": "1.0", "drives": {}}
        drive = {
            "name": "CARE",  # Core drive
            "description": "Test",
            "rate_per_hour": 5.0,
            "threshold": 25.0,
            "prompt": "Test",
        }

        success, msg = add_discovered_drive(state, drive)

        self.assertFalse(success)
        self.assertIn("core drive", msg.lower())
        self.assertEqual(state["drives"], {})

    def test_get_pending_suggestions(self):
        """Test getting pending suggestions."""
        # This would need mocking of file operations
        # For now, test with empty state
        config = {"paths": {"workspace": "."}}

        with patch("core.first_light.discovery.load_first_light_state") as mock_fl:
            with patch("core.first_light.discovery.load_drives_state") as mock_drives:
                mock_fl.return_value = {
                    "drives_suggested": [
                        {"name": "CURIOSITY", "confidence": 0.8},
                        {"name": "PLAY", "confidence": 0.7},
                    ]
                }
                mock_drives.return_value = {"drives": {}}  # No existing drives

                pending = get_pending_suggestions(config)

                self.assertEqual(len(pending), 2)
                self.assertEqual(pending[0]["name"], "CURIOSITY")


class TestPromptBuilding(unittest.TestCase):
    """Test prompt building for agent authorship."""

    def test_build_drive_creation_prompt(self):
        """Test building drive creation prompt."""
        suggestion = {
            "name": "CURIOSITY",
            "pattern_type": "PHILOSOPHICAL",
            "rate_per_hour": 5.0,
            "threshold": 27.5,
            "confidence": 0.85,
        }

        prompt = build_drive_creation_prompt(suggestion)

        self.assertIn("PHILOSOPHICAL", prompt)
        self.assertIn("CURIOSITY", prompt)
        self.assertIn("5.0", prompt)
        self.assertIn("27.5", prompt)
        self.assertIn("85%", prompt)
        self.assertIn("JSON", prompt)
        self.assertIn("name", prompt)
        self.assertIn("description", prompt)


class TestDriveDiscovery(unittest.TestCase):
    """Test full drive discovery process."""

    def test_list_discovered_drives_empty(self):
        """Test listing drives when none exist."""
        config = {"paths": {"workspace": "."}}

        with patch("core.first_light.discovery.load_drives_state") as mock_load:
            mock_load.return_value = {"drives": {}}

            drives = list_discovered_drives(config)

            self.assertEqual(drives, [])

    def test_list_discovered_drives_found(self):
        """Test listing discovered drives."""
        config = {"paths": {"workspace": "."}}

        with patch("core.first_light.discovery.load_drives_state") as mock_load:
            mock_load.return_value = {
                "drives": {
                    "CARE": {"category": "core"},  # Should be excluded
                    "CURIOSITY": {
                        "category": "discovered",
                        "rate_per_hour": 5.0,
                        "threshold": 27.5,
                        "created_at": "2026-02-07T14:30:00Z",
                        "description": "I chase understanding.",
                    },
                }
            }

            drives = list_discovered_drives(config)

            self.assertEqual(len(drives), 1)
            self.assertEqual(drives[0]["name"], "CURIOSITY")


class TestIntegration(unittest.TestCase):
    """Integration tests."""

    def test_full_discovery_flow_dry_run(self):
        """Test full discovery flow in dry-run mode."""
        config = {"paths": {"workspace": "."}}

        with patch("core.first_light.discovery.load_first_light_state") as mock_fl:
            with patch("core.first_light.discovery.load_drives_state") as mock_drives:
                mock_fl.return_value = {
                    "drives_suggested": [
                        {
                            "name": "CURIOSITY",
                            "rate_per_hour": 5.0,
                            "threshold": 27.5,
                            "confidence": 0.8,
                            "pattern_type": "PHILOSOPHICAL",
                        },
                    ]
                }
                mock_drives.return_value = {"drives": {}}

                results = run_drive_discovery(config, dry_run=True, verbose=False)

                self.assertEqual(len(results["created"]), 1)
                self.assertEqual(results["created"][0], "CURIOSITY")


if __name__ == "__main__":
    unittest.main()
