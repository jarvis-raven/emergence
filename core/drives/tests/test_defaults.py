"""Unit tests for core drive defaults loading and protection.

Tests loading from defaults.json, core drive protection,
human override merging, and state integrity enforcement.
"""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from core.drives.defaults import (
    load_core_drives,
    ensure_core_drives,
    is_core_drive,
    merge_human_overrides,
    get_core_drive_template,
    validate_core_overrides,
    get_defaults_path,
    CORE_DRIVE_NAMES,
    ALLOWED_OVERRIDE_FIELDS,
)
from core.drives.models import create_default_state


class TestLoadCoreDrives(unittest.TestCase):
    """Test loading core drive definitions from defaults.json."""

    def test_loads_all_three_core_drives(self):
        """All core drives should be loaded."""
        drives = load_core_drives()

        self.assertIn("CARE", drives)
        self.assertIn("MAINTENANCE", drives)
        self.assertIn("REST", drives)
        self.assertIn("WANDER", drives)
        self.assertEqual(len(drives), 4)

    def test_care_default_values(self):
        """CARE should have correct default values."""
        drives = load_core_drives()
        care = drives["CARE"]

        self.assertEqual(care["name"], "CARE")
        self.assertEqual(care["pressure"], 0.0)
        self.assertEqual(care["threshold"], 20.0)
        self.assertEqual(care["rate_per_hour"], 2.0)
        self.assertIn("relationship", care["description"].lower())
        self.assertEqual(care["category"], "core")
        self.assertEqual(care["created_by"], "system")
        self.assertEqual(care["activity_driven"], False)
        self.assertIsNone(care["discovered_during"])

    def test_maintenance_default_values(self):
        """MAINTENANCE should have correct default values."""
        drives = load_core_drives()
        maintenance = drives["MAINTENANCE"]

        self.assertEqual(maintenance["name"], "MAINTENANCE")
        self.assertEqual(maintenance["pressure"], 0.0)
        self.assertEqual(maintenance["threshold"], 25.0)
        self.assertEqual(maintenance["rate_per_hour"], 1.5)
        self.assertIn("health", maintenance["description"].lower())
        self.assertEqual(maintenance["category"], "core")
        self.assertEqual(maintenance["created_by"], "system")
        self.assertEqual(maintenance["activity_driven"], False)

    def test_rest_default_values(self):
        """REST should have correct default values (including activity_driven)."""
        drives = load_core_drives()
        rest = drives["REST"]

        self.assertEqual(rest["name"], "REST")
        self.assertEqual(rest["pressure"], 0.0)
        self.assertEqual(rest["threshold"], 30.0)
        self.assertEqual(rest["rate_per_hour"], 0.0)
        self.assertIn("recovery", rest["description"].lower())
        self.assertEqual(rest["category"], "core")
        self.assertEqual(rest["created_by"], "system")
        self.assertEqual(rest["activity_driven"], True)  # REST is activity-driven

    def test_all_drives_have_valid_prompt(self):
        """All core drives should have non-empty prompts."""
        drives = load_core_drives()

        for name, drive in drives.items():
            with self.subTest(drive=name):
                self.assertIn("prompt", drive)
                self.assertIsInstance(drive["prompt"], str)
                self.assertGreater(len(drive["prompt"]), 10)

    def test_load_from_custom_path(self):
        """Should be able to load from a custom path."""
        with TemporaryDirectory() as tmpdir:
            custom_path = Path(tmpdir) / "custom_defaults.json"
            test_data = {
                "drives": {
                    "CARE": {
                        "threshold": 15,
                        "rate_per_hour": 3.0,
                        "description": "Test description",
                        "prompt": "Test prompt",
                        "activity_driven": False,
                    }
                }
            }
            with open(custom_path, "w") as f:
                json.dump(test_data, f)

            drives = load_core_drives(custom_path)

            self.assertEqual(drives["CARE"]["threshold"], 15.0)
            self.assertEqual(drives["CARE"]["rate_per_hour"], 3.0)

    def test_missing_drives_section_raises(self):
        """Should raise ValueError if 'drives' section is missing."""
        with TemporaryDirectory() as tmpdir:
            bad_path = Path(tmpdir) / "bad_defaults.json"
            with open(bad_path, "w") as f:
                json.dump({"version": "1.0"}, f)

            with self.assertRaises(ValueError) as ctx:
                load_core_drives(bad_path)

            self.assertIn("missing 'drives' section", str(ctx.exception))


