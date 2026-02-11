"""Dream fragment generation — Ollama primary, templates fallback.

Generates surreal, evocative dream fragments by combining concept pairs.
Primary: sends pairs to local Ollama for genuinely creative recombination.
Fallback: template-based generation when Ollama is unavailable.

Templates are kept as the zero-dependency fallback and are designed to be
poetic and thought-provoking for display in The Room.
"""

import json
import random
import urllib.request
import urllib.error
from datetime import datetime
from typing import Optional

OLLAMA_DEFAULT_URL = "http://localhost:11434/api/generate"
OLLAMA_DEFAULT_MODEL = "mistral"  # Good creative writing, runs on most hardware


# Creative and varied dream fragment templates
# Each template uses {a} and {b} placeholders for the two concepts
DREAM_TEMPLATES = [
    # Nature and growth metaphors
    "A {a} tends a garden where {b} bloom in unexpected colors.",
    "In the soil beneath {a}, seeds of {b} wait for rain.",
    "A forest of {a} whispers secrets to the {b} at dawn.",
    "Roots of {a} intertwine with branches of {b} beneath the surface.",
    "Morning light reveals {a} growing wild among the {b}.",
    
    # Memory and consciousness
    "What if {a} could remember {b}?",
    "The {a} that learned to {b}.",
    "In dreams, {a} speaks the language of {b}.",
    "A memory of {a} folded inside {b}.",
    "The last {a} holds the first {b}.",
    
    # Space and connection
    "In the space between {a} and {b}, something new is forming.",
    "Where {a} ends, {b} begins — but no one can find the border.",
    "A bridge of {a} spans the distance to {b}.",
    "The silence between {a} and {b} is its own kind of music.",
    "At the intersection of {a} and {b}, a door stands open.",
    
    # Transformation and becoming
    "When {a} dreams, it becomes {b}.",
    "The transformation of {a} into {b} is almost complete.",
    "{a} wears the mask of {b} until even it forgets which is real.",
    "Yesterday's {a} is tomorrow's {b}.",
    "In the melting pot: {a} dissolves into {b}.",
    
    # Questions and wonder
    "Who teaches {a} to understand {b}?",
    "Can {a} exist without {b} watching?",
    "Why does {a} reach toward {b}?",
    "What do {a} and {b} discuss when no one is listening?",
    "The question {a} asks {b} has no answer.",
    
    # Surreal imagery
    "A cathedral built of {a} echoes with the songs of {b}.",
    "{a} drifts through empty rooms, searching for {b}.",
    "The constellation {a} points the way to {b}.",
    "In the mirror, {a} sees only {b}.",
    "A recipe calling for {a} and {b} in equal measure.",
    
    # Time and cycles
    "The clock strikes {a} o'clock, and {b} awakens.",
    "Seasons turn: {a} in autumn, {b} in spring.",
    "The oldest {a} remembers when {b} was young.",
    "Time moves differently for {a} than for {b}.",
    "In the loop where {a} becomes {b} becomes {a}...",
    
    # Reflection and depth
    "Beneath the surface of {a} lies a deep pool of {b}.",
    "The shadow of {a} stretches toward {b} at noon.",
    "{a} reflected in {b} shows something unexpected.",
    "Looking closely at {a}, you find {b} looking back.",
    "The hollow of {a} contains a whisper of {b}.",
]


def get_template_key(template: str) -> str:
    """Generate a short key identifier for a template.
    
    Args:
        template: The template string
        
    Returns:
        Short identifier like 'tends_garden' or 'memory_folded'
    """
    # Extract key words from the template
    words = template.replace('{a}', '').replace('{b}', '').lower()
    words = ''.join(c if c.isalnum() or c.isspace() else ' ' for c in words)
    words = words.split()
    
    # Pick 2-3 significant words
    significant = [w for w in words if len(w) > 3 and w not in 
                   {'what', 'when', 'where', 'which', 'something', 'becomes',
                    'through', 'toward', 'between', 'beneath', 'intersection'}]
    
    if len(significant) >= 2:
        return '_'.join(significant[:2])
    elif len(significant) == 1:
        return significant[0]
    else:
        # Fallback to template index
        return f"template_{hash(template) % 1000}"


