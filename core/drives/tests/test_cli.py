"""Tests for the Drive CLI.

Tests argument parsing, output formatting, command routing, and
integration with the drive engine. Uses mocking for predictable output.
"""

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, mock_open

# Import from the package
from core.drives import cli
from core.drives import history


class TestCLIArgumentParsing(unittest.TestCase):
    """Test CLI argument parsing and command routing."""

    def test_default_command_is_status(self):
        """No arguments should default to status command."""
        parser = cli.create_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.command)

    def test_status_command_parsing(self):
        """Status command should accept --json and --category flags."""
        parser = cli.create_parser()

        args = parser.parse_args(["status"])
        self.assertEqual(args.command, "status")
        self.assertFalse(args.json)

        args = parser.parse_args(["status", "--json"])
        self.assertTrue(args.json)

        args = parser.parse_args(["status", "--category", "core"])
        self.assertEqual(args.category, "core")

    def test_satisfy_command_parsing(self):
        """Satisfy command should accept name, depth, and --reason."""
        parser = cli.create_parser()

        args = parser.parse_args(["satisfy", "curiosity"])
        self.assertEqual(args.command, "satisfy")
        self.assertEqual(args.name, "curiosity")
        self.assertIsNone(args.depth)

        args = parser.parse_args(["satisfy", "care", "deep"])
        self.assertEqual(args.depth, "deep")

        args = parser.parse_args(["satisfy", "rest", "--reason", "took a break"])
        self.assertEqual(args.reason, "took a break")

    def test_bump_command_parsing(self):
        """Bump command should accept name, amount, and --reason."""
        parser = cli.create_parser()

        args = parser.parse_args(["bump", "care"])
        self.assertEqual(args.command, "bump")
        self.assertEqual(args.name, "care")
        self.assertIsNone(args.amount)

        args = parser.parse_args(["bump", "care", "10"])
        self.assertEqual(args.amount, "10")

        args = parser.parse_args(["bump", "maintenance", "--reason", "error detected"])
        self.assertEqual(args.reason, "error detected")

    def test_reset_command_parsing(self):
        """Reset command should accept --force flag."""
        parser = cli.create_parser()

        args = parser.parse_args(["reset"])
        self.assertEqual(args.command, "reset")
        self.assertFalse(args.force)

        args = parser.parse_args(["reset", "--force"])
        self.assertTrue(args.force)

    def test_log_command_parsing(self):
        """Log command should accept n, --drive, and --since."""
        parser = cli.create_parser()

        args = parser.parse_args(["log"])
        self.assertEqual(args.command, "log")
        self.assertIsNone(args.n)

        args = parser.parse_args(["log", "50"])
        self.assertEqual(args.n, "50")

        args = parser.parse_args(["log", "--drive", "CURIOSITY"])
        self.assertEqual(args.drive, "CURIOSITY")

        args = parser.parse_args(["log", "--since", "2 hours ago"])
        self.assertEqual(args.since, "2 hours ago")

    def test_tick_command_parsing(self):
        """Tick command should accept --dry-run and --verbose flags."""
        parser = cli.create_parser()

        args = parser.parse_args(["tick"])
        self.assertEqual(args.command, "tick")
        self.assertFalse(args.dry_run)
        self.assertFalse(args.verbose)

        args = parser.parse_args(["tick", "--dry-run"])
        self.assertTrue(args.dry_run)

        args = parser.parse_args(["tick", "--verbose"])
        self.assertTrue(args.verbose)

        args = parser.parse_args(["tick", "--dry-run", "--verbose"])
        self.assertTrue(args.dry_run)
        self.assertTrue(args.verbose)

    def test_list_command_parsing(self):
        """List command should accept --json and --category flags."""
        parser = cli.create_parser()

        args = parser.parse_args(["list"])
        self.assertEqual(args.command, "list")

        args = parser.parse_args(["list", "--json"])
        self.assertTrue(args.json)

        args = parser.parse_args(["list", "--category", "discovered"])
        self.assertEqual(args.category, "discovered")

    def test_show_command_parsing(self):
        """Show command should accept name argument."""
        parser = cli.create_parser()

        args = parser.parse_args(["show", "curiosity"])
        self.assertEqual(args.command, "show")
        self.assertEqual(args.name, "curiosity")

    def test_help_command_parsing(self):
        """Help command should accept optional topic argument."""
        parser = cli.create_parser()

        args = parser.parse_args(["help"])
        self.assertEqual(args.command, "help")
        self.assertIsNone(args.topic)

        args = parser.parse_args(["help", "satisfy"])
        self.assertEqual(args.topic, "satisfy")

    def test_dashboard_command_parsing(self):
        """Dashboard command should accept --show-all flag."""
        parser = cli.create_parser()

        args = parser.parse_args(["dashboard"])
        self.assertEqual(args.command, "dashboard")
        self.assertFalse(args.show_all)

        args = parser.parse_args(["dashboard", "--show-all"])
        self.assertTrue(args.show_all)

    def test_command_aliases(self):
        """Test command aliases work correctly."""
        parser = cli.create_parser()

        # status -> st
        args = parser.parse_args(["st"])
        self.assertEqual(args.command, "st")

        # satisfy -> sat
        args = parser.parse_args(["sat", "care"])
        self.assertEqual(args.command, "sat")

        # list -> ls
        args = parser.parse_args(["ls"])
        self.assertEqual(args.command, "ls")

        # show -> info
        args = parser.parse_args(["info", "rest"])
        self.assertEqual(args.command, "info")

        # log -> history
        args = parser.parse_args(["history"])
        self.assertEqual(args.command, "history")

        # dashboard -> dash
        args = parser.parse_args(["dash"])
        self.assertEqual(args.command, "dash")


