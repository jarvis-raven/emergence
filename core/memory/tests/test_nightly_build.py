"""Unit tests for Nightly Build.

Tests date determination, memory review, session review, topic extraction,
and prompt generation.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path

from core.memory.nightly_build import (
    load_config,
    get_date_to_process,
    review_daily_memory,
    review_sessions,
    extract_topics,
    count_sections,
    generate_self_update_prompt,
    generate_memory_curation_prompt,
    get_daily_dir,
    get_session_dir,
    get_status,
)


class TestConfigLoading(unittest.TestCase):
    """Test configuration loading."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = Path(self.temp_dir) / "emergence.json"
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_default_config(self):
        """Should return defaults when no config exists."""
        config = load_config(Path(self.temp_dir) / "nonexistent.json")
        
        self.assertIn("agent", config)
        self.assertIn("lifecycle", config)
        self.assertEqual(config["lifecycle"]["nightly_hour"], 3)
    
    def test_load_custom_config(self):
        """Should load custom config values."""
        custom = {
            "agent": {"name": "Test Agent"},
            "lifecycle": {"nightly_hour": 4}
        }
        self.config_file.write_text(json.dumps(custom))
        
        config = load_config(self.config_file)
        
        self.assertEqual(config["agent"]["name"], "Test Agent")
        self.assertEqual(config["lifecycle"]["nightly_hour"], 4)


class TestDateDetermination(unittest.TestCase):
    """Test date determination logic."""
    
    def test_default_is_yesterday(self):
        """Default should be yesterday (since we run at 3am)."""
        result = get_date_to_process()
        
        yesterday = datetime.now(timezone.utc) - timedelta(days=1)
        expected = yesterday.strftime("%Y-%m-%d")
        
        self.assertEqual(result, expected)
    
    def test_override_date(self):
        """Should use override when provided."""
        result = get_date_to_process("2026-02-07")
        
        self.assertEqual(result, "2026-02-07")


class TestDailyMemoryReview(unittest.TestCase):
    """Test daily memory file review."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.daily_dir = Path(self.temp_dir) / "memory"
        self.daily_dir.mkdir()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_review_existing_file(self):
        """Should review existing memory file."""
        daily_file = self.daily_dir / "2026-02-07.md"
        daily_file.write_text("## Session\n\nTest content.")
        
        result = review_daily_memory("2026-02-07", self.daily_dir)
        
        self.assertTrue(result["exists"])
        self.assertEqual(result["size"], len("## Session\n\nTest content."))
        self.assertIn("Session", result["content"])
    
    def test_review_missing_file(self):
        """Should handle missing file gracefully."""
        result = review_daily_memory("2026-02-06", self.daily_dir)
        
        self.assertFalse(result["exists"])
        self.assertEqual(result["size"], 0)


class TestSessionReview(unittest.TestCase):
    """Test session file review."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.session_dir = Path(self.temp_dir) / "sessions"
        self.session_dir.mkdir()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_review_sessions(self):
        """Should find and parse session files."""
        # Create session files
        (self.session_dir / "2026-02-07-1430-CURIOSITY.md").write_text("""---
drive: CURIOSITY
timestamp: 2026-02-07T14:30:00Z
pressure: 20/25
trigger: drive
---

## Summary
Explored topics.""")
        
        (self.session_dir / "2026-02-07-1600-SOCIAL.md").write_text("""---
drive: SOCIAL
timestamp: 2026-02-07T16:00:00Z
---

## Summary
Chat with human.""")
        
        sessions = review_sessions("2026-02-07", self.session_dir)
        
        self.assertEqual(len(sessions), 2)
        self.assertEqual(sessions[0]["drive"], "CURIOSITY")
        self.assertEqual(sessions[1]["drive"], "SOCIAL")
    
    def test_review_no_sessions(self):
        """Should return empty list when no sessions."""
        sessions = review_sessions("2026-02-06", self.session_dir)
        
        self.assertEqual(sessions, [])
    
    def test_review_parses_metadata(self):
        """Should parse frontmatter metadata."""
        (self.session_dir / "2026-02-07-1000-TEST.md").write_text("""---
drive: CURIOSITY
timestamp: 2026-02-07T10:00:00Z
pressure: 15/20
trigger: cron
---

Content.""")
        
        sessions = review_sessions("2026-02-07", self.session_dir)
        
        self.assertEqual(len(sessions), 1)
        self.assertEqual(sessions[0]["timestamp"], "2026-02-07T10:00:00Z")
        self.assertEqual(sessions[0]["pressure"], "15/20")
        self.assertEqual(sessions[0]["trigger"], "cron")


class TestTopicExtraction(unittest.TestCase):
    """Test topic extraction."""
    
    def test_extract_from_drives(self):
        """Should extract topics from session drives."""
        sessions = [
            {"drive": "CURIOSITY"},
            {"drive": "SOCIAL"},
            {"drive": "CREATIVE"}
        ]
        
        topics = extract_topics("", sessions)
        
        self.assertIn("learning", topics)
        self.assertIn("connection", topics)
        self.assertIn("creation", topics)
    
    def test_extract_from_content(self):
        """Should extract topics from content patterns."""
        content = "I wrote some code today. Python functions and scripts."
        sessions = []
        
        topics = extract_topics(content, sessions)
        
        self.assertIn("coding", topics)
    
    def test_extract_unique_sorted(self):
        """Should return unique, sorted topics."""
        sessions = [
            {"drive": "CURIOSITY"},
            {"drive": "CURIOSITY"}  # Duplicate
        ]
        
        topics = extract_topics("", sessions)
        
        # Should not have duplicates
        self.assertEqual(len(topics), len(set(topics)))
        # Should be sorted
        self.assertEqual(topics, sorted(topics))


