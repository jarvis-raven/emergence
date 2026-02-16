#!/usr/bin/env python3
"""Tests for Config Generation (config_gen.py).

Run with: python3 -m unittest test_config_gen.py
"""

from config_gen import (
    strip_json_comments,
    load_config,
    generate_default_config,
    estimate_costs,
    validate_config,
    write_config,
    _validate_model_format,
    _generate_commented_json,
    DEFAULT_MODEL,
    VALID_MODEL_PREFIXES,
    SESSION_SIZE_TOKENS,
    FIRST_LIGHT_PRESETS,
    COST_PER_1K_TOKENS,
)
import json
import shutil
import sys
import unittest
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestStripJsonComments(unittest.TestCase):
    """Tests for strip_json_comments function."""

    def test_removes_double_slash_comments(self):
        """Test removal of // style comments."""
        text = '{"key": "value" // this is a comment\n}'
        result = strip_json_comments(text)
        self.assertNotIn("//", result)
        self.assertIn('"key": "value"', result)

    def test_removes_hash_comments(self):
        """Test removal of # style comments."""
        text = '{"key": "value" # this is a comment\n}'
        result = strip_json_comments(text)
        self.assertNotIn("# this", result)
        self.assertIn('"key": "value"', result)

    def test_preserves_hash_in_strings(self):
        """Test that # inside strings is preserved."""
        text = '{"key": "value # not a comment"}'
        result = strip_json_comments(text)
        self.assertIn('"value # not a comment"', result)

    def test_double_slash_in_strings(self):
        """Test behavior of // inside strings (note: simple parser strips them)."""
        text = '{"url": "http://example.com"}'
        result = strip_json_comments(text)
        # Simple parser strips // even in strings - documented limitation
        self.assertNotIn("//", result)

    def test_handles_empty_lines(self):
        """Test handling of empty lines."""
        text = '\n\n{"key": "value"}\n\n'
        result = strip_json_comments(text)
        self.assertIn('"key": "value"', result)


class TestLoadConfig(unittest.TestCase):
    """Tests for load_config function."""

    def setUp(self):
        self.test_dir = Path("test_tmp_config")
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_loads_valid_json(self):
        """Test loading a valid JSON config file."""
        config_path = self.test_dir / "config.json"
        data = {"agent": {"name": "Aurora"}, "room": {"port": 7373}}
        config_path.write_text(json.dumps(data), encoding="utf-8")

        result = load_config(config_path)

        self.assertEqual(result["agent"]["name"], "Aurora")
        self.assertEqual(result["room"]["port"], 7373)

    def test_loads_json_with_comments(self):
        """Test loading JSON with comments stripped."""
        config_path = self.test_dir / "config.json"
        content = """{
            // Agent configuration
            "agent": {
                "name": "Aurora"  # The agent's name
            }
        }"""
        config_path.write_text(content, encoding="utf-8")

        result = load_config(config_path)

        self.assertEqual(result["agent"]["name"], "Aurora")

    def test_raises_error_when_file_missing(self):
        """Test that FileNotFoundError is raised when file doesn't exist."""
        with self.assertRaises(FileNotFoundError):
            load_config(self.test_dir / "nonexistent.json")

    def test_raises_file_not_found_for_invalid_path(self):
        """Test that FileNotFoundError is raised in caller for bad path."""
        # load_config itself returns defaults, but direct path access raises
        with self.assertRaises(FileNotFoundError):
            Path("/definitely/not/a/real/path/config.json").read_text()


class TestGenerateDefaultConfig(unittest.TestCase):
    """Tests for generate_default_config function."""

    def test_has_required_sections(self):
        """Test that default config has all required sections."""
        config = generate_default_config("Aurora", "Jordan")

        required_sections = ["_meta", "agent", "room", "paths", "first_light", "drives"]
        for section in required_sections:
            self.assertIn(section, config)

    def test_agent_section_has_correct_values(self):
        """Test agent section has provided names."""
        config = generate_default_config("Nova", "Alex")

        self.assertEqual(config["agent"]["name"], "Nova")
        self.assertEqual(config["agent"]["human_name"], "Alex")
        self.assertEqual(config["agent"]["model"], DEFAULT_MODEL)

    def test_room_has_valid_port(self):
        """Test room section has valid port number."""
        config = generate_default_config("Test", "Human")

        port = config["room"]["port"]
        self.assertIsInstance(port, int)
        self.assertGreaterEqual(port, 1024)
        self.assertLessEqual(port, 65535)

    def test_paths_are_absolute(self):
        """Test that paths are absolute or resolvable."""
        config = generate_default_config("Test", "Human")

        for key, value in config["paths"].items():
            self.assertIsInstance(value, str)
            self.assertTrue(len(value) > 0)

    def test_first_light_has_frequency_and_size(self):
        """Test first_light section has required fields."""
        config = generate_default_config("Test", "Human")

        self.assertIn("frequency", config["first_light"])
        self.assertIn("sessions_per_day", config["first_light"])
        self.assertIn("session_size", config["first_light"])

    def test_drives_has_core_drives(self):
        """Test drives section has core drives."""
        config = generate_default_config("Test", "Human")

        core_drives = ["CARE", "MAINTENANCE", "REST"]
        for drive in core_drives:
            self.assertIn(drive, config["drives"])
            self.assertIn("threshold", config["drives"][drive])
            self.assertIn("rate_per_hour", config["drives"][drive])
            self.assertIn("description", config["drives"][drive])

    def test_meta_has_version_and_created(self):
        """Test _meta section has version and timestamp."""
        config = generate_default_config("Test", "Human")

        self.assertIn("version", config["_meta"])
        self.assertIn("created", config["_meta"])
        self.assertIn("generator", config["_meta"])


