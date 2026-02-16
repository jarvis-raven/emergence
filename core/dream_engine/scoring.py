"""Insight scoring for dream pairs.

Scores concept pairs for interestingness based on:
- Rarity: Less common concepts score higher
- Distance: Cross-source pairs score higher
- Recency: Newer concepts get a slight bonus
"""

import math
from datetime import datetime, timezone
from typing import Optional


class InsightScorer:
    """Scores dream pairs for insight and interestingness."""

    def __init__(
        self,
        concept_frequencies: Optional[dict[str, int]] = None,
        max_score: int = 100,
        min_score: int = 0,
    ):
        """Initialize the insight scorer.

        Args:
            concept_frequencies: Dict mapping concept text to occurrence count
            max_score: Maximum possible score
            min_score: Minimum possible score
        """
        self.concept_frequencies = concept_frequencies or {}
        self.max_score = max_score
        self.min_score = min_score

        # Calculate total for frequency normalization
        self.total_occurrences = sum(self.concept_frequencies.values())
        if self.total_occurrences == 0:
            self.total_occurrences = 1

    def calculate_rarity_score(self, concept_text: str) -> float:
        """Calculate rarity score for a concept.

        Rarer concepts (lower frequency) get higher scores.
        Uses logarithmic scale to prevent extreme values.

        Args:
            concept_text: The concept text

        Returns:
            Rarity score (0-40 range)
        """
        freq = self.concept_frequencies.get(concept_text, 1)

        # Logarithmic rarity: log(total/freq) gives higher scores for rare items
        # Normalize to 0-40 range
        rarity = math.log(self.total_occurrences / max(freq, 1))
        normalized = min(40, rarity * 10)

        return normalized

    def calculate_distance_score(self, sources_a: list[str], sources_b: list[str]) -> float:
        """Calculate distance score based on source overlap.

        Concepts from completely different sources score highest.

        Args:
            sources_a: Source files for concept A
            sources_b: Source files for concept B

        Returns:
            Distance score (0-35 range)
        """
        set_a = set(sources_a)
        set_b = set(sources_b)

        # Calculate Jaccard distance
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)

        if union == 0:
            return 0

        # Jaccard similarity (0 = no overlap, 1 = identical)
        similarity = intersection / union

        # Convert to distance score (inverse similarity)
        # Completely different sources = 35 points
        # Some overlap = partial points
        distance = (1 - similarity) * 35

        return distance

    def calculate_recency_score(
        self, concept_sources: list[str], reference_date: Optional[datetime] = None
    ) -> float:
        """Calculate recency score for a concept.

        Concepts from recent files get a small bonus.

        Args:
            concept_sources: Source files for the concept
            reference_date: Date to calculate from (default: now)

        Returns:
            Recency score (0-15 range)
        """
        if reference_date is None:
            reference_date = datetime.now(timezone.utc)

        # Extract dates from source filenames (assuming YYYY-MM-DD format)
        newest_days_ago = float("inf")

        for source in concept_sources:
            # Try to extract date from filename
            # Expected format: 2026-02-07.md or 2026-02-07-something.md
            import re

            match = re.search(r"(\d{4}-\d{2}-\d{2})", source)
            if match:
                try:
                    date_str = match.group(1)
                    file_date = datetime.strptime(date_str, "%Y-%m-%d")
                    file_date = file_date.replace(tzinfo=timezone.utc)

                    days_ago = (reference_date - file_date).days
                    newest_days_ago = min(newest_days_ago, days_ago)
                except ValueError:
                    continue

        if newest_days_ago == float("inf"):
            return 0  # Couldn't parse any dates

        # Score based on recency
        # Today = 15 points, yesterday = 10 points, 7 days ago = 0 points
        if newest_days_ago == 0:
            return 15
        elif newest_days_ago == 1:
            return 10
        elif newest_days_ago <= 3:
            return 5
        else:
            return 0

    def calculate_tf_idf_contribution(self, tf_idf_score: float) -> float:
        """Calculate score contribution from TF-IDF score.

        Higher TF-IDF indicates more distinctive/important concepts.

        Args:
            tf_idf_score: The TF-IDF score from concept extraction

        Returns:
            Score contribution (0-10 range)
        """
        # Normalize TF-IDF score
        # Typical TF-IDF scores range from ~1 to ~20
        normalized = min(10, tf_idf_score / 2)
        return normalized

    def score_pair(
        self,
        concept_a: str,
        concept_b: str,
        sources_a: list[str],
        sources_b: list[str],
        score_a: float = 0.0,
        score_b: float = 0.0,
        reference_date: Optional[datetime] = None,
    ) -> dict:
        """Calculate complete insight score for a concept pair.

        Args:
            concept_a: First concept text
            concept_b: Second concept text
            sources_a: Source files for concept A
            sources_b: Source files for concept B
            score_a: TF-IDF score for concept A
            score_b: TF-IDF score for concept B
            reference_date: Date for recency calculation

        Returns:
            Dictionary with score breakdown and total
        """
        # Base score
        base = 10

        # Rarity scores
        rarity_a = self.calculate_rarity_score(concept_a)
        rarity_b = self.calculate_rarity_score(concept_b)
        rarity_total = (rarity_a + rarity_b) / 2

        # Distance score
        distance = self.calculate_distance_score(sources_a, sources_b)

        # Recency scores
        recency_a = self.calculate_recency_score(sources_a, reference_date)
        recency_b = self.calculate_recency_score(sources_b, reference_date)
        recency_total = (recency_a + recency_b) / 2

        # TF-IDF contribution
        tf_idf_contrib = (
            self.calculate_tf_idf_contribution(score_a)
            + self.calculate_tf_idf_contribution(score_b)
        ) / 2

        # Calculate total
        total = base + rarity_total + distance + recency_total + tf_idf_contrib

        # Clamp to valid range
        total = max(self.min_score, min(self.max_score, int(total)))

        return {
            "total": total,
            "breakdown": {
                "base": base,
                "rarity": round(rarity_total, 1),
                "distance": round(distance, 1),
                "recency": round(recency_total, 1),
                "tf_idf": round(tf_idf_contrib, 1),
            },
            "components": {
                "rarity_a": round(rarity_a, 1),
                "rarity_b": round(rarity_b, 1),
                "recency_a": round(recency_a, 1),
                "recency_b": round(recency_b, 1),
            },
        }

    def score_concept_pair(self, pair, reference_date: Optional[datetime] = None) -> dict:
        """Score a ConceptPair object.

        Args:
            pair: ConceptPair object
            reference_date: Date for recency calculation

        Returns:
            Score dictionary
        """
        return self.score_pair(
            concept_a=pair.concept_a,
            concept_b=pair.concept_b,
            sources_a=pair.sources_a,
            sources_b=pair.sources_b,
            score_a=pair.score_a,
            score_b=pair.score_b,
            reference_date=reference_date,
        )


