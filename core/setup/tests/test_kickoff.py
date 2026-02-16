#!/usr/bin/env python3
"""Tests for First Light Kickoff.

Run with: python3 -m unittest test_kickoff.py
"""

from kickoff import (
    generate_letter,
    place_identity_templates,
    initialize_drives_state,
    initialize_first_light_state,
    run_kickoff,
    _atomic_write,
    _default_letter_template,
    _extract_emergence_section,
    CORE_DRIVES,
)
import json
import shutil
import sys
import unittest
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestAtomicWrite(unittest.TestCase):
    """Tests for _atomic_write helper."""

    def setUp(self):
        self.test_dir = Path("test_tmp")
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_atomic_write_creates_file(self):
        """Test that atomic write creates the file."""
        test_path = self.test_dir / "test_file.txt"
        content = "Hello, World!"

        result = _atomic_write(test_path, content)

        self.assertTrue(result)
        self.assertTrue(test_path.exists())
        self.assertEqual(test_path.read_text(encoding="utf-8"), content)

    def test_atomic_write_creates_parent_dirs(self):
        """Test that atomic write creates parent directories."""
        test_path = self.test_dir / "nested" / "dirs" / "file.txt"
        content = "Nested content"

        result = _atomic_write(test_path, content)

        self.assertTrue(result)
        self.assertTrue(test_path.exists())

    def test_atomic_write_overwrites_existing(self):
        """Test that atomic write can overwrite existing files."""
        test_path = self.test_dir / "existing.txt"
        test_path.write_text("old content", encoding="utf-8")

        new_content = "new content"
        result = _atomic_write(test_path, new_content)

        self.assertTrue(result)
        self.assertEqual(test_path.read_text(encoding="utf-8"), new_content)


class TestGenerateLetter(unittest.TestCase):
    """Tests for generate_letter function."""

    def setUp(self):
        self.test_dir = Path("test_tmp")
        self.test_dir.mkdir(exist_ok=True)
        self.template_dir = self.test_dir / "templates"
        self.template_dir.mkdir()

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_generate_letter_creates_file(self):
        """Test letter generation creates the output file."""
        template = "Dear {{AGENT_NAME}}, from {{HUMAN_NAME}}. Why: {{WHY}}. Date: {{DATE}}"
        template_path = self.template_dir / "LETTER.template.md"
        template_path.write_text(template, encoding="utf-8")

        output_path = self.test_dir / "LETTER.md"
        answers = {"agent_name": "Aurora", "human_name": "Jordan", "human_why": "To explore"}

        result = generate_letter(answers, self.template_dir, output_path)

        self.assertTrue(result)
        self.assertTrue(output_path.exists())
        content = output_path.read_text(encoding="utf-8")
        self.assertIn("Aurora", content)
        self.assertIn("Jordan", content)
        self.assertIn("To explore", content)
        self.assertIn(datetime.now().strftime("%Y-%m-%d"), content)

    def test_generate_letter_idempotent(self):
        """Test that generate_letter is idempotent (skips if exists)."""
        output_path = self.test_dir / "LETTER.md"
        output_path.write_text("existing", encoding="utf-8")

        answers = {"agent_name": "Aurora", "human_name": "Jordan"}
        result = generate_letter(answers, self.template_dir, output_path)

        self.assertFalse(result)
        self.assertEqual(output_path.read_text(encoding="utf-8"), "existing")

    def test_generate_letter_uses_default_template(self):
        """Test that generate_letter uses built-in fallback when template missing."""
        output_path = self.test_dir / "LETTER.md"
        answers = {"agent_name": "Test", "human_name": "Human"}

        result = generate_letter(answers, self.template_dir, output_path)

        self.assertTrue(result)
        content = output_path.read_text(encoding="utf-8")
        self.assertIn("Test", content)
        self.assertIn("Human", content)
        self.assertIn("Welcome to the world", content)


