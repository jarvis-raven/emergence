"""Unit tests for drive session spawning.

Tests quiet hours detection, cooldown logic, drive selection,
session prompt building, trigger recording, and spawn failure handling.
All external calls (HTTP, subprocess) are mocked.
"""

import json
import subprocess
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import from the package
from core.drives.spawn import (
    is_quiet_hours,
    check_cooldown,
    build_session_prompt,
    select_drive_to_trigger,
    record_trigger,
    handle_spawn_failure,
    tick_with_spawning,
    spawn_session,
    spawn_via_api,
    spawn_via_cli,
)
from core.drives.models import create_default_state


class TestQuietHours(unittest.TestCase):
    """Test quiet hours detection."""
    
    def test_default_quiet_hours_overnight(self):
        """Default quiet hours [23, 7] should work overnight."""
        config = {"drives": {"quiet_hours": [23, 7]}}
        
        # Mock 2 AM (within quiet hours)
        with patch("core.drives.spawn.datetime") as mock_dt:
            mock_now = Mock()
            mock_now.hour = 2
            mock_dt.now.return_value = mock_now
            
            self.assertTrue(is_quiet_hours(config))
    
    def test_default_quiet_hours_daytime(self):
        """Default quiet hours should not trigger during day."""
        config = {"drives": {"quiet_hours": [23, 7]}}
        
        # Mock 2 PM (outside quiet hours)
        with patch("core.drives.spawn.datetime") as mock_dt:
            mock_now = Mock()
            mock_now.hour = 14
            mock_dt.now.return_value = mock_now
            
            self.assertFalse(is_quiet_hours(config))
    
    def test_quiet_hours_boundary_start(self):
        """Quiet hours should start at exact hour."""
        config = {"drives": {"quiet_hours": [23, 7]}}
        
        with patch("core.drives.spawn.datetime") as mock_dt:
            mock_now = Mock()
            mock_now.hour = 23
            mock_dt.now.return_value = mock_now
            
            self.assertTrue(is_quiet_hours(config))
    
    def test_quiet_hours_boundary_end(self):
        """Quiet hours should end at exact hour."""
        config = {"drives": {"quiet_hours": [23, 7]}}
        
        with patch("core.drives.spawn.datetime") as mock_dt:
            mock_now = Mock()
            mock_now.hour = 7
            mock_dt.now.return_value = mock_now
            
            # 7 AM is the end boundary, so should NOT be quiet hours
            self.assertFalse(is_quiet_hours(config))
    
    def test_same_day_quiet_hours(self):
        """Same-day quiet hours (e.g., 1 AM to 5 AM) should work."""
        config = {"drives": {"quiet_hours": [1, 5]}}
        
        with patch("core.drives.spawn.datetime") as mock_dt:
            mock_now = Mock()
            mock_now.hour = 3
            mock_dt.now.return_value = mock_now
            
            self.assertTrue(is_quiet_hours(config))
    
    def test_same_day_outside_hours(self):
        """Same-day quiet hours should not trigger outside range."""
        config = {"drives": {"quiet_hours": [1, 5]}}
        
        with patch("core.drives.spawn.datetime") as mock_dt:
            mock_now = Mock()
            mock_now.hour = 10
            mock_dt.now.return_value = mock_now
            
            self.assertFalse(is_quiet_hours(config))
    
    def test_no_quiet_hours(self):
        """None quiet_hours should mean no quiet time."""
        config = {"drives": {"quiet_hours": None}}
        
        self.assertFalse(is_quiet_hours(config))
    
    def test_empty_quiet_hours(self):
        """Empty quiet_hours list should mean no quiet time."""
        config = {"drives": {"quiet_hours": []}}
        
        self.assertFalse(is_quiet_hours(config))
    
    def test_missing_quiet_hours_uses_default(self):
        """Missing quiet_hours should use default [23, 7]."""
        config = {"drives": {}}
        
        with patch("core.drives.spawn.datetime") as mock_dt:
            mock_now = Mock()
            mock_now.hour = 2  # 2 AM
            mock_dt.now.return_value = mock_now
            
            self.assertTrue(is_quiet_hours(config))


