"""Concept extraction from memory files using TF-IDF-like scoring.

Extracts significant phrases (2+ word combinations) from recent memory files,
using term frequency vs document frequency for scoring. Filters stopwords
and returns high-quality concepts with source references.
"""

import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from glob import glob
from pathlib import Path
from typing import Optional


# Hardcoded stopwords (no external dependencies)
STOPWORDS = {
    # Common English stopwords
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
    "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
    "been", "being", "have", "has", "had", "do", "does", "did", "will",
    "would", "could", "should", "may", "might", "must", "can", "shall",
    "this", "that", "these", "those", "i", "you", "he", "she", "it",
    "we", "they", "them", "their", "there", "then", "than", "when",
    "where", "what", "who", "which", "why", "how", "all", "some", "any",
    "no", "not", "only", "just", "now", "here", "so", "if", "about",
    "up", "out", "many", "much", "more", "most", "other", "some", "time",
    "way", "even", "new", "like", "also", "back", "after", "use", "two",
    "how", "its", "our", "over", "such", "take", "than", "them", "well",
    "were", "work", "years", "your", "very", "still", "own", "under",
    "right", "old", "see", "him", "her", "between", "both", "life",
    "even", "here", "off", "too", "same", "used", "being", "make",
    "good", "come", "day", "get", "use", "man", "new", "now", "way",
    "may", "say", "great", "where", "through", "when", "come", "came",
    "each", "which", "their", "time", "will", "about", "if", "up",
    "out", "many", "then", "them", "these", "so", "some", "her",
    "would", "make", "like", "into", "him", "has", "two", "more",
    "go", "no", "way", "could", "my", "than", "first", "been",
    "call", "who", "oil", "sit", "now", "find", "long", "down",
    "day", "did", "get", "she", "may", "use", "her", "than",
    "each", "which", "how", "been", "were", "they", "its", "said",
    "have", "has", "had", "did", "does", "doing", "done", "being",
    # Markdown/formatting artifacts
    "http", "https", "www", "com", "org", "net", "io", "co", "uk",
    # Common verbs without meaning
    "said", "says", "get", "got", "goes", "went", "come", "came",
    "made", "make", "making", "take", "took", "taken", "see", "saw",
    "seen", "know", "knew", "known", "think", "thought", "thoughts",
    "look", "looked", "looking", "want", "wanted", "give", "gave",
    "given", "find", "found", "tell", "told", "become", "became",
    "leave", "left", "feel", "felt", "put", "bring", "brought",
    "begin", "began", "begun", "keep", "kept", "hold", "held",
    "write", "wrote", "written", "stand", "stood", "hear", "heard",
    "let", "mean", "meant", "meet", "met", "pay", "paid", "run",
    "ran", "read", "say", "seem", "seemed", "ask", "asked", "try",
    "tried", "need", "needed", "show", "showed", "play", "played",
    "move", "moved", "live", "lived", "believe", "believed", "bring",
    "happened", "happening", "happens", "help", "helped", "talk",
    "talked", "turn", "turned", "started", "starts", "start",
    # Memory-specific artifacts
    "session", "summary", "details", "timestamp", "drive", "pressure",
    "trigger", "file", "files", "memory", "content", "section",
}


def normalize_word(word: str) -> Optional[str]:
    """Normalize a word for concept extraction.
    
    Removes punctuation, lowercases, and filters out stopwords
    and non-alphabetic words.
    
    Args:
        word: Raw word from text
        
    Returns:
        Normalized word or None if it should be filtered
    """
    # Remove punctuation and lowercase
    cleaned = re.sub(r'^[^\w]+|[^\w]+$', '', word).lower()
    
    # Filter conditions
    if len(cleaned) < 3:  # Too short
        return None
    if cleaned in STOPWORDS:  # Common word
        return None
    if not cleaned.isalpha():  # Contains numbers/symbols
        return None
    if cleaned.endswith('ing') and len(cleaned) < 6:  # Gerunds that are too short
        return None
    
    return cleaned


def extract_phrases(text: str, min_words: int = 2, max_words: int = 4) -> list[str]:
    """Extract candidate phrases from text.
    
    Looks for sequences of meaningful words that could be concepts.
    
    Args:
        text: Source text to extract from
        min_words: Minimum words in a phrase
        max_words: Maximum words in a phrase
        
    Returns:
        List of extracted phrases
    """
    # Split into words and normalize
    raw_words = re.findall(r'\b[\w-]+\b', text)
    normalized = []
    
    for word in raw_words:
        norm = normalize_word(word)
        if norm:
            normalized.append(norm)
        else:
            normalized.append(None)  # Preserve position for gap detection
    
    phrases = []
    
    # Extract n-grams
    for n in range(min_words, max_words + 1):
        for i in range(len(normalized) - n + 1):
            window = normalized[i:i + n]
            
            # Check all words in window are valid (no gaps)
            if all(w is not None for w in window):
                phrase = ' '.join(window)
                phrases.append(phrase)
    
    return phrases