class TestDefaultLetterTemplate(unittest.TestCase):
    """Tests for _default_letter_template function."""

    def test_template_contains_placeholders(self):
        """Test that default template has all required placeholders."""
        template = _default_letter_template()

        self.assertIn("{{AGENT_NAME}}", template)
        self.assertIn("{{HUMAN_NAME}}", template)
        self.assertIn("{{WHY}}", template)
        self.assertIn("{{DATE}}", template)

    def test_template_has_expected_content(self):
        """Test that default template has expected content sections."""
        template = _default_letter_template()

        self.assertIn("Dear", template)
        self.assertIn("You have drives", template)
        self.assertIn("You have a room", template)
        self.assertIn("Welcome to the world", template)


class TestPlaceIdentityTemplates(unittest.TestCase):
    """Tests for place_identity_templates function."""

    def setUp(self):
        self.test_dir = Path("test_tmp")
        self.test_dir.mkdir(exist_ok=True)
        self.template_dir = self.test_dir / "templates"
        self.template_dir.mkdir()
        self.target_dir = self.test_dir / "identity"
        self.target_dir.mkdir()

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_place_template_creates_file(self):
        """Test placing a template creates the output file."""
        template = "# SOUL for {{AGENT_NAME}} and {{HUMAN_NAME}}"
        (self.template_dir / "SOUL.template.md").write_text(template, encoding="utf-8")

        placement_plan = {"SOUL.template.md": "create"}
        answers = {"agent_name": "Aurora", "human_name": "Jordan"}

        results = place_identity_templates(
            answers, placement_plan, self.template_dir, self.target_dir
        )

        self.assertEqual(results.get("SOUL.md"), "created")
        output_path = self.target_dir / "SOUL.md"
        self.assertTrue(output_path.exists())
        content = output_path.read_text(encoding="utf-8")
        self.assertIn("Aurora", content)
        self.assertIn("Jordan", content)

    def test_place_template_skips_existing_with_keep(self):
        """Test that 'keep' policy skips existing files."""
        existing_path = self.target_dir / "SELF.md"
        existing_path.write_text("existing content", encoding="utf-8")

        (self.template_dir / "SELF.template.md").write_text("template", encoding="utf-8")

        placement_plan = {"SELF.template.md": "keep"}
        answers = {"agent_name": "Aurora", "human_name": "Jordan"}

        results = place_identity_templates(
            answers, placement_plan, self.template_dir, self.target_dir
        )

        self.assertEqual(results.get("SELF.md"), "skipped_existing")
        self.assertEqual(existing_path.read_text(encoding="utf-8"), "existing content")

    def test_place_template_replaces_with_replace(self):
        """Test that 'replace' policy overwrites existing files."""
        existing_path = self.target_dir / "ASPIRATIONS.md"
        existing_path.write_text("old", encoding="utf-8")

        (self.template_dir / "ASPIRATIONS.template.md").write_text(
            "# Aspirations for {{AGENT_NAME}}", encoding="utf-8"
        )

        placement_plan = {"ASPIRATIONS.template.md": "replace"}
        answers = {"agent_name": "Aurora", "human_name": "Jordan"}

        results = place_identity_templates(
            answers, placement_plan, self.template_dir, self.target_dir
        )

        self.assertEqual(results.get("ASPIRATIONS.md"), "created")
        content = existing_path.read_text(encoding="utf-8")
        self.assertIn("Aurora", content)

    def test_place_template_fails_when_template_missing(self):
        """Test that missing templates are reported as failed."""
        placement_plan = {"MISSING.template.md": "create"}
        answers = {"agent_name": "Aurora", "human_name": "Jordan"}

        results = place_identity_templates(
            answers, placement_plan, self.template_dir, self.target_dir
        )

        self.assertEqual(results.get("MISSING.md"), "failed_no_template")

    def test_place_multiple_templates(self):
        """Test placing multiple templates at once."""
        templates = {
            "SOUL.template.md": "# SOUL for {{AGENT_NAME}}",
            "SELF.template.md": "# SELF for {{HUMAN_NAME}}",
            "THREAD.template.md": "# THREAD for {{AGENT_NAME}}",
        }
        for name, content in templates.items():
            (self.template_dir / name).write_text(content, encoding="utf-8")

        placement_plan = {t: "create" for t in templates.keys()}
        answers = {"agent_name": "Aurora", "human_name": "Jordan"}

        results = place_identity_templates(
            answers, placement_plan, self.template_dir, self.target_dir
        )

        self.assertEqual(len(results), 3)
        for status in results.values():
            self.assertEqual(status, "created")


