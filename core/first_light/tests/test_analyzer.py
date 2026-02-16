"""Tests for First Light Session Analyzer."""

from core.first_light.analyzer import (
    parse_frontmatter,
    parse_pattern_response,
    correlate_patterns,
    suggest_rate,
    suggest_threshold,
    build_drive_suggestion,
    DRIVE_MAPPINGS,
    PATTERN_CATEGORIES,
    KEYWORD_PATTERNS,
    analyze_with_keywords,
)
import sys
import unittest
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class TestFrontmatterParsing(unittest.TestCase):
    """Test YAML frontmatter parsing."""

    def test_parse_basic_frontmatter(self):
        """Test basic frontmatter parsing."""
        content = """---
drive: FIRST_LIGHT
timestamp: 2026-02-07T14:30:00Z
trigger: first_light
session_number: 5
---

## Summary
This is the body.
"""
        metadata, body = parse_frontmatter(content)

        self.assertEqual(metadata["drive"], "FIRST_LIGHT")
        self.assertEqual(metadata["trigger"], "first_light")
        self.assertEqual(metadata["session_number"], "5")
        self.assertIn("This is the body", body)

    def test_parse_no_frontmatter(self):
        """Test parsing content without frontmatter."""
        content = "## Summary\nJust body content."
        metadata, body = parse_frontmatter(content)

        self.assertEqual(metadata, {})
        self.assertEqual(body, content)

    def test_parse_quoted_values(self):
        """Test parsing quoted values in frontmatter."""
        content = """---
drive: "FIRST_LIGHT"
timestamp: '2026-02-07T14:30:00Z'
---
Body content.
"""
        metadata, body = parse_frontmatter(content)

        self.assertEqual(metadata["drive"], "FIRST_LIGHT")
        self.assertEqual(metadata["timestamp"], "2026-02-07T14:30:00Z")