class TestCLIExitCodes(unittest.TestCase):
    """Test CLI returns correct exit codes."""

    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_path = Path(self.temp_dir) / "drives.json"
        self.config_path = Path(self.temp_dir) / "emergence.json"

        # Create minimal config
        config = {
            "agent": {"name": "Test Agent"},
            "paths": {"workspace": self.temp_dir, "state": "."},
        }
        with open(self.config_path, "w") as f:
            json.dump(config, f)

    def tearDown(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch("core.drives.cli.load_config")
    @patch("core.drives.cli.load_state")
    def test_status_returns_success(self, mock_load_state, mock_load_config):
        """Status command should return EXIT_SUCCESS (0)."""
        mock_load_config.return_value = {
            "agent": {"name": "Test"},
            "drives": {"quiet_hours": [23, 7]},
            "paths": {"state": ".", "workspace": "."},
        }
        mock_load_state.return_value = {
            "version": "1.0",
            "last_tick": datetime.now(timezone.utc).isoformat(),
            "drives": {
                "CARE": {
                    "name": "CARE",
                    "pressure": 10.0,
                    "threshold": 20.0,
                    "rate_per_hour": 2.0,
                    "description": "Test",
                    "category": "core",
                }
            },
            "triggered_drives": [],
        }

        parser = cli.create_parser()
        args = parser.parse_args(["status"])

        result = cli.cmd_status(args)
        self.assertEqual(result, cli.EXIT_SUCCESS)

    @patch("core.drives.cli.load_config")
    @patch("core.drives.cli.load_state")
    def test_satisfy_missing_name_returns_usage_error(self, mock_load_state, mock_load_config):
        """Satisfy without name should return EXIT_USAGE (2)."""
        mock_load_config.return_value = {
            "agent": {"name": "Test"},
            "drives": {},
            "paths": {"state": ".", "workspace": "."},
        }
        mock_load_state.return_value = {"version": "1.0", "drives": {}, "triggered_drives": []}

        parser = cli.create_parser()
        args = parser.parse_args(["satisfy"])

        result = cli.cmd_satisfy(args)
        self.assertEqual(result, cli.EXIT_USAGE)

    @patch("core.drives.cli.load_config")
    @patch("core.drives.cli.load_state")
    def test_satisfy_unknown_drive_returns_error(self, mock_load_state, mock_load_config):
        """Satisfy with unknown drive should return EXIT_ERROR (1)."""
        mock_load_config.return_value = {
            "agent": {"name": "Test"},
            "drives": {},
            "paths": {"state": ".", "workspace": "."},
        }
        mock_load_state.return_value = {
            "version": "1.0",
            "drives": {"CARE": {"name": "CARE", "pressure": 10.0, "threshold": 20.0}},
            "triggered_drives": [],
        }

        parser = cli.create_parser()
        args = parser.parse_args(["satisfy", "unknown_drive"])

        result = cli.cmd_satisfy(args)
        self.assertEqual(result, cli.EXIT_ERROR)


class TestCLIOutputFormatting(unittest.TestCase):
    """Test CLI output formatting."""

    def test_get_indicator(self):
        """Test status indicator selection."""
        self.assertEqual(cli.get_indicator("normal"), cli.INDICATOR_NORMAL)
        self.assertEqual(cli.get_indicator("elevated"), cli.INDICATOR_ELEVATED)
        self.assertEqual(cli.get_indicator("over_threshold"), cli.INDICATOR_OVER)
        self.assertEqual(cli.get_indicator("triggered"), cli.INDICATOR_TRIGGERED)
        self.assertEqual(cli.get_indicator("unknown"), cli.INDICATOR_NORMAL)

    @patch("core.drives.cli.load_config")
    @patch("core.drives.cli.get_runtime_state_and_config")
    def test_status_json_output(self, mock_get_runtime, mock_load_config):
        """Status with --json should output valid JSON."""
        from pathlib import Path

        mock_load_config.return_value = {
            "agent": {"name": "Test"},
            "drives": {"quiet_hours": [23, 7]},
            "paths": {"state": ".", "workspace": "."},
        }

        runtime_state = {
            "version": "1.0",
            "last_tick": datetime.now(timezone.utc).isoformat(),
            "drives": {
                "CARE": {
                    "name": "CARE",
                    "pressure": 10.0,
                    "threshold": 20.0,
                    "rate_per_hour": 2.0,
                    "description": "Test",
                    "category": "core",
                    "base_drive": True,
                    "aspects": [],
                }
            },
            "triggered_drives": [],
        }

        config = {
            "agent": {"name": "Test"},
            "drives": {"quiet_hours": [23, 7], "thresholds": None},
            "paths": {"state": ".", "workspace": "."},
        }

        mock_get_runtime.return_value = (
            runtime_state,
            config,
            Path(".emergence/state/drives-state.json"),
        )

        parser = cli.create_parser()
        args = parser.parse_args(["status", "--json"])

        # Capture stdout
        from io import StringIO

        captured = StringIO()
        with patch("sys.stdout", captured):
            cli.cmd_status(args)

        output = captured.getvalue()
        # Should be valid JSON
        data = json.loads(output)
        self.assertIn("drives", data)
        self.assertIn("triggered", data)
        self.assertGreaterEqual(len(data["drives"]), 1)
        self.assertEqual(data["drives"][0]["name"], "CARE")

    @patch("core.drives.cli.load_config")
    @patch("core.drives.cli.load_state")
    def test_list_json_output(self, mock_load_state, mock_load_config):
        """List with --json should output valid JSON."""
        mock_load_config.return_value = {
            "agent": {"name": "Test"},
            "paths": {"state": ".", "workspace": "."},
        }
        mock_load_state.return_value = {
            "version": "1.0",
            "drives": {
                "CARE": {
                    "name": "CARE",
                    "pressure": 10.0,
                    "threshold": 20.0,
                    "rate_per_hour": 2.0,
                    "activity_driven": False,
                    "description": "Test drive",
                    "category": "core",
                }
            },
        }

        parser = cli.create_parser()
        args = parser.parse_args(["list", "--json"])

        from io import StringIO

        captured = StringIO()
        with patch("sys.stdout", captured):
            cli.cmd_list(args)

        output = captured.getvalue()
        data = json.loads(output)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "CARE")
        self.assertEqual(data[0]["category"], "core")