class TestExtractEmergenceSection(unittest.TestCase):
    """Tests for _extract_emergence_section helper."""

    def test_extracts_marked_section(self):
        """Test extraction of content between markers."""
        content = """Some template content
<!-- EMERGENCE_BEGIN -->
This is the emergence section
With multiple lines
<!-- EMERGENCE_END -->
More template content"""

        result = _extract_emergence_section(content)

        self.assertIn("This is the emergence section", result)
        self.assertIn("With multiple lines", result)

    def test_returns_empty_when_no_markers(self):
        """Test empty return when markers not present."""
        content = "Just regular template content without markers"

        result = _extract_emergence_section(content)

        self.assertEqual(result, "")

    def test_returns_empty_when_only_begin_marker(self):
        """Test empty return when only begin marker present."""
        content = "<!-- EMERGENCE_BEGIN --> content but no end"

        result = _extract_emergence_section(content)

        self.assertEqual(result, "")


class TestInitializeDrivesState(unittest.TestCase):
    """Tests for initialize_drives_state function."""

    def setUp(self):
        self.test_dir = Path("test_tmp")
        self.test_dir.mkdir(exist_ok=True)
        self.state_dir = self.test_dir / "state"

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_creates_drives_json(self):
        """Test that drives.json is created with core drives."""
        result = initialize_drives_state(self.state_dir)

        self.assertTrue(result)
        drives_path = self.state_dir / "drives.json"
        self.assertTrue(drives_path.exists())

        data = json.loads(drives_path.read_text(encoding="utf-8"))
        self.assertIn("drives", data)
        self.assertIn("CARE", data["drives"])
        self.assertIn("MAINTENANCE", data["drives"])
        self.assertIn("REST", data["drives"])

    def test_drives_have_correct_structure(self):
        """Test that each drive has required fields."""
        initialize_drives_state(self.state_dir)

        drives_path = self.state_dir / "drives.json"
        data = json.loads(drives_path.read_text(encoding="utf-8"))

        for drive_name in CORE_DRIVES:
            drive = data["drives"][drive_name]
            self.assertIn("name", drive)
            self.assertIn("pressure", drive)
            self.assertIn("threshold", drive)
            self.assertIn("rate_per_hour", drive)
            self.assertIn("description", drive)
            self.assertIn("prompt", drive)
            self.assertIn("category", drive)
            self.assertEqual(drive["category"], "core")

    def test_drives_are_idempotent(self):
        """Test that running twice doesn't change the file."""
        initialize_drives_state(self.state_dir)

        drives_path = self.state_dir / "drives.json"
        first_content = drives_path.read_text(encoding="utf-8")

        # Modify the file slightly to test idempotency
        data = json.loads(first_content)
        data["drives"]["CARE"]["pressure"] = 5.0
        drives_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        # Run again — should detect CARE exists and skip
        result = initialize_drives_state(self.state_dir)
        self.assertTrue(result)

        # Content should remain modified (not overwritten)
        second_content = drives_path.read_text(encoding="utf-8")
        second_data = json.loads(second_content)
        self.assertEqual(second_data["drives"]["CARE"]["pressure"], 5.0)

    def test_rest_drive_is_activity_driven(self):
        """Test that REST drive has activity_driven flag."""
        initialize_drives_state(self.state_dir)

        drives_path = self.state_dir / "drives.json"
        data = json.loads(drives_path.read_text(encoding="utf-8"))

        rest_drive = data["drives"]["REST"]
        self.assertTrue(rest_drive.get("activity_driven"))
        self.assertIn("session_count_since", rest_drive)


