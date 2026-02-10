"""Store operations for aspirations and projects.

Provides atomic read/write operations and CRUD functionality for the
aspirations.json state file. Uses write-to-temp-then-rename pattern
for crash safety.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .models import (
    AspirationsData,
    create_default_data,
    validate_aspiration,
    validate_project,
)


def load_aspirations(state_path: Path) -> AspirationsData:
    """Load aspirations data from JSON file.
    
    Returns default structure if file doesn't exist.
    Validates structure and schema on load.
    
    Args:
        state_path: Path to the aspirations.json file
        
    Returns:
        AspirationsData dictionary with loaded or default values
        
    Raises:
        SystemExit: If file exists but contains corrupted JSON
        
    Examples:
        >>> data = load_aspirations(Path(".emergence/state/aspirations.json"))
        >>> "aspirations" in data
        True
    """
    if not state_path.exists():
        return create_default_data()
    
    try:
        with open(state_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Aspirations file corrupted: {state_path}", file=sys.stderr)
        print(f"  Error: {e}", file=sys.stderr)
        print("  Options:", file=sys.stderr)
        print(f"    1. Fix the JSON manually", file=sys.stderr)
        print(f"    2. Reset: mv '{state_path}' '{state_path}.bak'", file=sys.stderr)
        sys.exit(1)
    except IOError as e:
        print(f"Error reading aspirations file: {e}", file=sys.stderr)
        return create_default_data()
    
    # Validate minimal structure
    if "version" not in data:
        data["version"] = 1
    if "aspirations" not in data:
        data["aspirations"] = []
    if "projects" not in data:
        data["projects"] = []
    if "meta" not in data:
        data["meta"] = {"updatedAt": datetime.now(timezone.utc).isoformat()}
    
    return data


def save_aspirations(state_path: Path, data: AspirationsData, backup: bool = True) -> bool:
    """Atomically save aspirations data to JSON file.
    
    Writes to a temporary file first, then renames for atomicity.
    This ensures state is never partially written.
    
    Args:
        state_path: Target path for the state file
        data: AspirationsData dictionary to save
        backup: If True, create .bak backup before overwriting
        
    Returns:
        True if save succeeded, False otherwise
        
    Examples:
        >>> data = create_default_data()
        >>> save_aspirations(Path("aspirations.json"), data)
        True
    """
    # Update metadata timestamp
    if "meta" not in data:
        data["meta"] = {}
    data["meta"]["updatedAt"] = datetime.now(timezone.utc).isoformat()
    
    # Ensure parent directory exists
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
    except IOError:
        return False
    
    # Create backup if requested and target exists
    if backup and state_path.exists():
        backup_path = state_path.with_suffix(".json.bak")
        try:
            with open(state_path, "r", encoding="utf-8") as src:
                with open(backup_path, "w", encoding="utf-8") as dst:
                    dst.write(src.read())
        except IOError:
            # Backup failure shouldn't prevent save
            pass
    
    # Write to temp file in same directory (for atomic rename)
    temp_path = state_path.with_suffix(".tmp")
    
    try:
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        # Atomic rename
        temp_path.rename(state_path)
        return True
        
    except Exception:
        # Clean up temp file on failure
        if temp_path.exists():
            try:
                temp_path.unlink()
            except OSError:
                pass
        return False


def _get_aspiration_ids(data: AspirationsData) -> set[str]:
    """Get set of all aspiration ids for validation."""
    return {a.get("id") for a in data.get("aspirations", []) if a.get("id")}


def _get_project_ids(data: AspirationsData) -> set[str]:
    """Get set of all project ids."""
    return {p.get("id") for p in data.get("projects", []) if p.get("id")}


def _project_count_for_aspiration(data: AspirationsData, aspiration_id: str) -> int:
    """Count how many projects are linked to a given aspiration."""
    return sum(
        1 for p in data.get("projects", [])
        if p.get("aspirationId") == aspiration_id
    )


def add_aspiration(data: AspirationsData, aspiration: dict) -> tuple[bool, str]:
    """Add a new aspiration after validation.
    
    Args:
        data: Current aspirations data
        aspiration: Aspiration dict to add
        
    Returns:
        Tuple of (success, message)
        
    Examples:
        >>> data = create_default_data()
        >>> aspiration = {"id": "test", "title": "Test", "description": "A test", "category": "creative", "createdAt": "2026-01-01"}
        >>> success, msg = add_aspiration(data, aspiration)
        >>> success
        True
    """
    # Validate
    is_valid, errors = validate_aspiration(aspiration)
    if not is_valid:
        return False, f"Validation failed: {'; '.join(errors)}"
    
    # Check for duplicate id
    existing_ids = _get_aspiration_ids(data)
    if aspiration.get("id") in existing_ids:
        return False, f"Aspiration with id '{aspiration['id']}' already exists"
    
    # Add the aspiration
    data["aspirations"].append(aspiration)
    return True, f"Added aspiration '{aspiration.get('id')}'"


def add_project(data: AspirationsData, project: dict) -> tuple[bool, str]:
    """Add a new project after validation.
    
    Validates that the project links to an existing aspiration.
    
    Args:
        data: Current aspirations data
        project: Project dict to add
        
    Returns:
        Tuple of (success, message)
        
    Examples:
        >>> data = create_default_data()
        >>> data["aspirations"].append({"id": "dream", "title": "Dream", "description": "A dream", "category": "creative", "createdAt": "2026-01-01"})
        >>> project = {"id": "proj", "name": "Project", "aspirationId": "dream", "status": "active", "category": "tool", "description": "A project", "updatedAt": "2026-01-01"}
        >>> success, msg = add_project(data, project)
        >>> success
        True
    """
    # Get valid aspiration ids for cross-validation
    valid_aspiration_ids = _get_aspiration_ids(data)
    
    # Validate
    is_valid, errors = validate_project(project, valid_aspiration_ids)
    if not is_valid:
        return False, f"Validation failed: {'; '.join(errors)}"
    
    # Check for duplicate id
    existing_ids = _get_project_ids(data)
    if project.get("id") in existing_ids:
        return False, f"Project with id '{project['id']}' already exists"
    
    # Add the project
    data["projects"].append(project)
    return True, f"Added project '{project.get('id')}'"


def remove_aspiration(data: AspirationsData, aspiration_id: str, force: bool = False) -> tuple[bool, str]:
    """Remove an aspiration by id.
    
    Only succeeds if the aspiration has no linked projects (unless force=True).
    
    Args:
        data: Current aspirations data
        aspiration_id: Id of aspiration to remove
        force: If True, remove even with linked projects (orphans them)
        
    Returns:
        Tuple of (success, message)
    """
    # Find the aspiration
    aspiration = None
    for a in data.get("aspirations", []):
        if a.get("id") == aspiration_id:
            aspiration = a
            break
    
    if aspiration is None:
        return False, f"Aspiration '{aspiration_id}' not found"
    
    # Check for linked projects
    linked_count = _project_count_for_aspiration(data, aspiration_id)
    if linked_count > 0 and not force:
        return False, f"Cannot remove aspiration '{aspiration_id}' — it has {linked_count} linked project(s). Use force=True to orphan them."
    
    # Remove the aspiration
    data["aspirations"] = [a for a in data["aspirations"] if a.get("id") != aspiration_id]
    return True, f"Removed aspiration '{aspiration_id}'"


def remove_project(data: AspirationsData, project_id: str) -> tuple[bool, str]:
    """Remove a project by id.
    
    Args:
        data: Current aspirations data
        project_id: Id of project to remove
        
    Returns:
        Tuple of (success, message)
    """
    # Find the project
    project = None
    for p in data.get("projects", []):
        if p.get("id") == project_id:
            project = p
            break
    
    if project is None:
        return False, f"Project '{project_id}' not found"
    
    # Remove the project
    data["projects"] = [p for p in data["projects"] if p.get("id") != project_id]
    return True, f"Removed project '{project_id}'"


def update_project_status(data: AspirationsData, project_id: str, status: str) -> tuple[bool, str]:
    """Update the status of a project.
    
    Args:
        data: Current aspirations data
        project_id: Id of project to update
        status: New status (active, idea, paused, completed)
        
    Returns:
        Tuple of (success, message)
    """
    # Validate status
    from .models import PROJECT_STATUSES
    if status not in PROJECT_STATUSES:
        return False, f"Invalid status: {status}. Must be one of: {', '.join(PROJECT_STATUSES)}"
    
    # Find the project
    for p in data.get("projects", []):
        if p.get("id") == project_id:
            p["status"] = status
            p["updatedAt"] = datetime.now(timezone.utc).isoformat()
            return True, f"Updated project '{project_id}' status to '{status}'"
    
    return False, f"Project '{project_id}' not found"


def link_project(data: AspirationsData, project_id: str, aspiration_id: str) -> tuple[bool, str]:
    """Link a project to a different aspiration.
    
    Args:
        data: Current aspirations data
        project_id: Id of project to relink
        aspiration_id: Id of aspiration to link to
        
    Returns:
        Tuple of (success, message)
    """
    # Validate aspiration exists
    valid_ids = _get_aspiration_ids(data)
    if aspiration_id not in valid_ids:
        return False, f"Aspiration '{aspiration_id}' not found"
    
    # Find and update the project
    for p in data.get("projects", []):
        if p.get("id") == project_id:
            old_aspiration = p.get("aspirationId", "unknown")
            p["aspirationId"] = aspiration_id
            p["updatedAt"] = datetime.now(timezone.utc).isoformat()
            return True, f"Linked project '{project_id}' to aspiration '{aspiration_id}' (was '{old_aspiration}')"
    
    return False, f"Project '{project_id}' not found"


def get_tree(data: AspirationsData) -> list[dict]:
    """Get aspirations with their nested projects.
    
    Returns a list of aspiration objects, each with a 'projects' key
    containing linked projects.
    
    Args:
        data: Current aspirations data
        
    Returns:
        List of aspiration dicts with nested 'projects' list
        
    Examples:
        >>> data = create_default_data()
        >>> tree = get_tree(data)
        >>> isinstance(tree, list)
        True
    """
    result = []
    
    # Build a map of aspiration_id -> projects
    projects_by_aspiration = {}
    for p in data.get("projects", []):
        asp_id = p.get("aspirationId")
        if asp_id not in projects_by_aspiration:
            projects_by_aspiration[asp_id] = []
        projects_by_aspiration[asp_id].append(p)
    
    # Build tree with projects nested under each aspiration
    for aspiration in data.get("aspirations", []):
        asp_id = aspiration.get("id")
        asp_copy = dict(aspiration)
        asp_copy["projects"] = projects_by_aspiration.get(asp_id, [])
        result.append(asp_copy)
    
    return result


def get_orphans(data: AspirationsData) -> list[dict]:
    """Get projects with invalid (orphaned) aspiration links.
    
    Args:
        data: Current aspirations data
        
    Returns:
        List of project dicts with invalid aspirationId references
        
    Examples:
        >>> data = create_default_data()
        >>> orphans = get_orphans(data)
        >>> isinstance(orphans, list)
        True
    """
    valid_ids = _get_aspiration_ids(data)
    
    orphans = []
    for p in data.get("projects", []):
        if p.get("aspirationId") not in valid_ids:
            orphans.append(p)
    
    return orphans


def get_barren(data: AspirationsData) -> list[dict]:
    """Get aspirations with zero linked projects.
    
    Args:
        data: Current aspirations data
        
    Returns:
        List of aspiration dicts with no linked projects
        
    Examples:
        >>> data = create_default_data()
        >>> barren = get_barren(data)
        >>> isinstance(barren, list)
        True
    """
    # Get all aspiration ids with projects
    aspiration_ids_with_projects = set()
    for p in data.get("projects", []):
        aspiration_ids_with_projects.add(p.get("aspirationId"))
    
    # Find aspirations with no projects
    barren = []
    for a in data.get("aspirations", []):
        if a.get("id") not in aspiration_ids_with_projects:
            barren.append(a)
    
    return barren
