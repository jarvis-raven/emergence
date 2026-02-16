"""Irreducibility testing for drive discovery consolidation.

Provides functionality to detect similar drives via Ollama embeddings and
generate irreducibility test prompts for agent decision-making.
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Constants for Phase 2
SIMILARITY_THRESHOLD = 0.75  # Triggers review suggestion
ASPECT_RATE_INCREMENT = 0.2  # Rate increase per aspect (/hr)
MAX_RATE_CAP = 2.5  # Maximum rate per hour
MAX_ASPECTS = 5  # 6th aspect triggers review


def load_embeddings_config(workspace: Path) -> dict:
    """Load embeddings configuration from emergence.json.

    Args:
        workspace: Path to workspace root

    Returns:
        Embeddings config dict with provider settings
    """
    config_file = workspace / "emergence.json"

    if not config_file.exists():
        # Default to Ollama if no config
        return {
            "provider": "ollama",
            "ollama": {"base_url": "http://localhost:11434/v1", "model": "nomic-embed-text"},
        }

    try:
        with open(config_file, "r") as f:
            config = json.load(f)
            return config.get(
                "embeddings",
                {
                    "provider": "ollama",
                    "ollama": {
                        "base_url": "http://localhost:11434/v1",
                        "model": "nomic-embed-text",
                    },
                },
            )
    except (json.JSONDecodeError, IOError):
        # Fall back to default on error
        return {
            "provider": "ollama",
            "ollama": {"base_url": "http://localhost:11434/v1", "model": "nomic-embed-text"},
        }


def get_embedding(text: str, workspace: Optional[Path] = None) -> Optional[list[float]]:
    """Get embedding vector for text using configured provider.

    Supports:
    - Ollama (local, free) - Uses Ollama /api/embeddings endpoint
    - OpenAI-compatible APIs (OpenRouter, etc.) - Uses /v1/embeddings endpoint

    Args:
        text: Text to embed (will be truncated to 2000 chars)
        workspace: Path to workspace root (for config loading)

    Returns:
        Embedding vector as list of floats, or None if failed
    """
    # Load config
    config = load_embeddings_config(workspace or Path.cwd())
    provider = config.get("provider", "ollama")

    text = text[:2000]  # Truncate very long text

    if provider == "ollama":
        return _get_ollama_embedding(text, config.get("ollama", {}))
    elif provider == "openai":
        return _get_openai_embedding(text, config.get("openai", {}))
    else:
        # Unknown provider, return None (will trigger fallback)
        return None


def _get_ollama_embedding(text: str, config: dict) -> Optional[list[float]]:
    """Get embedding from Ollama API.

    Args:
        text: Text to embed
        config: Ollama config dict (base_url, model)

    Returns:
        Embedding vector or None if failed
    """
    base_url = config.get("base_url", "http://localhost:11434/v1")
    model = config.get("model", "nomic-embed-text")

    # Ollama uses /api/embeddings (not /v1/embeddings)
    url = base_url.replace("/v1", "") + "/api/embeddings"

    req_data = json.dumps({"model": model, "prompt": text}).encode("utf-8")

    try:
        req = urllib.request.Request(
            url, data=req_data, headers={"Content-Type": "application/json"}, method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("embedding")
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def _get_openai_embedding(text: str, config: dict) -> Optional[list[float]]:
    """Get embedding from OpenAI-compatible API (OpenRouter, OpenAI, etc.).

    Args:
        text: Text to embed
        config: OpenAI config dict (base_url, model, api_key_env)

    Returns:
        Embedding vector or None if failed
    """
    base_url = config.get("base_url", "https://openrouter.ai/api/v1")
    model = config.get("model", "text-embedding-3-small")
    api_key_env = config.get("api_key_env", "OPENROUTER_API_KEY")

    # Get API key from environment
    api_key = os.environ.get(api_key_env)
    if not api_key:
        return None

    url = f"{base_url}/embeddings"

    req_data = json.dumps({"model": model, "input": text}).encode("utf-8")

    try:
        req = urllib.request.Request(
            url,
            data=req_data,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
            method="POST",
        )

        with urllib.request.urlopen(req, timeout=30) as response:
            result = json.loads(response.read().decode("utf-8"))
            # OpenAI format: {"data": [{"embedding": [...]}]}
            if "data" in result and len(result["data"]) > 0:
                return result["data"][0].get("embedding")
            return None
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """Calculate cosine similarity between two vectors.

    Args:
        a: First embedding vector
        b: Second embedding vector

    Returns:
        Cosine similarity score (0.0 to 1.0)
    """
    if not a or not b or len(a) != len(b):
        return 0.0

    dot_product = sum(x * y for x, y in zip(a, b))
    magnitude_a = sum(x * x for x in a) ** 0.5
    magnitude_b = sum(x * x for x in b) ** 0.5

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)


def find_similar_drives(
    new_drive_name: str,
    new_drive_desc: str,
    existing_drives: dict,
    workspace: Path,
    threshold: float = SIMILARITY_THRESHOLD,
) -> list[tuple[str, float, dict]]:
    """Find existing drives similar to a new drive via embeddings.

    Uses configured embeddings provider (Ollama, OpenAI-compatible, etc.).
    Falls back to simple text matching if embeddings unavailable.

    Args:
        new_drive_name: Name of the new drive
        new_drive_desc: Description of the new drive
        existing_drives: Dictionary of existing drives from drives.json
        workspace: Path to workspace root
        threshold: Similarity threshold (0.0-1.0)

    Returns:
        List of (drive_name, similarity_score, drive_data) tuples,
        sorted by similarity descending
    """
    # Combine name and description for embedding
    new_text = f"{new_drive_name}: {new_drive_desc}"
    new_embedding = get_embedding(new_text, workspace)

    if new_embedding is None:
        # Fall back to simple text matching if embeddings unavailable
        return _fallback_similarity(new_drive_name, new_drive_desc, existing_drives, threshold)

    similar = []

    for drive_name, drive_data in existing_drives.items():
        # Skip non-base drives (aspects don't count)
        if not drive_data.get("base_drive", True):
            continue

        # Get embedding for existing drive
        drive_desc = drive_data.get("description", "")
        existing_text = f"{drive_name}: {drive_desc}"
        existing_embedding = get_embedding(existing_text, workspace)

        if existing_embedding is None:
            continue

        similarity = cosine_similarity(new_embedding, existing_embedding)

        if similarity >= threshold:
            similar.append((drive_name, similarity, drive_data))

    # Sort by similarity descending
    similar.sort(key=lambda x: x[1], reverse=True)
    return similar


def _fallback_similarity(
    new_name: str, new_desc: str, existing_drives: dict, threshold: float
) -> list[tuple[str, float, dict]]:
    """Fallback similarity using simple word overlap when Ollama unavailable.

    Args:
        new_name: Name of new drive
        new_desc: Description of new drive
        existing_drives: Dictionary of existing drives
        threshold: Similarity threshold

    Returns:
        List of similar drives with estimated scores
    """
    new_words = set((new_name + " " + new_desc).lower().split())
    similar = []

    for drive_name, drive_data in existing_drives.items():
        if not drive_data.get("base_drive", True):
            continue

        drive_desc = drive_data.get("description", "")
        existing_words = set((drive_name + " " + drive_desc).lower().split())

        # Jaccard similarity
        intersection = len(new_words & existing_words)
        union = len(new_words | existing_words)

        if union > 0:
            similarity = intersection / union
            if similarity >= threshold * 0.5:  # Lower threshold for fallback
                similar.append((drive_name, similarity, drive_data))

    similar.sort(key=lambda x: x[1], reverse=True)
    return similar


def generate_irreducibility_test(
    new_drive_name: str, new_drive_desc: str, similar_drives: list[tuple[str, float, dict]]
) -> str:
    """Generate prompt for agent to test drive irreducibility.

    Args:
        new_drive_name: Name of the discovered drive
        new_drive_desc: Description of the discovered drive
        similar_drives: List of (name, similarity, data) tuples

    Returns:
        Formatted irreducibility test prompt
    """
    prompt = f"""⚖️ IRREDUCIBILITY TEST: {new_drive_name}

