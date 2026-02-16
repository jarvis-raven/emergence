"""Tests for the flush prompt rendering system."""

from core.memory.flush_prompt import (
    render_flush_prompt,
    get_template_path,
    load_config,
    _get_memory_dir,
    _get_drives_cli,
    _simple_yaml_parse,
)
import json
import sys
import tempfile
import unittest
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))


class TestTemplateRendering(unittest.TestCase):
    """Test template rendering with various configurations."""

    def setUp(self):
        """Create temporary template file for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_path = Path(self.temp_dir.name)

        self.template_content = """# Memory Flush Prompt

File: `${memory_dir}/${session_date}.md`
Timezone: ${timezone}
Drives CLI: ${drives_cli}

Capture everything to ${memory_dir}.
"""
        self.template_file = self.temp_path / "test-template.md"
        self.template_file.write_text(self.template_content)

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_basic_template_substitution(self):
        """Test basic variable substitution works."""
        config = {"memory": {"flush_prompt_template": str(self.template_file)}}
        result = render_flush_prompt(config)

        self.assertIn("memory", result)
        self.assertIn("drives", result)
        # Check that default values are present
        self.assertIn("GMT", result)

    def test_custom_memory_dir(self):
        """Test custom memory directory from config."""
        config = {
            "memory": {
                "flush_prompt_template": str(self.template_file),
                "daily_dir": "custom/memory",
            }
        }
        result = render_flush_prompt(config)

        self.assertIn("custom/memory", result)

    def test_custom_session_date(self):
        """Test session date override parameter."""
        config = {"memory": {"flush_prompt_template": str(self.template_file)}}
        custom_date = "2025-12-25"

        result = render_flush_prompt(config, session_date=custom_date)

        self.assertIn("2025-12-25", result)

    def test_custom_timezone(self):
        """Test timezone override parameter."""
        config = {"memory": {"flush_prompt_template": str(self.template_file)}}
        custom_tz = "PST"

        result = render_flush_prompt(config, timezone=custom_tz)

        self.assertIn("PST", result)

    def test_all_variables_substituted(self):
        """Test that all template variables are replaced."""
        config = {
            "memory": {"flush_prompt_template": str(self.template_file), "daily_dir": "my_memory"},
            "paths": {"drives_cli": "my_drives"},
        }
        custom_date = "2026-01-15"
        custom_tz = "EST"

        result = render_flush_prompt(config, custom_date, custom_tz)

        # Verify no $variable patterns remain (all substituted)
        self.assertNotIn("${memory_dir}", result)
        self.assertNotIn("${session_date}", result)
        self.assertNotIn("${timezone}", result)
        self.assertNotIn("${drives_cli}", result)

        # Verify actual values are present
        self.assertIn("my_memory", result)
        self.assertIn("2026-01-15", result)
        self.assertIn("EST", result)
        self.assertIn("my_drives", result)


class TestDefaultValues(unittest.TestCase):
    """Test default values when config is missing or incomplete."""

    def test_default_memory_dir(self):
        """Test default memory directory is 'memory'."""
        result = _get_memory_dir({})
        self.assertEqual(result, "memory")

    def test_default_memory_dir_with_empty_config(self):
        """Test default with None config."""
        result = _get_memory_dir(None)
        self.assertEqual(result, "memory")

    def test_default_drives_cli(self):
        """Test default drives CLI is 'drives'."""
        result = _get_drives_cli({})
        self.assertEqual(result, "drives")

    def test_default_drives_cli_with_empty_config(self):
        """Test default with None config."""
        result = _get_drives_cli(None)
        self.assertEqual(result, "drives")

    def test_config_memory_dir_override(self):
        """Test config overrides default memory dir."""
        config = {"memory": {"daily_dir": "logs"}}
        result = _get_memory_dir(config)
        self.assertEqual(result, "logs")

    def test_config_drives_cli_override(self):
        """Test config overrides default drives CLI."""
        config = {"paths": {"drives_cli": "/usr/local/bin/drives"}}
        result = _get_drives_cli(config)
        self.assertEqual(result, "/usr/local/bin/drives")


class TestTemplatePathResolution(unittest.TestCase):
    """Test template path resolution logic."""

    def test_default_template_path(self):
        """Test default path is in same directory as module."""
        path = get_template_path({})
        self.assertEqual(path.name, "flush-prompt.template.md")

    def test_custom_template_path_absolute(self):
        """Test absolute path in config is used directly."""
        config = {"memory": {"flush_prompt_template": "/custom/path/template.md"}}
        path = get_template_path(config)
        self.assertEqual(str(path), "/custom/path/template.md")

    def test_custom_template_path_relative(self):
        """Test relative path is resolved against workspace."""
        config = {
            "memory": {"flush_prompt_template": "templates/my-template.md"},
            "paths": {"workspace": "/workspace"},
        }
        path = get_template_path(config)
        # Should be relative to workspace
        self.assertIn("templates/my-template.md", str(path))


class TestConfigLoading(unittest.TestCase):
    """Test configuration file loading."""

    def setUp(self):
        """Create temporary directory for config files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.original_cwd = Path.cwd()

    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()

    def test_load_json_config(self):
        """Test loading JSON config file."""
        config_path = Path(self.temp_dir.name) / "test.json"
        test_config = {"memory": {"daily_dir": "json_memory"}, "paths": {"workspace": "/test"}}
        config_path.write_text(json.dumps(test_config))

        result = load_config(config_path)

        self.assertEqual(result["memory"]["daily_dir"], "json_memory")

    def test_load_yaml_config(self):
        """Test loading YAML config file."""
        config_path = Path(self.temp_dir.name) / "test.yaml"
        yaml_content = """
memory:
  daily_dir: yaml_memory
paths:
  workspace: /test
"""
        config_path.write_text(yaml_content)

        result = load_config(config_path)

        self.assertEqual(result["memory"]["daily_dir"], "yaml_memory")

    def test_missing_config_returns_empty(self):
        """Test that missing config returns empty dict."""
        result = load_config("/nonexistent/path/config.yaml")
        self.assertEqual(result, {})

    def test_simple_yaml_parser_bools(self):
        """Test YAML parser handles booleans."""
        yaml_text = """
enabled: true
disabled: false
"""
        result = _simple_yaml_parse(yaml_text)
        self.assertEqual(result["enabled"], True)
        self.assertEqual(result["disabled"], False)

    def test_simple_yaml_parser_numbers(self):
        """Test YAML parser handles numbers."""
        yaml_text = """
port: 8765
rate: 3.5
count: 10
"""
        result = _simple_yaml_parse(yaml_text)
        self.assertEqual(result["port"], 8765)
        self.assertEqual(result["rate"], 3.5)
        self.assertEqual(result["count"], 10)

    def test_simple_yaml_parser_strings(self):
        """Test YAML parser handles quoted strings."""
        yaml_text = """
name: "Test Agent"
path: '/test/path'
"""
        result = _simple_yaml_parse(yaml_text)
        self.assertEqual(result["name"], "Test Agent")
        self.assertEqual(result["path"], "/test/path")


