#!/usr/bin/env python3
"""Unit tests for the Init Wizard module.

Tests cover argument parsing, validation, phase orchestration,
and graceful handling of edge cases.
"""

import json
import os
import signal
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import from parent package
from core.setup.init_wizard import (
    parse_args,
    validate_name,
    InitAnswers,
    InitState,
    cleanup_partial_state,
    generate_letter,
    main,
    EXIT_SUCCESS,
    EXIT_ERROR,
    EXIT_INTERRUPT,
)


class TestArgumentParsing(unittest.TestCase):
    """Tests for CLI argument parsing."""
    
    def test_parse_args_interactive_defaults(self):
        """Test parsing with no arguments (interactive mode)."""
        args = parse_args([])
        
        self.assertTrue(args["interactive"])
        self.assertIsNone(args["name"])
        self.assertIsNone(args["human"])
        self.assertEqual(args["why"], "")
        self.assertEqual(args["workspace"], Path(".").resolve())
        self.assertFalse(args["auto_fix"])
    
    def test_parse_args_non_interactive_valid(self):
        """Test non-interactive mode with all required args."""
        args = parse_args([
            "--non-interactive",
            "--name", "Nova",
            "--human", "Sarah",
            "--why", "Creative partner"
        ])
        
        self.assertFalse(args["interactive"])
        self.assertEqual(args["name"], "Nova")
        self.assertEqual(args["human"], "Sarah")
        self.assertEqual(args["why"], "Creative partner")
    
    def test_parse_args_non_interactive_missing_name(self):
        """Test non-interactive mode fails without --name."""
        with self.assertRaises(SystemExit) as cm:
            parse_args(["--non-interactive", "--human", "Sarah"])
        
        self.assertEqual(cm.exception.code, EXIT_ERROR)
    
    def test_parse_args_non_interactive_missing_human(self):
        """Test non-interactive mode fails without --human."""
        with self.assertRaises(SystemExit) as cm:
            parse_args(["--non-interactive", "--name", "Nova"])
        
        self.assertEqual(cm.exception.code, EXIT_ERROR)
    
    def test_parse_args_workspace_path(self):
        """Test workspace path parsing and expansion."""
        args = parse_args(["--workspace", "~/test-workspace"])
        
        # Should expand ~ to home directory
        self.assertIn("test-workspace", str(args["workspace"]))
        self.assertTrue(args["workspace"].is_absolute())
    
    def test_parse_args_auto_fix(self):
        """Test auto-fix flag parsing."""
        args = parse_args(["--auto-fix"])
        self.assertTrue(args["auto_fix"])


class TestNameValidation(unittest.TestCase):
    """Tests for name validation function."""
    
    def test_validate_name_valid(self):
        """Test valid names pass validation."""
        valid_names = [
            "Aurora",
            "Nova",
            "Test Agent",
            "Agent-123",
            "Émilie",  # Unicode
        ]
        
        for name in valid_names:
            is_valid, msg = validate_name(name)
            self.assertTrue(is_valid, f"'{name}' should be valid: {msg}")
    
    def test_validate_name_empty(self):
        """Test empty name fails validation."""
        is_valid, msg = validate_name("")
        self.assertFalse(is_valid)
        self.assertIn("empty", msg.lower())
    
    def test_validate_name_newline(self):
        """Test name with newline fails validation."""
        is_valid, msg = validate_name("Agent\nName")
        self.assertFalse(is_valid)
        self.assertIn("newline", msg.lower())
    
    def test_validate_name_too_long(self):
        """Test very long name fails validation."""
        is_valid, msg = validate_name("A" * 101)
        self.assertFalse(is_valid)
        self.assertIn("100", msg)


class TestInitAnswers(unittest.TestCase):
    """Tests for InitAnswers data class."""
    
    def test_init_answers_creation(self):
        """Test InitAnswers stores values correctly."""
        answers = InitAnswers("Nova", "Sarah", "Creative partner")
        
        self.assertEqual(answers.agent_name, "Nova")
        self.assertEqual(answers.human_name, "Sarah")
        self.assertEqual(answers.human_why, "Creative partner")
    
    def test_init_answers_empty_why(self):
        """Test InitAnswers handles empty why."""
        answers = InitAnswers("Aurora", "Human", "")
        
        self.assertEqual(answers.human_why, "")