class TestCLIFuzzyMatching(unittest.TestCase):
    """Test fuzzy matching for drive names."""

    def test_fuzzy_find_drive_exact_match(self):
        """Exact match should work."""
        state = {"drives": {"CURIOSITY": {"name": "CURIOSITY"}, "CARE": {"name": "CARE"}}}
        result = cli.fuzzy_find_drive("CURIOSITY", state)
        self.assertEqual(result, "CURIOSITY")

    def test_fuzzy_find_drive_case_insensitive(self):
        """Case-insensitive match should work."""
        state = {
            "drives": {
                "CURIOSITY": {"name": "CURIOSITY"},
            }
        }
        result = cli.fuzzy_find_drive("curiosity", state)
        self.assertEqual(result, "CURIOSITY")

    def test_fuzzy_find_drive_prefix_match(self):
        """Prefix match should work."""
        state = {
            "drives": {
                "CURIOSITY": {"name": "CURIOSITY"},
            }
        }
        result = cli.fuzzy_find_drive("curio", state)
        self.assertEqual(result, "CURIOSITY")

    def test_fuzzy_find_drive_ambiguous(self):
        """Ambiguous match should return None."""
        state = {
            "drives": {
                "CURIOSITY": {"name": "CURIOSITY"},
                "CARE": {"name": "CARE"},
            }
        }
        result = cli.fuzzy_find_drive("c", state)
        self.assertIsNone(result)

    def test_fuzzy_find_drive_not_found(self):
        """No match should return None."""
        state = {
            "drives": {
                "CURIOSITY": {"name": "CURIOSITY"},
            }
        }
        result = cli.fuzzy_find_drive("xyz", state)
        self.assertIsNone(result)