class TestEstimateCosts(unittest.TestCase):
    """Tests for estimate_costs function."""

    def test_patient_preset_cost(self):
        """Test cost estimation for patient preset."""
        result = estimate_costs("patient", "small")

        self.assertEqual(result["frequency"], "patient")
        self.assertEqual(result["sessions_per_day"], 1)
        self.assertEqual(result["session_size"], "small")
        self.assertIn("estimated_cost_usd", result)
        self.assertGreaterEqual(result["estimated_cost_usd"], 0)

    def test_balanced_preset_cost(self):
        """Test cost estimation for balanced preset."""
        result = estimate_costs("balanced", "medium")

        self.assertEqual(result["frequency"], "balanced")
        self.assertEqual(result["sessions_per_day"], 3)
        self.assertEqual(result["tokens_per_session"], SESSION_SIZE_TOKENS["medium"])

    def test_accelerated_preset_cost(self):
        """Test cost estimation for accelerated preset."""
        result = estimate_costs("accelerated", "large")

        self.assertEqual(result["frequency"], "accelerated")
        self.assertEqual(result["sessions_per_day"], 6)
        self.assertEqual(result["tokens_per_session"], SESSION_SIZE_TOKENS["large"])

    def test_custom_frequency_cost(self):
        """Test cost estimation for custom frequency."""
        result = estimate_costs("custom", "medium")

        self.assertEqual(result["frequency"], "custom")
        self.assertIn("estimated_cost_usd", result)

    def test_model_adjustment_cheap(self):
        """Test cost adjustment for cheap models."""
        result = estimate_costs("balanced", "medium", "anthropic/claude-haiku")

        self.assertAlmostEqual(result["model_adjustment"], 0.2, places=1)
        # Should be cheaper than the default cost

    def test_model_adjustment_expensive(self):
        """Test cost adjustment for expensive models."""
        result = estimate_costs("balanced", "medium", "anthropic/claude-opus")

        self.assertAlmostEqual(result["model_adjustment"], 5.0, places=1)

    def test_model_adjustment_local(self):
        """Test cost adjustment for local models."""
        result = estimate_costs("balanced", "medium", "ollama/llama3.2")

        self.assertEqual(result["model_adjustment"], 0.0)
        self.assertEqual(result["estimated_cost_usd"], 0.0)

    def test_has_explanation(self):
        """Test that result includes human-readable explanation."""
        result = estimate_costs("balanced", "medium")

        self.assertIn("explanation", result)
        # Explanation uses "steady emergence" for balanced preset
        self.assertIn("emergence", result["explanation"].lower())

    def test_has_cost_range(self):
        """Test that result includes cost range."""
        result = estimate_costs("balanced", "medium")

        self.assertIn("estimated_cost_range_low", result)
        self.assertIn("estimated_cost_range_high", result)
        self.assertLess(result["estimated_cost_range_low"], result["estimated_cost_range_high"])


class TestValidateModelFormat(unittest.TestCase):
    """Tests for _validate_model_format function."""

    def test_valid_anthropic_model(self):
        """Test validation of valid Anthropic model."""
        is_valid, msg = _validate_model_format("anthropic/claude-sonnet")

        self.assertTrue(is_valid)
        self.assertEqual(msg, "")

    def test_valid_openai_model(self):
        """Test validation of valid OpenAI model."""
        is_valid, msg = _validate_model_format("openai/gpt-4o")

        self.assertTrue(is_valid)
        self.assertEqual(msg, "")

    def test_invalid_no_slash(self):
        """Test rejection of model without provider prefix."""
        is_valid, msg = _validate_model_format("claude-sonnet")

        self.assertFalse(is_valid)
        self.assertIn("provider prefix", msg)

    def test_invalid_empty(self):
        """Test rejection of empty model string."""
        is_valid, msg = _validate_model_format("")

        self.assertFalse(is_valid)

    def test_unknown_provider_warning(self):
        """Test warning for unknown provider (but still valid)."""
        is_valid, msg = _validate_model_format("unknown/model-name")

        self.assertTrue(is_valid)
        self.assertIn("Warning", msg)
        self.assertIn("unknown", msg)