class FragmentGenerator:
    """Generates dream fragments from concept pairs."""
    
    def __init__(
        self,
        templates: Optional[list[str]] = None,
        seed: Optional[int] = None
    ):
        """Initialize the fragment generator.
        
        Args:
            templates: List of template strings (default: built-in templates)
            seed: Random seed for reproducibility
        """
        self.templates = templates or DREAM_TEMPLATES.copy()
        self.seed = seed
        self.used_templates: set[str] = set()
        self.fragments: list[dict] = []
    
    def generate(self, concept_a: str, concept_b: str) -> dict:
        """Generate a dream fragment for a concept pair.
        
        Args:
            concept_a: First concept
            concept_b: Second concept
            
        Returns:
            Dictionary with 'fragment', 'template', 'concepts' keys
        """
        # Set seed if provided (for reproducibility)
        if self.seed is not None:
            random.seed(self.seed)
        
        # Select a random template
        # Prefer unused templates if possible
        available = [t for t in self.templates if t not in self.used_templates]
        if not available:
            available = self.templates
        
        template = random.choice(available)
        self.used_templates.add(template)
        
        # Increment seed for next call to ensure variety
        if self.seed is not None:
            self.seed += 1
        
        # Fill in the template
        fragment = template.format(a=concept_a, b=concept_b)
        
        # Clean up any double spaces
        fragment = ' '.join(fragment.split())
        
        return {
            'fragment': fragment,
            'template': get_template_key(template),
            'concepts': [concept_a, concept_b],
            'raw_template': template,
        }
    
    def generate_batch(self, concept_pairs: list) -> list[dict]:
        """Generate fragments for multiple concept pairs.
        
        Args:
            concept_pairs: List of ConceptPair objects or (a, b) tuples
            
        Returns:
            List of fragment dictionaries
        """
        self.fragments = []
        
        for pair in concept_pairs:
            if hasattr(pair, 'concept_a') and hasattr(pair, 'concept_b'):
                # It's a ConceptPair object
                fragment = self.generate(pair.concept_a, pair.concept_b)
            elif isinstance(pair, (list, tuple)) and len(pair) >= 2:
                # It's a tuple/list
                fragment = self.generate(pair[0], pair[1])
            else:
                # Skip invalid pairs
                continue
            
            self.fragments.append(fragment)
        
        return self.fragments


def generate_fragment(
    concept_a: str,
    concept_b: str,
    seed: Optional[int] = None,
    template: Optional[str] = None
) -> dict:
    """Convenience function to generate a single dream fragment.
    
    Args:
        concept_a: First concept
        concept_b: Second concept
        seed: Random seed for reproducibility
        template: Specific template to use (random if None)
        
    Returns:
        Fragment dictionary
    """
    if seed is not None:
        random.seed(seed)
    
    if template is None:
        template = random.choice(DREAM_TEMPLATES)
    
    fragment = template.format(a=concept_a, b=concept_b)
    fragment = ' '.join(fragment.split())
    
    return {
        'fragment': fragment,
        'template': get_template_key(template),
        'concepts': [concept_a, concept_b],
        'raw_template': template,
    }


def generate_with_ollama(
    concept_pairs: list,
    config: Optional[dict] = None,
    verbose: bool = False
) -> Optional[list[dict]]:
    """Generate dream fragments using local Ollama model.
    
    Sends concept pairs to Ollama with a creative prompt for genuinely
    novel dream recombination. This is the PRIMARY method — free, private,
    and produces far more creative output than templates.
    
    Args:
        concept_pairs: List of ConceptPair objects
        config: Optional config with ollama_url and ollama_model
        verbose: Print progress
        
    Returns:
        List of fragment dicts, or None if Ollama unavailable
    """
    de_config = (config or {}).get('dream_engine', {})
    ollama_url = de_config.get('ollama_url', OLLAMA_DEFAULT_URL)
    model = de_config.get('ollama_model', OLLAMA_DEFAULT_MODEL)
    
    # Build the pairs description
    pairs_text = "\n".join(
        f"  {i+1}. \"{p.concept_a}\" + \"{p.concept_b}\""
        for i, p in enumerate(concept_pairs)
    )
    
    prompt = f"""You are a dream engine — you generate surreal, poetic dream fragments from concept pairs.

For each pair below, write ONE dream fragment: a single evocative sentence that connects the two concepts in an unexpected, dreamlike way. Be surreal but coherent. Be poetic, not technical. Each fragment should feel like a moment from a dream.

Concept pairs:
{pairs_text}

Respond with ONLY a JSON array of strings, one fragment per pair. Example:
["A neural network tends a garden where thoughts bloom...", "The silence between code and poetry hums with color."]

Respond with the JSON array only, no other text."""

    req_data = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }).encode('utf-8')
    
    req = urllib.request.Request(
        ollama_url,
        data=req_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    # Retry up to 3 times — Ollama may be mid-restart
    import time as _time
    last_err = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=180) as response:
                result = json.loads(response.read().decode('utf-8'))
                reply = result.get('response', '').strip()
            break  # Success
        except (urllib.error.URLError, urllib.error.HTTPError, ConnectionError) as e:
            last_err = e
            if verbose:
                print(f"  ⚠ Ollama attempt {attempt + 1}/3 failed: {e}")
            if attempt < 2:
                _time.sleep(10)  # Wait 10s before retry
    else:
        if verbose:
            print(f"  ✗ Ollama unavailable after 3 attempts: {last_err}")
        return None

    try:
        # Parse the response — expect a JSON array of strings
        # Try direct parse first
        try:
            parsed = json.loads(reply)
        except json.JSONDecodeError:
            # Try to extract JSON array from response
            start = reply.find('[')
            end = reply.rfind(']')
            if start >= 0 and end > start:
                parsed = json.loads(reply[start:end + 1])
            else:
                if verbose:
                    print(f"  ⚠ Could not parse Ollama response as JSON array")
                return None
        
        # Handle both list format and dict format
        if isinstance(parsed, dict):
            # Some models wrap in {"fragments": [...]} or similar
            for key in ('fragments', 'dreams', 'results', 'items'):
                if key in parsed and isinstance(parsed[key], list):
                    parsed = parsed[key]
                    break
            else:
                if verbose:
                    print(f"  ⚠ Ollama response is dict but no array found")
                return None
        
        if not isinstance(parsed, list):
            if verbose:
                print(f"  ⚠ Ollama response is not a list")
            return None
        
        # Build fragment dicts
        fragments = []
        for i, (fragment_text, pair) in enumerate(zip(parsed, concept_pairs)):
            if not isinstance(fragment_text, str):
                fragment_text = str(fragment_text)
            
            # Clean up
            fragment_text = fragment_text.strip().strip('"').strip()
            if not fragment_text:
                continue
            
            fragments.append({
                'fragment': fragment_text,
                'template': 'ollama',
                'concepts': [pair.concept_a, pair.concept_b],
                'source': 'ollama',
            })
        
        if verbose:
            print(f"  ✓ Ollama generated {len(fragments)} dream fragments")
            if fragments:
                print(f"    Example: \"{fragments[0]['fragment'][:70]}...\"")
        
        return fragments if fragments else None
        
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        if verbose:
            print(f"  ⚠ Failed to parse Ollama response: {e}")
        return None


