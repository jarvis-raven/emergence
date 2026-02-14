"""Unit tests for configuration loading.

Tests comment stripping, config merging, validation, and path resolution.
"""

import sys
import os
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

# Import from the package
from core.drives.config import (
    strip_comments,
    load_config,
    validate_config,
    get_state_path,
    DEFAULT_CONFIG,
    find_config,
)


class TestStripComments(unittest.TestCase):
    """Test JSON comment stripping."""
    
    def test_strip_line_comments(self):
        """Lines starting with // should be stripped."""
        content = '''{
// This is a comment
"key": "value"
}'''
        result = strip_comments(content)
        self.assertNotIn("// This is a comment", result)
        self.assertIn('"key": "value"', result)
    
    def test_strip_hash_comments(self):
        """Lines starting with # should be stripped."""
        content = '''{
# Hash comment
"key": "value"
}'''
        result = strip_comments(content)
        self.assertNotIn("# Hash comment", result)
        self.assertIn('"key": "value"', result)
    
    def test_preserve_inline_content(self):
        """Content after values on same line should be preserved."""
        content = '{"key": "value" // not stripped}'
        result = strip_comments(content)
        # Inline comments after content are NOT stripped (this is intentional)
        self.assertIn("value", result)
    
    def test_strip_leading_whitespace_comments(self):
        """Comments with leading whitespace should be stripped."""
        content = '''{
    // Indented comment
    "key": "value"
}'''
        result = strip_comments(content)
        self.assertNotIn("// Indented comment", result)
        self.assertIn('"key": "value"', result)
    
    def test_empty_content(self):
        """Empty content should return empty."""
        result = strip_comments("")
        self.assertEqual(result, "")
    
    def test_no_comments(self):
        """Content without comments should be unchanged."""
        content = '{"key": "value"}'
        result = strip_comments(content)
        self.assertEqual(result, content)


class TestLoadConfig(unittest.TestCase):
    """Test configuration loading and merging."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "emergence.json"
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_defaults_when_no_config(self):
        """Should return defaults when config file doesn't exist."""
        nonexistent = Path(self.temp_dir) / "nonexistent.json"
        config = load_config(nonexistent)
        
        self.assertEqual(config["agent"]["name"], DEFAULT_CONFIG["agent"]["name"])
    
    def test_load_valid_config(self):
        """Should load and parse valid JSON config."""
        test_config = {"agent": {"name": "Test Agent"}}
        with open(self.config_path, "w") as f:
            json.dump(test_config, f)
        
        config = load_config(self.config_path)
        
        self.assertEqual(config["agent"]["name"], "Test Agent")
    
    def test_merge_with_defaults(self):
        """Should merge loaded config with defaults for missing fields."""
        test_config = {"agent": {"name": "Test Agent"}}  # Only override name
        with open(self.config_path, "w") as f:
            json.dump(test_config, f)
        
        config = load_config(self.config_path)
        
        # Name should be from loaded config
        self.assertEqual(config["agent"]["name"], "Test Agent")
        # Model should still be from defaults
        self.assertEqual(config["agent"]["model"], DEFAULT_CONFIG["agent"]["model"])
    
    def test_strip_comments_before_parse(self):
        """Should strip comments before parsing JSON."""
        content = '''{
// Agent settings
"agent": {
"name": "Test Agent"
}
}'''
        with open(self.config_path, "w") as f:
            f.write(content)
        
        config = load_config(self.config_path)
        
        self.assertEqual(config["agent"]["name"], "Test Agent")
    
    def test_invalid_json_exits(self):
        """Should exit with error for invalid JSON."""
        with open(self.config_path, "w") as f:
            f.write('{"invalid json')  # Missing closing brace
        
        with self.assertRaises(SystemExit) as cm:
            load_config(self.config_path)
        
        self.assertEqual(cm.exception.code, 1)