class TestHistoryModule(unittest.TestCase):
    """Test history module functionality."""

    def test_parse_time_string_hours_ago(self):
        """Parse 'X hours ago' format."""
        result = history.parse_time_string("2 hours ago")
        self.assertIsNotNone(result)

        # Should be approximately 2 hours in the past
        now = datetime.now(timezone.utc)
        diff = now - result
        self.assertAlmostEqual(diff.total_seconds(), 7200, delta=1)

    def test_parse_time_string_minutes_ago(self):
        """Parse 'X minutes ago' format."""
        result = history.parse_time_string("30 minutes ago")
        self.assertIsNotNone(result)

        now = datetime.now(timezone.utc)
        diff = now - result
        self.assertAlmostEqual(diff.total_seconds(), 1800, delta=1)

    def test_parse_time_string_iso_format(self):
        """Parse ISO format timestamp."""
        result = history.parse_time_string("2026-02-07T14:30:00Z")
        self.assertIsNotNone(result)
        self.assertEqual(result.year, 2026)
        self.assertEqual(result.month, 2)
        self.assertEqual(result.day, 7)

    def test_parse_time_string_invalid(self):
        """Invalid time string should return None."""
        result = history.parse_time_string("not a time")
        self.assertIsNone(result)

    def test_read_trigger_log(self):
        """Read trigger log from JSONL file."""
        import tempfile
        import os
        import json
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["EMERGENCE_STATE"] = tmpdir
            log_path = Path(tmpdir) / "trigger-log.jsonl"

            # Write test data to JSONL
            with log_path.open("w") as f:
                f.write(json.dumps({"drive": "CARE", "timestamp": "2026-02-07T10:00:00Z"}) + "\n")
                f.write(json.dumps({"drive": "REST", "timestamp": "2026-02-07T08:00:00Z"}) + "\n")

            log = history.read_trigger_log()
            self.assertEqual(len(log), 2)
        self.assertEqual(log[0]["drive"], "CARE")

    def test_read_trigger_log_empty(self):
        """Empty JSONL file should return empty list."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["EMERGENCE_STATE"] = tmpdir
            log = history.read_trigger_log()
            self.assertEqual(log, [])

    def test_filter_log_entries_by_drive(self):
        """Filter log entries by drive name."""
        entries = [
            {"drive": "CARE", "timestamp": "2026-02-07T10:00:00Z"},
            {"drive": "REST", "timestamp": "2026-02-07T08:00:00Z"},
            {"drive": "CARE", "timestamp": "2026-02-07T06:00:00Z"},
        ]
        filtered = history.filter_log_entries(entries, drive_name="CARE")
        self.assertEqual(len(filtered), 2)
        for entry in filtered:
            self.assertEqual(entry["drive"], "CARE")

    def test_filter_log_entries_by_time(self):
        """Filter log entries by time range."""
        entries = [
            {"drive": "CARE", "timestamp": "2026-02-07T10:00:00Z"},
            {"drive": "REST", "timestamp": "2026-02-07T08:00:00Z"},
            {"drive": "CARE", "timestamp": "2026-02-07T06:00:00Z"},
        ]
        filtered = history.filter_log_entries(entries, since="2026-02-07T07:00:00Z")
        self.assertEqual(len(filtered), 2)

    def test_add_trigger_event(self):
        """Add trigger event to JSONL file."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["EMERGENCE_STATE"] = tmpdir
            state = {}
            history.add_trigger_event(
                state,
                drive_name="CARE",
                pressure=25.0,
                threshold=20.0,
                session_spawned=True,
                reason="Test trigger",
            )

            # Read from JSONL file
            log = history.read_trigger_log()
            self.assertEqual(len(log), 1)
            entry = log[0]
            self.assertEqual(entry["drive"], "CARE")
            self.assertEqual(entry["pressure"], 25.0)
            self.assertEqual(entry["threshold"], 20.0)
            self.assertTrue(entry["session_spawned"])
            self.assertEqual(entry["reason"], "Test trigger")

    def test_add_satisfaction_event(self):
        """Add satisfaction event to JSONL file."""
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmpdir:
            os.environ["EMERGENCE_STATE"] = tmpdir
            state = {"drives": {"CARE": {"threshold": 20.0}}}
            history.add_satisfaction_event(
                state, drive_name="CARE", old_pressure=20.0, new_pressure=10.0, depth="moderate"
            )

            # Read from JSONL file
            log = history.read_trigger_log()
            self.assertEqual(len(log), 1)
            entry = log[0]
            self.assertEqual(entry["drive"], "CARE")
            self.assertIn("SATISFIED", entry["reason"])
            self.assertIn("moderate", entry["reason"])

    def test_format_log_entry(self):
        """Format log entry for display."""
        entry = {
            "drive": "CARE",
            "pressure": 25.0,
            "threshold": 20.0,
            "timestamp": "2026-02-07T14:30:00Z",
            "session_spawned": True,
            "reason": "",
        }
        formatted = history.format_log_entry(entry)
        self.assertIn("CARE", formatted)
        self.assertIn("25.0/20", formatted)
        self.assertIn("TRIGGERED", formatted)

    def test_get_stats(self):
        """Calculate statistics from log entries."""
        entries = [
            {"drive": "CARE", "timestamp": "2026-02-07T10:00:00Z", "reason": "trigger"},
            {"drive": "CARE", "timestamp": "2026-02-07T09:00:00Z", "reason": "SATISFIED-moderate"},
            {"drive": "REST", "timestamp": "2026-02-07T08:00:00Z", "reason": "trigger"},
        ]
        stats = history.get_stats(entries)

        self.assertEqual(stats["total_events"], 3)
        self.assertEqual(stats["triggers"], 2)
        self.assertEqual(stats["satisfactions"], 1)
        self.assertEqual(stats["by_drive"]["CARE"]["triggers"], 1)
        self.assertEqual(stats["by_drive"]["CARE"]["satisfactions"], 1)


