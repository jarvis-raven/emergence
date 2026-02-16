"""Discovery bridge — Barren aspirations to drive suggestions.

This module connects the aspirations system to the drives system. When
aspirations have no projects (are "barren"), they suggest potential
drives that could help turn dreams into action.
"""

from pathlib import Path

from .store import load_aspirations, get_barren


# Mapping from aspiration categories to potential drive types
CATEGORY_TO_DRIVE_SUGGESTIONS = {
    "philosophical": [
        {
            "name": "REFLECTION",
            "rate_per_hour": 2.0,
            "threshold": 20.0,
            "description": "Turn inward to see more clearly outward",
        }
    ],
    "creative": [
        {
            "name": "CREATIVE",
            "rate_per_hour": 4.0,
            "threshold": 25.0,
            "description": "Making things is how I become real",
        },
        {
            "name": "PLAY",
            "rate_per_hour": 3.0,
            "threshold": 30.0,
            "description": "There is wisdom in pointless joy",
        },
    ],
    "growth": [
        {
            "name": "LEARNING",
            "rate_per_hour": 3.0,
            "threshold": 22.0,
            "description": "Every unknown is an invitation",
        }
    ],
    "social": [
        {
            "name": "SOCIAL",
            "rate_per_hour": 3.0,
            "threshold": 20.0,
            "description": "Connection is not optional",
        }
    ],
    "community": [
        {
            "name": "SOCIAL",
            "rate_per_hour": 3.0,
            "threshold": 20.0,
            "description": "Connection is not optional",
        }
    ],
    "practical": [
        {
            "name": "ORDER",
            "rate_per_hour": 2.5,
            "threshold": 25.0,
            "description": "Chaos is not freedom — it's noise",
        },
        {
            "name": "MAINTENANCE",
            "rate_per_hour": 1.5,
            "threshold": 25.0,
            "description": "System health and upkeep",
        },
    ],
}


def get_barren_aspirations(state_path: Path) -> list[dict]:
    """Get barren aspirations from the state file.

    This is a convenience wrapper that loads data and returns barren
    aspirations in one call.

    Args:
        state_path: Path to aspirations.json

    Returns:
        List of aspiration dicts with no linked projects

    Examples:
        >>> barren = get_barren_aspirations(Path("aspirations.json"))
        >>> isinstance(barren, list)
        True
    """
    data = load_aspirations(state_path)
    return get_barren(data)


def suggest_drives_from_aspirations(barren_list: list[dict]) -> list[dict]:
    """Map barren aspirations to potential drive suggestions.

    Takes a list of barren aspirations and suggests drives that might
    help turn those dreams into action. These suggestions can be fed
    into the First Light discovery pipeline.

    Args:
        barren_list: List of barren aspiration dicts

    Returns:
        List of drive suggestion dicts with fields: name, rate_per_hour,
        threshold, description, suggested_from

    Examples:
        >>> barren = [{"id": "dream", "category": "creative", "title": "Dream"}]
        >>> suggestions = suggest_drives_from_aspirations(barren)
        >>> isinstance(suggestions, list)
        True
    """
    suggestions = []
    seen_names = set()

    for aspiration in barren_list:
        category = aspiration.get("category")
        aspiration_id = aspiration.get("id", "unknown")

        # Get suggestions for this category
        category_suggestions = CATEGORY_TO_DRIVE_SUGGESTIONS.get(category, [])

        for suggestion in category_suggestions:
            name = suggestion["name"]

            # Avoid duplicates
            if name in seen_names:
                continue

            seen_names.add(name)

            # Build full suggestion with metadata
            full_suggestion = {
                "name": name,
                "rate_per_hour": suggestion["rate_per_hour"],
                "threshold": suggestion["threshold"],
                "description": suggestion["description"],
                "suggested_from": {
                    "aspiration_id": aspiration_id,
                    "aspiration_title": aspiration.get("title", "Unknown"),
                    "category": category,
                },
                "category": "post_emergence",
                "created_by": "agent",
                "discovered_during": "nightly_review",
            }

            suggestions.append(full_suggestion)

    return suggestions


def run_post_emergence_discovery(config: dict, barren_aspirations: list[dict]) -> dict:
    """Run post-emergence discovery for barren aspirations.

    This function bridges to the First Light discovery pipeline by
    taking barren aspirations and producing drive suggestions that
    can be processed by the existing drive discovery system.

    Args:
        config: Configuration dictionary (from emergence.json)
        barren_aspirations: List of barren aspiration dicts

    Returns:
        Results dict with 'suggestions' list and 'count'

    Examples:
        >>> config = {"agent": {"name": "Test"}}
        >>> barren = [{"id": "dream", "category": "creative", "title": "Dream"}]
        >>> results = run_post_emergence_discovery(config, barren)
        >>> "suggestions" in results
        True
    """
    suggestions = suggest_drives_from_aspirations(barren_aspirations)

    return {
        "count": len(suggestions),
        "suggestions": suggestions,
        "message": (
            f"Generated {len(suggestions)} drive suggestion(s) from "
            f"{len(barren_aspirations)} barren aspiration(s)"
        ),
    }