class TestIsCoreDrive(unittest.TestCase):
    """Test the is_core_drive() checker function."""

    def test_care_is_core(self):
        """CARE should be recognized as a core drive."""
        self.assertTrue(is_core_drive("CARE"))

    def test_maintenance_is_core(self):
        """MAINTENANCE should be recognized as a core drive."""
        self.assertTrue(is_core_drive("MAINTENANCE"))

    def test_rest_is_core(self):
        """REST should be recognized as a core drive."""
        self.assertTrue(is_core_drive("REST"))

    def test_discovered_drive_is_not_core(self):
        """Discovered drives should not be core."""
        self.assertFalse(is_core_drive("CURIOSITY"))
        self.assertFalse(is_core_drive("SOCIAL"))
        self.assertFalse(is_core_drive("CREATIVE"))

    def test_core_drive_names_constant(self):
        """CORE_DRIVE_NAMES should contain all core drives."""
        self.assertEqual(CORE_DRIVE_NAMES, {"CARE", "MAINTENANCE", "REST", "WANDER"})


class TestEnsureCoreDrives(unittest.TestCase):
    """Test the ensure_core_drives() state protection function."""

    def test_adds_missing_core_drives(self):
        """Missing core drives should be added to state."""
        state = create_default_state()
        del state["drives"]["CARE"]
        del state["drives"]["REST"]

        changed = ensure_core_drives(state)

        self.assertTrue(changed)
        self.assertIn("CARE", state["drives"])
        self.assertIn("REST", state["drives"])
        # MAINTENANCE should still be there
        self.assertIn("MAINTENANCE", state["drives"])

    def test_missing_drive_gets_zero_pressure(self):
        """Re-added drives should start at zero pressure."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 50.0
        del state["drives"]["CARE"]

        ensure_core_drives(state)

        self.assertEqual(state["drives"]["CARE"]["pressure"], 0.0)

    def test_restores_category_if_modified(self):
        """If category was changed, it should be restored to 'core'."""
        state = create_default_state()
        state["drives"]["CARE"]["category"] = "discovered"

        changed = ensure_core_drives(state)

        self.assertTrue(changed)
        self.assertEqual(state["drives"]["CARE"]["category"], "core")

    def test_restores_created_by_if_modified(self):
        """If created_by was changed, it should be restored to 'system'."""
        state = create_default_state()
        state["drives"]["MAINTENANCE"]["created_by"] = "agent"

        changed = ensure_core_drives(state)

        self.assertTrue(changed)
        self.assertEqual(state["drives"]["MAINTENANCE"]["created_by"], "system")

    def test_adds_missing_fields(self):
        """If fields are missing, they should be added from defaults."""
        state = create_default_state()
        # Simulate old/corrupted drive missing some fields
        state["drives"]["REST"] = {
            "name": "REST",
            "pressure": 5.0,
            "threshold": 30.0,
            # Missing other fields
        }

        changed = ensure_core_drives(state)

        self.assertTrue(changed)
        rest = state["drives"]["REST"]
        self.assertIn("description", rest)
        self.assertIn("prompt", rest)
        self.assertIn("category", rest)
        self.assertEqual(rest["category"], "core")

    def test_no_change_when_all_valid(self):
        """Should return False when all core drives are present and valid."""
        state = create_default_state()

        changed = ensure_core_drives(state)

        self.assertFalse(changed)

    def test_preserves_existing_pressure_for_valid_drives(self):
        """Existing valid drives should keep their pressure."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 15.0

        ensure_core_drives(state)

        self.assertEqual(state["drives"]["CARE"]["pressure"], 15.0)