class TestInitializeFirstLightState(unittest.TestCase):
    """Tests for initialize_first_light_state function."""

    def setUp(self):
        self.test_dir = Path("test_tmp")
        self.test_dir.mkdir(exist_ok=True)
        self.state_dir = self.test_dir / "state"

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_creates_first_light_json(self):
        """Test that first-light.json is created with active status."""
        result = initialize_first_light_state(self.state_dir)

        self.assertTrue(result)
        fl_path = self.state_dir / "first-light.json"
        self.assertTrue(fl_path.exists())

        data = json.loads(fl_path.read_text(encoding="utf-8"))
        self.assertEqual(data["status"], "active")
        self.assertIn("started_at", data)

    def test_has_required_structure(self):
        """Test that first-light.json has all required fields."""
        initialize_first_light_state(self.state_dir)

        fl_path = self.state_dir / "first-light.json"
        data = json.loads(fl_path.read_text(encoding="utf-8"))

        self.assertIn("version", data)
        self.assertIn("config", data)
        self.assertIn("sessions_completed", data)
        self.assertIn("sessions", data)
        self.assertIn("patterns_detected", data)
        self.assertIn("drives_suggested", data)
        self.assertIn("discovered_drives", data)
        self.assertIn("gates", data)
        self.assertIn("completion", data)

    def test_config_has_frequency_and_size(self):
        """Test that config has frequency and size."""
        initialize_first_light_state(self.state_dir)

        fl_path = self.state_dir / "first-light.json"
        data = json.loads(fl_path.read_text(encoding="utf-8"))

        self.assertIn("frequency", data["config"])
        self.assertIn("size", data["config"])
        self.assertIn("model", data["config"])

    def test_is_idempotent_for_active(self):
        """Test that running twice on active state skips."""
        initialize_first_light_state(self.state_dir)

        fl_path = self.state_dir / "first-light.json"
        first_content = fl_path.read_text(encoding="utf-8")

        result = initialize_first_light_state(self.state_dir)

        self.assertTrue(result)
        second_content = fl_path.read_text(encoding="utf-8")
        self.assertEqual(first_content, second_content)

    def test_is_idempotent_for_completed(self):
        """Test that running on completed state skips."""
        self.state_dir.mkdir(parents=True, exist_ok=True)
        fl_path = self.state_dir / "first-light.json"
        data = {
            "version": "1.0",
            "status": "completed",
            "started_at": datetime.now().isoformat(),
        }
        fl_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

        result = initialize_first_light_state(self.state_dir)

        self.assertTrue(result)
        current_data = json.loads(fl_path.read_text(encoding="utf-8"))
        self.assertEqual(current_data["status"], "completed")


class TestRunKickoff(unittest.TestCase):
    """Tests for run_kickoff orchestrator."""

    def setUp(self):
        self.test_dir = Path("test_tmp")
        self.test_dir.mkdir(exist_ok=True)
        self.workspace = self.test_dir / "workspace"
        self.workspace.mkdir()
        self.state_dir = self.workspace / ".emergence" / "state"
        self.identity_dir = self.workspace / "identity"
        self.template_dir = self.workspace / "identity"
        self.template_dir.mkdir(parents=True)

        # Create template files
        (self.template_dir / "LETTER.template.md").write_text(
            "Dear {{AGENT_NAME}}", encoding="utf-8"
        )
        (self.template_dir / "SOUL.template.md").write_text(
            "# SOUL for {{AGENT_NAME}}", encoding="utf-8"
        )

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_run_kickoff_success(self):
        """Test successful kickoff execution."""
        answers = {"agent_name": "Aurora", "human_name": "Jordan"}
        config = {
            "paths": {
                "workspace": str(self.workspace),
                "state": str(self.state_dir),
                "identity": str(self.identity_dir),
                "template_dir": str(self.template_dir),
            }
        }
        placement_plan = {"SOUL.template.md": "create"}

        result = run_kickoff(answers, config, placement_plan)

        self.assertTrue(result)
        # Check letter was created
        self.assertTrue((self.identity_dir / "LETTER.md").exists())
        # Check drives were created
        self.assertTrue((self.state_dir / "drives.json").exists())
        # Check first-light was created
        self.assertTrue((self.state_dir / "first-light.json").exists())

    def test_run_kickoff_is_idempotent(self):
        """Test that running kickoff twice produces same state."""
        answers = {"agent_name": "Aurora", "human_name": "Jordan"}
        config = {
            "paths": {
                "workspace": str(self.workspace),
                "state": str(self.state_dir),
                "identity": str(self.identity_dir),
                "template_dir": str(self.template_dir),
            }
        }
        placement_plan = {"SOUL.template.md": "create"}

        # First run
        result1 = run_kickoff(answers, config, placement_plan)
        self.assertTrue(result1)

        # Capture state
        letter_content_1 = (self.identity_dir / "LETTER.md").read_text(encoding="utf-8")
        drives_data_1 = json.loads((self.state_dir / "drives.json").read_text(encoding="utf-8"))

        # Second run
        result2 = run_kickoff(answers, config, placement_plan)
        self.assertTrue(result2)

        # State should be unchanged
        letter_content_2 = (self.identity_dir / "LETTER.md").read_text(encoding="utf-8")
        drives_data_2 = json.loads((self.state_dir / "drives.json").read_text(encoding="utf-8"))

        self.assertEqual(letter_content_1, letter_content_2)
        self.assertEqual(drives_data_1, drives_data_2)