class TestValidateConfig(unittest.TestCase):
    """Test configuration validation."""
    
    def test_valid_config(self):
        """Valid config should return empty error list."""
        config = {
            "agent": {"name": "Test"},
            "paths": {"workspace": "."},
            "drives": {"quiet_hours": [23, 7]}
        }
        errors = validate_config(config)
        self.assertEqual(errors, [])
    
    def test_missing_agent_section(self):
        """Missing agent section should error."""
        config = {}
        errors = validate_config(config)
        self.assertIn("Missing required section: agent", errors)
    
    def test_missing_agent_name(self):
        """Missing agent.name should error."""
        config = {"agent": {}}
        errors = validate_config(config)
        self.assertIn("Missing required field: agent.name", errors)
    
    def test_invalid_quiet_hours_format(self):
        """Invalid quiet_hours format should error."""
        config = {"agent": {"name": "Test"}, "drives": {"quiet_hours": [23]}}
        errors = validate_config(config)
        self.assertIn("quiet_hours must be a list of [start_hour, end_hour]", errors)
    
    def test_quiet_hours_out_of_range(self):
        """quiet_hours hours > 23 should error."""
        config = {"agent": {"name": "Test"}, "drives": {"quiet_hours": [25, 5]}}
        errors = validate_config(config)
        self.assertIn("quiet_hours hours must be between 0 and 23", errors)
    
    def test_tick_interval_too_small(self):
        """tick_interval < 60 should warn."""
        config = {"agent": {"name": "Test"}, "drives": {"tick_interval": 30}}
        errors = validate_config(config)
        self.assertIn("tick_interval should be at least 60 seconds", errors)
    
    def test_path_with_double_dots(self):
        """Paths with .. should error."""
        config = {
            "agent": {"name": "Test"},
            "paths": {"workspace": "../outside"}
        }
        errors = validate_config(config)
        self.assertTrue(any(".." in e for e in errors))


class TestGetStatePath(unittest.TestCase):
    """Test state path resolution."""
    
    def test_default_paths(self):
        """Should resolve default paths correctly."""
        config = {"paths": {}}
        path = get_state_path(config, "drives.json")
        
        self.assertIn("drives.json", str(path))
    
    def test_custom_state_dir(self):
        """Should use custom state directory."""
        config = {"paths": {"state": "custom/state", "workspace": "."}}
        path = get_state_path(config, "drives.json")
        
        self.assertIn("custom/state", str(path))
    
    def test_custom_filename(self):
        """Should use custom filename."""
        config = {"paths": {}}
        path = get_state_path(config, "custom.json")
        
        self.assertIn("custom.json", str(path))


class TestFindConfig(unittest.TestCase):
    """Test config file discovery."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.subdir = Path(self.temp_dir) / "subdir"
        self.subdir.mkdir()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_find_in_current_dir(self):
        """Should find config in current directory."""
        config_path = Path(self.temp_dir) / "emergence.json"
        with open(config_path, "w") as f:
            f.write('{}')
        
        found = find_config(Path(self.temp_dir))
        
        # Compare resolved paths (handles /private prefix on macOS)
        self.assertEqual(found.resolve(), config_path.resolve())
    
    def test_find_in_parent_dir(self):
        """Should find config in parent directory."""
        config_path = Path(self.temp_dir) / "emergence.json"
        with open(config_path, "w") as f:
            f.write('{}')
        
        found = find_config(self.subdir)
        
        # Compare resolved paths (handles /private prefix on macOS)
        self.assertEqual(found.resolve(), config_path.resolve())
    
    def test_not_found_returns_none(self):
        """Should return None when no config found."""
        # Patch environment to avoid finding workspace config
        with patch.dict(os.environ, {"OPENCLAW_WORKSPACE": "/nonexistent/workspace"}):
            # Also patch Path.home to avoid ~/.emergence fallback
            with patch.object(Path, "home", return_value=Path("/nonexistent")):
                found = find_config(self.subdir)
                self.assertIsNone(found)


class TestManualModeConfig(unittest.TestCase):
    """Test manual_mode configuration (issue #34)."""
    
    def test_default_config_has_manual_mode_false(self):
        """Default config should have manual_mode: false."""
        self.assertIn("manual_mode", DEFAULT_CONFIG["drives"])
        self.assertFalse(DEFAULT_CONFIG["drives"]["manual_mode"])
    
    def test_load_config_with_manual_mode_true(self):
        """Should parse manual_mode: true from config file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_content = {
                "agent": {"name": "Test"},
                "drives": {"manual_mode": True}
            }
            json.dump(config_content, f)
            temp_path = f.name
        
        try:
            config = load_config(Path(temp_path))
            self.assertTrue(config["drives"]["manual_mode"])
        finally:
            os.unlink(temp_path)
    
    def test_load_config_manual_mode_defaults_false(self):
        """Should default to false when not specified in config."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            config_content = {
                "agent": {"name": "Test"},
                "drives": {"tick_interval": 900}  # No manual_mode specified
            }
            json.dump(config_content, f)
            temp_path = f.name
        
        try:
            config = load_config(Path(temp_path))
            self.assertFalse(config["drives"]["manual_mode"])
        finally:
            os.unlink(temp_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