class TestMergeHumanOverrides(unittest.TestCase):
    """Test merging human overrides from configuration."""

    def test_can_override_threshold(self):
        """Humans can override threshold."""
        defaults = load_core_drives()
        overrides = {"CARE": {"threshold": 15.0}}

        merged = merge_human_overrides(defaults, overrides)

        self.assertEqual(merged["CARE"]["threshold"], 15.0)
        self.assertEqual(merged["MAINTENANCE"]["threshold"], 25.0)  # Unchanged

    def test_can_override_rate_per_hour(self):
        """Humans can override rate_per_hour."""
        defaults = load_core_drives()
        overrides = {"MAINTENANCE": {"rate_per_hour": 3.0}}

        merged = merge_human_overrides(defaults, overrides)

        self.assertEqual(merged["MAINTENANCE"]["rate_per_hour"], 3.0)

    def test_can_override_prompt(self):
        """Humans can override prompt."""
        defaults = load_core_drives()
        overrides = {"REST": {"prompt": "Custom rest prompt"}}

        merged = merge_human_overrides(defaults, overrides)

        self.assertEqual(merged["REST"]["prompt"], "Custom rest prompt")

    def test_cannot_override_category(self):
        """Humans cannot override category (protected field)."""
        defaults = load_core_drives()
        overrides = {"CARE": {"category": "discovered"}}

        merged = merge_human_overrides(defaults, overrides)

        self.assertEqual(merged["CARE"]["category"], "core")

    def test_cannot_override_created_by(self):
        """Humans cannot override created_by (protected field)."""
        defaults = load_core_drives()
        overrides = {"MAINTENANCE": {"created_by": "human"}}

        merged = merge_human_overrides(defaults, overrides)

        self.assertEqual(merged["MAINTENANCE"]["created_by"], "system")

    def test_cannot_add_new_drive_via_override(self):
        """Unknown drives in overrides should be ignored."""
        defaults = load_core_drives()
        overrides = {"NEW_DRIVE": {"threshold": 10.0}}

        merged = merge_human_overrides(defaults, overrides)

        self.assertNotIn("NEW_DRIVE", merged)
        self.assertEqual(len(merged), 4)  # CARE, MAINTENANCE, REST, WANDER

    def test_multiple_overrides(self):
        """Multiple drive overrides should all be applied."""
        defaults = load_core_drives()
        overrides = {
            "CARE": {"threshold": 15.0},
            "MAINTENANCE": {"threshold": 20.0},
            "REST": {"threshold": 25.0},
        }

        merged = merge_human_overrides(defaults, overrides)

        self.assertEqual(merged["CARE"]["threshold"], 15.0)
        self.assertEqual(merged["MAINTENANCE"]["threshold"], 20.0)
        self.assertEqual(merged["REST"]["threshold"], 25.0)

    def test_does_not_modify_input_defaults(self):
        """Input defaults dict should not be modified."""
        defaults = load_core_drives()
        original_threshold = defaults["CARE"]["threshold"]
        overrides = {"CARE": {"threshold": 99.0}}

        merge_human_overrides(defaults, overrides)

        self.assertEqual(defaults["CARE"]["threshold"], original_threshold)

    def test_empty_overrides_returns_copy(self):
        """Empty overrides should return a copy of defaults."""
        defaults = load_core_drives()

        merged = merge_human_overrides(defaults, {})

        self.assertEqual(merged["CARE"]["threshold"], defaults["CARE"]["threshold"])
        self.assertIsNot(merged["CARE"], defaults["CARE"])  # Different objects


