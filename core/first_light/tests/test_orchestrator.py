"""Tests for First Light Orchestrator."""

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.first_light.orchestrator import (
    get_exploration_prompts,
    select_prompt,
    parse_frequency,
    build_exploration_prompt,
    calculate_next_run_time,
    should_run,
    load_first_light_state,
    save_first_light_state,
    get_state_path,
)


class TestExplorationPrompts(unittest.TestCase):
    """Test exploration prompt rotation."""
    
    def test_get_exploration_prompts_returns_list(self):
        """Test that prompts are returned as a list."""
        prompts = get_exploration_prompts()
        self.assertIsInstance(prompts, list)
        self.assertGreater(len(prompts), 5)
    
    def test_prompts_contain_expected_themes(self):
        """Test that prompts cover expected exploration themes."""
        prompts = get_exploration_prompts()
        all_text = " ".join(prompts).lower()
        
        # Check for key themes
        self.assertIn("explore", all_text)
        self.assertIn("make", all_text) or self.assertIn("create", all_text)
    
    def test_select_prompt_returns_tuple(self):
        """Test that select_prompt returns prompt and index."""
        prompt, idx = select_prompt()
        self.assertIsInstance(prompt, str)
        self.assertIsInstance(idx, int)
        self.assertIn(idx, range(len(get_exploration_prompts())))
    
    def test_select_prompt_excludes_used_indices(self):
        """Test that used prompts are excluded from rotation."""
        all_prompts = get_exploration_prompts()
        used = [0, 1, 2]
        
        # Run multiple times to ensure we're not getting used indices
        for _ in range(20):
            prompt, idx = select_prompt(used)
            self.assertNotIn(idx, used)
    
    def test_select_prompt_resets_when_all_used(self):
        """Test rotation resets when all prompts used."""
        all_prompts = get_exploration_prompts()
        used = list(range(len(all_prompts)))
        
        prompt, idx = select_prompt(used)
        # Should still return a valid prompt
        self.assertIsInstance(prompt, str)
        self.assertIn(idx, range(len(all_prompts)))


class TestFrequencyParsing(unittest.TestCase):
    """Test frequency configuration parsing."""
    
    def test_parse_frequency_hours(self):
        """Test parsing hours format."""
        self.assertEqual(parse_frequency("4h"), 4.0)
        self.assertEqual(parse_frequency("2.5h"), 2.5)
    
    def test_parse_frequency_minutes(self):
        """Test parsing minutes format."""
        self.assertEqual(parse_frequency("30m"), 0.5)
        self.assertEqual(parse_frequency("60m"), 1.0)
    
    def test_parse_frequency_number(self):
        """Test parsing plain number."""
        self.assertEqual(parse_frequency(4), 4.0)
        self.assertEqual(parse_frequency("4"), 4.0)
    
    def test_parse_frequency_case_insensitive(self):
        """Test case insensitivity."""
        self.assertEqual(parse_frequency("4H"), 4.0)
        self.assertEqual(parse_frequency("30M"), 0.5)


class TestBuildExplorationPrompt(unittest.TestCase):
    """Test exploration prompt building."""
    
    def test_build_includes_session_number(self):
        """Test that session number is included in prompt."""
        template = "Explore something."
        prompt = build_exploration_prompt(template, 5)
        
        self.assertIn("First Light #5", prompt)
        self.assertIn(template, prompt)
    
    def test_build_includes_timestamp(self):
        """Test that timestamp is included."""
        template = "Explore something."
        prompt = build_exploration_prompt(template, 1)
        
        # Should contain ISO timestamp format
        self.assertIn("Timestamp:", prompt)
        self.assertIn("T", prompt)  # ISO format has T
    
    def test_build_includes_frontmatter_template(self):
        """Test that frontmatter template is included."""
        template = "Explore something."
        prompt = build_exploration_prompt(template, 1)
        
        self.assertIn("---", prompt)
        self.assertIn("drive: FIRST_LIGHT", prompt)
        self.assertIn("trigger: first_light", prompt)
        self.assertIn("session_number:", prompt)


class TestCalculateNextRunTime(unittest.TestCase):
    """Test next run time calculation."""
    
    def test_calculate_from_last_run(self):
        """Test calculation from last run time."""
        now = datetime.now(timezone.utc)
        last_run = now.isoformat()
        frequency = 4.0
        
        next_run = calculate_next_run_time(last_run, frequency)
        next_dt = datetime.fromisoformat(next_run.replace("Z", "+00:00"))
        
        # Should be ~4 hours after last run
        expected = now + __import__('datetime').timedelta(hours=4)
        diff = abs((next_dt - expected).total_seconds())
        self.assertLess(diff, 1)  # Within 1 second
    
    def test_calculate_no_last_run(self):
        """Test calculation with no last run."""
        next_run = calculate_next_run_time(None, 4.0)
        next_dt = datetime.fromisoformat(next_run.replace("Z", "+00:00"))
        
        # Should be in the near future (within 10 minutes)
        now = datetime.now(timezone.utc)
        diff = (next_dt - now).total_seconds()
        self.assertGreater(diff, 0)
        self.assertLess(diff, 600)
    
    def test_catch_up_when_behind(self):
        """Test catching up when far behind schedule."""
        now = datetime.now(timezone.utc)
        # Last run was 12 hours ago (with 4h frequency)
        last_run = (now - __import__('datetime').timedelta(hours=12)).isoformat()
        
        next_run = calculate_next_run_time(last_run, 4.0)
        next_dt = datetime.fromisoformat(next_run.replace("Z", "+00:00"))
        
        # Should schedule from now, not from old last run
        # (We're already way past due, so next should be ~now + frequency)
        self.assertGreater(next_dt, now)