New drive discovered:
  Name: {new_drive_name}
  Description: {new_drive_desc}

This seems related to existing drive(s):
"""

    for drive_name, similarity, drive_data in similar_drives[:3]:  # Top 3
        drive_desc = drive_data.get("description", "No description")
        prompt += f"""
  • {drive_name} (similarity: {similarity:.2f})
    Description: {drive_desc}"""

    primary_drive = similar_drives[0][0] if similar_drives else "existing_drive"

    prompt += f"""

═══════════════════════════════════════════════════════════

IRREDUCIBILITY TEST:

Ask yourself: "Can I fully satisfy {new_drive_name} by satisfying {primary_drive}?"

Test both directions:
1. Does satisfying {primary_drive} always satisfy {new_drive_name}?
   → If yes: {new_drive_name} is an ASPECT of {primary_drive}

2. Does satisfying {new_drive_name} always satisfy {primary_drive}?
   → If yes: {primary_drive} is an ASPECT of {new_drive_name}

3. If NO to both:
   → {new_drive_name} is a DISTINCT drive

What makes {new_drive_name} irreducible (if it is)?
What unique satisfaction does it provide that {primary_drive} doesn't?

═══════════════════════════════════════════════════════════

DECISION: [DISTINCT | ASPECT_OF_{primary_drive}]

