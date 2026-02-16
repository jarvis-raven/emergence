"""Tests for the drive daemon implementation.

Tests PID file management, platform detection, daemon status,
signal handling, and lifecycle management.
"""

from core.drives import daemon
from core.drives import platform as platform_module
from core.drives import pidfile
import os
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestPidFile(unittest.TestCase):
    """Test PID file management functions."""

    def setUp(self):
        """Create a temporary directory for test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.pid_path = Path(self.temp_dir.name) / "test.pid"

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_write_pid_creates_file(self):
        """write_pid should create a PID file with current PID."""
        result = pidfile.write_pid(self.pid_path)

        self.assertTrue(result)
        self.assertTrue(self.pid_path.exists())

        content = self.pid_path.read_text().strip()
        self.assertEqual(content, str(os.getpid()))

    def test_write_pid_creates_parent_directories(self):
        """write_pid should create parent directories if needed."""
        nested_path = Path(self.temp_dir.name) / "deep" / "nested" / "test.pid"

        result = pidfile.write_pid(nested_path)

        self.assertTrue(result)
        self.assertTrue(nested_path.exists())

    def test_read_pid_returns_none_for_missing_file(self):
        """read_pid should return None if file doesn't exist."""
        result = pidfile.read_pid(self.pid_path)

        self.assertIsNone(result)

    def test_read_pid_returns_valid_pid(self):
        """read_pid should return the PID from file."""
        test_pid = 12345
        self.pid_path.write_text(str(test_pid))

        result = pidfile.read_pid(self.pid_path)

        self.assertEqual(result, test_pid)

    def test_read_pid_returns_none_for_invalid_content(self):
        """read_pid should return None for non-integer content."""
        self.pid_path.write_text("not a number")

        result = pidfile.read_pid(self.pid_path)

        self.assertIsNone(result)

    def test_read_pid_returns_none_for_empty_file(self):
        """read_pid should return None for empty file."""
        self.pid_path.write_text("")

        result = pidfile.read_pid(self.pid_path)

        self.assertIsNone(result)

    def test_remove_pid_deletes_file(self):
        """remove_pid should delete the PID file."""
        self.pid_path.write_text(str(os.getpid()))

        result = pidfile.remove_pid(self.pid_path)

        self.assertTrue(result)
        self.assertFalse(self.pid_path.exists())

    def test_remove_pid_returns_true_for_missing_file(self):
        """remove_pid should return True if file doesn't exist."""
        result = pidfile.remove_pid(self.pid_path)

        self.assertTrue(result)

    def test_is_process_alive_current_process(self):
        """is_process_alive should return True for current process."""
        result = pidfile.is_process_alive(os.getpid())

        self.assertTrue(result)

    def test_is_process_alive_invalid_pid(self):
        """is_process_alive should return False for invalid PID."""
        result = pidfile.is_process_alive(99999999)

        self.assertFalse(result)

    def test_is_process_alive_zero_pid(self):
        """is_process_alive should return False for zero/negative PID."""
        self.assertFalse(pidfile.is_process_alive(0))
        self.assertFalse(pidfile.is_process_alive(-1))

    def test_is_running_false_for_missing_file(self):
        """is_running should return False when PID file doesn't exist."""
        running, pid = pidfile.is_running(self.pid_path)

        self.assertFalse(running)
        self.assertIsNone(pid)

    def test_is_running_true_for_running_process(self):
        """is_running should return True when PID file points to running process."""
        pidfile.write_pid(self.pid_path)

        running, pid = pidfile.is_running(self.pid_path)

        self.assertTrue(running)
        self.assertEqual(pid, os.getpid())

    def test_is_running_false_for_dead_process(self):
        """is_running should return False and cleanup stale PID file."""
        self.pid_path.write_text("99999999")  # Invalid PID

        running, pid = pidfile.is_running(self.pid_path)

        self.assertFalse(running)
        self.assertIsNone(pid)
        self.assertFalse(self.pid_path.exists())  # Should clean up stale file

    def test_acquire_pidfile_success(self):
        """acquire_pidfile should succeed when no daemon running."""
        acquired, blocking_pid = pidfile.acquire_pidfile(self.pid_path)

        self.assertTrue(acquired)
        self.assertIsNone(blocking_pid)
        self.assertTrue(self.pid_path.exists())

    def test_acquire_pidfile_fails_when_running(self):
        """acquire_pidfile should fail when daemon already running."""
        # First, write a PID for current process
        pidfile.write_pid(self.pid_path)

        # Now try to acquire (should fail since we're "running")
        acquired, blocking_pid = pidfile.acquire_pidfile(self.pid_path)

        # This should succeed because it's the same PID
        self.assertTrue(acquired)

        # Test with different PID
        self.pid_path.write_text("12345")
        with patch("core.drives.pidfile.is_process_alive", return_value=True):
            acquired, blocking_pid = pidfile.acquire_pidfile(self.pid_path)
            self.assertFalse(acquired)
            self.assertEqual(blocking_pid, 12345)


