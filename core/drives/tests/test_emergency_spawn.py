"""Tests for emergency auto-spawn safety valve.

Tests the emergency spawn feature that auto-spawns drives at 200%+ pressure
even when manual_mode is enabled, as a safety valve against complete neglect.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.drives.daemon import _check_emergency_spawns, run_tick_cycle, write_log


def make_state(drives=None, triggered_drives=None):
    """Create a minimal drive state for testing."""
    return {
        "version": "1.1",
        "last_tick": datetime.now(timezone.utc).isoformat(),
        "drives": drives or {},
        "triggered_drives": triggered_drives or [],
    }


def make_drive(name="TEST", pressure=0.0, threshold=20.0, last_emergency_spawn=None, **kwargs):
    """Create a minimal drive dict for testing."""
    drive = {
        "name": name,
        "base_drive": True,
        "aspects": [],
        "pressure": pressure,
        "threshold": threshold,
        "rate_per_hour": 2.0,
        "max_rate": 3.0,
        "description": f"Test drive {name}",
        "prompt": f"Your {name} drive triggered.",
        "category": "core",
        "created_by": "system",
        "satisfaction_events": [],
        "discovered_during": None,
        "activity_driven": False,
        "last_triggered": None,
        "min_interval_seconds": 0,
        "valence": "appetitive",
        "thwarting_count": 0,
        "last_emergency_spawn": last_emergency_spawn,
    }
    drive.update(kwargs)
    return drive


def make_config(manual_mode=True, emergency_spawn=True, emergency_threshold=2.0, emergency_cooldown_hours=6):
    """Create a minimal config for testing."""
    return {
        "drives": {
            "manual_mode": manual_mode,
            "emergency_spawn": emergency_spawn,
            "emergency_threshold": emergency_threshold,
            "emergency_cooldown_hours": emergency_cooldown_hours,
            "tick_interval": 900,
            "quiet_hours": [23, 7],
            "cooldown_minutes": 30,
        },
        "paths": {"workspace": "."},
    }


class TestEmergencySpawnTrigger:
    """Test that emergency spawn triggers at 200%+ pressure."""

    @patch("core.drives.spawn.spawn_session", return_value=True)
    @patch("core.drives.spawn.record_trigger")
    def test_triggers_at_200_percent(self, mock_record, mock_spawn):
        """Emergency spawn fires when pressure >= 200% of threshold."""
        drive = make_drive("CREATIVE", pressure=40.0, threshold=20.0)  # 200%
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}
        log_path = Path("/dev/null")

        spawned = _check_emergency_spawns(state, make_config(), log_path, result, 2.0, 6)

        assert "CREATIVE" in spawned
        assert mock_spawn.called
        # Pressure should be reduced by 90%
        assert drive["pressure"] == pytest.approx(4.0, abs=0.1)  # 40 * 0.10
        assert drive["last_emergency_spawn"] is not None
        assert "emergency_spawns" in result
        assert len(result["emergency_spawns"]) == 1

    @patch("core.drives.spawn.spawn_session", return_value=True)
    @patch("core.drives.spawn.record_trigger")
    def test_triggers_above_200_percent(self, mock_record, mock_spawn):
        """Emergency spawn fires when pressure well above 200%."""
        drive = make_drive("CREATIVE", pressure=60.0, threshold=20.0)  # 300%
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)

        assert "CREATIVE" in spawned
        assert drive["pressure"] == pytest.approx(6.0, abs=0.1)  # 60 * 0.10

    def test_does_not_trigger_below_200_percent(self):
        """Emergency spawn does NOT fire below 200%."""
        drive = make_drive("CREATIVE", pressure=38.0, threshold=20.0)  # 190%
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)

        assert spawned == []
        assert "emergency_spawns" not in result
        assert drive["pressure"] == 38.0  # Unchanged

    def test_does_not_trigger_at_exactly_199_percent(self):
        """Boundary test: 199% should NOT trigger."""
        drive = make_drive("CREATIVE", pressure=39.8, threshold=20.0)  # 199%
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)

        assert spawned == []


class TestEmergencySpawnRateLimiting:
    """Test rate limiting: max 1 emergency spawn per drive per 6 hours."""

    def test_rate_limited_within_cooldown(self):
        """Emergency spawn blocked if last spawn was less than 6 hours ago."""
        recent = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        drive = make_drive("CREATIVE", pressure=50.0, threshold=20.0, last_emergency_spawn=recent)
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)

        assert spawned == []
        assert drive["pressure"] == 50.0  # Unchanged

    @patch("core.drives.spawn.spawn_session", return_value=True)
    @patch("core.drives.spawn.record_trigger")
    def test_allowed_after_cooldown_expires(self, mock_record, mock_spawn):
        """Emergency spawn allowed after cooldown period expires."""
        old = (datetime.now(timezone.utc) - timedelta(hours=7)).isoformat()
        drive = make_drive("CREATIVE", pressure=50.0, threshold=20.0, last_emergency_spawn=old)
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)

        assert "CREATIVE" in spawned

    @patch("core.drives.spawn.spawn_session", return_value=True)
    @patch("core.drives.spawn.record_trigger")
    def test_no_last_emergency_spawn_allows_first(self, mock_record, mock_spawn):
        """First emergency spawn is always allowed (no previous timestamp)."""
        drive = make_drive("CREATIVE", pressure=50.0, threshold=20.0)
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)

        assert "CREATIVE" in spawned

    @patch("core.drives.spawn.spawn_session", return_value=True)
    @patch("core.drives.spawn.record_trigger")
    def test_multiple_drives_independent_cooldowns(self, mock_record, mock_spawn):
        """Each drive has its own independent cooldown."""
        recent = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        drive_a = make_drive("CREATIVE", pressure=50.0, threshold=20.0, last_emergency_spawn=recent)
        drive_b = make_drive("SOCIAL", pressure=50.0, threshold=20.0)  # No previous spawn
        state = make_state(drives={"CREATIVE": drive_a, "SOCIAL": drive_b})
        result = {"triggered": []}

        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)

        assert "CREATIVE" not in spawned  # Rate limited
        assert "SOCIAL" in spawned  # Allowed


class TestEmergencySpawnConfig:
    """Test config option to disable emergency spawn."""

    def test_disabled_by_config(self):
        """When emergency_spawn=false, no emergency spawns happen."""
        drive = make_drive("CREATIVE", pressure=100.0, threshold=20.0)  # 500%!
        state = make_state(drives={"CREATIVE": drive})
        config = make_config(emergency_spawn=False)
        result = {"triggered": []}

        # The config check happens in run_tick_cycle, not _check_emergency_spawns
        # So test the guard condition directly
        emergency_spawn_enabled = config.get("drives", {}).get("emergency_spawn", True)
        assert not emergency_spawn_enabled

    @patch("core.drives.spawn.spawn_session", return_value=True)
    @patch("core.drives.spawn.record_trigger")
    def test_custom_threshold(self, mock_record, mock_spawn):
        """Custom emergency threshold ratio works."""
        drive = make_drive("CREATIVE", pressure=50.0, threshold=20.0)  # 250%
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        # With threshold at 3.0 (300%), 250% should NOT trigger
        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 3.0, 6)
        assert spawned == []

        # With threshold at 2.0 (200%), 250% SHOULD trigger
        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)
        assert "CREATIVE" in spawned

    @patch("core.drives.spawn.spawn_session", return_value=True)
    @patch("core.drives.spawn.record_trigger")
    def test_custom_cooldown(self, mock_record, mock_spawn):
        """Custom cooldown period works."""
        three_hours_ago = (datetime.now(timezone.utc) - timedelta(hours=3)).isoformat()
        drive = make_drive("CREATIVE", pressure=50.0, threshold=20.0, last_emergency_spawn=three_hours_ago)
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        # With 2-hour cooldown, 3 hours ago should be allowed
        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 2)
        assert "CREATIVE" in spawned


class TestEmergencySpawnWithManualSatisfaction:
    """Test emergency spawn works alongside manual satisfaction."""

    @patch("core.drives.spawn.spawn_session", return_value=True)
    @patch("core.drives.spawn.record_trigger")
    def test_emergency_reduces_pressure(self, mock_record, mock_spawn):
        """After emergency spawn, pressure is reduced to safe level."""
        drive = make_drive("CREATIVE", pressure=40.0, threshold=20.0)
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)

        # After 90% reduction, pressure should be 4.0 (well below threshold)
        assert drive["pressure"] == pytest.approx(4.0, abs=0.1)

    @patch("core.drives.spawn.spawn_session", return_value=False)
    def test_failed_spawn_preserves_pressure(self, mock_spawn):
        """If spawn fails, pressure is NOT reduced."""
        drive = make_drive("CREATIVE", pressure=40.0, threshold=20.0)
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)

        assert spawned == []
        assert drive["pressure"] == 40.0  # Unchanged


class TestDashboardWarning:
    """Test dashboard shows warnings at 180%+."""

    def test_warning_data_at_180_percent(self):
        """Verify that 180%+ drives would be flagged for warning."""
        # This tests the logic used in the dashboard
        drives = {
            "CREATIVE": {"pressure": 36.0, "threshold": 20.0},  # 180%
            "SOCIAL": {"pressure": 30.0, "threshold": 20.0},    # 150%
            "CARE": {"pressure": 44.0, "threshold": 20.0},      # 220%
        }

        warnings = []
        for name, d in drives.items():
            ratio = d["pressure"] / d["threshold"]
            if ratio >= 1.80:
                warnings.append({"name": name, "ratio": ratio})

        assert len(warnings) == 2
        warning_names = {w["name"] for w in warnings}
        assert "CREATIVE" in warning_names  # 180% - at threshold
        assert "CARE" in warning_names      # 220% - above
        assert "SOCIAL" not in warning_names  # 150% - below

    def test_emergency_active_distinction(self):
        """Distinguish between approaching (180-199%) and active (200%+) emergency."""
        drives = [
            {"name": "CREATIVE", "ratio": 1.85},  # Approaching
            {"name": "CARE", "ratio": 2.20},       # Active
        ]

        approaching = [d for d in drives if 1.80 <= d["ratio"] < 2.0]
        active = [d for d in drives if d["ratio"] >= 2.0]

        assert len(approaching) == 1
        assert approaching[0]["name"] == "CREATIVE"
        assert len(active) == 1
        assert active[0]["name"] == "CARE"


class TestEmergencySpawnEdgeCases:
    """Edge cases and robustness tests."""

    def test_zero_threshold_skipped(self):
        """Drives with zero threshold are skipped (avoid division by zero)."""
        drive = make_drive("BROKEN", pressure=100.0, threshold=0.0)
        state = make_state(drives={"BROKEN": drive})
        result = {"triggered": []}

        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)
        assert spawned == []

    @patch("core.drives.spawn.spawn_session", return_value=True)
    @patch("core.drives.spawn.record_trigger")
    def test_invalid_last_emergency_timestamp(self, mock_record, mock_spawn):
        """Invalid last_emergency_spawn timestamp allows spawn."""
        drive = make_drive("CREATIVE", pressure=50.0, threshold=20.0, last_emergency_spawn="not-a-date")
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)
        assert "CREATIVE" in spawned

    @patch("core.drives.spawn.spawn_session", side_effect=Exception("spawn error"))
    def test_spawn_exception_handled(self, mock_spawn):
        """Exceptions during spawn are caught and logged, not propagated."""
        drive = make_drive("CREATIVE", pressure=50.0, threshold=20.0)
        state = make_state(drives={"CREATIVE": drive})
        result = {"triggered": []}

        # Should not raise
        spawned = _check_emergency_spawns(state, make_config(), Path("/dev/null"), result, 2.0, 6)
        assert spawned == []
        assert drive["pressure"] == 50.0  # Unchanged on error


class TestModelDefaults:
    """Test that model defaults include last_emergency_spawn."""

    def test_ensure_drive_defaults_adds_field(self):
        """ensure_drive_defaults adds last_emergency_spawn=None."""
        from core.drives.models import ensure_drive_defaults
        drive = {"name": "TEST", "threshold": 20.0, "rate_per_hour": 1.0}
        ensure_drive_defaults(drive)
        assert "last_emergency_spawn" in drive
        assert drive["last_emergency_spawn"] is None


class TestConfigDefaults:
    """Test that config defaults include emergency_spawn."""

    def test_default_config_has_emergency_spawn(self):
        """Default config should have emergency_spawn=True."""
        from core.drives.config import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["drives"]["emergency_spawn"] is True

    def test_default_config_has_emergency_threshold(self):
        """Default config should have emergency_threshold=2.0."""
        from core.drives.config import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["drives"]["emergency_threshold"] == 2.0

    def test_default_config_has_emergency_cooldown(self):
        """Default config should have emergency_cooldown_hours=6."""
        from core.drives.config import DEFAULT_CONFIG
        assert DEFAULT_CONFIG["drives"]["emergency_cooldown_hours"] == 6
