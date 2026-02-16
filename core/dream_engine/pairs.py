"""Random pairing algorithm for dream generation.

Generates random concept pairs ensuring cross-source pollination
and avoiding duplicate pairs.
"""

import random
from datetime import datetime
from typing import Optional


class ConceptPair:
    """Represents a pair of concepts with their sources."""

    def __init__(
        self,
        concept_a: str,
        concept_b: str,
        sources_a: list[str],
        sources_b: list[str],
        score_a: float = 0.0,
        score_b: float = 0.0,
    ):
        """Initialize a concept pair.

        Args:
            concept_a: First concept text
            concept_b: Second concept text
            sources_a: Source files for concept_a
            sources_b: Source files for concept_b
            score_a: TF-IDF score for concept_a
            score_b: TF-IDF score for concept_b
        """
        self.concept_a = concept_a
        self.concept_b = concept_b
        self.sources_a = sources_a
        self.sources_b = sources_b
        self.score_a = score_a
        self.score_b = score_b
        self.shared_sources = set(sources_a) & set(sources_b)
        self.is_cross_source = len(self.shared_sources) == 0

    def to_dict(self) -> dict:
        """Convert pair to dictionary representation."""
        return {
            "concepts": [self.concept_a, self.concept_b],
            "sources_a": self.sources_a,
            "sources_b": self.sources_b,
            "score_a": self.score_a,
            "score_b": self.score_b,
            "is_cross_source": self.is_cross_source,
        }

    def __repr__(self) -> str:
        return f"ConceptPair('{self.concept_a}' + '{self.concept_b}')"

    def __eq__(self, other) -> bool:
        """Two pairs are equal if they contain the same concepts (order doesn't matter)."""
        if not isinstance(other, ConceptPair):
            return False
        return (self.concept_a == other.concept_a and self.concept_b == other.concept_b) or (
            self.concept_a == other.concept_b and self.concept_b == other.concept_a
        )

    def __hash__(self) -> int:
        """Hash based on sorted concepts for consistent equality checks."""
        return hash(tuple(sorted([self.concept_a, self.concept_b])))


class PairGenerator:
    """Generates random concept pairs with constraints."""

    def __init__(
        self,
        concepts: list[dict],
        pairs_to_generate: int = 8,
        require_cross_source: bool = True,
        max_attempts: int = 1000,
        seed: Optional[int] = None,
    ):
        """Initialize the pair generator.

        Args:
            concepts: List of concept dicts with 'text', 'score', 'sources' keys
            pairs_to_generate: Number of pairs to generate
            require_cross_source: Only generate cross-source pairs
            max_attempts: Maximum attempts before giving up
            seed: Random seed for reproducibility
        """
        self.concepts = concepts
        self.pairs_to_generate = pairs_to_generate
        self.require_cross_source = require_cross_source
        self.max_attempts = max_attempts
        self.seed = seed

        self.pairs: list[ConceptPair] = []
        self.generated_pairs: set = set()  # Track generated pairs to avoid duplicates

    def generate(self) -> list[ConceptPair]:
        """Generate concept pairs.

        Returns:
            List of ConceptPair objects
        """
        if len(self.concepts) < 2:
            return []

        # Set random seed at generate time for reproducibility
        if self.seed is not None:
            random.seed(self.seed)

        self.pairs = []
        self.generated_pairs = set()
        attempts = 0

        # Shuffle concepts for randomness (use a copy to avoid modifying original)
        shuffled = list(self.concepts)
        random.shuffle(shuffled)

        while len(self.pairs) < self.pairs_to_generate and attempts < self.max_attempts:
            attempts += 1

            # Select two different concepts using indices
            if len(shuffled) < 2:
                break

            idx_a = random.randrange(len(shuffled))
            idx_b = random.randrange(len(shuffled))

            # Skip if same index
            if idx_a == idx_b:
                continue

            concept_a = shuffled[idx_a]
            concept_b = shuffled[idx_b]

            # Check cross-source requirement
            sources_a = concept_a.get("sources", [])
            sources_b = concept_b.get("sources", [])
            shared = set(sources_a) & set(sources_b)

            if self.require_cross_source and shared:
                continue

            # Create pair
            pair = ConceptPair(
                concept_a=concept_a["text"],
                concept_b=concept_b["text"],
                sources_a=sources_a,
                sources_b=sources_b,
                score_a=concept_a.get("score", 0.0),
                score_b=concept_b.get("score", 0.0),
            )

            # Check for duplicates
            if pair in self.generated_pairs:
                continue

            # Add to results
            self.generated_pairs.add(pair)
            self.pairs.append(pair)

        return self.pairs

    def get_cross_source_pairs(self) -> list[ConceptPair]:
        """Get only cross-source pairs."""
        return [p for p in self.pairs if p.is_cross_source]

    def get_stats(self) -> dict:
        """Get statistics about generated pairs."""
        if not self.pairs:
            return {
                "total_pairs": 0,
                "cross_source_pairs": 0,
                "same_source_pairs": 0,
                "target_pairs": self.pairs_to_generate,
            }

        cross_source = sum(1 for p in self.pairs if p.is_cross_source)

        return {
            "total_pairs": len(self.pairs),
            "cross_source_pairs": cross_source,
            "same_source_pairs": len(self.pairs) - cross_source,
            "target_pairs": self.pairs_to_generate,
            "completion_rate": len(self.pairs) / self.pairs_to_generate,
        }


def generate_pairs(
    concepts: list[dict],
    pairs_to_generate: int = 8,
    require_cross_source: bool = True,
    reference_date: Optional[datetime] = None,
    verbose: bool = False,
) -> list[ConceptPair]:
    """Convenience function to generate concept pairs.

    Args:
        concepts: List of concept dicts
        pairs_to_generate: Number of pairs to generate
        require_cross_source: Only generate cross-source pairs
        reference_date: Date for random seed (default: today)
        verbose: Print progress messages

    Returns:
        List of ConceptPair objects
    """
    # Use date-based seed for reproducibility
    if reference_date is None:
        reference_date = datetime.now()

    seed = int(reference_date.strftime("%Y%m%d"))

    generator = PairGenerator(
        concepts=concepts,
        pairs_to_generate=pairs_to_generate,
        require_cross_source=require_cross_source,
        seed=seed,
    )

    pairs = generator.generate()

    if verbose:
        stats = generator.get_stats()
        print(f"Generated {stats['total_pairs']}/{stats['target_pairs']} pairs")
        print(f"  Cross-source: {stats['cross_source_pairs']}")
        if pairs:
            print(f"  Example: '{pairs[0].concept_a}' + '{pairs[0].concept_b}'")

    return pairs


def create_date_seed(date: Optional[datetime] = None) -> int:
    """Create a reproducible random seed from a date.

    Args:
        date: Date to use (default: today)

    Returns:
        Integer seed value
    """
    if date is None:
        date = datetime.now()
    return int(date.strftime("%Y%m%d"))