class TestPlatformDetection(unittest.TestCase):
    """Test platform detection and installation functions."""

    def test_detect_platform_returns_valid_value(self):
        """detect_platform should return a valid platform string."""
        result = platform_module.detect_platform()

        self.assertIn(result, ["macos", "linux", "generic"])

    def test_detect_platform_darwin_is_macos(self):
        """detect_platform should return 'macos' on Darwin."""
        with patch("platform.system", return_value="Darwin"):
            result = platform_module.detect_platform()
            self.assertEqual(result, "macos")

    def test_detect_platform_linux_is_linux(self):
        """detect_platform should return 'linux' on Linux."""
        with patch("platform.system", return_value="Linux"):
            result = platform_module.detect_platform()
            self.assertEqual(result, "linux")

    def test_detect_platform_windows_is_generic(self):
        """detect_platform should return 'generic' on Windows."""
        with patch("platform.system", return_value="Windows"):
            result = platform_module.detect_platform()
            self.assertEqual(result, "generic")

    def test_get_launchagent_dir(self):
        """get_launchagent_dir should return ~/Library/LaunchAgents."""
        result = platform_module.get_launchagent_dir()

        expected = Path.home() / "Library" / "LaunchAgents"
        self.assertEqual(result, expected)

    def test_get_systemd_dir(self):
        """get_systemd_dir should return ~/.config/systemd/user."""
        result = platform_module.get_systemd_dir()

        expected = Path.home() / ".config" / "systemd" / "user"
        self.assertEqual(result, expected)

    def test_generate_launchagent_plist_contains_key_values(self):
        """generate_launchagent_plist should contain expected configuration."""
        config = {"drives": {"tick_interval": 600}, "paths": {"workspace": "/test/workspace"}}

        plist = platform_module.generate_launchagent_plist(config)

        self.assertIn("com.emergence.drives", plist)
        self.assertIn("600", plist)  # tick_interval
        self.assertIn("/test/workspace", plist)
        self.assertIn('<?xml version="1.0"', plist)

    @unittest.skipUnless(sys.platform.startswith("linux"), "systemd tests only run on Linux")
    def test_generate_systemd_service_contains_key_values(self):
        """generate_systemd_service should contain expected configuration."""
        config = {"paths": {"workspace": "/test/workspace"}}

        service = platform_module.generate_systemd_service(config)

        self.assertIn("[Unit]", service)
        self.assertIn("[Service]", service)
        self.assertIn("/test/workspace", service)
        self.assertIn("Restart=on-failure", service)

    def test_generate_systemd_timer_contains_key_values(self):
        """generate_systemd_timer should contain expected configuration."""
        config = {"drives": {"tick_interval": 900}}

        timer = platform_module.generate_systemd_timer(config)

        self.assertIn("[Timer]", timer)
        self.assertIn("900s", timer)

    def test_generate_cron_entry_format(self):
        """generate_cron_entry should produce valid cron format."""
        config = {
            "drives": {"tick_interval": 900},  # 15 minutes
            "paths": {"workspace": "/test/workspace"},
        }

        cron = platform_module.generate_cron_entry(config)

        self.assertIn("*/15 * * * *", cron)
        self.assertIn("/test/workspace", cron)
        self.assertIn("tick", cron)

    def test_generate_cron_entry_hourly(self):
        """generate_cron_entry should format hourly intervals correctly."""
        config = {"drives": {"tick_interval": 3600}, "paths": {"workspace": "/test"}}  # 1 hour

        cron = platform_module.generate_cron_entry(config)

        self.assertIn("0 */1 * * *", cron)


