"""Aspirations module — Long-term dreams and the projects that pursue them.

This module provides schema validation, CRUD operations, and tree/orphan
analysis for the aspirations and projects system. Aspirations are the "why"
(intangible dreams), projects are the "what" (tangible work).

Example usage:
    >>> from core.aspirations import load_aspirations, get_tree
    >>> 
    >>> data = load_aspirations(state_path)
    >>> tree = get_tree(data)

Modules:
    models: Schema validation for aspirations and projects
    store: CRUD operations and tree queries
    discovery: Bridge from barren aspirations to drive suggestions
    cli: Command-line interface for human interaction

CLI Usage:
    python3 -m core.aspirations [command] [options]
    
    Commands:
        tree            Show aspirations with nested projects
        dreams          List all aspirations
        projects        List all projects grouped by status
        add-dream       Add a new aspiration
        add-project     Add a new project
        link            Link a project to an aspiration
        status          Update project status
        orphans         Show projects with invalid aspiration links
        barren          Show aspirations with no projects
"""

# Models and validation
from .models import (
    ASPIRATION_SCHEMA,
    PROJECT_SCHEMA,
    ASPIRATION_CATEGORIES,
    PROJECT_STATUSES,
    PROJECT_CATEGORIES,
    validate_aspiration,
    validate_project,
)

# Store and CRUD operations
from .store import (
    load_aspirations,
    save_aspirations,
    add_aspiration,
    add_project,
    remove_aspiration,
    remove_project,
    update_project_status,
    link_project,
    get_tree,
    get_orphans,
    get_barren,
)

# Discovery bridge
from .discovery import (
    get_barren_aspirations,
    suggest_drives_from_aspirations,
)

# CLI entry point
from .cli import main as cli_main

__version__ = "1.0.0"
__all__ = [
    # Models
    "ASPIRATION_SCHEMA",
    "PROJECT_SCHEMA",
    "ASPIRATION_CATEGORIES",
    "PROJECT_STATUSES",
    "PROJECT_CATEGORIES",
    "validate_aspiration",
    "validate_project",
    # Store
    "load_aspirations",
    "save_aspirations",
    "add_aspiration",
    "add_project",
    "remove_aspiration",
    "remove_project",
    "update_project_status",
    "link_project",
    "get_tree",
    "get_orphans",
    "get_barren",
    # Discovery
    "get_barren_aspirations",
    "suggest_drives_from_aspirations",
    # CLI
    "cli_main",
]
