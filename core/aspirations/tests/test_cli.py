"""Tests for the Aspirations CLI.

Tests argument parsing, command routing, and validation.
Uses mocking for predictable testing.
"""

import sys
import os
import json
import unittest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import from the package
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from core.aspirations.cli import (
    create_parser,
    cmd_tree,
    cmd_dreams,
    cmd_projects,
    cmd_add_dream,
    cmd_add_project,
    cmd_link,
    cmd_status,
    cmd_orphans,
    cmd_barren,
    EXIT_SUCCESS,
    EXIT_ERROR,
    EXIT_USAGE,
)


class TestCLIArgumentParsing(unittest.TestCase):
    """Test CLI argument parsing and command routing."""
    
    def test_default_no_command_defaults_to_overview(self):
        """No arguments should default to overview."""
        parser = create_parser()
        args = parser.parse_args([])
        self.assertIsNone(args.command)
    
    def test_tree_command_parsing(self):
        """Tree command should accept --json flag."""
        parser = create_parser()
        
        args = parser.parse_args(["tree"])
        self.assertEqual(args.command, "tree")
        self.assertFalse(args.json)
        
        args = parser.parse_args(["tree", "--json"])
        self.assertTrue(args.json)
    
    def test_dreams_command_parsing(self):
        """Dreams command should accept --json flag."""
        parser = create_parser()
        
        args = parser.parse_args(["dreams"])
        self.assertEqual(args.command, "dreams")
        self.assertFalse(args.json)
        
        args = parser.parse_args(["dreams", "--json"])
        self.assertTrue(args.json)
    
    def test_dreams_alias_aspirations(self):
        """Dreams command should have aspirations alias."""
        parser = create_parser()
        
        args = parser.parse_args(["aspirations"])
        self.assertEqual(args.command, "aspirations")
    
    def test_projects_command_parsing(self):
        """Projects command should accept --json flag."""
        parser = create_parser()
        
        args = parser.parse_args(["projects"])
        self.assertEqual(args.command, "projects")
        self.assertFalse(args.json)
        
        args = parser.parse_args(["projects", "--json"])
        self.assertTrue(args.json)
    
    def test_add_dream_command_parsing(self):
        """Add-dream command should parse title, --desc, and --category."""
        parser = create_parser()
        
        # Basic
        args = parser.parse_args(["add-dream", "My Dream"])
        self.assertEqual(args.command, "add-dream")
        self.assertEqual(args.title, "My Dream")
        
        # With description
        args = parser.parse_args(["add-dream", "My Dream", "--desc", "A description"])
        self.assertEqual(args.desc, "A description")
        
        # With category
        args = parser.parse_args(["add-dream", "My Dream", "--category", "creative"])
        self.assertEqual(args.category, "creative")
        
        # With all flags
        args = parser.parse_args([
            "add-dream", "My Dream",
            "--desc", "A description",
            "--category", "philosophical",
            "--throughline", "depth"
        ])
        self.assertEqual(args.title, "My Dream")
        self.assertEqual(args.desc, "A description")
        self.assertEqual(args.category, "philosophical")
        self.assertEqual(args.throughline, "depth")
    
    def test_add_dream_category_choices(self):
        """Add-dream should only accept valid categories."""
        parser = create_parser()
        
        # Valid category
        args = parser.parse_args(["add-dream", "Test", "--category", "creative"])
        self.assertEqual(args.category, "creative")
        
        # Invalid category should raise error
        with self.assertRaises(SystemExit):
            parser.parse_args(["add-dream", "Test", "--category", "invalid"])
    
    def test_add_project_command_parsing(self):
        """Add-project command should parse name, --for, --status, and other flags."""
        parser = create_parser()
        
        # Basic
        args = parser.parse_args(["add-project", "My Project", "--for", "my-dream"])
        self.assertEqual(args.command, "add-project")
        self.assertEqual(args.name, "My Project")
        self.assertEqual(args.for_aspiration, "my-dream")
        
        # With status
        args = parser.parse_args(["add-project", "My Project", "--for", "my-dream", "--status", "active"])
        self.assertEqual(args.status, "active")
        
        # With category
        args = parser.parse_args(["add-project", "My Project", "--for", "my-dream", "--category", "tool"])
        self.assertEqual(args.category, "tool")
        
        # With description
        args = parser.parse_args(["add-project", "My Project", "--for", "my-dream", "--desc", "A description"])
        self.assertEqual(args.desc, "A description")
    
    def test_add_project_status_choices(self):
        """Add-project should only accept valid statuses."""
        parser = create_parser()
        
        # Valid statuses
        for status in ["active", "idea", "paused", "completed"]:
            args = parser.parse_args(["add-project", "Test", "--for", "dream", "--status", status])
            self.assertEqual(args.status, status)
        
        # Invalid status should raise error
        with self.assertRaises(SystemExit):
            parser.parse_args(["add-project", "Test", "--for", "dream", "--status", "invalid"])
    
    def test_link_command_parsing(self):
        """Link command should parse project_id and aspiration_id."""
        parser = create_parser()
        
        args = parser.parse_args(["link", "proj-1", "dream-2"])
        self.assertEqual(args.command, "link")
        self.assertEqual(args.project_id, "proj-1")
        self.assertEqual(args.aspiration_id, "dream-2")
    
    def test_status_command_parsing(self):
        """Status command should parse project_id and status."""
        parser = create_parser()
        
        args = parser.parse_args(["status", "proj-1", "active"])
        self.assertEqual(args.command, "status")
        self.assertEqual(args.project_id, "proj-1")
        self.assertEqual(args.status, "active")
    
    def test_orphans_command_parsing(self):
        """Orphans command should accept --json flag."""
        parser = create_parser()
        
        args = parser.parse_args(["orphans"])
        self.assertEqual(args.command, "orphans")
        self.assertFalse(args.json)
        
        args = parser.parse_args(["orphans", "--json"])
        self.assertTrue(args.json)
    
    def test_barren_command_parsing(self):
        """Barren command should accept --json flag."""
        parser = create_parser()
        
        args = parser.parse_args(["barren"])
        self.assertEqual(args.command, "barren")
        self.assertFalse(args.json)
        
        args = parser.parse_args(["barren", "--json"])
        self.assertTrue(args.json)
    
    def test_config_flag_parsing(self):
        """All commands should accept --config flag."""
        parser = create_parser()
        
        args = parser.parse_args(["--config", "/path/to/config.json", "tree"])
        self.assertEqual(args.config, "/path/to/config.json")
        self.assertEqual(args.command, "tree")
    
    def test_version_flag(self):
        """--version should display version."""
        parser = create_parser()
        
        with self.assertRaises(SystemExit) as cm:
            parser.parse_args(["--version"])
        self.assertEqual(cm.exception.code, 0)