def build_concept_frequencies(concepts: list[dict]) -> dict[str, int]:
    """Build frequency map from concept list.

    Args:
        concepts: List of concept dicts with 'sources' key

    Returns:
        Dict mapping concept text to occurrence count
    """
    frequencies = {}
    for concept in concepts:
        text = concept.get("text", "")
        # Frequency = number of source files
        sources = concept.get("sources", [])
        frequencies[text] = len(sources)
    return frequencies


def score_pairs(
    pairs: list,
    concepts: list[dict],
    reference_date: Optional[datetime] = None,
    verbose: bool = False,
) -> list[tuple[object, dict]]:
    """Convenience function to score multiple pairs.

    Args:
        pairs: List of ConceptPair objects
        concepts: List of concept dicts (for frequency calculation)
        reference_date: Date for recency calculation
        verbose: Print progress messages

    Returns:
        List of (pair, score_dict) tuples
    """
    frequencies = build_concept_frequencies(concepts)
    scorer = InsightScorer(concept_frequencies=frequencies)

    results = []
    for pair in pairs:
        score = scorer.score_concept_pair(pair, reference_date)
        results.append((pair, score))

    # Sort by total score (descending)
    results.sort(key=lambda x: x[1]["total"], reverse=True)

    if verbose:
        if results:
            avg_score = sum(s["total"] for _, s in results) / len(results)
            print(f"Scored {len(results)} pairs (avg: {avg_score:.1f})")
            print(f"  Highest: {results[0][1]['total']} points")

    return results