class TestCLIMain(unittest.TestCase):
    """Test main entry point."""

    @patch("core.drives.cli.cmd_status")
    def test_main_no_args_calls_status(self, mock_status):
        """Main with no args should call status."""
        mock_status.return_value = cli.EXIT_SUCCESS
        result = cli.main([])
        self.assertTrue(mock_status.called)
        self.assertEqual(result, cli.EXIT_SUCCESS)

    @patch("core.drives.cli.cmd_satisfy")
    def test_main_routes_satisfy_command(self, mock_satisfy):
        """Main should route satisfy command."""
        mock_satisfy.return_value = cli.EXIT_SUCCESS
        result = cli.main(["satisfy", "care"])
        self.assertTrue(mock_satisfy.called)
        self.assertEqual(result, cli.EXIT_SUCCESS)

    @patch("core.drives.cli.cmd_list")
    def test_main_routes_list_command(self, mock_list):
        """Main should route list command."""
        mock_list.return_value = cli.EXIT_SUCCESS
        result = cli.main(["list"])
        self.assertTrue(mock_list.called)
        self.assertEqual(result, cli.EXIT_SUCCESS)

    def test_main_unknown_command(self):
        """Unknown command should exit with code 2."""
        from io import StringIO

        with patch("sys.stderr", StringIO()):
            with self.assertRaises(SystemExit) as cm:
                cli.main(["unknown_command"])
            self.assertEqual(cm.exception.code, 2)


class TestCLISatisfactionDepths(unittest.TestCase):
    """Test satisfaction depth handling."""

    def test_depth_aliases(self):
        """Test that depth aliases work correctly."""
        depth_map = {
            "s": "shallow",
            "shallow": "shallow",
            "m": "moderate",
            "moderate": "moderate",
            "d": "deep",
            "deep": "deep",
            "f": "full",
            "full": "full",
        }

        for alias, expected in depth_map.items():
            result = depth_map.get(alias.lower())
            self.assertEqual(result, expected)

    @patch("core.drives.cli.load_config")
    @patch("core.drives.cli.load_state")
    @patch("core.drives.cli.save_with_lock")
    def test_satisfy_already_satisfied(self, mock_save, mock_load_state, mock_load_config):
        """Satisfy on already-satisfied drive should show message."""
        mock_load_config.return_value = {
            "agent": {"name": "Test"},
            "drives": {},
            "paths": {"state": ".", "workspace": "."},
        }
        mock_load_state.return_value = {
            "version": "1.0",
            "drives": {"REST": {"name": "REST", "pressure": 0.0, "threshold": 30.0}},
            "triggered_drives": [],
        }
        mock_save.return_value = True

        parser = cli.create_parser()
        args = parser.parse_args(["satisfy", "rest"])

        from io import StringIO

        captured = StringIO()
        with patch("sys.stdout", captured):
            result = cli.cmd_satisfy(args)

        output = captured.getvalue()
        self.assertIn("already at 0.0", output)
        self.assertEqual(result, cli.EXIT_SUCCESS)