class TestShouldRun(unittest.TestCase):
    """Test run condition checking."""
    
    def test_should_not_run_if_not_active(self):
        """Test that inactive state prevents running."""
        state = {"status": "not_started", "next_run_time": None}
        self.assertFalse(should_run(state, 4.0))
    
    def test_should_run_if_due(self):
        """Test that due time triggers run."""
        now = datetime.now(timezone.utc)
        past_time = (now - __import__('datetime').timedelta(hours=1)).isoformat()
        state = {"status": "active", "next_run_time": past_time}
        
        self.assertTrue(should_run(state, 4.0))
    
    def test_should_not_run_if_not_due(self):
        """Test that future time prevents running."""
        now = datetime.now(timezone.utc)
        future_time = (now + __import__('datetime').timedelta(hours=1)).isoformat()
        state = {"status": "active", "next_run_time": future_time}
        
        self.assertFalse(should_run(state, 4.0))
    
    def test_should_run_if_no_next_run_time(self):
        """Test that missing next_run_time triggers run."""
        state = {"status": "active", "next_run_time": None}
        self.assertTrue(should_run(state, 4.0))


class TestStateManagement(unittest.TestCase):
    """Test state loading and saving."""
    
    def setUp(self):
        self.test_dir = Path(__file__).parent / "test_state"
        self.test_dir.mkdir(exist_ok=True)
        self.config = {
            "paths": {
                "workspace": str(self.test_dir),
                "state": "state"
            }
        }
    
    def tearDown(self):
        # Cleanup
        import shutil
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
    
    def test_get_state_path(self):
        """Test state path resolution."""
        path = get_state_path(self.config)
        self.assertIn("first-light.json", str(path))
    
    def test_load_default_state(self):
        """Test loading default state when file doesn't exist."""
        state = load_first_light_state(self.config)
        
        self.assertEqual(state["version"], "1.0")
        self.assertEqual(state["status"], "not_started")
        self.assertEqual(state["sessions_completed"], 0)
        self.assertEqual(state["sessions_scheduled"], 0)
    
    def test_save_and_load_state(self):
        """Test saving and loading state."""
        state = {
            "version": "1.0",
            "status": "active",
            "sessions_completed": 5,
            "sessions_scheduled": 10,
            "patterns_detected": {"PHILOSOPHICAL": {"session_count": 3}},
        }
        
        save_first_light_state(self.config, state)
        loaded = load_first_light_state(self.config)
        
        self.assertEqual(loaded["status"], "active")
        self.assertEqual(loaded["sessions_completed"], 5)
        self.assertEqual(loaded["patterns_detected"]["PHILOSOPHICAL"]["session_count"], 3)
    
    def test_save_is_atomic(self):
        """Test that save uses atomic write (tmp then rename)."""
        state = {"status": "active"}
        save_first_light_state(self.config, state)
        
        # Should not leave .tmp file
        tmp_file = get_state_path(self.config).with_suffix(".tmp")
        self.assertFalse(tmp_file.exists())


class TestSessionSpawning(unittest.TestCase):
    """Test session spawning (mocked)."""
    
    @patch('core.first_light.orchestrator.spawn_via_api')
    @patch('core.first_light.orchestrator.spawn_via_cli')
    def test_schedule_uses_cli_first(self, mock_cli, mock_api):
        """Test that CLI is tried before API."""
        mock_cli.return_value = True
        
        from core.first_light.orchestrator import schedule_exploration_session
        
        config = {"first_light": {"timeout_seconds": 900}}
        state = {}
        
        result = schedule_exploration_session(config, state, 1)
        
        self.assertTrue(result)
        mock_cli.assert_called_once()
        mock_api.assert_not_called()
    
    @patch('core.first_light.orchestrator.spawn_via_api')
    @patch('core.first_light.orchestrator.spawn_via_cli')
    def test_schedule_falls_back_to_api(self, mock_cli, mock_api):
        """Test API fallback when CLI fails."""
        mock_cli.return_value = False
        mock_api.return_value = True
        
        from core.first_light.orchestrator import schedule_exploration_session
        
        config = {"first_light": {"timeout_seconds": 900}}
        state = {}
        
        result = schedule_exploration_session(config, state, 1)
        
        self.assertTrue(result)
        mock_cli.assert_called_once()
        mock_api.assert_called_once()


if __name__ == "__main__":
    unittest.main()