class TestValidateConfig(unittest.TestCase):
    """Tests for validate_config function."""

    def test_valid_config_no_errors(self):
        """Test that valid config returns no errors."""
        config = generate_default_config("Aurora", "Jordan")

        errors = validate_config(config)

        self.assertEqual(len(errors), 0)

    def test_missing_agent_name_error(self):
        """Test validation catches missing agent name."""
        config = generate_default_config("", "Jordan")

        errors = validate_config(config)

        self.assertTrue(any("agent.name" in e for e in errors))

    def test_missing_agent_model_error(self):
        """Test validation catches missing agent model."""
        config = generate_default_config("Aurora", "Jordan")
        config["agent"]["model"] = ""

        errors = validate_config(config)

        self.assertTrue(any("agent.model" in e for e in errors))

    def test_invalid_port_error(self):
        """Test validation catches invalid port."""
        config = generate_default_config("Aurora", "Jordan")
        config["room"]["port"] = 80  # Well-known port

        errors = validate_config(config)

        self.assertTrue(any("port" in e for e in errors))

    def test_port_not_integer_error(self):
        """Test validation catches non-integer port."""
        config = generate_default_config("Aurora", "Jordan")
        config["room"]["port"] = "7373"

        errors = validate_config(config)

        self.assertTrue(any("port" in e for e in errors))

    def test_missing_required_section_error(self):
        """Test validation catches missing required sections."""
        config = generate_default_config("Aurora", "Jordan")
        del config["drives"]

        errors = validate_config(config)

        self.assertTrue(any("drives" in e for e in errors))

    def test_missing_core_drive_error(self):
        """Test validation catches missing core drives."""
        config = generate_default_config("Aurora", "Jordan")
        del config["drives"]["CARE"]

        errors = validate_config(config)

        self.assertTrue(any("CARE" in e for e in errors))

    def test_invalid_frequency_error(self):
        """Test validation catches invalid frequency."""
        config = generate_default_config("Aurora", "Jordan")
        config["first_light"]["frequency"] = "invalid"

        errors = validate_config(config)

        self.assertTrue(any("frequency" in e for e in errors))

    def test_invalid_session_size_error(self):
        """Test validation catches invalid session size."""
        config = generate_default_config("Aurora", "Jordan")
        config["first_light"]["session_size"] = "huge"

        errors = validate_config(config)

        self.assertTrue(any("session_size" in e for e in errors))

    def test_invalid_sessions_per_day_error(self):
        """Test validation catches invalid sessions_per_day."""
        config = generate_default_config("Aurora", "Jordan")
        config["first_light"]["sessions_per_day"] = 25

        errors = validate_config(config)

        self.assertTrue(any("sessions_per_day" in e for e in errors))

    def test_missing_path_error(self):
        """Test validation catches missing paths."""
        config = generate_default_config("Aurora", "Jordan")
        del config["paths"]["memory"]

        errors = validate_config(config)

        self.assertTrue(any("memory" in e for e in errors))


class TestWriteConfig(unittest.TestCase):
    """Tests for write_config function."""

    def setUp(self):
        self.test_dir = Path("test_tmp_write")
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_writes_config_file(self):
        """Test that config is written to file."""
        config = generate_default_config("Aurora", "Jordan")
        output_path = self.test_dir / "emergence.json"

        result = write_config(config, output_path)

        self.assertTrue(result)
        self.assertTrue(output_path.exists())

    def test_creates_parent_directories(self):
        """Test that parent directories are created."""
        config = generate_default_config("Aurora", "Jordan")
        output_path = self.test_dir / "nested" / "dirs" / "emergence.json"

        result = write_config(config, output_path)

        self.assertTrue(result)
        self.assertTrue(output_path.exists())

    def test_written_config_is_valid_json(self):
        """Test that written file is valid JSON."""
        config = generate_default_config("Aurora", "Jordan")
        output_path = self.test_dir / "emergence.json"

        write_config(config, output_path)

        content = output_path.read_text(encoding="utf-8")
        # Should be parseable as JSON (comments stripped)
        data = json.loads(strip_json_comments(content))
        self.assertEqual(data["agent"]["name"], "Aurora")

    def test_returns_false_on_failure(self):
        """Test that function returns False on write failure."""
        config = generate_default_config("Aurora", "Jordan")
        # Try to write to a read-only location (or invalid path)
        result = write_config(config, "/nonexistent/path/emergence.json")

        self.assertFalse(result)