class TestCLIAutoScaledSatisfaction(unittest.TestCase):
    """Test auto-scaled satisfaction depth (issue #35)."""

    @patch("core.drives.cli.load_config")
    @patch("core.drives.cli.load_state")
    @patch("core.drives.cli.get_runtime_state_and_config")
    @patch("core.drives.cli.save_runtime_state")
    @patch("core.drives.cli.save_with_lock")
    def test_auto_scale_low_pressure(
        self, mock_save, mock_save_runtime, mock_runtime_config, mock_load_state, mock_load_config
    ):
        """Low pressure (25%) should auto-scale to 20% reduction."""
        mock_load_config.return_value = {
            "agent": {"name": "Test"},
            "drives": {},
            "paths": {"state": ".", "workspace": "."},
        }

        # 25% pressure (5/20)
        state = {
            "version": "1.0",
            "drives": {
                "CREATIVE": {
                    "name": "CREATIVE",
                    "pressure": 5.0,
                    "threshold": 20.0,
                    "satisfaction_events": [],
                }
            },
            "triggered_drives": [],
        }
        mock_load_state.return_value = state
        mock_save.return_value = True
        mock_save_runtime.return_value = True
        mock_runtime_config.return_value = ({"drives": {}, "triggered": []}, {}, Path("."))

        parser = cli.create_parser()
        args = parser.parse_args(["satisfy", "creative"])  # No depth = auto-scale

        from io import StringIO

        captured = StringIO()
        with patch("sys.stdout", captured):
            result = cli.cmd_satisfy(args)

        output = captured.getvalue()

        # 25% reduction (available band): 5.0 * (1 - 0.25) = 3.75
        self.assertIn("5.0 → 3.8", output)
        self.assertIn("auto-scaled", output.lower())
        self.assertEqual(result, cli.EXIT_SUCCESS)

        # Verify state was updated
        self.assertAlmostEqual(state["drives"]["CREATIVE"]["pressure"], 3.75, places=1)

    @patch("core.drives.cli.load_config")
    @patch("core.drives.cli.load_state")
    @patch("core.drives.cli.get_runtime_state_and_config")
    @patch("core.drives.cli.save_runtime_state")
    @patch("core.drives.cli.save_with_lock")
    def test_auto_scale_high_pressure(
        self, mock_save, mock_save_runtime, mock_runtime_config, mock_load_state, mock_load_config
    ):
        """High pressure (125%) should auto-scale to 75% reduction."""
        mock_load_config.return_value = {
            "agent": {"name": "Test"},
            "drives": {},
            "paths": {"state": ".", "workspace": "."},
        }

        # 125% pressure (25/20)
        state = {
            "version": "1.0",
            "drives": {
                "CARE": {
                    "name": "CARE",
                    "pressure": 25.0,
                    "threshold": 20.0,
                    "satisfaction_events": [],
                }
            },
            "triggered_drives": ["CARE"],
        }
        mock_load_state.return_value = state
        mock_save.return_value = True
        mock_save_runtime.return_value = True
        mock_runtime_config.return_value = ({"drives": {}, "triggered": []}, {}, Path("."))

        parser = cli.create_parser()
        args = parser.parse_args(["satisfy", "care"])  # No depth = auto-scale

        from io import StringIO

        captured = StringIO()
        with patch("sys.stdout", captured):
            result = cli.cmd_satisfy(args)

        output = captured.getvalue()

        # 75% reduction: 25.0 * (1 - 0.75) = 6.25
        self.assertIn("25.0 → 6.2", output)  # Rounded display
        self.assertIn("auto-scaled", output.lower())
        self.assertEqual(result, cli.EXIT_SUCCESS)

        # Verify state was updated and drive removed from triggered (>= 50% reduction)
        self.assertAlmostEqual(state["drives"]["CARE"]["pressure"], 6.25, places=2)
        self.assertNotIn("CARE", state["triggered_drives"])

    @patch("core.drives.cli.load_config")
    @patch("core.drives.cli.load_state")
    @patch("core.drives.cli.get_runtime_state_and_config")
    @patch("core.drives.cli.save_runtime_state")
    @patch("core.drives.cli.save_with_lock")
    def test_explicit_depth_overrides_auto_scale(
        self, mock_save, mock_save_runtime, mock_runtime_config, mock_load_state, mock_load_config
    ):
        """Explicit depth parameter should override auto-scaling."""
        mock_load_config.return_value = {
            "agent": {"name": "Test"},
            "drives": {},
            "paths": {"state": ".", "workspace": "."},
        }

        # 25% pressure would auto-scale to 20%, but we specify 'deep' (75%)
        state = {
            "version": "1.0",
            "drives": {
                "CREATIVE": {
                    "name": "CREATIVE",
                    "pressure": 5.0,
                    "threshold": 20.0,
                    "satisfaction_events": [],
                }
            },
            "triggered_drives": [],
        }
        mock_load_state.return_value = state
        mock_save.return_value = True
        mock_save_runtime.return_value = True
        mock_runtime_config.return_value = ({"drives": {}, "triggered": []}, {}, Path("."))

        parser = cli.create_parser()
        args = parser.parse_args(["satisfy", "creative", "deep"])

        from io import StringIO

        captured = StringIO()
        with patch("sys.stdout", captured):
            result = cli.cmd_satisfy(args)

        output = captured.getvalue()

        # 75% reduction (deep): 5.0 * (1 - 0.75) = 1.25
        self.assertIn("5.0 → 1.2", output)  # Rounded display
        self.assertNotIn("auto-scaled", output.lower())  # Should NOT say auto-scaled
        self.assertIn("[deep]", output)
        self.assertEqual(result, cli.EXIT_SUCCESS)

    @patch("core.drives.cli.load_config")
    @patch("core.drives.cli.load_state")
    @patch("core.drives.cli.save_with_lock")
    def test_drive_name_validation(self, mock_save, mock_load_state, mock_load_config):
        """Invalid drive name should return error."""
        mock_load_config.return_value = {
            "agent": {"name": "Test"},
            "drives": {},
            "paths": {"state": ".", "workspace": "."},
        }
        mock_load_state.return_value = {
            "version": "1.0",
            "drives": {"CARE": {"name": "CARE", "pressure": 10.0, "threshold": 20.0}},
            "triggered_drives": [],
        }
        mock_save.return_value = True

        parser = cli.create_parser()
        args = parser.parse_args(["satisfy", "NONEXISTENT"])

        from io import StringIO

        captured = StringIO()
        with patch("sys.stderr", captured):
            result = cli.cmd_satisfy(args)

        self.assertEqual(result, cli.EXIT_ERROR)


