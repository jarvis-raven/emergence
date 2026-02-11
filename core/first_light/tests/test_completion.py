"""Tests for First Light completion mechanism."""

import json
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.first_light.completion import (
    load_first_light_json,
    save_first_light_json,
    calculate_gate_status,
    check_first_light_completion,
    complete_first_light,
    notify_first_light_completion,
    increment_session_count,
    get_first_light_status,
    format_status_display,
    manual_complete_first_light,
    check_and_notify_startup,
    DEFAULT_GATES,
)


class TestFirstLightCompletion:
    """Test suite for First Light completion mechanism."""

    def setup_method(self):
        """Set up test workspace."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.workspace = Path(self.temp_dir.name)
        self.state_dir = self.workspace / ".emergence" / "state"
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def teardown_method(self):
        """Clean up test workspace."""
        self.temp_dir.cleanup()

    def test_load_defaults(self):
        """Test loading defaults when file doesn't exist."""
        fl = load_first_light_json(self.workspace)
        assert fl["version"] == "1.0"
        assert fl["status"] == "not_started"
        assert fl["session_count"] == 0
        assert "gates" in fl
        assert "gate_status" in fl
        assert "completion_transition" in fl

    def test_save_and_load(self):
        """Test saving and loading state."""
        fl = load_first_light_json(self.workspace)
        fl["session_count"] = 5
        fl["status"] = "active"
        save_first_light_json(self.workspace, fl)

        loaded = load_first_light_json(self.workspace)
        assert loaded["session_count"] == 5
        assert loaded["status"] == "active"

    def test_increment_session_count(self):
        """Test session counting."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "active"
        save_first_light_json(self.workspace, fl)

        count = increment_session_count(self.workspace)
        assert count == 1

        count = increment_session_count(self.workspace)
        assert count == 2

        loaded = load_first_light_json(self.workspace)
        assert loaded["session_count"] == 2

    def test_calculate_gate_status_sessions(self):
        """Test sessions gate calculation."""
        fl = {
            "session_count": 5,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "discovered_drives": [],
            "gates": DEFAULT_GATES
        }
        status = calculate_gate_status(fl)
        assert status["sessions_met"] is False

        fl["session_count"] = 15
        status = calculate_gate_status(fl)
        assert status["sessions_met"] is True

    def test_calculate_gate_status_days(self):
        """Test days gate calculation."""
        started = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        fl = {
            "session_count": 15,
            "started_at": started,
            "discovered_drives": [{"name": "TEST"}],
            "gates": DEFAULT_GATES
        }
        status = calculate_gate_status(fl)
        assert status["days_met"] is False

        started = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        fl["started_at"] = started
        status = calculate_gate_status(fl)
        assert status["days_met"] is True

    def test_calculate_gate_status_drives(self):
        """Test drives gate calculation."""
        fl = {
            "session_count": 15,
            "started_at": (datetime.now(timezone.utc) - timedelta(days=10)).isoformat(),
            "discovered_drives": [{"name": "DRIVE1"}],
            "gates": DEFAULT_GATES
        }
        status = calculate_gate_status(fl)
        assert status["drives_met"] is False
        assert status["over_soft_limit"] is False

        fl["discovered_drives"] = [{"name": f"DRIVE{i}"} for i in range(10)]
        status = calculate_gate_status(fl)
        assert status["drives_met"] is True
        assert status["over_soft_limit"] is True

    def test_complete_first_light(self):
        """Test graduation ceremony."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "active"
        fl["session_count"] = 15
        fl["started_at"] = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        fl["discovered_drives"] = [
            {"name": "CREATION", "description": "Making things"},
            {"name": "CURIOSITY", "description": "Exploring"},
        ]
        save_first_light_json(self.workspace, fl)

        result = complete_first_light(self.workspace)
        assert result["success"] is True
        assert result["already_completed"] is False
        assert "🌅 FIRST LIGHT COMPLETE" in result["message"]
        assert "CREATION" in result["message"]

        loaded = load_first_light_json(self.workspace)
        assert loaded["status"] == "completed"
        assert loaded["completed_at"] is not None
        assert "CREATION" in loaded["completion_transition"]["locked_drives"]

    def test_already_completed(self):
        """Test completion when already completed."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "completed"
        save_first_light_json(self.workspace, fl)

        result = complete_first_light(self.workspace)
        assert result["success"] is True
        assert result["already_completed"] is True

    def test_notify_first_light_completion(self):
        """Test notification on next session."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "completed"
        fl["completion_transition"] = {
            "notified": False,
            "locked_drives": ["CREATION"],
            "transition_message": "Test graduation message"
        }
        save_first_light_json(self.workspace, fl)

        message = notify_first_light_completion(self.workspace)
        assert message == "Test graduation message"

        loaded = load_first_light_json(self.workspace)
        assert loaded["status"] == "graduated"
        assert loaded["completion_transition"]["notified"] is True

    def test_notify_already_notified(self):
        """Test notification when already notified."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "completed"
        fl["completion_transition"]["notified"] = True
        save_first_light_json(self.workspace, fl)

        message = notify_first_light_completion(self.workspace)
        assert message is None

    def test_notify_not_completed(self):
        """Test notification when not completed."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "active"
        save_first_light_json(self.workspace, fl)

        message = notify_first_light_completion(self.workspace)
        assert message is None

    def test_check_first_light_completion_auto(self):
        """Test auto-completion when gates met."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "active"
        fl["session_count"] = 15
        fl["started_at"] = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        fl["discovered_drives"] = [{"name": "DRIVE1"}, {"name": "DRIVE2"}, {"name": "DRIVE3"}]
        save_first_light_json(self.workspace, fl)

        result = check_first_light_completion(self.workspace, auto_complete=True)
        assert result["completed"] is True
        assert result["gates_met"] is True

        loaded = load_first_light_json(self.workspace)
        assert loaded["status"] == "completed"

    def test_check_first_light_completion_no_auto(self):
        """Test no auto-completion when disabled."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "active"
        fl["session_count"] = 15
        fl["started_at"] = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        fl["discovered_drives"] = [{"name": "DRIVE1"}, {"name": "DRIVE2"}, {"name": "DRIVE3"}]
        save_first_light_json(self.workspace, fl)

        result = check_first_light_completion(self.workspace, auto_complete=False)
        assert result["completed"] is False
        assert result["gates_met"] is True

        loaded = load_first_light_json(self.workspace)
        assert loaded["status"] == "active"

    def test_manual_complete_success(self):
        """Test manual completion with gates met."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "active"
        fl["session_count"] = 15
        fl["started_at"] = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        fl["discovered_drives"] = [{"name": "DRIVE1"}, {"name": "DRIVE2"}, {"name": "DRIVE3"}]
        save_first_light_json(self.workspace, fl)

        result = manual_complete_first_light(self.workspace, force=False)
        assert result["success"] is True
        assert result["forced"] is False

    def test_manual_complete_force(self):
        """Test manual completion with force override."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "active"
        fl["session_count"] = 3  # Not enough
        fl["discovered_drives"] = [{"name": "DRIVE1"}]
        save_first_light_json(self.workspace, fl)

        result = manual_complete_first_light(self.workspace, force=True)
        assert result["success"] is True
        assert result["forced"] is True

    def test_manual_complete_fail(self):
        """Test manual completion fails without force."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "active"
        fl["session_count"] = 3
        fl["discovered_drives"] = [{"name": "DRIVE1"}]
        save_first_light_json(self.workspace, fl)

        result = manual_complete_first_light(self.workspace, force=False)
        assert result["success"] is False
        assert result["error"] == "gates_not_met"

    def test_get_first_light_status(self):
        """Test getting comprehensive status."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "active"
        fl["session_count"] = 5
        fl["started_at"] = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat()
        fl["discovered_drives"] = [{"name": "DRIVE1"}]
        save_first_light_json(self.workspace, fl)

        status = get_first_light_status(self.workspace)
        assert status["status"] == "active"
        assert status["session_count"] == 5
        assert status["progress"]["sessions"]["current"] == 5
        assert status["progress"]["sessions"]["required"] == 10

    def test_format_status_display(self):
        """Test status display formatting."""
        status = {
            "status": "active",
            "session_count": 5,
            "discovered_drives": 2,
            "progress": {
                "sessions": {"current": 5, "required": 10, "percent": 50},
                "days": {"current": 3, "required": 7, "percent": 43},
                "drives": {"current": 2, "required": 3, "percent": 67}
            },
            "gate_status": {
                "sessions_met": False,
                "days_met": False,
                "drives_met": False,
                "over_soft_limit": False
            },
            "can_complete": False,
            "can_complete_manual": True
        }
        display = format_status_display(status)
        assert "First Light Status" in display
        assert "Sessions:" in display
        assert "50%" in display or "5/10" in display

    def test_check_and_notify_startup_not_ready(self):
        """Test startup check when not ready."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "active"
        fl["session_count"] = 3
        save_first_light_json(self.workspace, fl)

        message = check_and_notify_startup(self.workspace)
        assert message is None

    def test_check_and_notify_startup_gates_met(self):
        """Test startup check when gates met but not completed."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "active"
        fl["session_count"] = 15
        fl["started_at"] = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        fl["discovered_drives"] = [{"name": "D1"}, {"name": "D2"}, {"name": "D3"}]
        save_first_light_json(self.workspace, fl)

        message = check_and_notify_startup(self.workspace)
        assert message is not None
        assert "gates are all met" in message

    def test_check_and_notify_startup_pending_notification(self):
        """Test startup check when pending notification."""
        fl = load_first_light_json(self.workspace)
        fl["status"] = "completed"
        fl["completion_transition"] = {
            "notified": False,
            "locked_drives": ["CREATION"],
            "transition_message": "Graduation!"
        }
        save_first_light_json(self.workspace, fl)

        message = check_and_notify_startup(self.workspace)
        assert message == "Graduation!"

        loaded = load_first_light_json(self.workspace)
        assert loaded["status"] == "graduated"


def run_tests():
    """Run all tests."""
    test = TestFirstLightCompletion()
    
    methods = [m for m in dir(test) if m.startswith("test_")]
    passed = 0
    failed = 0
    
    for method_name in methods:
        test.setup_method()
        try:
            getattr(test, method_name)()
            print(f"✓ {method_name}")
            passed += 1
        except AssertionError as e:
            print(f"✗ {method_name}: {e}")
            failed += 1
        except Exception as e:
            print(f"✗ {method_name}: {type(e).__name__}: {e}")
            failed += 1
        finally:
            test.teardown_method()
    
    print()
    print(f"Results: {passed} passed, {failed} failed")
    return failed == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
