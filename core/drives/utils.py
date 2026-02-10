from typing import Optional
"""Utility functions for the drive engine.

Provides fuzzy name matching and other helper utilities.
"""


def fuzzy_match(name: str, candidates: list[str]) -> Optional[str]:
    """Fuzzy match a drive name against available candidates.
    
    Matching strategy (in order of preference):
    1. Exact match (case-insensitive)
    2. Prefix match (case-insensitive) — returns only if unique
    3. Substring match (case-insensitive) — returns only if unique
    
    Args:
        name: The name to match
        candidates: List of available drive names
        
    Returns:
        The matched drive name, or None if no match or ambiguous
        
    Examples:
        >>> fuzzy_match("curiosity", ["CURIOSITY", "CARE", "CREATIVE"])
        'CURIOSITY'
        >>> fuzzy_match("curio", ["CURIOSITY", "CARE"])
        'CURIOSITY'
        >>> fuzzy_match("c", ["CURIOSITY", "CARE"])  # Ambiguous
        None
        >>> fuzzy_match("xyz", ["CURIOSITY", "CARE"])
        None
    """
    if not name or not candidates:
        return None
    
    # Normalize: uppercase, replace hyphens/underscores with spaces
    def normalize(s: str) -> str:
        return s.upper().replace("-", " ").replace("_", " ")
    
    normalized_name = normalize(name)
    normalized_candidates = {normalize(c): c for c in candidates}
    
    # 1. Exact match on normalized form
    if normalized_name in normalized_candidates:
        return normalized_candidates[normalized_name]
    
    # 2. Prefix match - find candidates that start with the name
    prefix_matches = [
        original for norm, original in normalized_candidates.items()
        if norm.startswith(normalized_name)
    ]
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    
    # 3. Substring match - find candidates containing the name
    substring_matches = [
        original for norm, original in normalized_candidates.items()
        if normalized_name in norm
    ]
    if len(substring_matches) == 1:
        return substring_matches[0]
    
    # Ambiguous or no match
    return None


def get_ambiguous_matches(name: str, candidates: list[str]) -> list[str]:
    """Get all candidates that would match a fuzzy search.
    
    Useful for error messages when fuzzy_match returns None.
    
    Args:
        name: The name to match
        candidates: List of available drive names
        
    Returns:
        List of all matching candidates (may be empty or have multiple items)
    """
    if not name or not candidates:
        return []
    
    def normalize(s: str) -> str:
        return s.upper().replace("-", " ").replace("_", " ")
    
    normalized_name = normalize(name)
    normalized_candidates = {normalize(c): c for c in candidates}
    
    matches = set()
    
    # Exact matches
    if normalized_name in normalized_candidates:
        matches.add(normalized_candidates[normalized_name])
    
    # Prefix matches
    for norm, original in normalized_candidates.items():
        if norm.startswith(normalized_name):
            matches.add(original)
    
    # Substring matches
    for norm, original in normalized_candidates.items():
        if normalized_name in norm:
            matches.add(original)
    
    # Return in original order
    return [c for c in candidates if c in matches]


def format_pressure_bar(pressure: float, threshold: float, width: int = 20) -> str:
    """Render a visual pressure bar showing drive state.
    
    Args:
        pressure: Current pressure level
        threshold: Threshold level (defines 100%)
        width: Width of the bar in characters (default 20)
        
    Returns:
        ASCII/Unicode pressure bar string
        
    Examples:
        >>> format_pressure_bar(10.0, 20.0, 10)
        '[█████░░░░░] 50%'
        >>> format_pressure_bar(25.0, 20.0, 10)
        '[██████████] 125%'
    """
    if threshold <= 0:
        ratio = 0.0
    else:
        ratio = pressure / threshold
    
    pct = int(ratio * 100)
    
    # For visualization, cap at 150% (threshold * 1.5)
    display_ratio = min(ratio, 1.5)
    filled = int(display_ratio * width)
    empty = width - filled
    
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {pct}%"


def normalize_drive_name(name: str) -> str:
    """Normalize a drive name for comparison.
    
    Args:
        name: Raw drive name
        
    Returns:
        Uppercase name with hyphens/underscores replaced by spaces
        
    Examples:
        >>> normalize_drive_name("my-drive_name")
        'MY DRIVE NAME'
        >>> normalize_drive_name("CURIOSITY")
        'CURIOSITY'
    """
    return name.upper().replace("-", " ").replace("_", " ")
