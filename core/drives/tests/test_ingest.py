"""Unit tests for drive ingest system.

Tests content loading, LLM analysis, keyword fallback, impact parsing,
impact application, and the fallback chain.
"""

import json
import os
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import from the package
from core.drives.ingest import (
    load_experience_content,
    build_analysis_prompt,
    parse_impact_response,
    analyze_with_ollama,
    analyze_with_openrouter,
    analyze_with_keywords,
    analyze_content,
    apply_impacts,
    DRIVE_DESCRIPTIONS,
    OPENROUTER_DEFAULT_URL,
)
from core.drives.models import create_default_state


class TestLoadExperienceContent(unittest.TestCase):
    """Test content loading from memory files."""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_file = Path(self.temp_dir) / "test_session.md"

    def tearDown(self):
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_load_single_file(self):
        """Should load content from a specific file."""
        test_content = "# Test Session\n\nThis is test content."
        self.temp_file.write_text(test_content)

        result = load_experience_content(file_path=self.temp_file)

        self.assertEqual(result, test_content)

    def test_load_nonexistent_file(self):
        """Should return empty string for nonexistent file."""
        nonexistent = Path(self.temp_dir) / "nonexistent.md"

        result = load_experience_content(file_path=nonexistent)

        self.assertEqual(result, "")

    def test_load_recent_requires_config(self):
        """Should error if recent=True but no config provided."""
        result = load_experience_content(recent=True, config=None)

        self.assertEqual(result, "")

    def test_load_recent_finds_todays_files(self):
        """Should find and load today's memory files."""
        # Create test directories
        memory_dir = Path(self.temp_dir) / "memory"
        session_dir = memory_dir / "sessions"
        session_dir.mkdir(parents=True)

        today = datetime.now().strftime("%Y-%m-%d")

        # Create a daily file
        daily_file = memory_dir / f"{today}.md"
        daily_file.write_text("# Daily memory\nTest content")

        # Create a session file
        session_file = session_dir / f"{today}-1430-CURIOSITY.md"
        session_file.write_text("# Session\nExplored topics")

        config = {
            "memory": {"daily_dir": str(memory_dir), "session_dir": str(session_dir)},
            "paths": {"workspace": self.temp_dir},
        }

        result = load_experience_content(recent=True, config=config)

        self.assertIn("Daily memory", result)
        self.assertIn("Session", result)
        self.assertIn(f"{today}.md", result)

    def test_load_recent_truncates_long_files(self):
        """Should truncate files longer than 4000 chars."""
        memory_dir = Path(self.temp_dir) / "memory"
        memory_dir.mkdir()

        today = datetime.now().strftime("%Y-%m-%d")

        # Create a very long file
        long_content = "A" * 5000
        daily_file = memory_dir / f"{today}.md"
        daily_file.write_text(long_content)

        config = {"memory": {"daily_dir": str(memory_dir)}, "paths": {"workspace": self.temp_dir}}

        result = load_experience_content(recent=True, config=config)

        self.assertIn("[...truncated...]", result)
        # Should have last 4000 chars plus truncation marker
        self.assertLess(len(result), 4500)


class TestBuildAnalysisPrompt(unittest.TestCase):
    """Test prompt building for LLM analysis."""

    def test_includes_all_drives(self):
        """Prompt should include all provided drives."""
        drives = {"CURIOSITY": {}, "CREATIVE": {}}
        content = "Test content"

        prompt = build_analysis_prompt(content, drives)

        self.assertIn("CURIOSITY", prompt)
        self.assertIn("CREATIVE", prompt)

    def test_includes_drive_descriptions(self):
        """Prompt should include drive descriptions."""
        drives = {"CURIOSITY": {}}
        content = "Test"

        prompt = build_analysis_prompt(content, drives)

        self.assertIn(DRIVE_DESCRIPTIONS["CURIOSITY"], prompt)

    def test_includes_content(self):
        """Prompt should include the experience content."""
        drives = {"CURIOSITY": {}}
        content = "This is the experience content"

        prompt = build_analysis_prompt(content, drives)

        self.assertIn(content, prompt)

    def test_truncates_long_content(self):
        """Prompt should truncate content over 6000 chars."""
        drives = {"CURIOSITY": {}}
        content = "A" * 10000

        prompt = build_analysis_prompt(content, drives)

        self.assertNotIn(content, prompt)
        self.assertIn("A" * 100, prompt)  # Some content present

    def test_includes_scoring_rules(self):
        """Prompt should include delta scoring rules."""
        drives = {"CURIOSITY": {}}
        content = "Test"

        prompt = build_analysis_prompt(content, drives)

        self.assertIn("Positive delta", prompt)
        self.assertIn("Negative delta", prompt)
        self.assertIn("SATISFACTION DEPTH", prompt)