class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error handling."""

    def setUp(self):
        """Create temporary directory."""
        self.temp_dir = tempfile.TemporaryDirectory()

    def tearDown(self):
        """Clean up."""
        self.temp_dir.cleanup()

    def test_missing_template_raises_error(self):
        """Test that missing template file raises FileNotFoundError."""
        config = {"memory": {"flush_prompt_template": "/nonexistent/template.md"}}

        with self.assertRaises(FileNotFoundError):
            render_flush_prompt(config)

    def test_partial_substitution_with_safe_substitute(self):
        """Test that safe_substitute handles missing variables gracefully."""
        temp_path = Path(self.temp_dir.name) / "partial.md"
        # Template with an extra variable not in our substitution dict
        temp_path.write_text("Known: ${memory_dir}, Unknown: ${extra_var}")

        config = {"memory": {"flush_prompt_template": str(temp_path)}}
        result = render_flush_prompt(config)

        # Known variables should be substituted
        self.assertNotIn("${memory_dir}", result)
        # Unknown variables should remain (safe_substitute behavior)
        self.assertIn("${extra_var}", result)

    def test_empty_config_dict(self):
        """Test that empty config dict works."""
        result = _get_memory_dir({})
        self.assertEqual(result, "memory")


class TestIntegration(unittest.TestCase):
    """Integration tests with actual template file."""

    def test_actual_template_renders(self):
        """Test that the actual template file renders correctly."""
        # Find the actual template relative to this test
        test_dir = Path(__file__).parent
        memory_dir = test_dir.parent
        template_path = memory_dir / "flush-prompt.template.md"

        # Skip if template doesn't exist (should exist in real runs)
        if not template_path.exists():
            self.skipTest("Template file not found")

        config = {
            "memory": {"flush_prompt_template": str(template_path), "daily_dir": "test_memory"},
            "paths": {"drives_cli": "test_drives"},
        }

        result = render_flush_prompt(config, "2026-02-07", "GMT")

        # Verify core content is present
        self.assertIn("compaction boundary", result)
        self.assertIn("test_memory/2026-02-07.md", result)
        self.assertIn("test_drives", result)
        self.assertIn("Step 1", result)
        self.assertIn("Step 2", result)
        self.assertIn("Step 3", result)
        self.assertIn("Step 4", result)


if __name__ == "__main__":
    unittest.main()