def get_recent_memory_files(
    memory_dir: Path,
    lookback_days: int = 7,
    reference_date: Optional[datetime] = None
) -> list[Path]:
    """Get memory files from the last N days.
    
    Args:
        memory_dir: Directory containing memory files
        lookback_days: Number of days to look back
        reference_date: Date to calculate from (default: now)
        
    Returns:
        List of Path objects for memory files
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc)
    
    files = []
    
    for day_offset in range(lookback_days):
        date = reference_date - timedelta(days=day_offset)
        date_str = date.strftime('%Y-%m-%d')
        
        # Look for files matching YYYY-MM-DD*.md pattern
        pattern = memory_dir / f"{date_str}*.md"
        files.extend(Path(f) for f in glob(str(pattern)))
    
    # Sort by modification time (newest first)
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    
    return files


def calculate_tf_idf(
    file_phrases: dict[str, list[str]],
    max_concepts: int = 50
) -> list[tuple[str, float, list[str]]]:
    """Calculate TF-IDF-like scores for phrases across files.
    
    TF = term frequency in a document
    IDF = log(total_docs / docs_containing_term)
    Score = sum(TF * IDF) across all files
    
    Args:
        file_phrases: Dict mapping filepath to list of phrases from that file
        max_concepts: Maximum number of concepts to return
        
    Returns:
        List of (phrase, score, sources) tuples, sorted by score
    """
    total_docs = len(file_phrases)
    if total_docs == 0:
        return []
    
    # Calculate document frequency for each phrase
    doc_freq = Counter()
    phrase_counts = {}  # phrase -> {filepath: count}
    
    for filepath, phrases in file_phrases.items():
        # Count phrases in this document
        doc_counter = Counter(phrases)
        
        for phrase, count in doc_counter.items():
            doc_freq[phrase] += 1
            if phrase not in phrase_counts:
                phrase_counts[phrase] = {}
            phrase_counts[phrase][filepath] = count
    
    # Calculate TF-IDF scores
    scored_phrases = []
    
    for phrase, doc_count in doc_freq.items():
        # IDF: log(total_docs / docs_containing_phrase)
        idf = total_docs / doc_count
        
        # Sum TF * IDF across all documents
        total_score = 0
        for filepath, tf in phrase_counts[phrase].items():
            total_score += tf * idf
        
        # Get source files (up to 3 most frequent)
        sources = sorted(
            phrase_counts[phrase].items(),
            key=lambda x: x[1],
            reverse=True
        )[:3]
        source_files = [Path(p).name for p, _ in sources]
        
        scored_phrases.append((phrase, total_score, source_files))
    
    # Sort by score and return top N
    scored_phrases.sort(key=lambda x: x[1], reverse=True)
    return scored_phrases[:max_concepts]


class ConceptExtractor:
    """Extract and manage concepts from memory files."""
    
    def __init__(
        self,
        memory_dir: Path,
        lookback_days: int = 7,
        max_concepts: int = 50,
        reference_date: Optional[datetime] = None
    ):
        """Initialize the concept extractor.
        
        Args:
            memory_dir: Directory containing memory files
            lookback_days: Number of days to look back
            max_concepts: Maximum concepts to extract
            reference_date: Date to calculate from (default: now)
        """
        self.memory_dir = memory_dir
        self.lookback_days = lookback_days
        self.max_concepts = max_concepts
        self.reference_date = reference_date or datetime.now(timezone.utc)
        
        self.concepts: list[dict] = []
        self.source_files: list[Path] = []
    
    def extract(self) -> list[dict]:
        """Extract concepts from recent memory files.
        
        Returns:
            List of concept dicts with 'text', 'score', 'sources' keys
        """
        # Get recent memory files
        files = get_recent_memory_files(
            self.memory_dir,
            self.lookback_days,
            self.reference_date
        )
        
        if not files:
            return []
        
        self.source_files = files
        
        # Extract phrases from each file
        file_phrases = {}
        
        for filepath in files:
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Skip YAML frontmatter if present
                if content.startswith('---'):
                    parts = content.split('---', 2)
                    if len(parts) >= 3:
                        content = parts[2]
                
                phrases = extract_phrases(content)
                if phrases:
                    file_phrases[str(filepath)] = phrases
                    
            except (IOError, UnicodeDecodeError):
                # Skip files that can't be read
                continue
        
        if not file_phrases:
            return []
        
        # Calculate TF-IDF scores
        scored = calculate_tf_idf(file_phrases, self.max_concepts)
        
        # Build concept objects
        self.concepts = [
            {
                'text': phrase,
                'score': round(score, 2),
                'sources': sources,
            }
            for phrase, score, sources in scored
        ]
        
        return self.concepts
    
    def get_concept_by_text(self, text: str) -> Optional[dict]:
        """Get a concept by its text.
        
        Args:
            text: Concept text to look up
            
        Returns:
            Concept dict or None if not found
        """
        for concept in self.concepts:
            if concept['text'] == text:
                return concept
        return None
    
    def get_source_file_paths(self) -> list[str]:
        """Get list of source file paths as strings."""
        return [str(f) for f in self.source_files]


def extract_concepts(
    memory_dir: Path,
    lookback_days: int = 7,
    max_concepts: int = 50,
    reference_date: Optional[datetime] = None,
    verbose: bool = False
) -> tuple[list[dict], list[Path]]:
    """Convenience function to extract concepts from memory files.
    
    Args:
        memory_dir: Directory containing memory files
        lookback_days: Number of days to look back
        max_concepts: Maximum concepts to extract
        reference_date: Date to calculate from (default: now)
        verbose: Print progress messages
        
    Returns:
        Tuple of (concepts list, source files list)
    """
    extractor = ConceptExtractor(
        memory_dir=memory_dir,
        lookback_days=lookback_days,
        max_concepts=max_concepts,
        reference_date=reference_date
    )
    
    concepts = extractor.extract()
    
    if verbose:
        print(f"Found {len(extractor.source_files)} memory files")
        print(f"Extracted {len(concepts)} concepts")
        if concepts:
            print(f"Top concept: '{concepts[0]['text']}' (score: {concepts[0]['score']})")
    
    return concepts, extractor.source_files