class TestParseImpactResponse(unittest.TestCase):
    """Test parsing of LLM response into impact structures."""

    def test_parse_valid_json_object(self):
        """Should parse JSON with impacts key."""
        response = '{"impacts": [{"drive": "CURIOSITY", "delta": -15, "reason": "Explored"}]}'

        result = parse_impact_response(response)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["drive"], "CURIOSITY")
        self.assertEqual(result[0]["delta"], -15)

    def test_parse_valid_json_array(self):
        """Should parse raw JSON array."""
        response = '[{"drive": "CARE", "delta": -10, "reason": "Test"}]'

        result = parse_impact_response(response)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["drive"], "CARE")

    def test_parse_empty_array(self):
        """Should handle empty impacts array."""
        response = '{"impacts": []}'

        result = parse_impact_response(response)

        self.assertEqual(result, [])

    def test_parse_with_markdown_code_block(self):
        """Should extract JSON from markdown code block."""
        response = '```json\n{"impacts": [{"drive": "CREATIVE", "delta": 5}]}\n```'

        result = parse_impact_response(response)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["drive"], "CREATIVE")

    def test_parse_without_json_label(self):
        """Should extract JSON from unlabeled code block."""
        response = '```\n[{"drive": "REST", "delta": -20}]\n```'

        result = parse_impact_response(response)

        self.assertEqual(len(result), 1)

    def test_parse_invalid_json(self):
        """Should return empty list for invalid JSON."""
        response = "This is not JSON"

        result = parse_impact_response(response)

        self.assertEqual(result, [])

    def test_parse_empty_response(self):
        """Should return empty list for empty response."""
        result = parse_impact_response("")
        self.assertEqual(result, [])

    def test_validates_drive_name_uppercase(self):
        """Should normalize drive names to uppercase."""
        response = '{"impacts": [{"drive": "curiosity", "delta": -5}]}'

        result = parse_impact_response(response)

        self.assertEqual(result[0]["drive"], "CURIOSITY")

    def test_validates_delta_range(self):
        """Should clamp delta to valid range."""
        response = '{"impacts": [{"drive": "CURIOSITY", "delta": 50}]}'

        result = parse_impact_response(response)

        self.assertEqual(result[0]["delta"], 20)  # Clamped to max

    def test_validates_negative_delta_range(self):
        """Should clamp negative delta to valid range."""
        response = '{"impacts": [{"drive": "CURIOSITY", "delta": -50}]}'

        result = parse_impact_response(response)

        self.assertEqual(result[0]["delta"], -30)  # Clamped to min

    def test_skips_invalid_impacts(self):
        """Should skip impacts without drive name."""
        response = '{"impacts": [{"delta": -5}, {"drive": "CARE", "delta": -10}]}'

        result = parse_impact_response(response)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["drive"], "CARE")

    def test_handles_non_numeric_delta(self):
        """Should skip impacts with non-numeric delta."""
        response = '{"impacts": [{"drive": "CURIOSITY", "delta": "high"}]}'

        result = parse_impact_response(response)

        self.assertEqual(result, [])


