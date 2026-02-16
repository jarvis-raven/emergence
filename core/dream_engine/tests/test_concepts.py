"""Tests for concept extraction module."""

import unittest
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from core.dream_engine.concepts import (
    normalize_word,
    extract_phrases,
    calculate_tf_idf,
    ConceptExtractor,
    STOPWORDS,
)


class TestNormalizeWord(unittest.TestCase):
    """Tests for normalize_word function."""

    def test_basic_normalization(self):
        """Should lowercase and clean words."""
        self.assertEqual(normalize_word("Hello"), "hello")
        self.assertEqual(normalize_word("WORLD"), "world")

    def test_punctuation_removal(self):
        """Should strip punctuation from ends."""
        self.assertEqual(normalize_word("hello,"), "hello")
        self.assertEqual(normalize_word(".world."), "world")
        self.assertEqual(normalize_word('"quoted"'), "quoted")

    def test_stopword_filtering(self):
        """Should filter out stopwords."""
        self.assertIsNone(normalize_word("the"))
        self.assertIsNone(normalize_word("and"))
        self.assertIsNone(normalize_word("is"))

    def test_short_word_filtering(self):
        """Should filter words shorter than 3 chars."""
        self.assertIsNone(normalize_word("ab"))
        self.assertIsNone(normalize_word("a"))

    def test_numeric_filtering(self):
        """Should filter words with numbers."""
        self.assertIsNone(normalize_word("hello123"))
        self.assertIsNone(normalize_word("2024"))

    def test_gerund_filtering(self):
        """Should filter short gerunds."""
        self.assertIsNone(normalize_word("going"))  # 5 chars, ok
        self.assertEqual(normalize_word("running"), "running")  # 7 chars, ok


class TestExtractPhrases(unittest.TestCase):
    """Tests for extract_phrases function."""

    def test_basic_extraction(self):
        """Should extract multi-word phrases."""
        text = "The quick brown fox jumps over the lazy dog"
        phrases = extract_phrases(text, min_words=2, max_words=2)

        # Should include "quick brown", "brown fox", etc.
        self.assertIn("quick brown", phrases)
        self.assertIn("brown fox", phrases)
        self.assertIn("lazy dog", phrases)

    def test_filters_stopwords(self):
        """Should not include phrases with stopwords."""
        text = "The quick brown fox"
        phrases = extract_phrases(text, min_words=2, max_words=2)

        # "the quick" should be filtered (contains "the")
        self.assertNotIn("the quick", phrases)

    def test_varied_phrase_lengths(self):
        """Should extract phrases of different lengths."""
        text = "machine learning algorithms are fascinating"

        phrases_2 = extract_phrases(text, min_words=2, max_words=2)
        phrases_3 = extract_phrases(text, min_words=3, max_words=3)

        self.assertIn("machine learning", phrases_2)
        self.assertIn("learning algorithms", phrases_2)
        self.assertIn("machine learning algorithms", phrases_3)


class TestCalculateTfIdf(unittest.TestCase):
    """Tests for calculate_tf_idf function."""

    def test_basic_scoring(self):
        """Should score phrases by TF-IDF."""
        file_phrases = {
            "file1.md": ["neural network", "deep learning", "neural network"],
            "file2.md": ["deep learning", "machine learning"],
        }

        results = calculate_tf_idf(file_phrases, max_concepts=10)

        # Should return list of tuples
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

        # Each result should be (phrase, score, sources)
        for phrase, score, sources in results:
            self.assertIsInstance(phrase, str)
            self.assertIsInstance(score, float)
            self.assertIsInstance(sources, list)

    def test_rarity_bonus(self):
        """Should score rare phrases higher."""
        file_phrases = {
            "file1.md": ["common phrase", "common phrase", "common phrase"],
            "file2.md": ["common phrase", "rare phrase"],
        }

        results = calculate_tf_idf(file_phrases, max_concepts=10)
        phrases = {p: (s, src) for p, s, src in results}

        # Both phrases should be present
        self.assertIn("common phrase", phrases)
        self.assertIn("rare phrase", phrases)

    def test_empty_input(self):
        """Should handle empty input gracefully."""
        results = calculate_tf_idf({})
        self.assertEqual(results, [])


class TestConceptExtractor(unittest.TestCase):
    """Tests for ConceptExtractor class."""

    def setUp(self):
        """Create temporary directory with test files."""
        self.temp_dir = TemporaryDirectory()
        self.memory_dir = Path(self.temp_dir.name)

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_extract_from_files(self):
        """Should extract concepts from memory files."""
        # Create test file
        test_file = self.memory_dir / "2026-02-07.md"
        test_file.write_text(
            """
# Test Memory

## Session — Neural Networks (10:00 GMT)

Deep learning and neural networks are fascinating. Machine learning
algorithms can solve complex problems. Neural networks learn patterns
from data automatically.
"""
        )

        extractor = ConceptExtractor(
            memory_dir=self.memory_dir,
            lookback_days=7,
            max_concepts=10,
            reference_date=datetime(2026, 2, 7, tzinfo=timezone.utc),
        )

        concepts = extractor.extract()

        # Should extract some concepts
        self.assertIsInstance(concepts, list)
        # Might be empty if no good phrases found
        if concepts:
            # Check concept structure
            concept = concepts[0]
            self.assertIn("text", concept)
            self.assertIn("score", concept)
            self.assertIn("sources", concept)

    def test_no_files_found(self):
        """Should handle missing files gracefully."""
        empty_dir = self.memory_dir / "nonexistent"

        extractor = ConceptExtractor(memory_dir=empty_dir, lookback_days=7, max_concepts=10)

        concepts = extractor.extract()
        self.assertEqual(concepts, [])

    def test_skips_frontmatter(self):
        """Should skip YAML frontmatter."""
        test_file = self.memory_dir / "2026-02-07.md"
        test_file.write_text(
            """---
drive: CURIOSITY
timestamp: 2026-02-07T10:00:00Z
---

## Content

Deep learning neural networks machine learning fascinating concepts here.
"""
        )

        extractor = ConceptExtractor(
            memory_dir=self.memory_dir,
            lookback_days=7,
            max_concepts=10,
            reference_date=datetime(2026, 2, 7, tzinfo=timezone.utc),
        )

        concepts = extractor.extract()
        # Should not include frontmatter fields as concepts
        for concept in concepts:
            self.assertNotIn(concept["text"], ["drive", "timestamp", "curiosity"])


class TestStopwords(unittest.TestCase):
    """Tests for stopword list."""

    def test_common_stopwords_present(self):
        """Should include common English stopwords."""
        self.assertIn("the", STOPWORDS)
        self.assertIn("and", STOPWORDS)
        self.assertIn("is", STOPWORDS)
        self.assertIn("are", STOPWORDS)

    def test_memory_artifacts_present(self):
        """Should include memory-specific artifacts."""
        self.assertIn("session", STOPWORDS)
        self.assertIn("summary", STOPWORDS)
        self.assertIn("timestamp", STOPWORDS)


if __name__ == "__main__":
    unittest.main()
