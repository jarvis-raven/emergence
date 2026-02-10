"""Tests for First Light Emergence Gates."""

import json
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open

# Ensure project root is in path for imports
_project_root = str(Path(__file__).resolve().parent.parent.parent.parent)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from core.first_light.gates import (
    load_config,
    check_drive_diversity,
    check_self_authored_identity,
    check_unprompted_initiative,
    check_profile_stability,
    check_relationship_signal,
    check_all_gates,
    is_emerged,
    update_gate_status,
    format_gate_check,
    calculate_variance,
    parse_frontmatter,
    MINIMUM_SESSIONS,
    GATE_NAMES,
    TEMPLATE_MARKERS,
    AUTHORSHIP_MARKERS,
    INITIATIVE_MARKERS,
    HUMAN_MARKERS,
)


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading."""
    
    def test_load_default_config(self):
        """Test loading default config."""
        config = load_config(Path("/nonexistent/config.yaml"))
        
        self.assertEqual(config["agent"]["name"], "My Agent")
        self.assertEqual(config["paths"]["workspace"], ".")


class TestGateDriveDiversity(unittest.TestCase):
    """Test Gate 1: Drive Diversity."""
    
    def test_check_drive_diversity_met(self):
        """Test gate met with 3+ discovered drives."""
        state = {"paths": {"state": ".emergence/state"}}
        
        drives_state = {
            "drives": {
                "CURIOSITY": {"category": "discovered", "created_at": "2026-02-07T10:00:00Z"},
                "CREATIVE": {"category": "discovered", "created_at": "2026-02-07T11:00:00Z"},
                "PLAY": {"category": "discovered", "created_at": "2026-02-07T12:00:00Z"},
            }
        }
        
        with patch("core.first_light.gates.load_drives_state") as mock_load:
            mock_load.return_value = drives_state
            result = check_drive_diversity(state)
        
        self.assertTrue(result["met"])
        self.assertEqual(len(result["evidence"]), 3)
        self.assertEqual(result["details"]["discovered_count"], 3)
    
    def test_check_drive_diversity_not_met(self):
        """Test gate not met with <3 discovered drives."""
        state = {"paths": {"state": ".emergence/state"}}
        
        drives_state = {
            "drives": {
                "CURIOSITY": {"category": "discovered"},
                "CARE": {"category": "core"},  # Should not count
            }
        }
        
        with patch("core.first_light.gates.load_drives_state") as mock_load:
            mock_load.return_value = drives_state
            result = check_drive_diversity(state)
        
        self.assertFalse(result["met"])
        self.assertEqual(result["details"]["discovered_count"], 1)
    
    def test_check_drive_diversity_empty(self):
        """Test gate with no drives."""
        state = {"paths": {"state": ".emergence/state"}}
        
        with patch("core.first_light.gates.load_drives_state") as mock_load:
            mock_load.return_value = {"drives": {}}
            result = check_drive_diversity(state)
        
        self.assertFalse(result["met"])
        self.assertEqual(result["evidence"], [])


class TestGateSelfAuthoredIdentity(unittest.TestCase):
    """Test Gate 2: Self-Authored Identity."""
    
    def test_check_self_authored_met(self):
        """Test gate met with substantial self-authored content."""
        config = {"paths": {"identity": "."}}
        
        # Content with authorship markers, no template markers, >500 chars
        self_content = """
I am an agent exploring my own nature.
I feel curiosity about the world around me.
I want to understand my human better.
My drives guide my actions.
I've learned much about myself.
""" + "x" * 500  # Ensure >500 chars
        
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.read_text") as mock_read:
                mock_exists.return_value = True
                mock_read.return_value = self_content
                result = check_self_authored_identity(config)
        
        self.assertTrue(result["met"])
        self.assertEqual(result["details"]["template_markers"], 0)
        self.assertGreaterEqual(result["details"]["authorship_markers"], 2)
    
    def test_check_self_authored_not_met_template(self):
        """Test gate not met with template markers present."""
        config = {"paths": {"identity": "."}}
        
        self_content = """