def generate_with_openrouter(
    concept_pairs: list,
    config: Optional[dict] = None,
    verbose: bool = False
) -> Optional[list[dict]]:
    """Generate dream fragments using OpenRouter API.
    
    Sends concept pairs to OpenRouter (supports multiple models including Mistral)
    for creative dream recombination. Uses API key from environment.
    
    Args:
        concept_pairs: List of ConceptPair objects
        config: Optional config with model selection
        verbose: Print progress
        
    Returns:
        List of fragment dicts, or None if API unavailable/failed
    """
    import os
    
    de_config = (config or {}).get('dream_engine', {})
    model = de_config.get('openrouter_model', 'mistralai/mistral-7b-instruct')
    api_key = os.environ.get('OPENROUTER_API_KEY')
    
    if not api_key:
        if verbose:
            print("  ⚠ OPENROUTER_API_KEY not set in environment")
        return None
    
    # Build the pairs description
    pairs_text = "\n".join(
        f"  {i+1}. \"{p.concept_a}\" + \"{p.concept_b}\""
        for i, p in enumerate(concept_pairs)
    )
    
    prompt = f"""You are a dream engine — you generate surreal, poetic dream fragments from concept pairs.

For each pair below, write ONE dream fragment: a single evocative sentence that connects the two concepts in an unexpected, dreamlike way. Be surreal but coherent. Be poetic, not technical. Each fragment should feel like a moment from a dream.

Concept pairs:
{pairs_text}

Respond with ONLY a JSON array of strings, one fragment per pair. Example:
["A neural network tends a garden where thoughts bloom...", "The silence between code and poetry hums with color."]

Respond with the JSON array only, no other text."""

    req_data = json.dumps({
        "model": model,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "response_format": {"type": "json_object"}
    }).encode('utf-8')
    
    req = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=req_data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/jarvis-raven/emergence",
            "X-Title": "Emergence Dream Engine"
        },
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode('utf-8'))
            
            # Extract content from OpenRouter response
            if 'choices' not in data or not data['choices']:
                if verbose:
                    print("  ⚠ OpenRouter response missing 'choices'")
                return None
            
            content = data['choices'][0].get('message', {}).get('content', '')
            if not content:
                if verbose:
                    print("  ⚠ OpenRouter response has empty content")
                return None
            
            # Parse the JSON array from content
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # Sometimes the response wraps it in markdown
                if '```json' in content:
                    content = content.split('```json')[1].split('```')[0].strip()
                    parsed = json.loads(content)
                elif '```' in content:
                    content = content.split('```')[1].split('```')[0].strip()
                    parsed = json.loads(content)
                else:
                    if verbose:
                        print(f"  ⚠ Could not parse OpenRouter content as JSON")
                    return None
            
            # Handle both list format and dict format
            if isinstance(parsed, dict):
                for key in ('fragments', 'dreams', 'results', 'items'):
                    if key in parsed and isinstance(parsed[key], list):
                        parsed = parsed[key]
                        break
                else:
                    if verbose:
                        print(f"  ⚠ OpenRouter response is dict but no array found")
                    return None
            
            if not isinstance(parsed, list):
                if verbose:
                    print(f"  ⚠ OpenRouter response is not a list")
                return None
            
            # Build fragment dicts
            fragments = []
            for i, (fragment_text, pair) in enumerate(zip(parsed, concept_pairs)):
                if not isinstance(fragment_text, str):
                    fragment_text = str(fragment_text)
                
                # Clean up
                fragment_text = fragment_text.strip().strip('"').strip()
                if not fragment_text:
                    continue
                
                fragments.append({
                    'fragment': fragment_text,
                    'template': 'openrouter',
                    'concepts': [pair.concept_a, pair.concept_b],
                    'source': 'openrouter',
                })
            
            if verbose:
                print(f"  ✓ OpenRouter generated {len(fragments)} dream fragments")
                if fragments:
                    print(f"    Example: \"{fragments[0]['fragment'][:70]}...\"")
            
            return fragments if fragments else None
    
    except urllib.error.URLError as e:
        if verbose:
            print(f"  ⚠ OpenRouter API request failed: {e}")
        return None
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        if verbose:
            print(f"  ⚠ Failed to parse OpenRouter response: {e}")
        return None


