"""Schema validation for aspirations and projects.

Defines the structure of aspirations (the "why") and projects (the "what")
using TypedDict for Python 3.9+ compatibility.
"""

from typing import TypedDict, Optional, Literal
from datetime import datetime, timezone


# Valid aspiration categories
ASPIRATION_CATEGORIES = [
    "philosophical",
    "creative",
    "growth",
    "social",
    "community",
    "practical",
]

# Valid project statuses
PROJECT_STATUSES = ["active", "idea", "paused", "completed"]

# Valid project categories
PROJECT_CATEGORIES = ["framework", "tool", "creative", "community", "personal"]


class Aspiration(TypedDict, total=False):
    """A single aspiration — the "why" behind work.

    Aspirations are long-term dreams, questions, and ambitions that give
    direction to projects. They represent the intangible motivations
    behind tangible work.

    Attributes:
        id: Unique kebab-case identifier (e.g., 'understand-self')
        title: Human-readable name
        description: What this dream means, in detail
        category: Thematic category for grouping
        createdAt: ISO 8601 date when first articulated
        throughline: Optional thematic thread (e.g., 'depth', 'connection')
    """

    id: str
    title: str
    description: str
    category: Literal["philosophical", "creative", "growth", "social", "community", "practical"]
    createdAt: str
    throughline: Optional[str]


class Project(TypedDict, total=False):
    """A single project — the "what" that pursues an aspiration.

    Projects are tangible work items linked to aspirations. They have
    status, dates, and details that track progress over time.

    Attributes:
        id: Unique kebab-case identifier
        name: Human-readable display name
        aspirationId: Reference to parent aspiration's id
        status: Current state of the project
        category: Type of work (framework, tool, etc.)
        description: One-line summary
        details: Optional expanded information
        links: Optional repository/local/URL references
        startDate: Optional ISO 8601 date (null for ideas)
        updatedAt: ISO 8601 date of last meaningful change
    """

    id: str
    name: str
    aspirationId: str
    status: Literal["active", "idea", "paused", "completed"]
    category: Literal["framework", "tool", "creative", "community", "personal"]
    description: str
    details: Optional[str]
    links: Optional[dict]
    startDate: Optional[str]
    updatedAt: str


class AspirationsData(TypedDict, total=False):
    """The complete data structure for aspirations and projects.

    This is the structure persisted to and loaded from aspirations.json.

    Attributes:
        version: Schema version for migration support
        aspirations: List of aspiration objects
        projects: List of project objects
        meta: Optional metadata including updatedAt timestamp
    """

    version: int
    aspirations: list[Aspiration]
    projects: list[Project]
    meta: Optional[dict]


# Schema definitions for validation
ASPIRATION_SCHEMA = {
    "required": ["id", "title", "description", "category", "createdAt"],
    "optional": ["throughline"],
    "fields": {
        "id": {"type": str, "description": "Unique kebab-case identifier"},
        "title": {"type": str, "description": "Human-readable name"},
        "description": {"type": str, "description": "What this dream means"},
        "category": {"type": str, "allowed": ASPIRATION_CATEGORIES},
        "createdAt": {"type": str, "description": "ISO 8601 date"},
        "throughline": {"type": str, "description": "Thematic thread"},
    },
}

PROJECT_SCHEMA = {
    "required": ["id", "name", "aspirationId", "status", "category", "description", "updatedAt"],
    "optional": ["details", "links", "startDate"],
    "fields": {
        "id": {"type": str, "description": "Unique kebab-case identifier"},
        "name": {"type": str, "description": "Display name"},
        "aspirationId": {"type": str, "description": "Links to parent aspiration"},
        "status": {"type": str, "allowed": PROJECT_STATUSES},
        "category": {"type": str, "allowed": PROJECT_CATEGORIES},
        "description": {"type": str, "description": "One-liner"},
        "details": {"type": str, "description": "Expanded info"},
        "links": {"type": dict, "description": "Repo/local/URL references"},
        "startDate": {"type": str, "description": "ISO 8601 date or null"},
        "updatedAt": {"type": str, "description": "ISO 8601 date of last change"},
    },
}


def create_default_data() -> AspirationsData:
    """Create a fresh aspirations data structure.

    Returns:
        An AspirationsData with empty aspirations and projects lists.
    """
    return {
        "version": 1,
        "aspirations": [],
        "projects": [],
        "meta": {
            "updatedAt": datetime.now(timezone.utc).isoformat(),
        },
    }


def _validate_aspiration_id(data: dict, errors: list[str]) -> None:
    """Validate aspiration id field."""
    if "id" in data:
        id_val = data["id"]
        if not isinstance(id_val, str):
            errors.append(f"Aspiration id must be a string, got {type(id_val).__name__}")
        elif " " in id_val:
            errors.append(f"Aspiration id should be kebab-case (no spaces): {id_val}")