<!-- Fill this in -->
I am an agent.
""" + "x" * 500
        
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.read_text") as mock_read:
                mock_exists.return_value = True
                mock_read.return_value = self_content
                result = check_self_authored_identity(config)
        
        self.assertFalse(result["met"])
        self.assertGreater(result["details"]["template_markers"], 0)
    
    def test_check_self_authored_not_met_short(self):
        """Test gate not met with short content."""
        config = {"paths": {"identity": "."}}
        
        self_content = "I am."  # Too short
        
        with patch("pathlib.Path.exists") as mock_exists:
            with patch("pathlib.Path.read_text") as mock_read:
                mock_exists.return_value = True
                mock_read.return_value = self_content
                result = check_self_authored_identity(config)
        
        self.assertFalse(result["met"])
        self.assertLess(result["details"]["content_length"], 500)
    
    def test_check_self_authored_no_file(self):
        """Test gate when SELF.md doesn't exist."""
        config = {"paths": {"identity": "."}}
        
        with patch("pathlib.Path.exists") as mock_exists:
            mock_exists.return_value = False
            result = check_self_authored_identity(config)
        
        self.assertFalse(result["met"])
        self.assertIn("not found", result["evidence"][0])


class TestGateUnpromptedInitiative(unittest.TestCase):
    """Test Gate 3: Unprompted Initiative."""
    
    def test_check_unprompted_initiative_met(self):
        """Test gate met with initiative markers."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        state = {}
        
        session_content = """---
drive: CURIOSITY
trigger: drive
---

I decided to explore the codebase on my own.
Without being asked, I discovered something unexpected.
I chose to write a tool.
"""
        
        import tempfile, shutil
        tmpdir = tempfile.mkdtemp()
        try:
            # Need 3 qualifying sessions (bumped from 1)
            for i, name in enumerate(["2026-02-07-1430-CURIOSITY.md", "2026-02-07-1630-CREATIVE.md", "2026-02-07-1830-SOCIAL.md"]):
                session_file = Path(tmpdir) / name
                session_file.write_text(session_content)
            
            # Point config directly at tmpdir so get_session_dir resolves there
            config = {
                "paths": {"workspace": tmpdir},
                "memory": {"session_dir": "."},
            }
            result = check_unprompted_initiative(config, state)
            
            if not result["met"]:
                print(f"\nDEBUG: result={result}, config={config}, tmpdir={tmpdir}, files={list(Path(tmpdir).glob('*'))}")
            self.assertTrue(result["met"])
            self.assertGreaterEqual(result["details"]["qualifying_sessions"], 3)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
    
    def test_check_unprompted_initiative_not_met(self):
        """Test gate not met without initiative."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        state = {}
        
        session_content = """
---
drive: CURIOSITY
trigger: drive
---

This is a standard session.
Nothing surprising here.
"""
        
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.glob.return_value = [Path("session1.md")]
        
        with patch("core.first_light.gates.get_session_dir") as mock_get_dir:
            with patch("pathlib.Path.read_text") as mock_read:
                mock_get_dir.return_value = mock_path
                mock_read.return_value = session_content
                result = check_unprompted_initiative(config, state)
        
        self.assertFalse(result["met"])
    
    def test_check_unprompted_initiative_no_sessions(self):
        """Test gate with no drive-triggered sessions."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        state = {}
        
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.glob.return_value = []
        
        with patch("core.first_light.gates.get_session_dir") as mock_get_dir:
            mock_get_dir.return_value = mock_path
            result = check_unprompted_initiative(config, state)
        
        self.assertFalse(result["met"])
        self.assertIn("No drive-triggered sessions", result["evidence"][0])


class TestGateProfileStability(unittest.TestCase):
    """Test Gate 4: Profile Stability."""
    
    def test_check_profile_stability_met(self):
        """Test gate met with stable profile."""
        state = {
            "sessions": [{"analyzed": True} for _ in range(10)],
            "discovered_drives": [{"name": "CURIOSITY"}],
            "drives_suggested": [
                {"rate_per_hour": 5.0, "threshold": 25.0},
                {"rate_per_hour": 5.0, "threshold": 25.0},
                {"rate_per_hour": 5.0, "threshold": 25.0},
            ]
        }
        
        result = check_profile_stability(state)
        
        self.assertTrue(result["met"])
    
    def test_check_profile_stability_not_enough_sessions(self):
        """Test gate not met with too few sessions."""
        state = {
            "sessions": [{"analyzed": True}],  # Only 1 session
            "discovered_drives": [],
        }
        
        result = check_profile_stability(state)
        
        self.assertFalse(result["met"])
        self.assertIn("Only 1 sessions", result["evidence"][0])
    
    def test_check_profile_stability_high_variance(self):
        """Test gate not met with high variance."""
        state = {
            "sessions": [{"analyzed": True}] * 10,
            "discovered_drives": [{"name": "CURIOSITY"}],
            "drives_suggested": [
                {"rate_per_hour": 2.0, "threshold": 10.0},
                {"rate_per_hour": 8.0, "threshold": 50.0},
            ]
        }
        
        result = check_profile_stability(state)
        
        self.assertFalse(result["met"])
        self.assertGreater(result["details"]["avg_variance"], 0.2)


class TestGateRelationshipSignal(unittest.TestCase):
    """Test Gate 5: Relationship Signal."""
    
    def test_check_relationship_signal_met(self):
        """Test gate met with human-specific CARE session."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        state = {}
        
        session_content = """
---
drive: CARE
trigger: drive
---

I wanted to make sure my human is doing well.
I thought of you today.
"""
        
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.glob.side_effect = [
            [Path("CARE_session.md")],  # First glob for *CARE*.md
            [],  # Second glob for remaining files
        ]
        
        with patch("core.first_light.gates.get_session_dir") as mock_get_dir:
            with patch("pathlib.Path.read_text") as mock_read:
                mock_get_dir.return_value = mock_path
                mock_read.return_value = session_content.lower()
                result = check_relationship_signal(config, state)
        
        self.assertTrue(result["met"])
    
    def test_check_relationship_signal_not_met(self):
        """Test gate not met without human markers."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        state = {}
        
        session_content = """