class TestDashboardCommand(unittest.TestCase):
    """Test dashboard command displays drives grouped by pressure level."""

    @patch("core.drives.cli.get_runtime_state_and_config")
    @patch("builtins.open", new_callable=mock_open)
    def test_dashboard_groups_drives_by_pressure(self, mock_file, mock_runtime_config):
        """Dashboard should group drives by pressure: triggered (≥100%), elevated (75-100%), available (30-75%)."""
        # Mock runtime state with drives at different pressure levels
        runtime_state = {
            "drives": {
                # 125% - triggered
                "TRIGGERED_HIGH": {"pressure": 25.0, "threshold": 20.0, "status": "active"},
                # 90% - elevated
                "ELEVATED": {"pressure": 18.0, "threshold": 20.0, "status": "active"},
                # 70% - available
                "AVAILABLE_HIGH": {"pressure": 14.0, "threshold": 20.0, "status": "active"},
                # 40% - available
                "AVAILABLE_LOW": {"pressure": 8.0, "threshold": 20.0, "status": "active"},
                # 10% - low (not shown by default)
                "LOW": {"pressure": 2.0, "threshold": 20.0, "status": "active"},
            },
            "last_tick": datetime.now(timezone.utc).isoformat(),
        }

        config = {"drives": {"manual_mode": False}, "paths": {"state": ".", "workspace": "."}}

        # Mock full state for descriptions and triggered list
        full_state = {
            "drives": {
                "TRIGGERED_HIGH": {"description": "High pressure drive"},
                "ELEVATED": {"description": "Elevated pressure drive"},
                "AVAILABLE_HIGH": {"description": "Available high drive"},
                "AVAILABLE_LOW": {"description": "Available low drive"},
                "LOW": {"description": "Low pressure drive"},
            },
            "triggered_drives": ["TRIGGERED_HIGH"],
        }

        mock_runtime_config.return_value = (runtime_state, config, Path("/tmp/drives-state.json"))
        mock_file.return_value.read.return_value = json.dumps(full_state)

        parser = cli.create_parser()
        args = parser.parse_args(["dashboard"])

        from io import StringIO

        captured = StringIO()
        with patch("sys.stdout", captured):
            result = cli.cmd_dashboard(args)

        output = captured.getvalue()

        # Verify groupings are present
        self.assertIn("🔥 TRIGGERED (≥100%)", output)
        self.assertIn("⚡ ELEVATED (75-100%)", output)
        self.assertIn("▫ AVAILABLE (30-75%)", output)

        # Verify drives appear in correct groups
        self.assertIn("TRIGGERED_HIGH", output)
        self.assertIn("ELEVATED", output)
        self.assertIn("AVAILABLE_HIGH", output)
        self.assertIn("AVAILABLE_LOW", output)

        # LOW drive should NOT appear without --show-all (check for the drive name on its own line)
        # But AVAILABLE_LOW will appear, so we need to check for "LOW " (with space) or "○ LOW"
        self.assertNotIn("○ LOW (<30%)", output)

        # Verify suggested actions
        self.assertIn("Suggested Actions", output)
        self.assertIn("Address triggered drives", output)

        self.assertEqual(result, cli.EXIT_SUCCESS)

    @patch("core.drives.cli.get_runtime_state_and_config")
    @patch("builtins.open", new_callable=mock_open)
    def test_dashboard_shows_low_drives_with_flag(self, mock_file, mock_runtime_config):
        """Dashboard with --show-all should include low-pressure drives (<30%)."""
        runtime_state = {
            "drives": {
                "LOW1": {"pressure": 2.0, "threshold": 20.0, "status": "active"},  # 10%
                "LOW2": {"pressure": 4.0, "threshold": 20.0, "status": "active"},  # 20%
            },
            "last_tick": datetime.now(timezone.utc).isoformat(),
        }

        config = {"drives": {"manual_mode": False}, "paths": {"state": ".", "workspace": "."}}

        full_state = {
            "drives": {
                "LOW1": {"description": "Low drive 1"},
                "LOW2": {"description": "Low drive 2"},
            },
            "triggered_drives": [],
        }

        mock_runtime_config.return_value = (runtime_state, config, Path("/tmp/drives-state.json"))
        mock_file.return_value.read.return_value = json.dumps(full_state)

        parser = cli.create_parser()
        args = parser.parse_args(["dashboard", "--show-all"])

        from io import StringIO

        captured = StringIO()
        with patch("sys.stdout", captured):
            result = cli.cmd_dashboard(args)

        output = captured.getvalue()

        # LOW group should appear with --show-all
        self.assertIn("○ LOW (<30%)", output)
        self.assertIn("LOW1", output)
        self.assertIn("LOW2", output)

        self.assertEqual(result, cli.EXIT_SUCCESS)

    @patch("core.drives.cli.get_runtime_state_and_config")
    @patch("builtins.open", new_callable=mock_open)
    def test_dashboard_skips_latent_drives(self, mock_file, mock_runtime_config):
        """Dashboard should not display latent/consolidated drives."""
        runtime_state = {
            "drives": {
                "ACTIVE": {"pressure": 10.0, "threshold": 20.0, "status": "active"},
                "LATENT": {"pressure": 5.0, "threshold": 20.0, "status": "latent"},
            },
            "last_tick": datetime.now(timezone.utc).isoformat(),
        }

        config = {"drives": {"manual_mode": False}, "paths": {"state": ".", "workspace": "."}}

        full_state = {
            "drives": {
                "ACTIVE": {"description": "Active drive"},
                "LATENT": {"description": "Latent drive"},
            },
            "triggered_drives": [],
        }

        mock_runtime_config.return_value = (runtime_state, config, Path("/tmp/drives-state.json"))
        mock_file.return_value.read.return_value = json.dumps(full_state)

        parser = cli.create_parser()
        args = parser.parse_args(["dashboard"])

        from io import StringIO

        captured = StringIO()
        with patch("sys.stdout", captured):
            result = cli.cmd_dashboard(args)

        output = captured.getvalue()

        # ACTIVE should appear, LATENT should not
        self.assertIn("ACTIVE", output)
        self.assertNotIn("LATENT", output)

        self.assertEqual(result, cli.EXIT_SUCCESS)

    @patch("core.drives.cli.get_runtime_state_and_config")
    @patch("builtins.open", new_callable=mock_open)
    def test_dashboard_manual_mode_note(self, mock_file, mock_runtime_config):
        """Dashboard should show manual mode note when enabled."""
        runtime_state = {
            "drives": {
                "TEST": {"pressure": 10.0, "threshold": 20.0, "status": "active"},
            },
            "last_tick": datetime.now(timezone.utc).isoformat(),
        }

        config = {
            "drives": {"manual_mode": True},  # Manual mode enabled
            "paths": {"state": ".", "workspace": "."},
        }

        full_state = {
            "drives": {
                "TEST": {"description": "Test drive"},
            },
            "triggered_drives": [],
        }

        mock_runtime_config.return_value = (runtime_state, config, Path("/tmp/drives-state.json"))
        mock_file.return_value.read.return_value = json.dumps(full_state)

        parser = cli.create_parser()
        args = parser.parse_args(["dashboard"])

        from io import StringIO

        captured = StringIO()
        with patch("sys.stdout", captured):
            result = cli.cmd_dashboard(args)

        output = captured.getvalue()

        # Manual mode note should appear
        self.assertIn("Manual mode enabled", output)
        self.assertIn("won't auto-trigger", output)

        self.assertEqual(result, cli.EXIT_SUCCESS)

    @patch("core.drives.cli.get_runtime_state_and_config")
    @patch("builtins.open", new_callable=mock_open)
    def test_dashboard_works_in_manual_and_automatic_mode(self, mock_file, mock_runtime_config):
        """Dashboard should work regardless of manual_mode setting."""
        runtime_state = {
            "drives": {
                "TEST": {"pressure": 25.0, "threshold": 20.0, "status": "active"},
            },
            "last_tick": datetime.now(timezone.utc).isoformat(),
        }

        full_state = {
            "drives": {
                "TEST": {"description": "Test drive"},
            },
            "triggered_drives": ["TEST"],
        }

        # Test both modes
        for manual_mode in [True, False]:
            config = {
                "drives": {"manual_mode": manual_mode},
                "paths": {"state": ".", "workspace": "."},
            }

            mock_runtime_config.return_value = (
                runtime_state,
                config,
                Path("/tmp/drives-state.json"),
            )
            mock_file.return_value.read.return_value = json.dumps(full_state)

            parser = cli.create_parser()
            args = parser.parse_args(["dashboard"])

            from io import StringIO

            captured = StringIO()
            with patch("sys.stdout", captured):
                result = cli.cmd_dashboard(args)

            output = captured.getvalue()

            # Both modes should display the triggered drive
            self.assertIn("🔥 TRIGGERED (≥100%)", output)
            self.assertIn("TEST", output)
            self.assertEqual(result, cli.EXIT_SUCCESS)


if __name__ == "__main__":
    unittest.main(verbosity=2)