class TestCLIInvalidCommands(unittest.TestCase):
    """Test that invalid commands are rejected."""
    
    def test_invalid_command_rejected(self):
        """Unknown command should raise error."""
        parser = create_parser()
        
        with self.assertRaises(SystemExit) as cm:
            parser.parse_args(["invalid-command"])
        # argparse exits with code 2 for unknown subcommands
        self.assertEqual(cm.exception.code, 2)
    
    def test_add_project_missing_for_flag(self):
        """Add-project without --for should fail."""
        parser = create_parser()
        
        # Can parse, but command should fail
        args = parser.parse_args(["add-project", "Test"])
        self.assertIsNone(args.for_aspiration)
    
    def test_link_missing_args(self):
        """Link without args should have None values."""
        parser = create_parser()
        
        args = parser.parse_args(["link"])
        self.assertIsNone(args.project_id)
        self.assertIsNone(args.aspiration_id)
    
    def test_status_missing_args(self):
        """Status without args should have None values."""
        parser = create_parser()
        
        args = parser.parse_args(["status"])
        self.assertIsNone(args.project_id)
        self.assertIsNone(args.status)


class TestCLICategoryValidation(unittest.TestCase):
    """Test category validation in CLI."""
    
    def test_aspiration_categories_accepted(self):
        """All valid aspiration categories should be accepted."""
        from core.aspirations.models import ASPIRATION_CATEGORIES
        parser = create_parser()
        
        for category in ASPIRATION_CATEGORIES:
            args = parser.parse_args(["add-dream", "Test", "--category", category])
            self.assertEqual(args.category, category)
    
    def test_project_categories_accepted(self):
        """All valid project categories should be accepted."""
        from core.aspirations.models import PROJECT_CATEGORIES
        parser = create_parser()
        
        for category in PROJECT_CATEGORIES:
            args = parser.parse_args(["add-project", "Test", "--for", "dream", "--category", category])
            self.assertEqual(args.category, category)