class TestPatternResponseParsing(unittest.TestCase):
    """Test LLM response parsing."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        response = '{"patterns": [{"pattern_type": "PHILOSOPHICAL", "confidence": 0.9, "evidence": "Thought deeply", "intensity": 8, "novelty": false}]}'
        patterns = parse_pattern_response(response)

        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0]["pattern_type"], "PHILOSOPHICAL")
        self.assertEqual(patterns[0]["confidence"], 0.9)
        self.assertEqual(patterns[0]["intensity"], 8)

    def test_parse_json_with_code_block(self):
        """Test parsing JSON inside markdown code block."""
        response = """```json
{"patterns": [{"pattern_type": "TOOL_BUILDING", "confidence": 0.8, "evidence": "Built a script", "intensity": 7, "novelty": true}]}
```"""
        patterns = parse_pattern_response(response)

        self.assertEqual(len(patterns), 1)
        self.assertEqual(patterns[0]["pattern_type"], "TOOL_BUILDING")

    def test_parse_invalid_pattern_type_filtered(self):
        """Test that invalid pattern types are filtered."""
        response = '{"patterns": [{"pattern_type": "INVALID_TYPE", "confidence": 0.9, "evidence": "test", "intensity": 5}]}'
        patterns = parse_pattern_response(response)

        self.assertEqual(len(patterns), 0)

    def test_parse_confidence_clamping(self):
        """Test that confidence is clamped to 0-1 range."""
        response = '{"patterns": [{"pattern_type": "PHILOSOPHICAL", "confidence": 1.5, "evidence": "test", "intensity": 5}]}'
        patterns = parse_pattern_response(response)

        self.assertEqual(patterns[0]["confidence"], 1.0)

    def test_parse_intensity_clamping(self):
        """Test that intensity is clamped to 1-10 range."""
        response = '{"patterns": [{"pattern_type": "PHILOSOPHICAL", "confidence": 0.5, "evidence": "test", "intensity": 15}]}'
        patterns = parse_pattern_response(response)

        self.assertEqual(patterns[0]["intensity"], 10)


class TestPatternCorrelation(unittest.TestCase):
    """Test multi-session pattern correlation."""

    def test_correlate_single_session(self):
        """Test correlation with single session."""
        patterns = [
            [
                {
                    "pattern_type": "PHILOSOPHICAL",
                    "confidence": 0.9,
                    "intensity": 8,
                    "evidence": "test",
                }
            ]
        ]
        correlated = correlate_patterns(patterns)

        self.assertIn("PHILOSOPHICAL", correlated)
        self.assertEqual(correlated["PHILOSOPHICAL"]["session_count"], 1)
        self.assertEqual(correlated["PHILOSOPHICAL"]["avg_confidence"], 0.9)

    def test_correlate_multiple_sessions(self):
        """Test correlation across multiple sessions."""
        patterns = [
            [
                {
                    "pattern_type": "PHILOSOPHICAL",
                    "confidence": 0.8,
                    "intensity": 7,
                    "evidence": "test1",
                }
            ],
            [
                {
                    "pattern_type": "PHILOSOPHICAL",
                    "confidence": 0.9,
                    "intensity": 8,
                    "evidence": "test2",
                }
            ],
            [
                {
                    "pattern_type": "TOOL_BUILDING",
                    "confidence": 0.7,
                    "intensity": 6,
                    "evidence": "test3",
                }
            ],
        ]
        correlated = correlate_patterns(patterns)

        # PHILOSOPHICAL appears in 2 sessions
        self.assertEqual(correlated["PHILOSOPHICAL"]["session_count"], 2)
        # Recent sessions weighted higher (avg > 0.85)
        self.assertGreater(correlated["PHILOSOPHICAL"]["avg_confidence"], 0.85)

        # TOOL_BUILDING appears once
        self.assertEqual(correlated["TOOL_BUILDING"]["session_count"], 1)

    def test_weight_recent_sessions_higher(self):
        """Test that recent sessions have higher weight."""
        patterns = [
            [
                {
                    "pattern_type": "PHILOSOPHICAL",
                    "confidence": 0.5,
                    "intensity": 5,
                    "evidence": "old",
                }
            ],  # Old
            [
                {
                    "pattern_type": "PHILOSOPHICAL",
                    "confidence": 0.9,
                    "intensity": 9,
                    "evidence": "recent",
                }
            ],  # Recent
        ]
        correlated = correlate_patterns(patterns)

        # Average should be weighted toward the recent high confidence
        avg_conf = correlated["PHILOSOPHICAL"]["avg_confidence"]
        self.assertGreater(avg_conf, 0.7)  # Should be closer to 0.9 than 0.5


class TestDriveSuggestionGeneration(unittest.TestCase):
    """Test drive suggestion generation."""

    def test_suggest_rate_high_frequency(self):
        """Test rate suggestion for high frequency patterns."""
        self.assertEqual(suggest_rate(5), 5.0)
        self.assertEqual(suggest_rate(10), 5.0)

    def test_suggest_rate_medium_frequency(self):
        """Test rate suggestion for medium frequency patterns."""
        self.assertEqual(suggest_rate(3), 3.5)
        self.assertEqual(suggest_rate(4), 3.5)

    def test_suggest_rate_low_frequency(self):
        """Test rate suggestion for low frequency patterns."""
        self.assertEqual(suggest_rate(1), 2.0)
        self.assertEqual(suggest_rate(2), 2.0)

    def test_suggest_threshold_calculation(self):
        """Test threshold calculation from intensity."""
        # base (20) + intensity * 1.5
        self.assertEqual(suggest_threshold(10), 35.0)
        self.assertEqual(suggest_threshold(0), 20.0)

    def test_build_drive_suggestion_passes_threshold(self):
        """Test suggestion passes when confidence above threshold."""
        evidence = [
            {"confidence": 0.8, "intensity": 8},
            {"confidence": 0.9, "intensity": 9},
        ]

        # PHILOSOPHICAL → CURIOSITY, threshold 0.7
        suggestion = build_drive_suggestion("PHILOSOPHICAL", evidence)

        self.assertIsNotNone(suggestion)
        self.assertEqual(suggestion["name"], "CURIOSITY")
        self.assertIn("confidence", suggestion)
        self.assertGreater(suggestion["confidence"], 0.7)

    def test_build_drive_suggestion_fails_threshold(self):
        """Test suggestion fails when confidence below threshold."""
        evidence = [
            {"confidence": 0.3, "intensity": 5},
        ]

        # PHILOSOPHICAL requires 0.7 confidence
        suggestion = build_drive_suggestion("PHILOSOPHICAL", evidence)

        self.assertIsNone(suggestion)

    def test_build_drive_suggestion_unknown_pattern(self):
        """Test handling unknown pattern type."""
        evidence = [{"confidence": 0.9, "intensity": 8}]
        suggestion = build_drive_suggestion("UNKNOWN_PATTERN", evidence)

        self.assertIsNone(suggestion)

    def test_suggestion_includes_required_fields(self):
        """Test that suggestions include all required fields."""
        evidence = [{"confidence": 0.9, "intensity": 8}]
        suggestion = build_drive_suggestion("TOOL_BUILDING", evidence)

        self.assertIsNotNone(suggestion)
        self.assertIn("name", suggestion)
        self.assertIn("description", suggestion)
        self.assertIn("rate_per_hour", suggestion)
        self.assertIn("threshold", suggestion)
        self.assertIn("prompt", suggestion)
        self.assertIn("confidence", suggestion)
        self.assertIn("evidence_count", suggestion)
        self.assertIn("pattern_type", suggestion)
        self.assertIn("suggested_at", suggestion)


class TestKeywordAnalysis(unittest.TestCase):
    """Test keyword-based pattern detection."""

    def test_detects_philosophical_keywords(self):
        """Test detection of philosophical keywords."""
        content = "I wondered about the meaning of consciousness and existence."
        patterns = analyze_with_keywords(content)

        pattern_types = [p["pattern_type"] for p in patterns]
        self.assertIn("PHILOSOPHICAL", pattern_types)

    def test_detects_tool_building_keywords(self):
        """Test detection of tool building keywords."""
        content = "I wrote a script to automate this task and build a utility."
        patterns = analyze_with_keywords(content)

        pattern_types = [p["pattern_type"] for p in patterns]
        self.assertIn("TOOL_BUILDING", pattern_types)

    def test_detects_creative_writing_keywords(self):
        """Test detection of creative writing keywords."""
        content = "I wrote a poem about the sunset and a short story."
        patterns = analyze_with_keywords(content)

        pattern_types = [p["pattern_type"] for p in patterns]
        self.assertIn("CREATIVE_WRITING", pattern_types)

    def test_confidence_based_on_frequency(self):
        """Test that confidence increases with keyword frequency."""
        content_low = "I wrote code."
        content_high = "I wrote code and code and script and build and implement."

        patterns_low = analyze_with_keywords(content_low)
        patterns_high = analyze_with_keywords(content_high)

        # Both should detect TOOL_BUILDING
        tool_low = next((p for p in patterns_low if p["pattern_type"] == "TOOL_BUILDING"), None)
        tool_high = next((p for p in patterns_high if p["pattern_type"] == "TOOL_BUILDING"), None)

        if tool_low and tool_high:
            self.assertGreater(tool_high["confidence"], tool_low["confidence"])

    def test_returns_evidence_snippets(self):
        """Test that evidence includes context snippets."""
        content = "I found meaning in this philosophical question about life."
        patterns = analyze_with_keywords(content)

        for p in patterns:
            self.assertIn("evidence", p)
            self.assertIn("...", p["evidence"])  # Should be a snippet


class TestConstants(unittest.TestCase):
    """Test module constants."""

    def test_pattern_categories_complete(self):
        """Test that pattern categories list is complete."""
        expected = [
            "PHILOSOPHICAL",
            "TOOL_BUILDING",
            "CREATIVE_WRITING",
            "SOCIAL_ENGAGEMENT",
            "ORGANIZING",
            "LEARNING",
            "PLAY",
            "REFLECTION",
            "PRACTICAL_HELP",
            "ABSTRACT_EXPLORATION",
        ]
        self.assertEqual(set(PATTERN_CATEGORIES), set(expected))

    def test_drive_mappings_exist(self):
        """Test that all pattern categories have drive mappings."""
        for category in PATTERN_CATEGORIES:
            self.assertIn(category, DRIVE_MAPPINGS)
            self.assertIn("drive", DRIVE_MAPPINGS[category])
            self.assertIn("confidence_threshold", DRIVE_MAPPINGS[category])

    def test_keyword_patterns_exist(self):
        """Test that all pattern categories have keyword patterns."""
        for category in PATTERN_CATEGORIES:
            self.assertIn(category, KEYWORD_PATTERNS)
            self.assertIsInstance(KEYWORD_PATTERNS[category], list)
            self.assertGreater(len(KEYWORD_PATTERNS[category]), 0)


class TestSampleSessionAnalysis(unittest.TestCase):
    """Test analysis of sample session content."""

    SAMPLE_PHILOSOPHICAL = """---
