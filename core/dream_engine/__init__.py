"""Dream Engine — Creative memory recombination system.

The Dream Engine extracts concepts from recent memory files, randomly pairs
them from different sources, generates surreal "dream fragments," and scores
them for insight. It runs nightly via cron and outputs to
memory/dreams/YYYY-MM-DD.json.

Modules:
    config: Configuration loading from emergence.json
    concepts: TF-IDF-like concept extraction from memory files
    pairs: Random pairing algorithm with cross-source constraint
    fragments: Dream fragment generation from creative templates
    scoring: Insight scoring based on rarity, distance, and recency
    dream: Main entry point and CLI interface

Usage:
    python3 -m core.dream_engine.dream run
    python3 -m core.dream_engine.dream status
"""

__version__ = "1.0.0"

from .config import load_config, get_dream_dir, get_memory_dir, get_dream_engine_config
from .concepts import extract_concepts, ConceptExtractor
from .pairs import generate_pairs, ConceptPair, PairGenerator
from .fragments import generate_fragment, generate_fragments, DREAM_TEMPLATES
from .scoring import score_pairs, InsightScorer

__all__ = [
    # Version
    "__version__",
    # Config
    "load_config",
    "get_dream_dir",
    "get_memory_dir",
    "get_dream_engine_config",
    # Concepts
    "extract_concepts",
    "ConceptExtractor",
    # Pairs
    "generate_pairs",
    "ConceptPair",
    "PairGenerator",
    # Fragments
    "generate_fragment",
    "generate_fragments",
    "DREAM_TEMPLATES",
    # Scoring
    "score_pairs",
    "InsightScorer",
]
