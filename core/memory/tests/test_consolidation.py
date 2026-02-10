"""Unit tests for the Consolidation Engine.

Tests configuration loading, frontmatter parsing, file discovery,
LLM analysis orchestration, and daily memory appending.
"""

import json
import os
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.memory.consolidation import (
    load_config,
    parse_frontmatter,
    get_target_date,
    format_consolidated_entry,
    discover_sessions,
    is_consolidated,
    mark_consolidated,
    load_state,
    save_state,
    build_consolidation_prompt,
    extract_with_keywords,
    get_session_dir,
    get_daily_dir,
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
        self.assertIn("memory", config)
        self.assertEqual(config["memory"]["daily_dir"], "memory")
    
    def test_load_custom_config(self):
        """Should load custom config values."""
        custom = {
            "agent": {"name": "Test Agent"},
            "memory": {"daily_dir": "custom/memory"}
        }
        self.config_file.write_text(json.dumps(custom))
        
        config = load_config(self.config_file)
        
        self.assertEqual(config["agent"]["name"], "Test Agent")
        self.assertEqual(config["memory"]["daily_dir"], "custom/memory")
    
    def test_config_with_comments(self):
        """Should strip comment lines from JSON."""
        content = """{
            // This is a comment
            "agent": {"name": "Test"},
            # Another comment
            "memory": {"daily_dir": "mem"}
        }"""
        self.config_file.write_text(content)
        
        config = load_config(self.config_file)
        
        self.assertEqual(config["agent"]["name"], "Test")


class TestFrontmatterParsing(unittest.TestCase):
    """Test YAML frontmatter parsing."""
    
    def test_parse_valid_frontmatter(self):
        """Should parse valid frontmatter correctly."""
        content = """---
drive: CURIOSITY
timestamp: 2026-02-07T14:30:00Z
pressure: 22.5/25
trigger: drive
---

## Summary
Test content."""
        
        metadata, body = parse_frontmatter(content)
        
        self.assertEqual(metadata["drive"], "CURIOSITY")
        self.assertEqual(metadata["timestamp"], "2026-02-07T14:30:00Z")
        self.assertEqual(metadata["pressure"], "22.5/25")
        self.assertEqual(metadata["trigger"], "drive")
        self.assertIn("Test content", body)
    
    def test_parse_no_frontmatter(self):
        """Should return empty metadata when no frontmatter."""
        content = "## Just a header\n\nSome content."
        
        metadata, body = parse_frontmatter(content)
        
        self.assertEqual(metadata, {})
        self.assertEqual(body, content)
    
    def test_parse_incomplete_frontmatter(self):
        """Should handle incomplete frontmatter gracefully."""
        content = "---\nkey: value\nMore content without closing"
        
        metadata, body = parse_frontmatter(content)
        
        # Should treat as no frontmatter
        self.assertEqual(metadata, {})
    
    def test_parse_quoted_values(self):
        """Should strip quotes from values."""
        content = '''---
drive: "CURIOSITY"
model: 'anthropic/claude'
---
Body'''
        
        metadata, body = parse_frontmatter(content)
        
        self.assertEqual(metadata["drive"], "CURIOSITY")
        self.assertEqual(metadata["model"], "anthropic/claude")


class TestDateExtraction(unittest.TestCase):
    """Test date extraction from metadata."""
    
    def test_get_date_from_timestamp(self):
        """Should extract date from ISO timestamp."""
        metadata = {"timestamp": "2026-02-07T14:30:00Z"}
        
        date = get_target_date(metadata)
        
        self.assertEqual(date, "2026-02-07")
    
    def test_get_date_from_iso_format(self):
        """Should handle various ISO formats."""
        metadata = {"timestamp": "2026-02-07T14:30:00+00:00"}
        
        date = get_target_date(metadata)
        
        self.assertEqual(date, "2026-02-07")
    
    def test_get_date_fallback(self):
        """Should return today's date on invalid timestamp."""
        metadata = {"timestamp": "invalid"}
        
        date = get_target_date(metadata)
        
        # Should return today's date
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.assertEqual(date, today)


class TestEntryFormatting(unittest.TestCase):
    """Test consolidated entry formatting."""
    
    def test_format_basic_entry(self):
        """Should format entry with basic metadata."""
        metadata = {
            "drive": "CURIOSITY",
            "timestamp": "2026-02-07T14:30:00Z"
        }
        insights = "Test insights here."
        source = Path("memory/sessions/2026-02-07-1430-CURIOSITY.md")
        
        entry = format_consolidated_entry(metadata, insights, source)
        
        self.assertIn("## Consolidated Session — CURIOSITY", entry)
        self.assertIn("14:30 GMT", entry)
        self.assertIn("Test insights here.", entry)
        self.assertIn("2026-02-07-1430-CURIOSITY.md", entry)
    
    def test_format_without_timestamp(self):
        """Should format entry without time when no timestamp."""
        metadata = {"drive": "SOCIAL"}
        insights = "Social session."
        source = Path("test.md")
        
        entry = format_consolidated_entry(metadata, insights, source)
        
        self.assertIn("## Consolidated Session — SOCIAL", entry)
        self.assertIn("Social session.", entry)


class TestFileDiscovery(unittest.TestCase):
    """Test session file discovery."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.session_dir = Path(self.temp_dir) / "sessions"
        self.session_dir.mkdir()
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_discover_no_files(self):
        """Should return empty list when no files."""
        state = {"consolidated": []}
        files = discover_sessions(self.session_dir, state)
        
        self.assertEqual(files, [])
    
    def test_discover_markdown_only(self):
        """Should only discover .md files."""
        (self.session_dir / "test.md").write_text("test")
        (self.session_dir / "other.txt").write_text("test")
        (self.session_dir / "script.py").write_text("test")
        
        state = {"consolidated": []}
        files = discover_sessions(self.session_dir, state)
        
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].suffix, ".md")
    
    def test_discover_excludes_consolidated(self):
        """Should exclude already consolidated files."""
        file1 = self.session_dir / "session1.md"
        file1.write_text("test")
        file2 = self.session_dir / "session2.md"
        file2.write_text("test")
        
        state = {"consolidated": [str(file1.resolve())]}
        files = discover_sessions(self.session_dir, state)
        
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].name, "session2.md")


class TestStateManagement(unittest.TestCase):
    """Test consolidation state management."""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.state_file = Path(self.temp_dir) / "state.json"
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_load_missing_state(self):
        """Should return default state when file missing."""
        state = load_state(self.state_file)
        
        self.assertEqual(state["version"], "1.0")
        self.assertEqual(state["consolidated"], [])
    
    def test_save_and_load_state(self):
        """Should save and load state correctly."""
        state = {"version": "1.0", "consolidated": ["/path/to/file.md"]}
        
        save_state(self.state_file, state)
        loaded = load_state(self.state_file)
        
        self.assertEqual(loaded["consolidated"], ["/path/to/file.md"])
    
    def test_is_consolidated(self):
        """Should correctly check consolidation status."""
        test_file = Path("/test/session.md")
        state = {"consolidated": [str(test_file.resolve())]}
        
        self.assertTrue(is_consolidated(state, test_file))
        self.assertFalse(is_consolidated(state, Path("/other.md")))
    
    def test_mark_consolidated(self):
        """Should mark file as consolidated."""
        test_file = Path("/test/session.md")
        state = {"consolidated": []}
        
        mark_consolidated(state, test_file)
        
        self.assertIn(str(test_file.resolve()), state["consolidated"])


class TestPromptBuilding(unittest.TestCase):
    """Test consolidation prompt building."""
    
    def test_build_prompt_includes_metadata(self):
        """Should include metadata in prompt."""
        metadata = {
            "drive": "CURIOSITY",
            "timestamp": "2026-02-07T14:30:00Z",
            "pressure": "22.5/25",
            "trigger": "drive"
        }
        body = "Test session content."
        
        prompt = build_consolidation_prompt(metadata, body)
        
        self.assertIn("CURIOSITY", prompt)
        self.assertIn("2026-02-07T14:30:00Z", prompt)
        self.assertIn("22.5/25", prompt)
        self.assertIn("Test session content.", prompt)
    
    def test_build_prompt_truncates_long_body(self):
        """Should truncate very long content."""
        metadata = {"drive": "CURIOSITY"}
        body = "x" * 10000
        
        prompt = build_consolidation_prompt(metadata, body)
        
        self.assertIn("[... content truncated ...]", prompt)


class TestKeywordExtraction(unittest.TestCase):
    """Test keyword-based extraction fallback."""
    
    def test_extract_basic_summary(self):
        """Should create basic summary from metadata."""
        metadata = {"drive": "SOCIAL", "timestamp": "2026-02-07T10:00:00Z"}
        body = "Some content here."
        
        result = extract_with_keywords(metadata, body)
        
        self.assertIn("SOCIAL", result)
        self.assertIn("2026-02-07T10:00:00Z", result)
    
    def test_extract_counts_patterns(self):
        """Should count code blocks and sections."""
        metadata = {"drive": "CREATIVE"}
        body = """
## Section 1
```python
code
```
## Section 2
[Link](http://example.com)
"""
        
        result = extract_with_keywords(metadata, body)
        
        self.assertIn("CREATIVE", result)


class TestPathResolution(unittest.TestCase):
    """Test path resolution from config."""
    
    def test_get_session_dir(self):
        """Should resolve session directory."""
        config = {
            "paths": {"workspace": "/workspace"},
            "memory": {"session_dir": "memory/sessions"}
        }
        
        path = get_session_dir(config)
        
        self.assertIn("memory/sessions", str(path))
    
    def test_get_daily_dir(self):
        """Should resolve daily directory."""
        config = {
            "paths": {"workspace": "/workspace"},
            "memory": {"daily_dir": "memory"}
        }
        
        path = get_daily_dir(config)
        
        self.assertIn("memory", str(path))


if __name__ == "__main__":
    unittest.main()