def _validate_aspiration_category(data: dict, errors: list[str]) -> None:
    """Validate aspiration category field."""
    if "category" in data:
        cat = data["category"]
        if cat not in ASPIRATION_CATEGORIES:
            errors.append(
                f"Invalid aspiration category: {cat}. "
                f"Must be one of: {', '.join(ASPIRATION_CATEGORIES)}"
            )


def validate_aspiration(data: dict) -> tuple[bool, list[str]]:
    """Validate an aspiration definition and return any errors.

    Args:
        data: The aspiration dict to validate

    Returns:
        Tuple of (is_valid, list_of_error_messages)

    Examples:
        >>> aspiration = {
        ...     "id": "test", "title": "Test", "description": "A test",
        ...     "category": "creative", "createdAt": "2026-01-01"
        ... }
        >>> valid, errors = validate_aspiration(aspiration)
        >>> valid
        True
    """
    errors = []

    # Check required fields
    for field in ASPIRATION_SCHEMA["required"]:
        if field not in data:
            errors.append(f"Aspiration missing required field: {field}")

    # Validate id
    _validate_aspiration_id(data, errors)

    # Validate category
    _validate_aspiration_category(data, errors)

    # Validate string fields
    string_fields = ["title", "description", "createdAt"]
    for field in string_fields:
        if field in data and not isinstance(data[field], str):
            errors.append(f"Aspiration {field} must be a string")

    # Validate throughline if present
    if "throughline" in data and data["throughline"] is not None:
        if not isinstance(data["throughline"], str):
            errors.append("Aspiration throughline must be a string or null")

    return len(errors) == 0, errors


def _validate_project_id(data: dict, errors: list[str]) -> None:
    """Validate project id field."""
    if "id" in data:
        id_val = data["id"]
        if not isinstance(id_val, str):
            errors.append(f"Project id must be a string, got {type(id_val).__name__}")
        elif " " in id_val:
            errors.append(f"Project id should be kebab-case (no spaces): {id_val}")


def _validate_project_status(data: dict, errors: list[str]) -> None:
    """Validate project status field."""
    if "status" in data:
        status = data["status"]
        if status not in PROJECT_STATUSES:
            errors.append(
                f"Invalid project status: {status}. Must be one of: {', '.join(PROJECT_STATUSES)}"
            )


def _validate_project_category(data: dict, errors: list[str]) -> None:
    """Validate project category field."""
    if "category" in data:
        cat = data["category"]
        if cat not in PROJECT_CATEGORIES:
            errors.append(
                f"Invalid project category: {cat}. Must be one of: {', '.join(PROJECT_CATEGORIES)}"
            )


def _validate_project_aspiration_link(
    data: dict, valid_aspiration_ids: Optional[set], errors: list[str]
) -> None:
    """Validate project aspirationId link."""
    if "aspirationId" in data and valid_aspiration_ids is not None:
        if data["aspirationId"] not in valid_aspiration_ids:
            errors.append(
                f"Project aspirationId '{data['aspirationId']}' "
                "does not reference a valid aspiration"
            )


def validate_project(
    data: dict, valid_aspiration_ids: Optional[set] = None
) -> tuple[bool, list[str]]:
    """Validate a project definition and return any errors.

    Args:
        data: The project dict to validate
        valid_aspiration_ids: Optional set of valid aspiration ids for cross-validation

    Returns:
        Tuple of (is_valid, list_of_error_messages)

    Examples:
        >>> project = {
        ...     "id": "test", "name": "Test", "aspirationId": "dream",
        ...     "status": "active", "category": "tool",
        ...     "description": "A test", "updatedAt": "2026-01-01"
        ... }
        >>> valid, errors = validate_project(project)
        >>> valid
        True
    """
    errors = []

    # Check required fields
    for field in PROJECT_SCHEMA["required"]:
        if field not in data:
            errors.append(f"Project missing required field: {field}")

    # Validate id
    _validate_project_id(data, errors)

    # Validate status
    _validate_project_status(data, errors)

    # Validate category
    _validate_project_category(data, errors)

    # Validate aspirationId exists if provided
    _validate_project_aspiration_link(data, valid_aspiration_ids, errors)

    # Validate string fields
    string_fields = ["name", "description", "aspirationId", "updatedAt"]
    for field in string_fields:
        if field in data and not isinstance(data[field], str):
            errors.append(f"Project {field} must be a string")

    # Validate dates if present
    if "startDate" in data and data["startDate"] is not None:
        if not isinstance(data["startDate"], str):
            errors.append("Project startDate must be a string or null")

    # Validate links if present
    if "links" in data and data["links"] is not None:
        if not isinstance(data["links"], dict):
            errors.append("Project links must be an object or null")

    return len(errors) == 0, errors