class TestDaemonStatus(unittest.TestCase):
    """Test daemon status checking functions."""

    def setUp(self):
        """Create a temporary directory for test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = {
            "paths": {"workspace": self.temp_dir.name, "state": ".emergence/state"},
            "drives": {"tick_interval": 900},
        }

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_daemon_status_not_running(self):
        """daemon_status should return running=False when no PID file."""
        status = daemon.daemon_status(self.config)

        self.assertFalse(status["running"])
        self.assertIsNone(status["pid"])

    def test_daemon_status_running(self):
        """daemon_status should return running=True when daemon is running."""
        # Create PID file with current PID
        pid_path = Path(self.temp_dir.name) / ".emergence" / "drives.pid"
        pid_path.parent.mkdir(parents=True, exist_ok=True)
        pid_path.write_text(str(os.getpid()))

        status = daemon.daemon_status(self.config)

        self.assertTrue(status["running"])
        self.assertEqual(status["pid"], os.getpid())

    def test_get_daemon_log_path(self):
        """get_daemon_log_path should return correct path."""
        log_path = daemon.get_daemon_log_path(self.config)

        expected = Path(self.temp_dir.name) / ".emergence" / "logs" / "daemon.log"
        self.assertEqual(log_path, expected)


class TestSignalHandling(unittest.TestCase):
    """Test daemon signal handling."""

    def test_setup_signals_registers_handlers(self):
        """setup_signals should register signal handlers."""
        with patch("signal.signal") as mock_signal:
            daemon.setup_signals()

            # Should register SIGTERM, SIGHUP, and SIGINT
            calls = mock_signal.call_args_list
            signals = [call[0][0] for call in calls]

            self.assertIn(signal.SIGTERM, signals)
            self.assertIn(signal.SIGHUP, signals)
            self.assertIn(signal.SIGINT, signals)

    def test_sigterm_handler_sets_flag(self):
        """SIGTERM handler should set shutdown flag."""
        # Reset flag
        daemon._shutdown_requested = False

        # Simulate signal
        daemon._handle_sigterm(signal.SIGTERM, None)

        self.assertTrue(daemon._shutdown_requested)

        # Reset for other tests
        daemon._shutdown_requested = False

    def test_sighup_handler_sets_flag(self):
        """SIGHUP handler should set reload flag."""
        # Reset flag
        daemon._config_reload_requested = False

        # Simulate signal
        daemon._handle_sighup(signal.SIGHUP, None)

        self.assertTrue(daemon._config_reload_requested)

        # Reset for other tests
        daemon._config_reload_requested = False


class TestLogWriting(unittest.TestCase):
    """Test daemon log writing."""

    def setUp(self):
        """Create a temporary directory for test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_path = Path(self.temp_dir.name) / "daemon.log"

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_write_log_creates_file(self):
        """write_log should create log file."""
        daemon.write_log(self.log_path, "Test message")

        self.assertTrue(self.log_path.exists())
        content = self.log_path.read_text()
        self.assertIn("Test message", content)
        self.assertIn("[INFO]", content)

    def test_write_log_appends(self):
        """write_log should append to existing log file."""
        daemon.write_log(self.log_path, "First message")
        daemon.write_log(self.log_path, "Second message")

        content = self.log_path.read_text()
        self.assertIn("First message", content)
        self.assertIn("Second message", content)

    def test_write_log_includes_level(self):
        """write_log should include log level."""
        daemon.write_log(self.log_path, "Warning", level="WARN")

        content = self.log_path.read_text()
        self.assertIn("[WARN]", content)

    def test_write_log_creates_directories(self):
        """write_log should create parent directories."""
        nested_log = Path(self.temp_dir.name) / "deep" / "nested" / "daemon.log"

        daemon.write_log(nested_log, "Test")

        self.assertTrue(nested_log.exists())