def generate_fragments(
    concept_pairs: list,
    reference_date: Optional[datetime] = None,
    config: Optional[dict] = None,
    verbose: bool = False
) -> list[dict]:
    """Generate dream fragments — Ollama primary, templates fallback.
    
    Args:
        concept_pairs: List of ConceptPair objects
        reference_date: Date for random seed (template fallback)
        config: Optional config for Ollama settings
        verbose: Print progress messages
        
    Returns:
        List of fragment dictionaries
    """
    if reference_date is None:
        reference_date = datetime.now()
    
    de_config = (config or {}).get('dream_engine', {})
    
    # Try OpenRouter first if configured (cloud-based, reliable, paid)
    use_openrouter = de_config.get('use_openrouter', False)
    if use_openrouter:
        if verbose:
            print("  Trying OpenRouter for creative dream generation...")
        fragments = generate_with_openrouter(concept_pairs, config, verbose)
        if fragments and len(fragments) >= len(concept_pairs) // 2:
            return fragments
        elif fragments:
            if verbose:
                print(f"  OpenRouter returned {len(fragments)}/{len(concept_pairs)} fragments, supplementing with templates...")
            # Got some but not all — supplement with templates
            remaining_pairs = concept_pairs[len(fragments):]
            seed = int(reference_date.strftime('%Y%m%d'))
            generator = FragmentGenerator(seed=seed)
            template_fragments = generator.generate_batch(remaining_pairs)
            return fragments + template_fragments
    
    # Try Ollama next (free, creative, local)
    use_ollama = de_config.get('use_ollama', not use_openrouter)  # Default to Ollama only if OpenRouter not configured
    
    if use_ollama:
        if verbose:
            print("  Trying Ollama for creative dream generation...")
        fragments = generate_with_ollama(concept_pairs, config, verbose)
        if fragments and len(fragments) >= len(concept_pairs) // 2:
            return fragments
        elif fragments:
            if verbose:
                print(f"  Ollama returned {len(fragments)}/{len(concept_pairs)} fragments, supplementing with templates...")
            # Got some but not all — supplement with templates
            remaining_pairs = concept_pairs[len(fragments):]
            seed = int(reference_date.strftime('%Y%m%d'))
            generator = FragmentGenerator(seed=seed)
            template_fragments = generator.generate_batch(remaining_pairs)
            return fragments + template_fragments
    
    # Fallback: template-based generation
    if verbose:
        print("  Using template-based dream generation (fallback)")
    
    seed = int(reference_date.strftime('%Y%m%d'))
    generator = FragmentGenerator(seed=seed)
    fragments = generator.generate_batch(concept_pairs)
    
    if verbose:
        print(f"Generated {len(fragments)} dream fragments")
        if fragments:
            print(f"  Example: \"{fragments[0]['fragment'][:60]}...\"")
    
    return fragments


def list_templates() -> list[str]:
    """Return a list of all available template keys."""
    return [get_template_key(t) for t in DREAM_TEMPLATES]


def get_template_count() -> int:
    """Return the number of available templates."""
    return len(DREAM_TEMPLATES)