class TestInitState(unittest.TestCase):
    """Tests for InitState tracking."""
    
    def test_init_state_defaults(self):
        """Test InitState initializes correctly."""
        state = InitState()
        
        self.assertEqual(state.created_paths, [])
        self.assertIsNone(state.workspace)
        self.assertFalse(state.interrupted)
    
    def test_init_state_with_paths(self):
        """Test InitState tracks created paths."""
        state = InitState()
        state.created_paths = [Path("/test/dir1"), Path("/test/dir2")]
        state.workspace = Path("/test")
        
        self.assertEqual(len(state.created_paths), 2)
        self.assertEqual(state.workspace, Path("/test"))


class TestCleanupPartialState(unittest.TestCase):
    """Tests for cleanup functionality."""
    
    def test_cleanup_empty_dirs(self):
        """Test cleanup removes empty directories."""
        with tempfile.TemporaryDirectory() as tmp:
            state = InitState()
            test_dir = Path(tmp) / "test_dir"
            test_dir.mkdir()
            state.created_paths = [test_dir]
            
            self.assertTrue(test_dir.exists())
            cleanup_partial_state(state)
            self.assertFalse(test_dir.exists())
    
    def test_cleanup_non_empty_dirs_preserved(self):
        """Test cleanup doesn't remove non-empty directories."""
        with tempfile.TemporaryDirectory() as tmp:
            state = InitState()
            test_dir = Path(tmp) / "test_dir"
            test_dir.mkdir()
            (test_dir / "file.txt").write_text("content")
            state.created_paths = [test_dir]
            
            cleanup_partial_state(state)
            # Directory with files should remain (rmdir will fail silently)
            self.assertTrue(test_dir.exists())
    
    def test_cleanup_files(self):
        """Test cleanup removes files."""
        with tempfile.TemporaryDirectory() as tmp:
            state = InitState()
            test_file = Path(tmp) / "test.txt"
            test_file.write_text("content")
            state.created_paths = [test_file]
            
            self.assertTrue(test_file.exists())
            cleanup_partial_state(state)
            self.assertFalse(test_file.exists())