class TestCLIExitCodes(unittest.TestCase):
    """Test CLI returns correct exit codes."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_path = Path(self.temp_dir) / "aspirations.json"
        self.config_path = Path(self.temp_dir) / "emergence.json"
        
        # Create minimal config
        config = {
            "agent": {"name": "Test Agent"},
            "paths": {
                "workspace": self.temp_dir,
                "state": "."
            }
        }
        with open(self.config_path, "w") as f:
            json.dump(config, f)
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('core.aspirations.cli.get_state_path_from_config')
    def test_tree_returns_success(self, mock_get_path):
        """Tree command should return EXIT_SUCCESS (0)."""
        mock_get_path.return_value = self.state_path
        
        parser = create_parser()
        args = parser.parse_args(["tree"])
        
        result = cmd_tree(args)
        self.assertEqual(result, EXIT_SUCCESS)
    
    @patch('core.aspirations.cli.get_state_path_from_config')
    def test_add_dream_missing_title_returns_usage_error(self, mock_get_path):
        """Add-dream without title should return EXIT_USAGE (2)."""
        mock_get_path.return_value = self.state_path
        
        parser = create_parser()
        args = parser.parse_args(["add-dream"])
        
        result = cmd_add_dream(args)
        self.assertEqual(result, EXIT_USAGE)
    
    @patch('core.aspirations.cli.get_state_path_from_config')
    def test_add_project_missing_for_returns_usage_error(self, mock_get_path):
        """Add-project without --for should return EXIT_USAGE (2)."""
        mock_get_path.return_value = self.state_path
        
        parser = create_parser()
        args = parser.parse_args(["add-project", "Test"])
        
        result = cmd_add_project(args)
        self.assertEqual(result, EXIT_USAGE)
    
    @patch('core.aspirations.cli.get_state_path_from_config')
    def test_link_missing_args_returns_usage_error(self, mock_get_path):
        """Link without args should return EXIT_USAGE (2)."""
        mock_get_path.return_value = self.state_path
        
        parser = create_parser()
        args = parser.parse_args(["link"])
        
        result = cmd_link(args)
        self.assertEqual(result, EXIT_USAGE)
    
    @patch('core.aspirations.cli.get_state_path_from_config')
    def test_status_missing_args_returns_usage_error(self, mock_get_path):
        """Status without args should return EXIT_USAGE (2)."""
        mock_get_path.return_value = self.state_path
        
        parser = create_parser()
        args = parser.parse_args(["status"])
        
        result = cmd_status(args)
        self.assertEqual(result, EXIT_USAGE)


class TestCLICommandVariants(unittest.TestCase):
    """Test all command variants work correctly."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()
        self.state_path = Path(self.temp_dir) / "aspirations.json"
        self.config_path = Path(self.temp_dir) / "emergence.json"
        
        # Create valid data file
        test_data = {
            "version": 1,
            "aspirations": [
                {"id": "test-dream", "title": "Test Dream", "description": "A test", "category": "creative", "createdAt": "2026-01-01"},
            ],
            "projects": [
                {"id": "test-project", "name": "Test Project", "aspirationId": "test-dream", "status": "idea", "category": "tool", "description": "A test", "updatedAt": "2026-01-01"},
            ],
            "meta": {"updatedAt": datetime.now(timezone.utc).isoformat()},
        }
        self.state_path.write_text(json.dumps(test_data))
        
        # Create config
        config = {
            "agent": {"name": "Test Agent"},
            "paths": {"workspace": self.temp_dir, "state": "."}
        }
        self.config_path.write_text(json.dumps(config))
    
    def tearDown(self):
        """Clean up test fixtures."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @patch('core.aspirations.cli.get_state_path_from_config')
    def test_overview_command(self, mock_get_path):
        """Overview command should work."""
        mock_get_path.return_value = self.state_path
        
        parser = create_parser()
        args = parser.parse_args(["overview"])
        
        # Import cmd_overview locally since it's not in the import list
        from core.aspirations.cli import cmd_overview
        result = cmd_overview(args)
        self.assertEqual(result, EXIT_SUCCESS)
    
    @patch('core.aspirations.cli.get_state_path_from_config')
    def test_dreams_command(self, mock_get_path):
        """Dreams command should work."""
        mock_get_path.return_value = self.state_path
        
        parser = create_parser()
        args = parser.parse_args(["dreams"])
        
        result = cmd_dreams(args)
        self.assertEqual(result, EXIT_SUCCESS)
    
    @patch('core.aspirations.cli.get_state_path_from_config')
    def test_projects_command(self, mock_get_path):
        """Projects command should work."""
        mock_get_path.return_value = self.state_path
        
        parser = create_parser()
        args = parser.parse_args(["projects"])
        
        result = cmd_projects(args)
        self.assertEqual(result, EXIT_SUCCESS)
    
    @patch('core.aspirations.cli.get_state_path_from_config')
    def test_orphans_command(self, mock_get_path):
        """Orphans command should work."""
        mock_get_path.return_value = self.state_path
        
        parser = create_parser()
        args = parser.parse_args(["orphans"])
        
        result = cmd_orphans(args)
        self.assertEqual(result, EXIT_SUCCESS)
    
    @patch('core.aspirations.cli.get_state_path_from_config')
    def test_barren_command(self, mock_get_path):
        """Barren command should work."""
        mock_get_path.return_value = self.state_path
        
        parser = create_parser()
        args = parser.parse_args(["barren"])
        
        result = cmd_barren(args)
        self.assertEqual(result, EXIT_SUCCESS)


# Need datetime import for the test
from datetime import datetime, timezone


if __name__ == "__main__":
    unittest.main(verbosity=2)