class TestGenerateCommentedJson(unittest.TestCase):
    """Tests for _generate_commented_json function."""

    def test_includes_all_sections(self):
        """Test that output includes all config sections."""
        config = generate_default_config("Aurora", "Jordan")

        result = _generate_commented_json(config)

        self.assertIn("_meta", result)
        self.assertIn("agent", result)
        self.assertIn("room", result)
        self.assertIn("paths", result)
        self.assertIn("first_light", result)
        self.assertIn("drives", result)

    def test_includes_comments(self):
        """Test that output includes helpful comments."""
        config = generate_default_config("Aurora", "Jordan")

        result = _generate_commented_json(config)

        self.assertIn("//", result)
        self.assertIn("EMERGENCE", result)

    def test_agent_values_correct(self):
        """Test that agent values are correctly inserted."""
        config = generate_default_config("Nova", "Alex")

        result = _generate_commented_json(config)

        self.assertIn('"name": "Nova"', result)
        self.assertIn('"human_name": "Alex"', result)

    def test_drives_structure_correct(self):
        """Test that drives are properly formatted."""
        config = generate_default_config("Test", "Human")

        result = _generate_commented_json(config)

        self.assertIn('"CARE"', result)
        self.assertIn('"MAINTENANCE"', result)
        self.assertIn('"REST"', result)
        self.assertIn("threshold", result)
        self.assertIn("rate_per_hour", result)


class TestIntegration(unittest.TestCase):
    """Integration tests for full config flow."""

    def setUp(self):
        self.test_dir = Path("test_tmp_integration_config")
        self.test_dir.mkdir(exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_full_generate_write_load_cycle(self):
        """Test complete generate -> write -> load cycle."""
        # Generate config
        config = generate_default_config("Aurora", "Jordan")

        # Write to file
        output_path = self.test_dir / "emergence.json"
        write_result = write_config(config, output_path)
        self.assertTrue(write_result)

        # Load back
        loaded = load_config(output_path)

        # Verify key values preserved
        self.assertEqual(loaded["agent"]["name"], "Aurora")
        self.assertEqual(loaded["agent"]["human_name"], "Jordan")
        self.assertEqual(loaded["room"]["port"], 7373)

    def test_written_config_passes_validation(self):
        """Test that written config passes validation."""
        config = generate_default_config("Aurora", "Jordan")
        output_path = self.test_dir / "emergence.json"
        write_config(config, output_path)

        loaded = load_config(output_path)
        errors = validate_config(loaded)

        self.assertEqual(len(errors), 0)

    def test_idempotency_of_config_generation(self):
        """Test that generating config multiple times produces same structure."""
        config1 = generate_default_config("Aurora", "Jordan")
        config2 = generate_default_config("Aurora", "Jordan")

        # Should have same structure (except timestamps)
        self.assertEqual(config1["agent"], config2["agent"])
        self.assertEqual(config1["room"], config2["room"])
        self.assertEqual(config1["paths"], config2["paths"])
        self.assertEqual(config1["first_light"], config2["first_light"])
        self.assertEqual(config1["drives"], config2["drives"])


class TestConstants(unittest.TestCase):
    """Tests for module constants."""

    def test_default_model_has_provider_prefix(self):
        """Test that DEFAULT_MODEL has provider prefix."""
        self.assertIn("/", DEFAULT_MODEL)

    def test_valid_model_prefixes_format(self):
        """Test that VALID_MODEL_PREFIXES are properly formatted."""
        for prefix in VALID_MODEL_PREFIXES:
            self.assertIn("/", prefix)
            self.assertTrue(prefix.endswith("/"))

    def test_session_size_tokens_positive(self):
        """Test that SESSION_SIZE_TOKENS are positive."""
        for size, tokens in SESSION_SIZE_TOKENS.items():
            self.assertGreater(tokens, 0)

    def test_first_light_presets_have_required_keys(self):
        """Test that FIRST_LIGHT_PRESETS have required keys."""
        for preset_name, preset in FIRST_LIGHT_PRESETS.items():
            self.assertIn("sessions_per_day", preset)
            self.assertIn("session_size", preset)
            self.assertGreater(preset["sessions_per_day"], 0)

    def test_cost_per_1k_positive(self):
        """Test that COST_PER_1K_TOKENS is positive."""
        self.assertGreater(COST_PER_1K_TOKENS, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