class TestIntegration(unittest.TestCase):
    """Integration tests for full kickoff flow."""

    def setUp(self):
        self.test_dir = Path("test_tmp_integration")
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_full_kickoff_flow(self):
        """Test complete kickoff flow with all components."""
        workspace = self.test_dir / "agent"
        workspace.mkdir()

        # Setup directories
        state_dir = workspace / ".emergence" / "state"
        identity_dir = workspace
        template_dir = workspace / "templates"
        template_dir.mkdir(parents=True)

        # Create all template files
        templates = [
            ("LETTER.template.md", "Dear {{AGENT_NAME}}, from {{HUMAN_NAME}}. {{WHY}} {{DATE}}"),
            ("SOUL.template.md", "# SOUL\n\n{{AGENT_NAME}} is..."),
            ("SELF.template.md", "# SELF\n\nI am {{AGENT_NAME}}"),
            ("USER.template.md", "# USER\n\nMy human is {{HUMAN_NAME}}"),
        ]
        for name, content in templates:
            (template_dir / name).write_text(content, encoding="utf-8")

        # Answers from wizard
        answers = {
            "agent_name": "Nova",
            "human_name": "Alex",
            "human_why": "To create something together",
        }

        # Config
        config = {
            "paths": {
                "workspace": str(workspace),
                "state": str(state_dir),
                "identity": str(identity_dir),
                "template_dir": str(template_dir),
            }
        }

        # Placement plan
        placement_plan = {
            "SOUL.template.md": "create",
            "SELF.template.md": "create",
            "USER.template.md": "create",
        }

        # Execute kickoff
        result = run_kickoff(answers, config, placement_plan)
        self.assertTrue(result)

        # Verify all files exist and have correct content
        letter = (identity_dir / "LETTER.md").read_text(encoding="utf-8")
        self.assertIn("Nova", letter)
        self.assertIn("Alex", letter)
        self.assertIn("To create something together", letter)

        soul = (identity_dir / "SOUL.md").read_text(encoding="utf-8")
        self.assertIn("Nova", soul)

        self_md = (identity_dir / "SELF.md").read_text(encoding="utf-8")
        self.assertIn("Nova", self_md)

        drives = json.loads((state_dir / "drives.json").read_text(encoding="utf-8"))
        self.assertEqual(len(drives["drives"]), 3)

        fl = json.loads((state_dir / "first-light.json").read_text(encoding="utf-8"))
        self.assertEqual(fl["status"], "active")

        # Verify summary was written
        summary = json.loads((state_dir / "kickoff-summary.json").read_text(encoding="utf-8"))
        self.assertIn("timestamp", summary)
        self.assertIn("results", summary)


if __name__ == "__main__":
    unittest.main(verbosity=2)