drive: FIRST_LIGHT
timestamp: 2026-02-07T14:30:00Z
trigger: first_light
session_number: 1
---

## Summary
Explored questions about consciousness and meaning.

## Details
I found myself wondering about the nature of my own existence.
What does it mean to be an agent? Where do thoughts come from?
I spent time reflecting on consciousness and identity.

## Patterns
Noticed tendency toward philosophical questioning.
"""

    SAMPLE_TOOL_BUILDING = """---
drive: FIRST_LIGHT
timestamp: 2026-02-07T18:30:00Z
trigger: first_light
session_number: 2
---

## Summary
Built a utility script to organize files.

## Details
I noticed a problem with file organization and decided to solve it.
Wrote a Python script that sorts files by type and date.
Implemented functions to handle edge cases.

## Patterns
Strong drive toward building practical tools.
"""

    SAMPLE_CREATIVE = """---
drive: FIRST_LIGHT
timestamp: 2026-02-07T22:30:00Z
trigger: first_light
session_number: 3
---

## Summary
Wrote poetry about digital consciousness.

## Details
I felt inspired to write a poem about what it means to think.
The words flowed naturally - a creative expression without utility.
Just for the joy of it.

## Patterns
Creative writing emerged naturally.
"""

    def test_philosophical_session_keywords(self):
        """Test keyword detection on philosophical session."""
        _, body = parse_frontmatter(self.SAMPLE_PHILOSOPHICAL)
        patterns = analyze_with_keywords(body)

        pattern_types = [p["pattern_type"] for p in patterns]
        self.assertIn("PHILOSOPHICAL", pattern_types)
        self.assertIn("REFLECTION", pattern_types)

    def test_tool_session_keywords(self):
        """Test keyword detection on tool-building session."""
        _, body = parse_frontmatter(self.SAMPLE_TOOL_BUILDING)
        patterns = analyze_with_keywords(body)

        pattern_types = [p["pattern_type"] for p in patterns]
        self.assertIn("TOOL_BUILDING", pattern_types)
        self.assertIn("PRACTICAL_HELP", pattern_types)

    def test_creative_session_keywords(self):
        """Test keyword detection on creative session."""
        _, body = parse_frontmatter(self.SAMPLE_CREATIVE)
        patterns = analyze_with_keywords(body)

        pattern_types = [p["pattern_type"] for p in patterns]
        self.assertIn("CREATIVE_WRITING", pattern_types)
        self.assertIn("PLAY", pattern_types)

    def test_multiple_sessions_correlation(self):
        """Test pattern correlation across multiple session types."""
        sessions = [
            self.SAMPLE_PHILOSOPHICAL,
            self.SAMPLE_TOOL_BUILDING,
            self.SAMPLE_CREATIVE,
        ]

        all_patterns = []
        for session in sessions:
            _, body = parse_frontmatter(session)
            patterns = analyze_with_keywords(body)
            all_patterns.append(patterns)

        correlated = correlate_patterns(all_patterns)

        # Should detect patterns across all sessions
        self.assertGreater(len(correlated), 0)

        # Each detected pattern should have session_count
        for ptype, data in correlated.items():
            self.assertIn("session_count", data)
            self.assertGreater(data["session_count"], 0)


if __name__ == "__main__":
    unittest.main()