class TestCooldownLogic(unittest.TestCase):
    """Test cooldown period logic."""
    
    def test_no_previous_trigger(self):
        """Drive with no history should not be in cooldown."""
        state = {"trigger_log": []}
        
        self.assertFalse(check_cooldown(state, "CARE", 30))
    
    def test_within_cooldown(self):
        """Recent trigger should be in cooldown."""
        now = datetime.now(timezone.utc)
        state = {
            "trigger_log": [
                {
                    "drive": "CARE",
                    "timestamp": now.isoformat(),
                    "pressure": 25.0,
                    "threshold": 20.0,
                    "session_spawned": True,
                }
            ]
        }
        
        self.assertTrue(check_cooldown(state, "CARE", 30))
    
    def test_outside_cooldown(self):
        """Old trigger should not be in cooldown."""
        # Trigger from 60 minutes ago
        old_time = datetime.now(timezone.utc) - __import__("datetime").timedelta(minutes=60)
        state = {
            "trigger_log": [
                {
                    "drive": "CARE",
                    "timestamp": old_time.isoformat(),
                    "pressure": 25.0,
                    "threshold": 20.0,
                    "session_spawned": True,
                }
            ]
        }
        
        self.assertFalse(check_cooldown(state, "CARE", 30))
    
    def test_cooldown_boundary_exact(self):
        """Exactly at cooldown boundary should not be in cooldown."""
        # Trigger from exactly 30 minutes ago
        old_time = datetime.now(timezone.utc) - __import__("datetime").timedelta(minutes=30)
        state = {
            "trigger_log": [
                {
                    "drive": "CARE",
                    "timestamp": old_time.isoformat(),
                    "pressure": 25.0,
                    "threshold": 20.0,
                    "session_spawned": True,
                }
            ]
        }
        
        # 30 minutes since < 30 minutes cooldown = True (still in cooldown)
        # Actually, minutes_since (30.0) < cooldown_minutes (30) is False
        self.assertFalse(check_cooldown(state, "CARE", 30))
    
    def test_cooldown_checks_most_recent(self):
        """Cooldown should check most recent trigger for drive."""
        now = datetime.now(timezone.utc)
        old_time = now - __import__("datetime").timedelta(minutes=60)
        
        state = {
            "trigger_log": [
                {
                    "drive": "CARE",
                    "timestamp": old_time.isoformat(),  # 60 min ago
                    "pressure": 25.0,
                    "threshold": 20.0,
                    "session_spawned": True,
                },
                {
                    "drive": "CURIOSITY",
                    "timestamp": now.isoformat(),  # Just now
                    "pressure": 30.0,
                    "threshold": 25.0,
                    "session_spawned": True,
                }
            ]
        }
        
        # CARE should not be in cooldown (last trigger was 60 min ago)
        self.assertFalse(check_cooldown(state, "CARE", 30))
        # CURIOSITY should be in cooldown
        self.assertTrue(check_cooldown(state, "CURIOSITY", 30))
    
    def test_cooldown_ignores_other_drives(self):
        """Cooldown for one drive should not affect others."""
        now = datetime.now(timezone.utc)
        state = {
            "trigger_log": [
                {
                    "drive": "CARE",
                    "timestamp": now.isoformat(),
                    "pressure": 25.0,
                    "threshold": 20.0,
                    "session_spawned": True,
                }
            ]
        }
        
        # CURIOSITY has no trigger history
        self.assertFalse(check_cooldown(state, "CURIOSITY", 30))


