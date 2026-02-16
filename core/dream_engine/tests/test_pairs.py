"""Tests for pairing algorithm module."""

import unittest
from datetime import datetime, timezone

from core.dream_engine.pairs import (
    ConceptPair,
    PairGenerator,
    generate_pairs,
    create_date_seed,
)


class TestConceptPair(unittest.TestCase):
    """Tests for ConceptPair class."""

    def test_initialization(self):
        """Should initialize with correct attributes."""
        pair = ConceptPair(
            concept_a="neural network",
            concept_b="garden",
            sources_a=["2026-02-07.md"],
            sources_b=["2026-02-06.md"],
            score_a=5.0,
            score_b=3.0,
        )

        self.assertEqual(pair.concept_a, "neural network")
        self.assertEqual(pair.concept_b, "garden")
        self.assertEqual(pair.sources_a, ["2026-02-07.md"])
        self.assertEqual(pair.sources_b, ["2026-02-06.md"])
        self.assertEqual(pair.score_a, 5.0)
        self.assertEqual(pair.score_b, 3.0)
        self.assertTrue(pair.is_cross_source)

    def test_same_source_detection(self):
        """Should detect same-source pairs."""
        pair = ConceptPair(
            concept_a="concept one",
            concept_b="concept two",
            sources_a=["2026-02-07.md", "2026-02-06.md"],
            sources_b=["2026-02-07.md", "2026-02-05.md"],
        )

        self.assertFalse(pair.is_cross_source)
        self.assertEqual(pair.shared_sources, {"2026-02-07.md"})

    def test_to_dict(self):
        """Should convert to dictionary."""
        pair = ConceptPair(
            concept_a="a",
            concept_b="b",
            sources_a=["file1.md"],
            sources_b=["file2.md"],
            score_a=1.0,
            score_b=2.0,
        )

        d = pair.to_dict()
        self.assertEqual(d["concepts"], ["a", "b"])
        self.assertEqual(d["is_cross_source"], True)

    def test_equality(self):
        """Should consider pairs equal regardless of order."""
        pair1 = ConceptPair("a", "b", ["f1"], ["f2"])
        pair2 = ConceptPair("b", "a", ["f2"], ["f1"])
        pair3 = ConceptPair("a", "c", ["f1"], ["f2"])

        self.assertEqual(pair1, pair2)
        self.assertNotEqual(pair1, pair3)
        self.assertEqual(hash(pair1), hash(pair2))


class TestPairGenerator(unittest.TestCase):
    """Tests for PairGenerator class."""

    def test_basic_generation(self):
        """Should generate requested number of pairs."""
        concepts = [
            {"text": f"concept_{i}", "sources": [f"file{i}.md"], "score": float(i)}
            for i in range(10)
        ]

        generator = PairGenerator(concepts=concepts, pairs_to_generate=5, require_cross_source=True)

        pairs = generator.generate()
        self.assertEqual(len(pairs), 5)

    def test_no_duplicates(self):
        """Should not generate duplicate pairs."""
        concepts = [
            {"text": f"concept_{i}", "sources": [f"file{i}.md"], "score": float(i)}
            for i in range(20)
        ]

        generator = PairGenerator(concepts=concepts, pairs_to_generate=10)

        pairs = generator.generate()
        pair_set = set(pairs)

        # All pairs should be unique
        self.assertEqual(len(pairs), len(pair_set))

    def test_cross_source_requirement(self):
        """Should respect cross-source requirement."""
        concepts = [
            {"text": "a", "sources": ["file1.md"], "score": 1.0},
            {"text": "b", "sources": ["file1.md"], "score": 1.0},  # Same source
            {"text": "c", "sources": ["file2.md"], "score": 1.0},  # Different source
        ]

        generator = PairGenerator(concepts=concepts, pairs_to_generate=2, require_cross_source=True)

        pairs = generator.generate()

        # All pairs should be cross-source
        for pair in pairs:
            self.assertTrue(pair.is_cross_source)

    def test_not_enough_concepts(self):
        """Should handle insufficient concepts."""
        concepts = [{"text": "only_one", "sources": ["file1.md"], "score": 1.0}]

        generator = PairGenerator(concepts=concepts, pairs_to_generate=5)

        pairs = generator.generate()
        self.assertEqual(pairs, [])

    def test_reproducibility(self):
        """Should produce reproducible results with same seed."""
        concepts = [
            {"text": f"concept_{i}", "sources": [f"file{i % 3}.md"], "score": float(i)}
            for i in range(20)
        ]

        generator1 = PairGenerator(concepts, 5, seed=42)
        generator2 = PairGenerator(concepts, 5, seed=42)

        pairs1 = generator1.generate()
        pairs2 = generator2.generate()

        # Should generate same pairs
        self.assertEqual(len(pairs1), len(pairs2))
        for p1, p2 in zip(pairs1, pairs2):
            self.assertEqual(p1.concept_a, p2.concept_a)
            self.assertEqual(p1.concept_b, p2.concept_b)

    def test_get_stats(self):
        """Should return generation statistics."""
        concepts = [
            {"text": f"concept_{i}", "sources": [f"file{i}.md"], "score": float(i)}
            for i in range(10)
        ]

        generator = PairGenerator(concepts, 5)
        generator.generate()

        stats = generator.get_stats()
        self.assertEqual(stats["target_pairs"], 5)
        self.assertEqual(stats["total_pairs"], 5)


class TestGeneratePairs(unittest.TestCase):
    """Tests for generate_pairs convenience function."""

    def test_basic_usage(self):
        """Should generate pairs with default settings."""
        concepts = [{"text": f"concept_{i}", "sources": [f"file{i}.md"]} for i in range(10)]

        pairs = generate_pairs(concepts, pairs_to_generate=3)
        self.assertEqual(len(pairs), 3)

    def test_date_based_seed(self):
        """Should use date for seed."""
        concepts = [{"text": f"concept_{i}", "sources": [f"file{i}.md"]} for i in range(10)]

        date = datetime(2026, 2, 7, tzinfo=timezone.utc)
        pairs1 = generate_pairs(concepts, pairs_to_generate=3, reference_date=date)
        pairs2 = generate_pairs(concepts, pairs_to_generate=3, reference_date=date)

        # Same date should give same results
        self.assertEqual(len(pairs1), len(pairs2))


class TestCreateDateSeed(unittest.TestCase):
    """Tests for create_date_seed function."""

    def test_specific_date(self):
        """Should create consistent seed for same date."""
        date = datetime(2026, 2, 7, tzinfo=timezone.utc)
        seed1 = create_date_seed(date)
        seed2 = create_date_seed(date)

        self.assertEqual(seed1, seed2)
        self.assertEqual(seed1, 20260207)

    def test_different_dates(self):
        """Should create different seeds for different dates."""
        date1 = datetime(2026, 2, 7, tzinfo=timezone.utc)
        date2 = datetime(2026, 2, 8, tzinfo=timezone.utc)

        seed1 = create_date_seed(date1)
        seed2 = create_date_seed(date2)

        self.assertNotEqual(seed1, seed2)


if __name__ == "__main__":
    unittest.main()