class TestTickCycle(unittest.TestCase):
    """Test the tick cycle execution."""

    def setUp(self):
        """Create a temporary directory and state."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = {
            "paths": {"workspace": self.temp_dir.name, "state": ".emergence/state"},
            "drives": {
                "tick_interval": 900,
                "max_pressure_ratio": 1.5,
                "manual_mode": False,  # Default v0.2.x behavior
            },
        }
        self.state_path = Path(self.temp_dir.name) / ".emergence" / "state" / "drives.json"
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.log_path = Path(self.temp_dir.name) / "daemon.log"

        # Create initial state
        from core.drives.state import create_default_state

        self.state = create_default_state()
        self.state["drives"]["CARE"]["pressure"] = 15.0  # Below threshold

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_run_tick_cycle_updates_pressures(self):
        """run_tick_cycle should update drive pressures."""
        from core.drives.state import save_state

        save_state(self.state_path, self.state)

        result = daemon.run_tick_cycle(self.state, self.config, self.state_path, self.log_path)

        self.assertIn("CARE", [u["name"] for u in result["updated"]])

    def test_run_tick_cycle_detects_triggers(self):
        """run_tick_cycle should detect drives over threshold."""
        from core.drives.state import save_state

        # Set pressure above threshold
        self.state["drives"]["CARE"]["pressure"] = 25.0
        save_state(self.state_path, self.state)

        result = daemon.run_tick_cycle(self.state, self.config, self.state_path, self.log_path)

        # Should have triggered CARE
        triggered_names = [t["name"] for t in result["triggered"]]
        self.assertIn("CARE", triggered_names)

    def test_manual_mode_false_spawns_sessions(self):
        """With manual_mode: false, should spawn sessions when triggered."""
        from core.drives.state import save_state

        # Set manual_mode to false (v0.2.x behavior)
        self.config["drives"]["manual_mode"] = False

        # Set pressure above threshold
        self.state["drives"]["CARE"]["pressure"] = 25.0
        save_state(self.state_path, self.state)

        # Mock spawn_session to avoid actual spawning
        with patch("core.drives.spawn.spawn_session") as mock_spawn:
            mock_spawn.return_value = True
            with patch("core.drives.spawn.record_trigger"):
                result = daemon.run_tick_cycle(
                    self.state, self.config, self.state_path, self.log_path
                )

        # Should have detected trigger
        triggered_names = [t["name"] for t in result["triggered"]]
        self.assertIn("CARE", triggered_names)

        # Should have attempted to spawn
        mock_spawn.assert_called()

    def test_manual_mode_true_never_spawns(self):
        """With manual_mode: true, should never spawn sessions."""
        from core.drives.state import save_state

        # Set manual_mode to true (v0.3.0+ manual satisfaction)
        self.config["drives"]["manual_mode"] = True

        # Set pressure above threshold
        self.state["drives"]["CARE"]["pressure"] = 25.0
        save_state(self.state_path, self.state)

        # Mock spawn_session to ensure it's never called
        with patch("core.drives.spawn.spawn_session") as mock_spawn:
            result = daemon.run_tick_cycle(self.state, self.config, self.state_path, self.log_path)

        # Should have detected trigger
        triggered_names = [t["name"] for t in result["triggered"]]
        self.assertIn("CARE", triggered_names)

        # Should NOT have attempted to spawn
        mock_spawn.assert_not_called()

    def test_manual_mode_pressure_still_accumulates(self):
        """In manual mode, pressure should still accumulate normally."""
        from core.drives.state import save_state

        # Set manual_mode to true
        self.config["drives"]["manual_mode"] = True

        # Set initial pressure below threshold
        self.state["drives"]["CARE"]["pressure"] = 10.0
        save_state(self.state_path, self.state)

        # Run tick cycle
        result = daemon.run_tick_cycle(self.state, self.config, self.state_path, self.log_path)

        # Pressure should have increased
        self.assertIn("CARE", [u["name"] for u in result["updated"]])
        updated_care = [u for u in result["updated"] if u["name"] == "CARE"][0]
        self.assertGreater(updated_care["new"], updated_care["old"])


class TestStartStopDaemon(unittest.TestCase):
    """Test daemon start/stop lifecycle (with mocked fork)."""

    def setUp(self):
        """Create a temporary directory for test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = {
            "paths": {"workspace": self.temp_dir.name, "state": ".emergence/state"},
            "drives": {"tick_interval": 900},
        }
        self.pid_path = Path(self.temp_dir.name) / ".emergence" / "drives.pid"

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_start_daemon_fails_if_already_running(self):
        """start_daemon should fail if daemon already running."""
        # Create PID file simulating another process
        self.pid_path.parent.mkdir(parents=True, exist_ok=True)
        self.pid_path.write_text("99999999")

        with patch("core.drives.pidfile.is_process_alive", return_value=True):
            result = daemon.start_daemon(self.config, detach=False, pid_path=self.pid_path)

            self.assertFalse(result["success"])
            self.assertTrue(result.get("already_running"))
            self.assertEqual(result["pid"], 99999999)

    def test_start_daemon_foreground_runs_daemon(self):
        """start_daemon in foreground mode should run daemon."""
        with patch("core.drives.daemon.run_daemon") as mock_run:
            mock_run.return_value = 0
            result = daemon.start_daemon(self.config, detach=False, pid_path=self.pid_path)

            self.assertTrue(result["success"])
            self.assertFalse(result["detached"])
            mock_run.assert_called_once()

    def test_stop_daemon_reports_not_running(self):
        """stop_daemon should report when daemon not running."""
        result = daemon.stop_daemon(self.config, pid_path=self.pid_path)

        self.assertFalse(result["success"])
        self.assertFalse(result.get("was_running", True))

    def test_stop_daemon_sends_sigterm(self):
        """stop_daemon should send SIGTERM to running daemon."""
        # Create PID file with fake PID
        self.pid_path.parent.mkdir(parents=True, exist_ok=True)
        self.pid_path.write_text("12345")

        with patch("os.kill") as mock_kill:
            with patch("core.drives.daemon.is_process_alive", side_effect=[True, False]):
                result = daemon.stop_daemon(self.config, pid_path=self.pid_path, timeout=0.5)

                mock_kill.assert_any_call(12345, signal.SIGTERM)
                self.assertTrue(result.get("stopped"))


class TestIntegration(unittest.TestCase):
    """Integration tests for daemon components."""

    def setUp(self):
        """Create a temporary directory for test files."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config = {
            "paths": {"workspace": self.temp_dir.name, "state": ".emergence/state"},
            "drives": {"tick_interval": 900},
        }

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_full_pid_lifecycle(self):
        """Test full PID file lifecycle: write, read, check, remove."""
        pid_path = Path(self.temp_dir.name) / "test.pid"

        # Write PID
        pidfile.write_pid(pid_path)
        self.assertTrue(pid_path.exists())

        # Read PID
        read = pidfile.read_pid(pid_path)
        self.assertEqual(read, os.getpid())

        # Check running
        running, pid = pidfile.is_running(pid_path)
        self.assertTrue(running)
        self.assertEqual(pid, os.getpid())

        # Remove
        pidfile.remove_pid(pid_path)
        self.assertFalse(pid_path.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