class TestAnalyzeWithOllama(unittest.TestCase):
    """Test Ollama LLM analysis (mocked HTTP calls)."""

    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_successful_ollama_call(self, mock_request_class, mock_urlopen):
        """Should parse Ollama response correctly."""
        # Setup mock response
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "response": '{"impacts": [{"drive": "CURIOSITY", "delta": -15, "reason": "Explored"}]}'
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        drives = {"CURIOSITY": {}}
        content = "Test content"

        result = analyze_with_ollama(content, drives)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["drive"], "CURIOSITY")
        self.assertEqual(result[0]["delta"], -15)

    @patch("urllib.request.urlopen")
    def test_ollama_connection_error(self, mock_urlopen):
        """Should raise URLError when Ollama unavailable."""
        from urllib.error import URLError

        mock_urlopen.side_effect = URLError("Connection refused")

        drives = {"CURIOSITY": {}}
        content = "Test"

        with self.assertRaises(URLError):
            analyze_with_ollama(content, drives)

    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_uses_config_url(self, mock_request_class, mock_urlopen):
        """Should use custom URL from config."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": '{"impacts": []}'}).encode(
            "utf-8"
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response

        drives = {"CURIOSITY": {}}
        config = {"ingest": {"ollama_url": "http://custom:11434/api/generate"}}

        analyze_with_ollama("Test", drives, config)

        # Verify Request was called with custom URL
        mock_request_class.assert_called_once()
        args, _ = mock_request_class.call_args
        self.assertEqual(args[0], "http://custom:11434/api/generate")

    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_uses_config_model(self, mock_request_class, mock_urlopen):
        """Should use custom model from config."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"response": '{"impacts": []}'}).encode(
            "utf-8"
        )
        mock_urlopen.return_value.__enter__.return_value = mock_response

        drives = {"CURIOSITY": {}}
        config = {"ingest": {"ollama_model": "custom-model"}}

        analyze_with_ollama("Test", drives, config)

        # Check that the request data contains custom model
        mock_request_class.assert_called_once()
        _, kwargs = mock_request_class.call_args
        request_data = json.loads(kwargs["data"])
        self.assertEqual(request_data["model"], "custom-model")


