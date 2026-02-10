"""Tests for First Light Status."""

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.first_light.status import (
    load_config,
    load_first_light_state,
    load_drives_state,
    count_sessions,
    count_discovered_drives,
    get_discovered_drive_names,
    count_met_gates,
    get_gate_details,
    determine_phase,
    calculate_progress_percentage,
    get_first_light_status,
    generate_progress_bar,
    format_status_display,
    format_status_json,
    TARGET_SESSIONS,
)


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading."""
    
    def test_load_default_config(self):
        """Test loading default config."""
        config = load_config(Path("/nonexistent/config.yaml"))
        
        self.assertEqual(config["agent"]["name"], "My Agent")
        self.assertEqual(config["paths"]["workspace"], ".")


class TestSessionCounting(unittest.TestCase):
    """Test session counting."""
    
    def test_count_sessions_empty(self):
        """Test counting with no sessions."""
        config = {"paths": {"workspace": "."}}
        
        with patch("core.first_light.status.load_first_light_state") as mock_load:
            mock_load.return_value = {"sessions": []}
            counts = count_sessions(config)
        
        self.assertEqual(counts["total"], 0)
        self.assertEqual(counts["analyzed"], 0)
        self.assertEqual(counts["recent"], 0)
    
    def test_count_sessions_with_analyzed(self):
        """Test counting with analyzed sessions."""
        config = {"paths": {"workspace": "."}}
        
        sessions = [
            {"analyzed": True, "scheduled_at": "2026-02-07T10:00:00Z"},
            {"analyzed": True, "scheduled_at": "2026-02-07T11:00:00Z"},
            {"analyzed": False, "scheduled_at": "2026-02-07T12:00:00Z"},
        ]
        
        with patch("core.first_light.status.load_first_light_state") as mock_load:
            mock_load.return_value = {"sessions": sessions, "sessions_scheduled": 3}
            counts = count_sessions(config)
        
        self.assertEqual(counts["total"], 3)
        self.assertEqual(counts["analyzed"], 2)


class TestDriveCounting(unittest.TestCase):
    """Test drive counting."""
    
    def test_count_discovered_drives(self):
        """Test counting discovered drives."""
        state = {
            "drives": {
                "CARE": {"category": "core"},
                "CURIOSITY": {"category": "discovered"},
                "PLAY": {"category": "discovered"},
            }
        }
        
        count = count_discovered_drives(state)
        
        self.assertEqual(count, 2)
    
    def test_get_discovered_drive_names(self):
        """Test getting discovered drive names."""
        state = {
            "drives": {
                "CARE": {"category": "core"},
                "CURIOSITY": {"category": "discovered"},
                "PLAY": {"category": "discovered"},
            }
        }
        
        names = get_discovered_drive_names(state)
        
        self.assertEqual(len(names), 2)
        self.assertIn("CURIOSITY", names)
        self.assertIn("PLAY", names)


class TestGateCounting(unittest.TestCase):
    """Test gate counting."""
    
    def test_count_met_gates(self):
        """Test counting met gates."""
        state = {
            "gates": {
                "drive_diversity": {"met": True},
                "self_authored_identity": {"met": True},
                "unprompted_initiative": {"met": False},
            }
        }
        
        count = count_met_gates(state)
        
        self.assertEqual(count, 2)
    
    def test_count_met_gates_empty(self):
        """Test counting with no gates."""
        state = {"gates": {}}
        
        count = count_met_gates(state)
        
        self.assertEqual(count, 0)
    
    def test_get_gate_details(self):
        """Test getting gate details."""
        state = {
            "gates": {
                "drive_diversity": {"met": True, "evidence": ["3 drives"]},
            }
        }
        
        details = get_gate_details(state)
        
        self.assertTrue(details["drive_diversity"]["met"])
        self.assertEqual(details["drive_diversity"]["evidence"], ["3 drives"])


class TestPhaseDetermination(unittest.TestCase):
    """Test phase determination."""
    
    def test_phase_not_started(self):
        """Test not_started phase."""
        state = {"status": "not_started"}
        phase = determine_phase(state, 0, 0)
        
        self.assertEqual(phase, "not_started")
    
    def test_phase_active(self):
        """Test active phase."""
        state = {"status": "active"}
        phase = determine_phase(state, 3, 0)
        
        self.assertEqual(phase, "active")
    
    def test_phase_stabilizing(self):
        """Test stabilizing phase."""
        state = {"status": "active"}
        phase = determine_phase(state, 5, 2)
        
        self.assertEqual(phase, "stabilizing")
    
    def test_phase_emerged(self):
        """Test emerged phase."""
        state = {"status": "completed"}
        phase = determine_phase(state, 10, 5)
        
        self.assertEqual(phase, "emerged")
    
    def test_phase_emerged_from_gates(self):
        """Test emerged when all gates met."""
        state = {"status": "active"}
        phase = determine_phase(state, 3, 5)  # All gates met
        
        self.assertEqual(phase, "emerged")


class TestProgressCalculation(unittest.TestCase):
    """Test progress percentage calculation."""
    
    def test_progress_zero(self):
        """Test progress at zero."""
        pct = calculate_progress_percentage(0, 0, 0)
        
        self.assertEqual(pct, 0)
    
    def test_progress_complete(self):
        """Test progress at 100%."""
        pct = calculate_progress_percentage(TARGET_SESSIONS, 3, 5)
        
        self.assertEqual(pct, 100)
    
    def test_progress_partial(self):
        """Test partial progress."""
        # 5 sessions (50% of 40% = 20%)
        # 1 drive (33% of 30% = 10%)
        # 2 gates (40% of 30% = 12%)
        pct = calculate_progress_percentage(5, 1, 2)
        
        self.assertGreater(pct, 0)
        self.assertLess(pct, 100)


class TestFullStatus(unittest.TestCase):
    """Test full status compilation."""
    
    def test_get_first_light_status_not_started(self):
        """Test status when not started."""
        config = {"paths": {"workspace": "."}}
        
        with patch("core.first_light.status.load_first_light_state") as mock_fl:
            with patch("core.first_light.status.load_drives_state") as mock_drives:
                mock_fl.return_value = {"status": "not_started", "sessions": []}
                mock_drives.return_value = {"drives": {}}
                
                status = get_first_light_status(config)
        
        self.assertEqual(status["phase"], "not_started")
        self.assertEqual(status["progress"]["percentage"], 0)
        self.assertFalse(status["emerged"])
    
    def test_get_first_light_status_active(self):
        """Test status when active."""
        config = {"paths": {"workspace": "."}}
        
        with patch("core.first_light.status.load_first_light_state") as mock_fl:
            with patch("core.first_light.status.load_drives_state") as mock_drives:
                mock_fl.return_value = {
                    "status": "active",
                    "sessions": [{"analyzed": True}] * 3,
                    "sessions_scheduled": 3,
                    "started_at": "2026-02-01T00:00:00Z",
                    "gates": {},
                }
                mock_drives.return_value = {
                    "drives": {
                        "CURIOSITY": {"category": "discovered"},
                    }
                }
                
                status = get_first_light_status(config)
        
        self.assertEqual(status["phase"], "active")
        self.assertEqual(status["progress"]["drives"]["discovered"], 1)
        self.assertGreater(status["timing"]["elapsed_days"], 0)
    
    def test_get_first_light_status_emerged(self):
        """Test status when emerged."""
        config = {"paths": {"workspace": "."}}
        
        with patch("core.first_light.status.load_first_light_state") as mock_fl:
            with patch("core.first_light.status.load_drives_state") as mock_drives:
                mock_fl.return_value = {
                    "status": "completed",
                    "sessions": [{"analyzed": True}] * 10,
                    "emerged_at": "2026-02-07T00:00:00Z",
                    "gates": {
                        "drive_diversity": {"met": True},
                        "self_authored_identity": {"met": True},
                        "unprompted_initiative": {"met": True},
                        "profile_stability": {"met": True},
                        "relationship_signal": {"met": True},
                    }
                }
                mock_drives.return_value = {
                    "drives": {
                        "CURIOSITY": {"category": "discovered"},
                        "PLAY": {"category": "discovered"},
                        "SOCIAL": {"category": "discovered"},
                    }
                }
                
                status = get_first_light_status(config)
        
        self.assertEqual(status["phase"], "emerged")
        self.assertTrue(status["emerged"])
        self.assertEqual(status["emerged_at"], "2026-02-07T00:00:00Z")


class TestProgressBar(unittest.TestCase):
    """Test progress bar generation."""
    
    def test_progress_bar_empty(self):
        """Test empty progress bar."""
        bar = generate_progress_bar(0, 10, width=10)
        
        self.assertEqual(bar, "░░░░░░░░░░")
    
    def test_progress_bar_full(self):
        """Test full progress bar."""
        bar = generate_progress_bar(10, 10, width=10)
        
        self.assertEqual(bar, "██████████")
    
    def test_progress_bar_half(self):
        """Test half progress bar."""
        bar = generate_progress_bar(5, 10, width=10)
        
        self.assertEqual(bar, "█████░░░░░")
    
    def test_progress_bar_overflow(self):
        """Test progress bar caps at 100%."""
        bar = generate_progress_bar(15, 10, width=10)
        
        self.assertEqual(bar, "██████████")


class TestFormatting(unittest.TestCase):
    """Test output formatting."""
    
    def test_format_status_display_not_started(self):
        """Test formatting not_started status."""
        status = {
            "phase": "not_started",
            "status": "not_started",
            "progress": {
                "percentage": 0,
                "sessions": {"completed": 0, "scheduled": 0, "target": TARGET_SESSIONS},
                "drives": {"discovered": 0, "names": [], "target": 3},
                "gates": {"met": 0, "total": 5, "details": {}},
            },
            "timing": {"started_at": None, "elapsed_days": 0, "estimated_completion": None},
            "emerged": False,
            "emerged_at": None,
        }
        
        output = format_status_display(status)
        
        self.assertIn("Not Started", output)
        self.assertIn("Progress", output)
        self.assertIn("Gates Detail", output)
    
    def test_format_status_display_emerged(self):
        """Test formatting emerged status."""
        status = {
            "phase": "emerged",
            "status": "completed",
            "progress": {
                "percentage": 100,
                "sessions": {"completed": 10, "scheduled": 10, "target": TARGET_SESSIONS},
                "drives": {"discovered": 3, "names": ["CURIOSITY", "PLAY", "SOCIAL"], "target": 3},
                "gates": {"met": 5, "total": 5, "details": {}},
            },
            "timing": {
                "started_at": "2026-02-01T00:00:00Z",
                "elapsed_days": 6,
                "estimated_completion": None,
            },
            "emerged": True,
            "emerged_at": "2026-02-07T00:00:00Z",
        }
        
        output = format_status_display(status)
        
        self.assertIn("EMERGED", output)
        self.assertIn("Complete!", output)
    
    def test_format_status_json(self):
        """Test JSON formatting."""
        status = {
            "phase": "active",
            "progress": {"percentage": 50},
        }
        
        output = format_status_json(status)
        
        parsed = json.loads(output)
        self.assertEqual(parsed["phase"], "active")
        self.assertEqual(parsed["progress"]["percentage"], 50)


class TestIntegration(unittest.TestCase):
    """Integration tests."""
    
    def test_full_status_with_all_data(self):
        """Test status with complete data."""
        config = {"paths": {"workspace": "."}}
        
        fl_state = {
            "status": "active",
            "sessions": [{"analyzed": True, "scheduled_at": "2026-02-07T10:00:00Z"}] * 7,
            "sessions_scheduled": 7,
            "started_at": "2026-02-01T00:00:00Z",
            "gates": {
                "drive_diversity": {"met": True, "evidence": ["3 drives"]},
                "self_authored_identity": {"met": True, "evidence": []},
                "profile_stability": {"met": True, "evidence": []},
            }
        }
        
        drives_state = {
            "drives": {
                "CURIOSITY": {"category": "discovered"},
                "PLAY": {"category": "discovered"},
                "SOCIAL": {"category": "discovered"},
            }
        }
        
        with patch("core.first_light.status.load_first_light_state") as mock_fl:
            with patch("core.first_light.status.load_drives_state") as mock_drives:
                mock_fl.return_value = fl_state
                mock_drives.return_value = drives_state
                
                status = get_first_light_status(config)
        
        self.assertEqual(status["phase"], "stabilizing")
        self.assertEqual(status["progress"]["drives"]["discovered"], 3)
        self.assertEqual(status["progress"]["gates"]["met"], 3)
        self.assertGreater(status["progress"]["percentage"], 0)


if __name__ == "__main__":
    unittest.main()