If DISTINCT:
  • New drive will be created with base rate (1.5/hr)
  • Builds pressure independently
  • Budget impact: +~$2.50/day projected

If ASPECT:
  • {primary_drive} prompt will be enriched
  • Rate increases by {ASPECT_RATE_INCREMENT}/hr (capped at {MAX_RATE_CAP}/hr)
  • "{new_drive_desc}" becomes part of {primary_drive}
  • Budget impact: Minimal (shared pressure)

═══════════════════════════════════════════════════════════

Your felt experience determines the outcome, not the similarity score.

What is your decision?"""

    return prompt


def apply_irreducibility_decision(
    decision: str,
    new_drive_name: str,
    new_drive_desc: str,
    parent_drive_name: Optional[str],
    workspace: Path,
) -> dict:
    """Apply agent's irreducibility decision to the drive system.

    Args:
        decision: "DISTINCT" or "ASPECT_OF_NAME"
        new_drive_name: Name of the new drive
        new_drive_desc: Description of the new drive
        parent_drive_name: Name of parent drive (if ASPECT decision)
        workspace: Path to workspace root

    Returns:
        Result dictionary with status and message
    """
    from ..drives.state import load_state, save_state
    from ..drives.config import get_state_path
    from ..drives.models import ensure_drive_defaults

    emergence_dir = workspace / ".emergence"
    state_path = get_state_path({"paths": {"state": str(emergence_dir / "state")}})

    if not state_path.exists():
        return {"success": False, "error": "No drives.json found"}

    drives_state = load_state(state_path)
    drives = drives_state.get("drives", {})

    # Normalize decision
    decision = decision.upper().strip()

    if decision == "DISTINCT":
        # Check if drive already exists
        if new_drive_name in drives:
            return {"success": False, "error": f"Drive {new_drive_name} already exists"}

        # Create new base drive
        now = datetime.now(timezone.utc).isoformat()
        new_drive = {
            "name": new_drive_name,
            "base_drive": True,
            "aspects": [],
            "pressure": 0.0,
            "threshold": 20.0,
            "rate_per_hour": 1.5,
            "max_rate": MAX_RATE_CAP,
            "description": new_drive_desc,
            "prompt": f"Your {new_drive_name} drive has triggered. {new_drive_desc}",
            "category": "discovered",
            "created_by": "agent",
            "created_at": now,
            "satisfaction_events": [],
            "discovered_during": "first_light",
            "activity_driven": False,
            "last_triggered": None,
            "min_interval_seconds": 14400,  # 4 hours
        }

        drives[new_drive_name] = new_drive
        drives_state["drives"] = drives
        drives_state["last_tick"] = now

        save_state(state_path, drives_state)

        return {
            "success": True,
            "action": "created_distinct",
            "drive": new_drive_name,
            "message": f"Created {new_drive_name} as distinct drive (rate: 1.5/hr)",
        }

    elif decision.startswith("ASPECT"):
        if not parent_drive_name or parent_drive_name not in drives:
            return {"success": False, "error": f"Parent drive {parent_drive_name} not found"}

        parent = drives[parent_drive_name]

        # Check max aspects
        current_aspects = parent.get("aspects", [])
        if len(current_aspects) >= MAX_ASPECTS:
            return {
                "success": False,
                "error": f"{parent_drive_name} already has {MAX_ASPECTS} aspects. Consider review.",
                "needs_review": True,
            }

        # Add as aspect
        aspect_name = new_drive_name.lower().replace("_", " ")
        if aspect_name not in current_aspects:
            current_aspects.append(aspect_name)
            parent["aspects"] = current_aspects

        # Increase rate (capped)
        current_rate = parent.get("rate_per_hour", 1.5)
        new_rate = min(current_rate + ASPECT_RATE_INCREMENT, MAX_RATE_CAP)
        parent["rate_per_hour"] = new_rate

        # Enrich prompt
        current_prompt = parent.get("prompt", "")
        aspect_hint = f"including {new_drive_desc}"
        if aspect_hint not in current_prompt:
            if "—" in current_prompt:
                parent["prompt"] = f"{current_prompt}, {aspect_hint}"
            else:
                parent["prompt"] = f"{current_prompt} — {aspect_hint}"

        # Update description
        aspects_str = ", ".join(current_aspects)
        base_desc = parent.get("description", "").split(" (")[0]  # Remove old aspects
        parent["description"] = f"{base_desc} ({aspects_str})"

        # Apply defaults for backwards compatibility
        parent = ensure_drive_defaults(parent)

        drives[parent_drive_name] = parent
        drives_state["drives"] = drives
        drives_state["last_tick"] = datetime.now(timezone.utc).isoformat()

        save_state(state_path, drives_state)

        return {
            "success": True,
            "action": "added_aspect",
            "drive": parent_drive_name,
            "aspect": aspect_name,
            "new_rate": new_rate,
            "message": f"Added {aspect_name} as aspect of {parent_drive_name} (rate: {new_rate:.1f}/hr)",
        }

    else:
        return {
            "success": False,
            "error": f"Unknown decision: {decision}. Use DISTINCT or ASPECT_OF_<name>",
        }


def load_pending_reviews(workspace: Path) -> list[dict]:
    """Load pending drive reviews from pending-reviews.json.

    Args:
        workspace: Path to workspace root

    Returns:
        List of pending review entries
    """
    reviews_path = workspace / ".emergence" / "pending-reviews.json"

    if not reviews_path.exists():
        return []

    try:
        content = reviews_path.read_text()
        return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return []


def save_pending_reviews(workspace: Path, reviews: list[dict]):
    """Save pending drive reviews to pending-reviews.json.

    Args:
        workspace: Path to workspace root
        reviews: List of review entries
    """
    reviews_path = workspace / ".emergence" / "pending-reviews.json"
    reviews_path.parent.mkdir(parents=True, exist_ok=True)
    reviews_path.write_text(json.dumps(reviews, indent=2))


def add_pending_review(
    workspace: Path,
    new_drive_name: str,
    new_drive_desc: str,
    similar_drives: list[tuple[str, float, dict]],
    source_session: str,
):
    """Add a new drive discovery to pending reviews.

    Args:
        workspace: Path to workspace root
        new_drive_name: Name of discovered drive
        new_drive_desc: Description of discovered drive
        similar_drives: List of similar existing drives
        source_session: Source session file name
    """
    reviews = load_pending_reviews(workspace)

    # Check if already pending
    for review in reviews:
        if review.get("new_drive") == new_drive_name:
            return

    review_entry = {
        "new_drive": new_drive_name,
        "new_drive_description": new_drive_desc,
        "similar_drives": [
            {"name": name, "similarity": round(similarity, 2)}
            for name, similarity, _ in similar_drives[:3]
        ],
        "discovered_at": datetime.now(timezone.utc).isoformat(),
        "source_session": source_session,
        "status": "pending",
    }

    reviews.append(review_entry)
    save_pending_reviews(workspace, reviews)


def review_pending_drives(workspace: Path, specific_drive: Optional[str] = None) -> str:
    """Generate review output for pending drive consolidations.

    Args:
        workspace: Path to workspace root
        specific_drive: If provided, only show review for this drive

    Returns:
        Formatted review text
    """
    reviews = load_pending_reviews(workspace)

    if not reviews:
        return "ℹ No pending drive reviews."

    if specific_drive:
        # Find specific drive review
        for review in reviews:
            if review.get("new_drive") == specific_drive.upper():
                return generate_irreducibility_test(
                    review["new_drive"],
                    review["new_drive_description"],
                    [(d["name"], d["similarity"], {}) for d in review.get("similar_drives", [])],
                )
        return f"✗ No pending review found for: {specific_drive}"

    # List all pending
    output = "⚖️ Pending Drive Reviews:\n"
    output += "=" * 52 + "\n\n"

    for review in reviews:
        new_drive = review.get("new_drive")
        similar = review.get("similar_drives", [])
        source = review.get("source_session", "unknown")

        output += f"  • {new_drive}\n"
        output += f"    Similar to: {', '.join(d['name'] for d in similar)}\n"
        output += f"    Source: {source}\n"
        output += f"    Run: drives review {new_drive}\n\n"

    output += f"\nTotal pending: {len(reviews)}"
    output += f"\nRun 'drives review <name>' for irreducibility test"

    return output


def remove_pending_review(workspace: Path, drive_name: str):
    """Remove a review from pending list (after decision applied).

    Args:
        workspace: Path to workspace root
        drive_name: Name of drive to remove from pending
    """
    reviews = load_pending_reviews(workspace)
    reviews = [r for r in reviews if r.get("new_drive") != drive_name.upper()]
    save_pending_reviews(workspace, reviews)