class TestGetCoreDriveTemplate(unittest.TestCase):
    """Test getting individual core drive templates."""

    def test_get_care_template(self):
        """Should return CARE template."""
        template = get_core_drive_template("CARE")

        self.assertIsNotNone(template)
        self.assertEqual(template["name"], "CARE")
        self.assertEqual(template["pressure"], 0.0)

    def test_get_returns_copy(self):
        """Should return a copy, not the original."""
        template1 = get_core_drive_template("CARE")
        template2 = get_core_drive_template("CARE")

        template1["pressure"] = 50.0

        self.assertEqual(template2["pressure"], 0.0)  # Unchanged

    def test_non_core_returns_none(self):
        """Should return None for non-core drives."""
        result = get_core_drive_template("CURIOSITY")

        self.assertIsNone(result)


class TestValidateCoreOverrides(unittest.TestCase):
    """Test validation of human overrides."""

    def test_valid_override_returns_empty(self):
        """Valid overrides should return empty error list."""
        overrides = {"CARE": {"threshold": 15.0}}

        errors = validate_core_overrides(overrides)

        self.assertEqual(errors, [])

    def test_unknown_drive_warning(self):
        """Unknown drives should generate warning."""
        overrides = {"UNKNOWN": {"threshold": 10.0}}

        errors = validate_core_overrides(overrides)

        self.assertEqual(len(errors), 1)
        self.assertIn("Unknown drive", errors[0])

    def test_protected_field_error(self):
        """Trying to override protected fields should generate error."""
        overrides = {"CARE": {"category": "discovered"}}

        errors = validate_core_overrides(overrides)

        self.assertEqual(len(errors), 1)
        self.assertIn("protected", errors[0].lower())

    def test_negative_value_error(self):
        """Negative numeric values should generate error."""
        overrides = {"CARE": {"threshold": -5.0}}

        errors = validate_core_overrides(overrides)

        self.assertEqual(len(errors), 1)
        self.assertIn("non-negative", errors[0])

    def test_zero_threshold_warning(self):
        """Zero threshold should generate warning (drive never triggers)."""
        overrides = {"CARE": {"threshold": 0.0}}

        errors = validate_core_overrides(overrides)

        self.assertEqual(len(errors), 1)
        self.assertIn("never triggers", errors[0])


class TestAllowedOverrideFields(unittest.TestCase):
    """Test the ALLOWED_OVERRIDE_FIELDS constant."""

    def test_contains_threshold(self):
        """Should allow threshold override."""
        self.assertIn("threshold", ALLOWED_OVERRIDE_FIELDS)

    def test_contains_rate_per_hour(self):
        """Should allow rate_per_hour override."""
        self.assertIn("rate_per_hour", ALLOWED_OVERRIDE_FIELDS)

    def test_contains_prompt(self):
        """Should allow prompt override."""
        self.assertIn("prompt", ALLOWED_OVERRIDE_FIELDS)

    def test_does_not_contain_category(self):
        """Should not allow category override."""
        self.assertNotIn("category", ALLOWED_OVERRIDE_FIELDS)

    def test_does_not_contain_created_by(self):
        """Should not allow created_by override."""
        self.assertNotIn("created_by", ALLOWED_OVERRIDE_FIELDS)


class TestDefaultsFileExists(unittest.TestCase):
    """Test that the actual defaults.json file exists and is valid."""

    def test_defaults_json_exists(self):
        """defaults.json should exist alongside defaults.py."""
        path = get_defaults_path()
        self.assertTrue(path.exists(), f"defaults.json not found at {path}")

    def test_defaults_json_is_valid_json(self):
        """defaults.json should be valid JSON."""
        path = get_defaults_path()
        with open(path, "r") as f:
            data = json.load(f)  # Should not raise

        self.assertIn("drives", data)

    def test_all_core_drives_in_defaults_json(self):
        """defaults.json should contain all three core drives."""
        path = get_defaults_path()
        with open(path, "r") as f:
            data = json.load(f)

        drives = data["drives"]
        self.assertIn("CARE", drives)
        self.assertIn("MAINTENANCE", drives)
        self.assertIn("REST", drives)


if __name__ == "__main__":
    unittest.main()
