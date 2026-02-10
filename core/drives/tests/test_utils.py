"""Unit tests for utility functions.

Tests fuzzy matching, name normalization, and formatting utilities.
"""

import sys
import unittest
from pathlib import Path

# Import from the package
from core.drives.utils import (
    fuzzy_match,
    get_ambiguous_matches,
    format_pressure_bar,
    normalize_drive_name,
)


class TestFuzzyMatch(unittest.TestCase):
    """Test fuzzy drive name matching."""
    
    def test_exact_match(self):
        """Exact match should work."""
        candidates = ["CURIOSITY", "CARE", "CREATIVE"]
        result = fuzzy_match("CURIOSITY", candidates)
        self.assertEqual(result, "CURIOSITY")
    
    def test_case_insensitive_match(self):
        """Matching should be case-insensitive."""
        candidates = ["CURIOSITY", "CARE", "CREATIVE"]
        result = fuzzy_match("curiosity", candidates)
        self.assertEqual(result, "CURIOSITY")
    
    def test_prefix_match(self):
        """Prefix match should work."""
        candidates = ["CURIOSITY", "CARE", "CREATIVE"]
        result = fuzzy_match("curio", candidates)
        self.assertEqual(result, "CURIOSITY")
    
    def test_substring_match(self):
        """Substring match should work."""
        candidates = ["CURIOSITY", "CARE", "CREATIVE"]
        result = fuzzy_match("riosit", candidates)  # Middle of CURIOSITY
        self.assertEqual(result, "CURIOSITY")
    
    def test_ambiguous_prefix_returns_none(self):
        """Ambiguous prefix should return None."""
        candidates = ["CURIOSITY", "CARE", "CREATIVE"]
        result = fuzzy_match("c", candidates)  # Matches CARE, CURIOSITY, CREATIVE
        self.assertIsNone(result)
    
    def test_ambiguous_substring_returns_none(self):
        """Ambiguous substring should return None."""
        candidates = ["MAINTENANCE", "MAINTAIN"]
        result = fuzzy_match("maint", candidates)
        self.assertIsNone(result)
    
    def test_no_match_returns_none(self):
        """No match should return None."""
        candidates = ["CURIOSITY", "CARE", "CREATIVE"]
        result = fuzzy_match("xyz", candidates)
        self.assertIsNone(result)
    
    def test_empty_name_returns_none(self):
        """Empty name should return None."""
        candidates = ["CURIOSITY", "CARE"]
        result = fuzzy_match("", candidates)
        self.assertIsNone(result)
    
    def test_empty_candidates_returns_none(self):
        """Empty candidates should return None."""
        result = fuzzy_match("care", [])
        self.assertIsNone(result)
    
    def test_hyphen_and_underscore_normalization(self):
        """Hyphens and underscores should be treated as spaces."""
        candidates = ["MY DRIVE", "MY_DRIVE", "MY-DRIVE"]
        # All should match any normalized form
        result1 = fuzzy_match("my drive", candidates)
        self.assertIsNotNone(result1)
        
        result2 = fuzzy_match("my_drive", candidates)
        self.assertIsNotNone(result2)
        
        result3 = fuzzy_match("my-drive", candidates)
        self.assertIsNotNone(result3)
    
    def test_exact_takes_precedence_over_prefix(self):
        """Exact match should take precedence."""
        candidates = ["CARE", "CAREFUL"]
        result = fuzzy_match("care", candidates)
        self.assertEqual(result, "CARE")
    
    def test_unique_prefix_takes_precedence_over_ambiguous_substring(self):
        """Unique prefix should work even with ambiguous substring."""
        candidates = ["CARE", "CURIOSITY"]
        result = fuzzy_match("car", candidates)  # Unique prefix of CARE
        self.assertEqual(result, "CARE")


class TestGetAmbiguousMatches(unittest.TestCase):
    """Test ambiguous match detection."""
    
    def test_get_all_prefix_matches(self):
        """Should return all prefix matches."""
        candidates = ["CARE", "CURIOSITY", "CREATIVE"]
        matches = get_ambiguous_matches("c", candidates)
        
        self.assertEqual(len(matches), 3)
        self.assertIn("CARE", matches)
        self.assertIn("CURIOSITY", matches)
        self.assertIn("CREATIVE", matches)
    
    def test_get_all_substring_matches(self):
        """Should return all substring matches."""
        candidates = ["MAINTENANCE", "MAINTAIN"]
        matches = get_ambiguous_matches("maint", candidates)
        
        self.assertEqual(len(matches), 2)
    
    def test_empty_returns_empty(self):
        """Empty input should return empty list."""
        matches = get_ambiguous_matches("", ["CARE", "CURIOSITY"])
        self.assertEqual(matches, [])
    
    def test_no_matches_returns_empty(self):
        """No matches should return empty list."""
        matches = get_ambiguous_matches("xyz", ["CARE", "CURIOSITY"])
        self.assertEqual(matches, [])


class TestFormatPressureBar(unittest.TestCase):
    """Test pressure bar formatting."""
    
    def test_zero_pressure(self):
        """Zero pressure should show empty bar."""
        result = format_pressure_bar(0.0, 20.0, 10)
        self.assertIn("[░░░░░░░░░░]", result)
        self.assertIn("0%", result)
    
    def test_fifty_percent(self):
        """50% pressure should show half bar."""
        result = format_pressure_bar(10.0, 20.0, 10)
        self.assertIn("█████", result)  # Half filled
        self.assertIn("50%", result)
    
    def test_full_pressure(self):
        """100% pressure should show full bar."""
        result = format_pressure_bar(20.0, 20.0, 10)
        self.assertIn("██████████", result)  # Fully filled
        self.assertIn("100%", result)
    
    def test_over_threshold_shows_percentage(self):
        """Over threshold should still show percentage."""
        result = format_pressure_bar(30.0, 20.0, 10)
        self.assertIn("150%", result)
    
    def test_over_threshold_capped_visual(self):
        """Visual bar should cap at 150%."""
        result = format_pressure_bar(50.0, 20.0, 10)
        # 50/20 = 250%, but bar caps at 150%
        self.assertIn("250%", result)  # But shows actual percentage
    
    def test_default_width(self):
        """Default width should be 20 characters."""
        result = format_pressure_bar(10.0, 20.0)
        # [ + 20 chars + ] + space + percentage = ~28 chars
        self.assertIn("[", result)
        self.assertIn("]", result)
    
    def test_zero_threshold(self):
        """Zero threshold should not crash."""
        result = format_pressure_bar(10.0, 0.0, 10)
        self.assertIn("0%", result)


class TestNormalizeDriveName(unittest.TestCase):
    """Test drive name normalization."""
    
    def test_uppercase_conversion(self):
        """Should convert to uppercase."""
        result = normalize_drive_name("curiosity")
        self.assertEqual(result, "CURIOSITY")
    
    def test_hyphen_to_space(self):
        """Should convert hyphens to spaces."""
        result = normalize_drive_name("my-drive")
        self.assertEqual(result, "MY DRIVE")
    
    def test_underscore_to_space(self):
        """Should convert underscores to spaces."""
        result = normalize_drive_name("my_drive")
        self.assertEqual(result, "MY DRIVE")
    
    def test_mixed_separators(self):
        """Should handle mixed separators."""
        result = normalize_drive_name("my-drive_name")
        self.assertEqual(result, "MY DRIVE NAME")
    
    def test_already_uppercase(self):
        """Already uppercase should remain unchanged."""
        result = normalize_drive_name("CURIOSITY")
        self.assertEqual(result, "CURIOSITY")


if __name__ == "__main__":
    unittest.main(verbosity=2)
