"""Tests for insight scoring module."""

import unittest
from datetime import datetime, timezone

from core.dream_engine.scoring import (
    InsightScorer,
    build_concept_frequencies,
    score_pairs,
)


class TestInsightScorer(unittest.TestCase):
    """Tests for InsightScorer class."""
    
    def test_initialization(self):
        """Should initialize with correct attributes."""
        frequencies = {"concept": 5}
        scorer = InsightScorer(
            concept_frequencies=frequencies,
            max_score=100,
            min_score=0
        )
        
        self.assertEqual(scorer.concept_frequencies, frequencies)
        self.assertEqual(scorer.max_score, 100)
        self.assertEqual(scorer.min_score, 0)
    
    def test_rarity_score(self):
        """Should score rare concepts higher."""
        frequencies = {
            "common": 10,
            "rare": 1,
        }
        scorer = InsightScorer(frequencies)
        
        common_score = scorer.calculate_rarity_score("common")
        rare_score = scorer.calculate_rarity_score("rare")
        
        # Rare should score higher (or equal if same frequency)
        self.assertGreaterEqual(rare_score, common_score)
    
    def test_distance_score_cross_source(self):
        """Should give high score for cross-source pairs."""
        scorer = InsightScorer()
        
        score = scorer.calculate_distance_score(
            sources_a=["file1.md", "file2.md"],
            sources_b=["file3.md", "file4.md"]
        )
        
        # Completely different sources should get max distance score
        self.assertGreaterEqual(score, 30)
    
    def test_distance_score_same_source(self):
        """Should give low score for same-source pairs."""
        scorer = InsightScorer()
        
        score = scorer.calculate_distance_score(
            sources_a=["file1.md"],
            sources_b=["file1.md"]
        )
        
        # Same source should get 0 distance score
        self.assertEqual(score, 0)
    
    def test_distance_score_partial_overlap(self):
        """Should give medium score for partial overlap."""
        scorer = InsightScorer()
        
        score = scorer.calculate_distance_score(
            sources_a=["file1.md", "file2.md"],
            sources_b=["file2.md", "file3.md"]  # One overlap
        )
        
        # Should be between 0 and max
        self.assertGreater(score, 0)
        self.assertLess(score, 35)
    
    def test_recency_score_today(self):
        """Should give max score for today's concepts."""
        scorer = InsightScorer()
        today = datetime(2026, 2, 7, tzinfo=timezone.utc)
        
        score = scorer.calculate_recency_score(
            concept_sources=["2026-02-07.md"],
            reference_date=today
        )
        
        self.assertEqual(score, 15)
    
    def test_recency_score_yesterday(self):
        """Should give high score for yesterday's concepts."""
        scorer = InsightScorer()
        today = datetime(2026, 2, 7, tzinfo=timezone.utc)
        
        score = scorer.calculate_recency_score(
            concept_sources=["2026-02-06.md"],
            reference_date=today
        )
        
        self.assertEqual(score, 10)
    
    def test_recency_score_week_ago(self):
        """Should give low score for old concepts."""
        scorer = InsightScorer()
        today = datetime(2026, 2, 7, tzinfo=timezone.utc)
        
        score = scorer.calculate_recency_score(
            concept_sources=["2026-01-31.md"],
            reference_date=today
        )
        
        self.assertEqual(score, 0)
    
    def test_score_pair_structure(self):
        """Should return properly structured score dict."""
        scorer = InsightScorer()
        
        result = scorer.score_pair(
            concept_a="neural network",
            concept_b="garden",
            sources_a=["2026-02-07.md"],
            sources_b=["2026-02-06.md"],
            score_a=5.0,
            score_b=3.0
        )
        
        self.assertIn('total', result)
        self.assertIn('breakdown', result)
        self.assertIn('components', result)
        
        self.assertIn('base', result['breakdown'])
        self.assertIn('rarity', result['breakdown'])
        self.assertIn('distance', result['breakdown'])
        self.assertIn('recency', result['breakdown'])
        self.assertIn('tf_idf', result['breakdown'])
    
    def test_score_range(self):
        """Should return score within valid range."""
        scorer = InsightScorer(max_score=100, min_score=0)
        
        result = scorer.score_pair(
            concept_a="a",
            concept_b="b",
            sources_a=["file1.md"],
            sources_b=["file2.md"]
        )
        
        self.assertGreaterEqual(result['total'], 0)
        self.assertLessEqual(result['total'], 100)
    
    def test_cross_source_bonus(self):
        """Cross-source pairs should score higher."""
        frequencies = {"a": 1, "b": 1}
        scorer = InsightScorer(frequencies)
        
        # Cross-source pair
        cross_source = scorer.score_pair(
            concept_a="a",
            concept_b="b",
            sources_a=["file1.md"],
            sources_b=["file2.md"]
        )
        
        # Same-source pair
        same_source = scorer.score_pair(
            concept_a="a",
            concept_b="b",
            sources_a=["file1.md"],
            sources_b=["file1.md"]
        )
        
        # Cross-source should have higher distance score
        self.assertGreater(
            cross_source['breakdown']['distance'],
            same_source['breakdown']['distance']
        )


class TestBuildConceptFrequencies(unittest.TestCase):
    """Tests for build_concept_frequencies function."""
    
    def test_basic_building(self):
        """Should build frequency map from sources."""
        concepts = [
            {'text': 'concept_a', 'sources': ['file1.md', 'file2.md']},
            {'text': 'concept_b', 'sources': ['file1.md']},
        ]
        
        frequencies = build_concept_frequencies(concepts)
        
        self.assertEqual(frequencies['concept_a'], 2)
        self.assertEqual(frequencies['concept_b'], 1)
    
    def test_empty_sources(self):
        """Should handle empty sources list."""
        concepts = [
            {'text': 'concept_a', 'sources': []},
        ]
        
        frequencies = build_concept_frequencies(concepts)
        
        self.assertEqual(frequencies['concept_a'], 0)


class TestScorePairs(unittest.TestCase):
    """Tests for score_pairs convenience function."""
    
    def test_basic_scoring(self):
        """Should score multiple pairs."""
        class MockPair:
            def __init__(self, a, b, sources_a, sources_b, score_a=0, score_b=0):
                self.concept_a = a
                self.concept_b = b
                self.sources_a = sources_a
                self.sources_b = sources_b
                self.score_a = score_a
                self.score_b = score_b
        
        pairs = [
            MockPair("a", "b", ["f1.md"], ["f2.md"]),
            MockPair("c", "d", ["f3.md"], ["f4.md"]),
        ]
        
        concepts = [
            {'text': 'a', 'sources': ['f1.md']},
            {'text': 'b', 'sources': ['f2.md']},
            {'text': 'c', 'sources': ['f3.md']},
            {'text': 'd', 'sources': ['f4.md']},
        ]
        
        results = score_pairs(pairs, concepts)
        
        self.assertEqual(len(results), 2)
        
        # Should be sorted by score (descending)
        scores = [s['total'] for _, s in results]
        self.assertEqual(scores, sorted(scores, reverse=True))
    
    def test_empty_pairs(self):
        """Should handle empty pairs list."""
        results = score_pairs([], [])
        self.assertEqual(results, [])


if __name__ == '__main__':
    unittest.main()