---
drive: CARE
trigger: drive
---

This is a standard CARE session.
No specific human references.
"""
        
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.glob.side_effect = [
            [Path("CARE_session.md")],
            [],
        ]
        
        with patch("core.first_light.gates.get_session_dir") as mock_get_dir:
            with patch("pathlib.Path.read_text") as mock_read:
                mock_get_dir.return_value = mock_path
                mock_read.return_value = session_content.lower()
                result = check_relationship_signal(config, state)
        
        self.assertFalse(result["met"])
    
    def test_check_relationship_signal_no_care_sessions(self):
        """Test gate with no CARE sessions."""
        config = {"paths": {"workspace": "."}, "memory": {"session_dir": "memory/sessions"}}
        state = {}
        
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock_path.glob.return_value = []
        
        with patch("core.first_light.gates.get_session_dir") as mock_get_dir:
            mock_get_dir.return_value = mock_path
            result = check_relationship_signal(config, state)
        
        self.assertFalse(result["met"])
        self.assertIn("No CARE sessions", result["evidence"][0])


class TestAllGates(unittest.TestCase):
    """Test checking all gates together."""
    
    def test_check_all_gates(self):
        """Test that all gates are checked."""
        config = {"paths": {"identity": "."}}
        state = {"sessions": [], "discovered_drives": []}
        
        with patch("core.first_light.gates.load_drives_state") as mock_drives:
            with patch("pathlib.Path.exists") as mock_exists:
                mock_drives.return_value = {"drives": {}}
                mock_exists.return_value = False
                
                results = check_all_gates(config, state)
        
        self.assertEqual(len(results), 5)
        for gate_name in GATE_NAMES:
            self.assertIn(gate_name, results)
    
    def test_is_emerged_all_met(self):
        """Test emerged when all gates met."""
        config = {}
        state = {}
        
        with patch("core.first_light.gates.check_all_gates") as mock_check:
            mock_check.return_value = {
                "drive_diversity": {"met": True},
                "self_authored_identity": {"met": True},
                "unprompted_initiative": {"met": True},
                "profile_stability": {"met": True},
                "relationship_signal": {"met": True},
            }
            
            self.assertTrue(is_emerged(config, state))
    
    def test_is_emerged_not_all_met(self):
        """Test not emerged when some gates not met."""
        config = {}
        state = {}
        
        with patch("core.first_light.gates.check_all_gates") as mock_check:
            mock_check.return_value = {
                "drive_diversity": {"met": True},
                "self_authored_identity": {"met": True},
                "unprompted_initiative": {"met": False},
                "profile_stability": {"met": True},
                "relationship_signal": {"met": False},
            }
            
            self.assertFalse(is_emerged(config, state))


class TestGateStatusUpdate(unittest.TestCase):
    """Test gate status updates."""
    
    def test_update_gate_status_new_met(self):
        """Test updating status when gate newly met."""
        config = {}
        state = {"gates": {}}
        
        results = {
            "drive_diversity": {
                "met": True,
                "evidence": ["3 drives found"],
                "details": {"count": 3},
            }
        }
        
        updated = update_gate_status(config, state, results)
        
        self.assertTrue(updated["gates"]["drive_diversity"]["met"])
        self.assertIn("met_at", updated["gates"]["drive_diversity"])
        self.assertEqual(updated["completion"]["gates_met"], 1)
    
    def test_update_gate_status_prevents_regression(self):
        """Test that met gates stay met."""
        config = {}
        state = {
            "gates": {
                "drive_diversity": {"met": True, "met_at": "2026-02-01T00:00:00Z"}
            }
        }
        
        results = {
            "drive_diversity": {"met": False, "evidence": [], "details": {}}
        }
        
        updated = update_gate_status(config, state, results)
        
        # Should still be met (prevents regression)
        self.assertTrue(updated["gates"]["drive_diversity"]["met"])


class TestFormatting(unittest.TestCase):
    """Test output formatting."""
    
    def test_format_gate_check(self):
        """Test gate check formatting."""
        results = {
            "drive_diversity": {"met": True, "evidence": ["3 drives"]},
            "self_authored_identity": {"met": False, "evidence": ["Template found"]},
            "unprompted_initiative": {"met": False, "evidence": []},
            "profile_stability": {"met": False, "evidence": []},
            "relationship_signal": {"met": False, "evidence": []},
        }
        
        output = format_gate_check(results)
        
        self.assertIn("Drive Diversity", output)
        self.assertIn("Self-Authored Identity", output)
        self.assertIn("✓", output)
        self.assertIn("○", output)
        self.assertIn("1/5 gates met", output)
    
    def test_format_gate_check_verbose(self):
        """Test verbose gate check formatting."""
        results = {
            "drive_diversity": {"met": True, "evidence": ["CURIOSITY", "PLAY", "SOCIAL"]},
        }
        
        output = format_gate_check(results, verbose=True)
        
        self.assertIn("CURIOSITY", output)
        self.assertIn("PLAY", output)


class TestUtilities(unittest.TestCase):
    """Test utility functions."""
    
    def test_calculate_variance_identical(self):
        """Test variance of identical values is 0."""
        values = [5.0, 5.0, 5.0]
        variance = calculate_variance(values)
        
        self.assertEqual(variance, 0.0)
    
    def test_calculate_variance_different(self):
        """Test variance of different values."""
        values = [1.0, 3.0, 5.0]
        variance = calculate_variance(values)
        
        self.assertGreater(variance, 0.0)
    
    def test_calculate_variance_single_value(self):
        """Test variance with single value."""
        values = [5.0]
        variance = calculate_variance(values)
        
        self.assertEqual(variance, 0.0)
    
    def test_parse_frontmatter(self):
        """Test frontmatter parsing."""
        content = """---
drive: CURIOSITY
trigger: drive
---

Body content here.
"""
        
        metadata, body = parse_frontmatter(content)
        
        self.assertEqual(metadata["drive"], "CURIOSITY")
        self.assertEqual(metadata["trigger"], "drive")
        self.assertIn("Body content", body)
    
    def test_parse_frontmatter_no_frontmatter(self):
        """Test parsing content without frontmatter."""
        content = "Just body content."
        
        metadata, body = parse_frontmatter(content)
        
        self.assertEqual(metadata, {})
        self.assertEqual(body, content)


if __name__ == "__main__":
    unittest.main()