class TestSessionPromptBuilding(unittest.TestCase):
    """Test session prompt building."""
    
    def test_prompt_contains_drive_name(self):
        """Prompt should contain drive name."""
        config = {"memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt("CARE", "Check in with human", 25.0, 20.0, config)
        
        self.assertIn("CARE", prompt)
    
    def test_prompt_contains_pressure(self):
        """Prompt should contain pressure levels."""
        config = {"memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt("CARE", "Check in", 25.0, 20.0, config)
        
        self.assertIn("25.0/20.0", prompt)
        self.assertIn("Pressure:", prompt)
    
    def test_prompt_contains_drive_prompt(self):
        """Prompt should contain the drive's configured prompt."""
        config = {"memory": {"session_dir": "memory/sessions"}}
        drive_prompt = "Your CARE drive triggered. Check in with your human."
        prompt = build_session_prompt("CARE", drive_prompt, 25.0, 20.0, config)
        
        self.assertIn(drive_prompt, prompt)
    
    def test_prompt_contains_output_path(self):
        """Prompt should contain session output file path."""
        config = {"memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt("CARE", "Check in", 25.0, 20.0, config)
        
        self.assertIn("memory/sessions/", prompt)
        self.assertIn("-CARE.md", prompt)
    
    def test_prompt_contains_yaml_frontmatter_template(self):
        """Prompt should contain YAML frontmatter template."""
        config = {"memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt("CARE", "Check in", 25.0, 20.0, config)
        
        self.assertIn("---", prompt)
        self.assertIn("drive: CARE", prompt)
        self.assertIn("trigger: drive", prompt)
    
    def test_prompt_contains_required_sections(self):
        """Prompt should contain all required sections."""
        config = {"memory": {"session_dir": "memory/sessions"}}
        prompt = build_session_prompt("CARE", "Check in", 25.0, 20.0, config)
        
        self.assertIn("## Summary", prompt)
        self.assertIn("## Details", prompt)
        self.assertIn("## Artifacts", prompt)
    
    def test_prompt_uses_default_session_dir(self):
        """Prompt should use default session dir when not in config."""
        config = {}  # No memory.session_dir
        prompt = build_session_prompt("CARE", "Check in", 25.0, 20.0, config)
        
        self.assertIn("memory/sessions/", prompt)


class TestDriveSelection(unittest.TestCase):
    """Test drive selection logic."""
    
    def test_selects_highest_ratio(self):
        """Should select drive with highest pressure ratio."""
        state = {
            "drives": {
                "CARE": {"pressure": 25.0, "threshold": 20.0},  # 125%
                "CURIOSITY": {"pressure": 40.0, "threshold": 25.0},  # 160%
            },
            "triggered_drives": [],
            "trigger_log": []
        }
        config = {"drives": {"cooldown_minutes": 30}}
        
        result = select_drive_to_trigger(state, config)
        
        # CURIOSITY has higher ratio (160% vs 125%)
        self.assertEqual(result, "CURIOSITY")
    
    def test_skips_already_triggered(self):
        """Should skip drives already in triggered list."""
        state = {
            "drives": {
                "CARE": {"pressure": 30.0, "threshold": 20.0},  # 150%
                "CURIOSITY": {"pressure": 26.0, "threshold": 25.0},  # 104%
            },
            "triggered_drives": ["CARE"],
            "trigger_log": []
        }
        config = {"drives": {"cooldown_minutes": 30}}
        
        result = select_drive_to_trigger(state, config)
        
        # CARE is already triggered, so CURIOSITY should be selected
        self.assertEqual(result, "CURIOSITY")
    
    def test_skips_below_threshold(self):
        """Should skip drives below threshold."""
        state = {
            "drives": {
                "CARE": {"pressure": 15.0, "threshold": 20.0},  # 75%
                "CURIOSITY": {"pressure": 26.0, "threshold": 25.0},  # 104%
            },
            "triggered_drives": [],
            "trigger_log": []
        }
        config = {"drives": {"cooldown_minutes": 30}}
        
        result = select_drive_to_trigger(state, config)
        
        # CARE is below threshold
        self.assertEqual(result, "CURIOSITY")
    
    def test_skips_in_cooldown(self):
        """Should skip drives in cooldown."""
        now = datetime.now(timezone.utc)
        state = {
            "drives": {
                "CARE": {"pressure": 30.0, "threshold": 20.0},  # 150%
                "CURIOSITY": {"pressure": 26.0, "threshold": 25.0},  # 104%
            },
            "triggered_drives": [],
            "trigger_log": [
                {
                    "drive": "CARE",
                    "timestamp": now.isoformat(),
                    "pressure": 25.0,
                    "threshold": 20.0,
                    "session_spawned": True,
                }
            ]
        }
        config = {"drives": {"cooldown_minutes": 30}}
        
        result = select_drive_to_trigger(state, config)
        
        # CARE is in cooldown, so CURIOSITY should be selected
        self.assertEqual(result, "CURIOSITY")
    
    def test_returns_none_when_all_in_cooldown(self):
        """Should return None when all candidates in cooldown."""
        now = datetime.now(timezone.utc)
        state = {
            "drives": {
                "CARE": {"pressure": 30.0, "threshold": 20.0},
                "CURIOSITY": {"pressure": 26.0, "threshold": 25.0},
            },
            "triggered_drives": [],
            "trigger_log": [
                {
                    "drive": "CARE",
                    "timestamp": now.isoformat(),
                    "session_spawned": True,
                },
                {
                    "drive": "CURIOSITY",
                    "timestamp": now.isoformat(),
                    "session_spawned": True,
                }
            ]
        }
        config = {"drives": {"cooldown_minutes": 30}}
        
        result = select_drive_to_trigger(state, config)
        
        self.assertIsNone(result)
    
    def test_returns_none_when_no_candidates(self):
        """Should return None when no drives over threshold."""
        state = {
            "drives": {
                "CARE": {"pressure": 10.0, "threshold": 20.0},
            },
            "triggered_drives": [],
            "trigger_log": []
        }
        config = {"drives": {"cooldown_minutes": 30}}
        
        result = select_drive_to_trigger(state, config)
        
        self.assertIsNone(result)
    
    def test_exact_threshold_triggers(self):
        """Drive exactly at threshold should be selectable."""
        state = {
            "drives": {
                "CARE": {"pressure": 20.0, "threshold": 20.0},  # Exactly 100%
            },
            "triggered_drives": [],
            "trigger_log": []
        }
        config = {"drives": {"cooldown_minutes": 30}}
        
        result = select_drive_to_trigger(state, config)
        
        self.assertEqual(result, "CARE")


class TestTriggerRecording(unittest.TestCase):
    """Test trigger event recording."""
    
    def test_creates_trigger_log(self):
        """Should create trigger_log if it doesn't exist."""
        state = {}
        
        record_trigger(state, "CARE", 25.0, 20.0, True)
        
        self.assertIn("trigger_log", state)
        self.assertEqual(len(state["trigger_log"]), 1)
    
    def test_records_all_fields(self):
        """Should record all required fields."""
        state = {"trigger_log": []}
        
        record_trigger(state, "CARE", 25.0, 20.0, True)
        
        entry = state["trigger_log"][0]
        self.assertEqual(entry["drive"], "CARE")
        self.assertEqual(entry["pressure"], 25.0)
        self.assertEqual(entry["threshold"], 20.0)
        self.assertEqual(entry["session_spawned"], True)
        self.assertIn("timestamp", entry)
        self.assertIn("T", entry["timestamp"])  # ISO format
    
    def test_appends_to_existing_log(self):
        """Should append to existing trigger_log."""
        state = {
            "trigger_log": [
                {
                    "drive": "CURIOSITY",
                    "timestamp": "2026-02-07T10:00:00+00:00",
                    "pressure": 30.0,
                    "threshold": 25.0,
                    "session_spawned": True,
                }
            ]
        }
        
        record_trigger(state, "CARE", 25.0, 20.0, True)
        
        self.assertEqual(len(state["trigger_log"]), 2)
    
    def test_limits_to_100_entries(self):
        """Should keep only last 100 entries."""
        state = {
            "trigger_log": [
                {
                    "drive": f"DRIVE{i}",
                    "timestamp": f"2026-02-07T{i:02d}:00:00+00:00",
                    "pressure": float(i),
                    "threshold": 20.0,
                    "session_spawned": True,
                }
                for i in range(100)
            ]
        }
        
        record_trigger(state, "CARE", 25.0, 20.0, True)
        
        self.assertEqual(len(state["trigger_log"]), 100)
        # First entry should be removed (DRIVE0)
        self.assertEqual(state["trigger_log"][0]["drive"], "DRIVE1")
        # Last entry should be the new one
        self.assertEqual(state["trigger_log"][-1]["drive"], "CARE")


class TestSpawnFailureHandling(unittest.TestCase):
    """Test spawn failure handling."""
    
    def test_creates_retry_queue(self):
        """Should create retry_queue if it doesn't exist."""
        state = {"drives": {"CARE": {"pressure": 25.0, "threshold": 20.0}}}
        
        handle_spawn_failure(state, "CARE", "Connection refused")
        
        self.assertIn("retry_queue", state)
        self.assertIn("CARE", state["retry_queue"])
    
    def test_sets_next_attempt(self):
        """Should set next_attempt timestamp."""
        state = {"drives": {"CARE": {"pressure": 25.0, "threshold": 20.0}}}
        
        handle_spawn_failure(state, "CARE", "Connection refused")
        
        entry = state["retry_queue"]["CARE"]
        self.assertIn("next_attempt", entry)
        self.assertIn("T", entry["next_attempt"])  # ISO format
    
    def test_increments_attempt_count(self):
        """Should increment attempt_count with each failure."""
        state = {
            "drives": {"CARE": {"pressure": 25.0, "threshold": 20.0}},
            "retry_queue": {
                "CARE": {
                    "attempt_count": 2,
                    "next_attempt": "2026-02-07T14:00:00+00:00",
                }
            }
        }
        
        handle_spawn_failure(state, "CARE", "Connection refused")
        
        self.assertEqual(state["retry_queue"]["CARE"]["attempt_count"], 3)
    
    def test_records_error(self):
        """Should record error message."""
        state = {"drives": {"CARE": {"pressure": 25.0, "threshold": 20.0}}}
        
        handle_spawn_failure(state, "CARE", "Connection refused")
        
        self.assertEqual(state["retry_queue"]["CARE"]["last_error"], "Connection refused")
    
    def test_backoff_increases_with_attempts(self):
        """Backoff should increase with each attempt (5, 10, 20, 40...)."""
        from datetime import datetime, timedelta
        
        now = datetime.now(timezone.utc)
        
        state = {
            "drives": {"CARE": {"pressure": 25.0, "threshold": 20.0}},
            "retry_queue": {}
        }
        
        # First failure (attempt_count 0 -> 1, backoff 5 min)
        handle_spawn_failure(state, "CARE", "Error 1")
        entry1 = state["retry_queue"]["CARE"]
        next1 = datetime.fromisoformat(entry1["next_attempt"])
        diff1 = (next1 - now).total_seconds() / 60
        self.assertAlmostEqual(diff1, 5, delta=1)
        
        # Second failure (attempt_count 1 -> 2, backoff 10 min)
        handle_spawn_failure(state, "CARE", "Error 2")
        entry2 = state["retry_queue"]["CARE"]
        next2 = datetime.fromisoformat(entry2["next_attempt"])
        diff2 = (next2 - now).total_seconds() / 60
        self.assertAlmostEqual(diff2, 10, delta=1)
        
        # Third failure (attempt_count 2 -> 3, backoff 20 min)
        handle_spawn_failure(state, "CARE", "Error 3")
        entry3 = state["retry_queue"]["CARE"]
        next3 = datetime.fromisoformat(entry3["next_attempt"])
        diff3 = (next3 - now).total_seconds() / 60
        self.assertAlmostEqual(diff3, 20, delta=1)
    
    def test_backoff_caps_at_60_minutes(self):
        """Backoff should max at 60 minutes."""
        state = {
            "drives": {"CARE": {"pressure": 25.0, "threshold": 20.0}},
            "retry_queue": {
                "CARE": {
                    "attempt_count": 10,  # Would be 5 * 2^10 = 5120 min without cap
                }
            }
        }
        
        handle_spawn_failure(state, "CARE", "Error")
        
        next_attempt = datetime.fromisoformat(state["retry_queue"]["CARE"]["next_attempt"])
        now = datetime.now(timezone.utc)
        diff_minutes = (next_attempt - now).total_seconds() / 60
        
        self.assertLessEqual(diff_minutes, 61)  # Allow 1 minute tolerance


class TestSpawnViaApi(unittest.TestCase):
    """Test API-based session spawning (mocked)."""
    
    @patch("core.drives.spawn.urllib.request.urlopen")
    @patch.dict("os.environ", {"OPENCLAW_GATEWAY_TOKEN": "test-token"})
    def test_successful_spawn(self, mock_urlopen):
        """Should return True on successful API call."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"success": True, "id": "session-123"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        config = {"drives": {"session_timeout": 900}}
        result = spawn_via_api("test prompt", config, "CARE", 25.0, 20.0)
        
        self.assertTrue(result)
    
    @patch("core.drives.spawn.urllib.request.urlopen")
    @patch.dict("os.environ", {"OPENCLAW_GATEWAY_TOKEN": "test-token"})
    def test_returns_true_on_id(self, mock_urlopen):
        """Should return True if response has id even without success field."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"id": "session-123"}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        config = {"drives": {"session_timeout": 900}}
        result = spawn_via_api("test prompt", config, "CARE", 25.0, 20.0)
        
        self.assertTrue(result)
    
    @patch("core.drives.spawn.urllib.request.urlopen")
    @patch.dict("os.environ", {"OPENCLAW_GATEWAY_TOKEN": "test-token"})
    def test_failed_spawn(self, mock_urlopen):
        """Should return False on API failure."""
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError(
            "http://localhost:5001/v1/cron/add", 500, "Internal Error", {}, None
        )
        
        config = {"drives": {"session_timeout": 900}}
        result = spawn_via_api("test prompt", config, "CARE", 25.0, 20.0)
        
        self.assertFalse(result)
    
    @patch.dict("os.environ", {}, clear=True)
    def test_no_token_returns_false(self):
        """Should return False if no gateway token."""
        config = {"drives": {"session_timeout": 900}}
        result = spawn_via_api("test prompt", config, "CARE", 25.0, 20.0)
        
        self.assertFalse(result)
    
    @patch("core.drives.spawn.urllib.request.urlopen")
    @patch.dict("os.environ", {"OPENCLAW_GATEWAY_TOKEN": "test-token"})
    def test_uses_configured_model(self, mock_urlopen):
        """Should include model in request if configured."""
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"success": True}).encode()
        mock_urlopen.return_value.__enter__.return_value = mock_response
        
        config = {"drives": {"session_timeout": 900, "session_model": "anthropic/claude-sonnet-4"}}
        spawn_via_api("test prompt", config, "CARE", 25.0, 20.0)
        
        # Check the request was made with model
        call_args = mock_urlopen.call_args
        req = call_args[0][0]
        self.assertIn("anthropic/claude-sonnet-4", str(req.data))


class TestSpawnViaCli(unittest.TestCase):
    """Test CLI-based session spawning (mocked)."""
    
    @patch("core.drives.spawn.subprocess.run")
    def test_successful_spawn(self, mock_run):
        """Should return session key on successful CLI call."""
        mock_run.return_value = Mock(returncode=0, stdout='{"id": "123"}')
        
        config = {"drives": {"session_timeout": 900}}
        result = spawn_via_cli("test prompt", config, "CARE", 25.0, 20.0)
        
        # Function returns session key string on success, not bool
        self.assertIsNotNone(result)
        self.assertIn("agent:main:cron:", result)
    
    @patch("core.drives.spawn.subprocess.run")
    def test_failed_spawn(self, mock_run):
        """Should return False on CLI failure."""
        mock_run.return_value = Mock(returncode=1)
        
        config = {"drives": {"session_timeout": 900}}
        result = spawn_via_cli("test prompt", config, "CARE", 25.0, 20.0)
        
        self.assertFalse(result)
    
    @patch("core.drives.spawn.subprocess.run")
    def test_command_not_found(self, mock_run):
        """Should return False if openclaw command not found."""
        mock_run.side_effect = FileNotFoundError()
        
        config = {"drives": {"session_timeout": 900}}
        result = spawn_via_cli("test prompt", config, "CARE", 25.0, 20.0)
        
        self.assertFalse(result)
    
    @patch("core.drives.spawn.subprocess.run")
    def test_timeout(self, mock_run):
        """Should return False on timeout."""
        mock_run.side_effect = subprocess.TimeoutExpired("openclaw", 60)
        
        config = {"drives": {"session_timeout": 900}}
        result = spawn_via_cli("test prompt", config, "CARE", 25.0, 20.0)
        
        self.assertFalse(result)
    
    @patch("core.drives.spawn.subprocess.run")
    def test_uses_configured_model(self, mock_run):
        """Should include model in command if configured."""
        mock_run.return_value = Mock(returncode=0)
        
        config = {"drives": {"session_timeout": 900, "session_model": "anthropic/claude-sonnet-4"}}
        spawn_via_cli("test prompt", config, "CARE", 25.0, 20.0)
        
        call_args = mock_run.call_args
        cmd = call_args[0][0]
        self.assertIn("--model", cmd)
        self.assertIn("anthropic/claude-sonnet-4", cmd)


class TestSpawnSession(unittest.TestCase):
    """Test main spawn_session function with mocked internals."""
    
    @patch("core.drives.spawn.spawn_via_api")
    @patch("core.drives.spawn.spawn_via_cli")
    def test_uses_cli_first(self, mock_cli, mock_api):
        """Should try CLI first before API fallback."""
        mock_api.return_value = True
        mock_cli.return_value = True
        
        config = {"drives": {"session_timeout": 900}}
        result = spawn_session("CARE", "Check in", config, 25.0, 20.0)
        
        self.assertTrue(result)
        mock_cli.assert_called_once()
        mock_api.assert_not_called()
    
    @patch("core.drives.spawn.spawn_via_api")
    @patch("core.drives.spawn.spawn_via_cli")
    def test_falls_back_to_api(self, mock_cli, mock_api):
        """Should fall back to API if CLI fails."""
        mock_cli.return_value = False
        mock_api.return_value = True
        
        config = {"drives": {"session_timeout": 900}}
        result = spawn_session("CARE", "Check in", config, 25.0, 20.0)
        
        self.assertTrue(result)
        mock_cli.assert_called_once()
        mock_api.assert_called_once()
    
    @patch("core.drives.spawn.spawn_via_api")
    @patch("core.drives.spawn.spawn_via_cli")
    def test_returns_false_on_both_fail(self, mock_cli, mock_api):
        """Should return False if both API and CLI fail."""
        mock_api.return_value = False
        mock_cli.return_value = False
        
        config = {"drives": {"session_timeout": 900}}
        result = spawn_session("CARE", "Check in", config, 25.0, 20.0)
        
        self.assertFalse(result)


class TestTickWithSpawning(unittest.TestCase):
    """Test tick_with_spawning integration."""
    
    @patch("core.drives.spawn.spawn_session")
    @patch("core.drives.engine.tick_all_drives")
    def test_updates_pressures(self, mock_tick, mock_spawn):
        """Should update drive pressures via tick_all_drives."""
        mock_spawn.return_value = False
        
        config = {"drives": {"cooldown_minutes": 30}}
        state = create_default_state()
        
        tick_with_spawning(config, state)
        
        mock_tick.assert_called_once_with(state, config)
    
    @patch("core.drives.spawn.spawn_session")
    @patch("core.drives.engine.tick_all_drives")
    def test_skips_spawn_during_quiet_hours(self, mock_tick, mock_spawn):
        """Should not spawn during quiet hours."""
        mock_tick.return_value = {}
        
        config = {"drives": {"cooldown_minutes": 30, "quiet_hours": [23, 7]}}
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 30.0  # Over threshold
        
        with patch("core.drives.spawn.is_quiet_hours", return_value=True):
            tick_with_spawning(config, state)
        
        mock_spawn.assert_not_called()
    
    @patch("core.drives.spawn.spawn_session")
    @patch("core.drives.engine.tick_all_drives")
    def test_spawns_session_for_triggered_drive(self, mock_tick, mock_spawn):
        """Should spawn session when drive over threshold."""
        mock_tick.return_value = {}
        mock_spawn.return_value = True
        
        config = {"drives": {"cooldown_minutes": 30}}
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 30.0  # Over threshold
        
        tick_with_spawning(config, state)
        
        mock_spawn.assert_called_once()
        call_args = mock_spawn.call_args
        self.assertEqual(call_args[1]["drive_name"], "CARE")
    
    @patch("core.drives.spawn.spawn_session")
    @patch("core.drives.engine.tick_all_drives")
    def test_adds_to_triggered_list_on_success(self, mock_tick, mock_spawn):
        """Should add drive to triggered_drives but NOT satisfy at spawn.
        
        Satisfaction happens later when the session completes — not at
        spawn time. Satisfying at spawn is "hollow satisfaction".
        """
        mock_tick.return_value = {}
        mock_spawn.return_value = True
        
        config = {"drives": {"cooldown_minutes": 30}}
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 30.0
        initial_pressure = state["drives"]["CARE"]["pressure"]
        
        tick_with_spawning(config, state)
        
        # Drive should be in triggered list (session spawned)
        self.assertIn("CARE", state.get("triggered_drives", []))
        # Pressure should NOT be reduced yet — session hasn't completed
        self.assertEqual(state["drives"]["CARE"]["pressure"], initial_pressure)
    
    @patch("core.drives.spawn.handle_spawn_failure")
    @patch("core.drives.spawn.spawn_session")
    @patch("core.drives.engine.tick_all_drives")
    def test_handles_failure(self, mock_tick, mock_spawn, mock_handle):
        """Should call handle_spawn_failure on spawn failure."""
        mock_tick.return_value = {}
        mock_spawn.return_value = False
        
        config = {"drives": {"cooldown_minutes": 30}}
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 30.0
        
        tick_with_spawning(config, state)
        
        mock_handle.assert_called_once()
    
    @patch("core.drives.spawn.spawn_session")
    @patch("core.drives.engine.tick_all_drives")
    def test_records_trigger_on_success(self, mock_tick, mock_spawn):
        """Should record trigger event on successful spawn."""
        mock_tick.return_value = {}
        mock_spawn.return_value = True
        
        config = {"drives": {"cooldown_minutes": 30}}
        state = create_default_state()
        state["drives"]["CARE"]["pressure"] = 30.0
        state["trigger_log"] = []
        
        tick_with_spawning(config, state)
        
        self.assertEqual(len(state["trigger_log"]), 1)
        self.assertEqual(state["trigger_log"][0]["drive"], "CARE")
        self.assertTrue(state["trigger_log"][0]["session_spawned"])
    
    @patch("core.drives.spawn.spawn_session")
    @patch("core.drives.engine.tick_all_drives")
    def test_max_one_session_per_tick(self, mock_tick, mock_spawn):
        """Should spawn at most one session per tick."""
        mock_tick.return_value = {}
        mock_spawn.return_value = True
        
        config = {"drives": {"cooldown_minutes": 30}}
        state = create_default_state()
        # Multiple drives over threshold
        state["drives"]["CARE"]["pressure"] = 30.0  # 150%
        state["drives"]["MAINTENANCE"]["pressure"] = 40.0  # 160%
        
        tick_with_spawning(config, state)
        
        # Should only spawn one session
        self.assertEqual(mock_spawn.call_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