class TestGenerateLetter(unittest.TestCase):
    """Tests for letter generation."""
    
    def test_letter_contains_all_answers(self):
        """Test letter includes all three answers."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "identity").mkdir(parents=True)
            
            answers = InitAnswers("Nova", "Sarah", "To explore creativity")
            letter_path = generate_letter(workspace, answers)
            
            content = letter_path.read_text(encoding="utf-8")
            
            self.assertIn("Nova", content)
            self.assertIn("Sarah", content)
            self.assertIn("To explore creativity", content)
    
    def test_letter_handles_empty_why(self):
        """Test letter handles empty why gracefully."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "identity").mkdir(parents=True)
            
            answers = InitAnswers("Aurora", "Human", "")
            letter_path = generate_letter(workspace, answers)
            
            content = letter_path.read_text(encoding="utf-8")
            
            # Should have placeholder text
            self.assertIn("silence", content.lower())
    
    def test_letter_in_identity_folder(self):
        """Test letter is created in identity folder."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "identity").mkdir(parents=True)
            
            answers = InitAnswers("Test", "Human", "Test")
            letter_path = generate_letter(workspace, answers)
            
            self.assertEqual(letter_path.parent.name, "identity")
            self.assertEqual(letter_path.name, "LETTER.md")
    
    def test_letter_structure(self):
        """Test letter has expected structure."""
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Path(tmp)
            (workspace / "identity").mkdir(parents=True)
            
            answers = InitAnswers("Nova", "Sarah", "Test")
            letter_path = generate_letter(workspace, answers)
            
            content = letter_path.read_text(encoding="utf-8")
            
            # Check for expected sections
            self.assertIn("# LETTER.md", content)
            self.assertIn("Dear Nova", content)
            self.assertIn("Why You're Here", content)
            self.assertIn("What To Do Now", content)
            self.assertIn("Welcome to Emergence", content)


class TestMainOrchestration(unittest.TestCase):
    """Integration tests for main orchestrator."""
    
    @patch("core.setup.init_wizard.run_prerequisite_check")
    @patch("core.setup.init_wizard.generate_placement_plan")
    @patch("core.setup.init_wizard.generate_default_config")
    @patch("core.setup.init_wizard.write_config")
    def test_main_non_interactive_success(
        self, mock_write, mock_config, mock_plan, mock_prereq
    ):
        """Test successful non-interactive run."""
        with tempfile.TemporaryDirectory() as tmp:
            mock_prereq.return_value = 0  # Success
            mock_plan.return_value = {
                "agent_type": "new",
                "files": {},
                "summary": {"total_files": 0}
            }
            mock_config.return_value = {"agent": {"name": "Nova"}}
            mock_write.return_value = True
            
            workspace = Path(tmp) / "test-workspace"
            
            with patch("sys.stdout"):
                result = main([
                    "--non-interactive",
                    "--name", "Nova",
                    "--human", "Sarah",
                    "--workspace", str(workspace)
                ])
            
            self.assertEqual(result, EXIT_SUCCESS)
            mock_prereq.assert_called_once()
            mock_plan.assert_called_once()
            mock_config.assert_called_once()
            mock_write.assert_called_once()
    
    @patch("core.setup.init_wizard.run_prerequisite_check")
    def test_main_prereq_failure(self, mock_prereq):
        """Test main exits on prerequisite failure."""
        with tempfile.TemporaryDirectory() as tmp:
            mock_prereq.return_value = 1  # Hard failure
            
            workspace = Path(tmp) / "test-workspace"
            
            with patch("sys.stdout"):
                result = main([
                    "--non-interactive",
                    "--name", "Nova",
                    "--human", "Sarah",
                    "--workspace", str(workspace)
                ])
            
            self.assertEqual(result, EXIT_ERROR)
    
    @patch("core.setup.init_wizard.run_prerequisite_check")
    @patch("core.setup.init_wizard.generate_placement_plan")
    @patch("core.setup.init_wizard.generate_default_config")
    @patch("core.setup.init_wizard.write_config")
    def test_main_config_write_failure(
        self, mock_write, mock_config, mock_plan, mock_prereq
    ):
        """Test main exits if config write fails."""
        with tempfile.TemporaryDirectory() as tmp:
            mock_prereq.return_value = 0
            mock_plan.return_value = {"agent_type": "new"}
            mock_config.return_value = {}
            mock_write.return_value = False  # Write failed
            
            workspace = Path(tmp) / "test-workspace"
            
            with patch("sys.stdout"):
                result = main([
                    "--non-interactive",
                    "--name", "Nova",
                    "--human", "Sarah",
                    "--workspace", str(workspace)
                ])
            
            self.assertEqual(result, EXIT_ERROR)


class TestEdgeCases(unittest.TestCase):
    """Tests for edge cases and error conditions."""
    
    def test_validate_name_unicode(self):
        """Test validation handles unicode names."""
        unicode_names = [
            "Аврора",  # Cyrillic
            "オーロラ",  # Japanese
            "极光",  # Chinese
            "Aurora 🌟",  # Emoji
        ]
        
        for name in unicode_names:
            is_valid, _ = validate_name(name)
            self.assertTrue(is_valid, f"'{name}' should be valid")
    
    def test_init_answers_special_chars(self):
        """Test InitAnswers handles special characters."""
        answers = InitAnswers(
            "Agent O'Brien",
            "Sarah-Jane",
            "Testing \"quoted\" reasons"
        )
        
        self.assertEqual(answers.agent_name, "Agent O'Brien")
        self.assertEqual(answers.human_name, "Sarah-Jane")
        self.assertEqual(answers.human_why, 'Testing "quoted" reasons')


class TestSignalHandling(unittest.TestCase):
    """Tests for interrupt signal handling."""
    
    def test_cleanup_on_interrupt(self):
        """Test cleanup function is called properly."""
        with tempfile.TemporaryDirectory() as tmp:
            state = InitState()
            test_dir = Path(tmp) / "cleanup_test"
            test_dir.mkdir()
            state.created_paths = [test_dir]
            
            # Simulate cleanup
            cleanup_partial_state(state)
            
            self.assertFalse(test_dir.exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