class TestAnalyzeWithOpenRouter(unittest.TestCase):
    """Test OpenRouter API analysis (mocked HTTP calls)."""

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"})
    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_successful_openrouter_call(self, mock_request_class, mock_urlopen):
        """Should parse OpenRouter response correctly."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {
                "choices": [
                    {
                        "message": {
                            "content": '{"impacts": [{"drive": "CREATIVE", "delta": 8, "reason": "Built"}]}'
                        }
                    }
                ]
            }
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        drives = {"CREATIVE": {}}
        content = "Test content"

        result = analyze_with_openrouter(content, drives)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["drive"], "CREATIVE")

    def test_raises_without_api_key(self):
        """Should raise ValueError without API key."""
        # Ensure no API key is set
        with patch.dict(os.environ, {}, clear=True):
            drives = {"CURIOSITY": {}}
            content = "Test"

            with self.assertRaises(ValueError) as ctx:
                analyze_with_openrouter(content, drives)

            self.assertIn("API key not found", str(ctx.exception))

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"})
    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_uses_config_model(self, mock_request_class, mock_urlopen):
        """Should use custom model from config."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(
            {"choices": [{"message": {"content": '{"impacts": []}'}}]}
        ).encode("utf-8")
        mock_urlopen.return_value.__enter__.return_value = mock_response

        drives = {"CURIOSITY": {}}
        config = {"ingest": {"openrouter_model": "anthropic/claude-3-haiku"}}

        analyze_with_openrouter("Test", drives, config)

        # Check request data contains custom model
        mock_request_class.assert_called_once()
        _, kwargs = mock_request_class.call_args
        request_data = json.loads(kwargs["data"])
        self.assertEqual(request_data["model"], "anthropic/claude-3-haiku")

    @patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"})
    @patch("urllib.request.urlopen")
    def test_http_error_handling(self, mock_urlopen):
        """Should raise HTTPError on API errors."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError(OPENROUTER_DEFAULT_URL, 401, "Unauthorized", {}, None)

        drives = {"CURIOSITY": {}}

        with self.assertRaises(HTTPError):
            analyze_with_openrouter("Test", drives)


class TestAnalyzeWithKeywords(unittest.TestCase):
    """Test keyword-based fallback analysis."""

    def test_detects_curiosity_keywords(self):
        """Should detect curiosity-related keywords."""
        content = "I was curious and explored new ideas"
        drives = {"CURIOSITY": {}}

        result = analyze_with_keywords(content, drives)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["drive"], "CURIOSITY")
        self.assertLess(result[0]["delta"], 0)  # Negative = satisfaction

    def test_detects_social_keywords(self):
        """Should detect social-related keywords."""
        content = "Had a great conversation with the human"
        drives = {"SOCIAL": {}}

        result = analyze_with_keywords(content, drives)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["drive"], "SOCIAL")

    def test_detects_creative_keywords(self):
        """Should detect creative-related keywords."""
        content = "Built a new tool and wrote some code"
        drives = {"CREATIVE": {}}

        result = analyze_with_keywords(content, drives)

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["drive"], "CREATIVE")

    def test_multiple_keyword_matches(self):
        """Should handle multiple keyword matches per drive."""
        content = "curious curious curious"  # Multiple matches
        drives = {"CURIOSITY": {}}

        result = analyze_with_keywords(content, drives)

        self.assertEqual(len(result), 1)
        # More matches = more negative delta (but capped)
        self.assertLessEqual(result[0]["delta"], -5)

    def test_ignores_unknown_drives(self):
        """Should ignore drives without keyword mappings."""
        content = "Some random content"
        drives = {"UNKNOWN_DRIVE": {}}

        result = analyze_with_keywords(content, drives)

        self.assertEqual(result, [])

    def test_no_match_returns_empty(self):
        """Should return empty list when no keywords match."""
        content = "The weather is nice today"
        drives = {"CURIOSITY": {}, "CREATIVE": {}}

        result = analyze_with_keywords(content, drives)

        self.assertEqual(result, [])


class TestAnalyzeContentOrchestrator(unittest.TestCase):
    """Test the analyze_content orchestrator with fallback chain."""

    @patch("core.drives.ingest.analyze_with_ollama")
    def test_uses_ollama_first(self, mock_ollama):
        """Should use Ollama when available."""
        mock_ollama.return_value = [{"drive": "CURIOSITY", "delta": -10}]

        result = analyze_content("Test", {"CURIOSITY": {}}, verbose=False)

        mock_ollama.assert_called_once()
        self.assertEqual(len(result), 1)

    @patch("core.drives.ingest.analyze_with_openrouter")
    @patch("core.drives.ingest.analyze_with_ollama")
    def test_fallback_to_openrouter(self, mock_ollama, mock_openrouter):
        """Should fallback to OpenRouter when Ollama fails."""
        from urllib.error import URLError

        mock_ollama.side_effect = URLError("Connection refused")
        mock_openrouter.return_value = [{"drive": "CURIOSITY", "delta": -10}]

        with patch.dict(os.environ, {"OPENROUTER_API_KEY": "test-key"}):
            result = analyze_content("Test", {"CURIOSITY": {}}, verbose=False)

        mock_ollama.assert_called_once()
        mock_openrouter.assert_called_once()
        self.assertEqual(len(result), 1)

    @patch("core.drives.ingest.analyze_with_keywords")
    @patch("core.drives.ingest.analyze_with_ollama")
    def test_fallback_to_keywords(self, mock_ollama, mock_keywords):
        """Should fallback to keywords when both APIs fail."""
        from urllib.error import URLError

        mock_ollama.side_effect = URLError("Connection refused")
        mock_keywords.return_value = [{"drive": "CURIOSITY", "delta": -5}]

        # No API key set
        with patch.dict(os.environ, {}, clear=True):
            result = analyze_content("Test", {"CURIOSITY": {}}, verbose=False)

        mock_ollama.assert_called_once()
        mock_keywords.assert_called_once()
        self.assertEqual(len(result), 1)

    @patch("core.drives.ingest.analyze_with_ollama")
    def test_returns_empty_if_all_fail(self, mock_ollama):
        """Should return empty list if all methods fail."""
        from urllib.error import URLError

        mock_ollama.side_effect = URLError("Connection refused")

        with patch.dict(os.environ, {}, clear=True):
            with patch("core.drives.ingest.analyze_with_keywords") as mock_kw:
                mock_kw.return_value = []
                result = analyze_content("Test", {"CURIOSITY": {}}, verbose=False)

        self.assertEqual(result, [])


class TestApplyImpacts(unittest.TestCase):
    """Test impact application to drive state."""

    def test_applies_negative_delta(self):
        """Should reduce pressure for negative delta."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 20.0

        impacts = [{"drive": "CARE", "delta": -10, "reason": "Test"}]

        new_state, changes = apply_impacts(state, impacts)

        self.assertEqual(new_state["drives"]["CARE"]["pressure"], 10.0)
        self.assertEqual(len(changes), 1)

    def test_applies_positive_delta(self):
        """Should increase pressure for positive delta."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 10.0

        impacts = [{"drive": "CARE", "delta": 5, "reason": "Test"}]

        new_state, changes = apply_impacts(state, impacts)

        self.assertEqual(new_state["drives"]["CARE"]["pressure"], 15.0)

    def test_clamps_to_minimum(self):
        """Should clamp pressure to minimum of 0."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 5.0

        impacts = [{"drive": "CARE", "delta": -10, "reason": "Test"}]

        new_state, _ = apply_impacts(state, impacts)

        self.assertEqual(new_state["drives"]["CARE"]["pressure"], 0.0)

    def test_clamps_to_maximum(self):
        """Should clamp pressure to threshold * 1.5."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0  # Over threshold

        impacts = [{"drive": "CARE", "delta": 20, "reason": "Test"}]

        new_state, _ = apply_impacts(state, impacts)

        # Threshold is 20.0, max is 20.0 * 1.5 = 30.0
        self.assertEqual(new_state["drives"]["CARE"]["pressure"], 30.0)

    def test_removes_from_triggered_on_significant_reduction(self):
        """Should remove drive from triggered list if delta < -5."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        state["triggered_drives"] = ["CARE"]

        impacts = [{"drive": "CARE", "delta": -10, "reason": "Test"}]

        new_state, _ = apply_impacts(state, impacts)

        self.assertNotIn("CARE", new_state["triggered_drives"])

    def test_keeps_in_triggered_on_small_reduction(self):
        """Should keep drive in triggered list if delta >= -5."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 25.0
        state["triggered_drives"] = ["CARE"]

        impacts = [{"drive": "CARE", "delta": -3, "reason": "Test"}]

        new_state, _ = apply_impacts(state, impacts)

        self.assertIn("CARE", new_state["triggered_drives"])

    def test_reports_unknown_drives(self):
        """Should report unknown drives in changes."""
        state = create_default_state()

        impacts = [{"drive": "UNKNOWN", "delta": -5, "reason": "Test"}]

        _, changes = apply_impacts(state, impacts)

        self.assertEqual(len(changes), 1)
        self.assertIn("Unknown drive", changes[0])

    def test_formats_change_description(self):
        """Should format change descriptions correctly."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 20.0

        impacts = [{"drive": "CARE", "delta": -10, "reason": "Helped human"}]

        _, changes = apply_impacts(state, impacts)

        self.assertIn("↓ CARE", changes[0])
        self.assertIn("20.0 → 10.0", changes[0])
        self.assertIn("(-10)", changes[0])
        self.assertIn("Helped human", changes[0])

    def test_handles_multiple_impacts(self):
        """Should apply multiple impacts in one call."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 20.0
        state["drives"]["CURIOSITY"] = {
            "name": "CURIOSITY",
            "pressure": 25.0,
            "threshold": 25.0,
            "rate_per_hour": 5.0,
        }

        impacts = [
            {"drive": "CARE", "delta": -10, "reason": "Helped"},
            {"drive": "CURIOSITY", "delta": -15, "reason": "Explored"},
        ]

        new_state, changes = apply_impacts(state, impacts)

        self.assertEqual(len(changes), 2)
        self.assertEqual(new_state["drives"]["CARE"]["pressure"], 10.0)
        self.assertEqual(new_state["drives"]["CURIOSITY"]["pressure"], 10.0)


class TestDryRunMode(unittest.TestCase):
    """Test that ingest can work in dry-run mode (analysis only)."""

    def test_analyze_content_does_not_modify_state(self):
        """analyze_content should never modify state."""
        # This is inherent in the function signature - it doesn't take state
        with patch("core.drives.ingest.analyze_with_ollama") as mock:
            mock.return_value = [{"drive": "CURIOSITY", "delta": -10}]

            result = analyze_content("Test", {"CURIOSITY": {}}, verbose=False)

            # Should just return impacts without touching any state
            self.assertEqual(len(result), 1)

    def test_apply_impacts_vs_dry_run(self):
        """State modification only happens in apply_impacts."""
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 20.0
        original_pressure = state["drives"]["CARE"]["pressure"]

        impacts = [{"drive": "CARE", "delta": -10, "reason": "Test"}]

        # Just analyzing doesn't change state
        # (analyze_content returns impacts, doesn't take state)

        # apply_impacts DOES change state
        new_state, _ = apply_impacts(state, impacts)

        self.assertNotEqual(new_state["drives"]["CARE"]["pressure"], original_pressure)


if __name__ == "__main__":
    unittest.main(verbosity=2)