class TestSectionCounting(unittest.TestCase):
    """Test section counting in memory content."""
    
    def test_count_conversations(self):
        """Should count conversation sections."""
        content = """## Morning Conversation — Test
Content
## Chat with Human
Content
## Deep Conversation — Philosophy
Content"""
        
        counts = count_sections(content)
        
        self.assertEqual(counts["conversations"], 3)
    
    def test_count_consolidated(self):
        """Should count consolidated sections."""
        content = """## Consolidated Session — CURIOSITY
Content
## Consolidated Session — SOCIAL
Content"""
        
        counts = count_sections(content)
        
        self.assertEqual(counts["consolidated"], 2)
    
    def test_count_mixed(self):
        """Should count mixed section types."""
        content = """## Session — Activity
Content
## Conversation — Chat
Content
## Consolidated Session — DRIVE
Content
## Other Section
Content"""
        
        counts = count_sections(content)
        
        self.assertEqual(counts["sessions"], 1)
        self.assertEqual(counts["conversations"], 1)
        self.assertEqual(counts["consolidated"], 1)
        self.assertEqual(counts["other"], 1)


class TestSelfUpdatePrompt(unittest.TestCase):
    """Test SELF.md update prompt generation."""
    
    def test_prompt_includes_date(self):
        """Should include date in prompt."""
        memory = {"exists": True, "size": 1000, "line_count": 50, "content": ""}
        sessions = []
        topics = []
        config = {"agent": {"name": "Test Agent"}}
        
        prompt = generate_self_update_prompt("2026-02-07", memory, sessions, topics, config)
        
        self.assertIn("2026-02-07", prompt)
    
    def test_prompt_includes_sessions(self):
        """Should include session summary in prompt."""
        memory = {"exists": True, "size": 1000, "line_count": 50, "content": ""}
        sessions = [
            {"drive": "CURIOSITY", "trigger": "drive"},
            {"drive": "SOCIAL", "trigger": "cron"}
        ]
        topics = []
        config = {"agent": {"name": "Test"}}
        
        prompt = generate_self_update_prompt("2026-02-07", memory, sessions, topics, config)
        
        self.assertIn("CURIOSITY", prompt)
        self.assertIn("SOCIAL", prompt)
    
    def test_prompt_includes_topics(self):
        """Should include topics in prompt."""
        memory = {"exists": True, "size": 1000, "line_count": 50, "content": ""}
        sessions = []
        topics = ["coding", "writing", "research"]
        config = {"agent": {"name": "Test"}}
        
        prompt = generate_self_update_prompt("2026-02-07", memory, sessions, topics, config)
        
        self.assertIn("coding", prompt)
        self.assertIn("writing", prompt)
        self.assertIn("research", prompt)
    
    def test_prompt_has_sections(self):
        """Should include all update sections."""
        memory = {"exists": True, "size": 1000, "line_count": 50, "content": ""}
        sessions = []
        topics = []
        config = {"agent": {"name": "Test"}}
        
        prompt = generate_self_update_prompt("2026-02-07", memory, sessions, topics, config)
        
        self.assertIn("Current State", prompt)
        self.assertIn("Recent Discoveries", prompt)
        self.assertIn("What I'm Exploring", prompt)
        self.assertIn("Relationship Status", prompt)


class TestMemoryCurationPrompt(unittest.TestCase):
    """Test MEMORY.md curation prompt generation."""
    
    def test_prompt_includes_rules(self):
        """Should include curation rules."""
        memory = {"exists": True, "size": 1000, "content": ""}
        sessions = []
        config = {}
        
        prompt = generate_memory_curation_prompt("2026-02-07", memory, sessions, config)
        
        self.assertIn("Keep under 50 lines", prompt)
        self.assertIn("vault keys", prompt)
        self.assertIn("Do NOT add", prompt)
    
    def test_prompt_includes_date(self):
        """Should include date in prompt."""
        memory = {"exists": True, "size": 1000, "content": ""}
        sessions = []
        config = {}
        
        prompt = generate_memory_curation_prompt("2026-02-07", memory, sessions, config)
        
        self.assertIn("2026-02-07", prompt)


class TestPathResolution(unittest.TestCase):
    """Test path resolution from config."""
    
    def test_get_daily_dir(self):
        """Should resolve daily directory."""
        config = {
            "paths": {"workspace": "/workspace"},
            "memory": {"daily_dir": "memory"}
        }
        
        path = get_daily_dir(config)
        
        self.assertIn("memory", str(path))
    
    def test_get_session_dir(self):
        """Should resolve session directory."""
        config = {
            "paths": {"workspace": "/workspace"},
            "memory": {"session_dir": "memory/sessions"}
        }
        
        path = get_session_dir(config)
        
        self.assertIn("sessions", str(path))


class TestStatus(unittest.TestCase):
    """Test status reporting."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_dir = Path(self.temp_dir) / ".emergence" / "state"
        self.state_dir.mkdir(parents=True)
        
        self.config = {
            "paths": {
                "workspace": self.temp_dir,
                "state": ".emergence/state"
            }
        }
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_get_status_no_state(self):
        """Should report status when no state exists."""
        status = get_status(self.config)
        
        self.assertEqual(status["runs_completed"], 0)
        self.assertIsNone(status["last_run"])


if __name__ == "__main__":
    unittest.main()
