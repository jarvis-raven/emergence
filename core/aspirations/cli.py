"""CLI entry point for the Aspirations module.

Provides a human-facing interface to the aspirations system with
commands for viewing, adding, and managing dreams and projects.
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Import from the aspirations module
from .store import (
    load_aspirations,
    save_aspirations,
    add_aspiration,
    add_project,
    update_project_status,
    link_project,
    get_tree,
    get_orphans,
    get_barren,
)
from .models import ASPIRATION_CATEGORIES, PROJECT_STATUSES, PROJECT_CATEGORIES


# --- Constants ---
VERSION = "1.0.0"
EXIT_SUCCESS = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def get_state_path_from_config(config_path: Optional[Path] = None) -> Path:
    """Resolve state path from emergence.json config.

    Args:
        config_path: Optional explicit path to config file

    Returns:
        Path to aspirations.json
    """
    defaults = {
        "paths": {
            "workspace": ".",
            "state": ".emergence/state",
        }
    }

    if config_path is None:
        # Search upward for emergence.json
        current = Path.cwd()
        for _ in range(100):  # Prevent infinite loops
            config_file = current / "emergence.json"
            if config_file.exists():
                config_path = config_file
                break
            parent = current.parent
            if parent == current:  # At root
                break
            current = parent

    if config_path and config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            # Strip comments
            lines = [
                l
                for l in content.split("\n")
                if not l.strip().startswith("//") and not l.strip().startswith("#")
            ]
            config = json.loads("\n".join(lines))
        except (json.JSONDecodeError, IOError):
            config = defaults
    else:
        config = defaults

    workspace = config.get("paths", {}).get("workspace", ".")
    state_dir = config.get("paths", {}).get("state", ".emergence/state")

    return Path(workspace) / state_dir / "aspirations.json"


def ensure_data(data: dict) -> dict:
    """Ensure data has minimal structure."""
    if "aspirations" not in data:
        data["aspirations"] = []
    if "projects" not in data:
        data["projects"] = []
    return data


# --- Command Implementations ---


def cmd_tree(args) -> int:
    """Show tree view: aspirations with nested projects."""
    state_path = get_state_path_from_config(Path(args.config) if args.config else None)
    data = load_aspirations(state_path)
    data = ensure_data(data)

    tree = get_tree(data)

    if not tree:
        print("No aspirations yet. Use 'add-dream' to create one.")
        return EXIT_SUCCESS

    # JSON output
    if getattr(args, "json", False):
        print(json.dumps(tree, indent=2))
        return EXIT_SUCCESS

    print("🌳 Aspirations Tree")
    print("=" * 50)

    for aspiration in tree:
        asp_id = aspiration.get("id", "unknown")
        title = aspiration.get("title", "Untitled")
        category = aspiration.get("category", "unknown")
        projects = aspiration.get("projects", [])

        print(f"\n✨ {title}")
        print(f"   id: {asp_id} | category: {category}")

        if projects:
            for project in projects:
                status = project.get("status", "unknown")
                proj_name = project.get("name", "Untitled")
                proj_cat = project.get("category", "unknown")
                status_icon = {"active": "▶", "idea": "💡", "paused": "⏸", "completed": "✓"}.get(
                    status, "•"
                )
                print(f"   {status_icon} {proj_name} ({proj_cat}, {status})")
        else:
            print(f"   (no projects yet)")

    return EXIT_SUCCESS


def cmd_dreams(args) -> int:
    """List all aspirations."""
    state_path = get_state_path_from_config(Path(args.config) if args.config else None)
    data = load_aspirations(state_path)
    data = ensure_data(data)

    aspirations = data.get("aspirations", [])

    # JSON output
    if getattr(args, "json", False):
        print(json.dumps(aspirations, indent=2))
        return EXIT_SUCCESS

    if not aspirations:
        print("No aspirations yet. Use 'add-dream' to create one.")
        return EXIT_SUCCESS

    print("✨ Aspirations")
    print("=" * 50)

    for a in aspirations:
        asp_id = a.get("id", "unknown")
        title = a.get("title", "Untitled")
        category = a.get("category", "unknown")
        throughline = a.get("throughline")

        # Count linked projects
        project_count = sum(1 for p in data.get("projects", []) if p.get("aspirationId") == asp_id)

        print(f"\n{title}")
        print(f"  id: {asp_id}")
        print(f"  category: {category}")
        if throughline:
            print(f"  throughline: {throughline}")
        print(f"  projects: {project_count}")
        print(f"  {a.get('description', '')[:80]}...")

    return EXIT_SUCCESS


def cmd_projects(args) -> int:
    """List all projects grouped by status."""
    state_path = get_state_path_from_config(Path(args.config) if args.config else None)
    data = load_aspirations(state_path)
    data = ensure_data(data)

    projects = data.get("projects", [])

    # JSON output
    if getattr(args, "json", False):
        print(json.dumps(projects, indent=2))
        return EXIT_SUCCESS

    if not projects:
        print("No projects yet. Use 'add-project' to create one.")
        return EXIT_SUCCESS

    # Group by status
    by_status = {"active": [], "idea": [], "paused": [], "completed": []}
    for p in projects:
        status = p.get("status", "unknown")
        if status in by_status:
            by_status[status].append(p)

    # Build aspiration id -> title map
    asp_map = {a.get("id"): a.get("title", "Unknown") for a in data.get("aspirations", [])}

    print("📁 Projects")
    print("=" * 50)

    status_order = ["active", "idea", "paused", "completed"]
    status_icons = {"active": "▶", "idea": "💡", "paused": "⏸", "completed": "✓"}

    for status in status_order:
        projs = by_status[status]
        if not projs:
            continue

        print(f"\n{status_icons.get(status, '•')} {status.upper()} ({len(projs)})")
        print("-" * 30)

        for p in projs:
            name = p.get("name", "Untitled")
            category = p.get("category", "unknown")
            asp_id = p.get("aspirationId", "unknown")
            asp_title = asp_map.get(asp_id, f"[{asp_id}]")

            print(f"  {name}")
            print(f"    category: {category}")
            print(f"    aspiration: {asp_title}")
            print(f"    {p.get('description', '')[:60]}...")

    return EXIT_SUCCESS


def cmd_add_dream(args) -> int:
    """Add a new aspiration."""
    state_path = get_state_path_from_config(Path(args.config) if args.config else None)
    data = load_aspirations(state_path)
    data = ensure_data(data)

    # Get title from args or prompt
    title = args.title if hasattr(args, "title") and args.title else None

    if not title:
        print(
            '✗ Usage: add-dream "Title" [--desc "..."] [--category philosophical]', file=sys.stderr
        )
        return EXIT_USAGE

    # Generate kebab-case id from title
    asp_id = title.lower().replace(" ", "-").replace("_", "-")
    asp_id = "".join(c for c in asp_id if c.isalnum() or c == "-")

    # Get description
    description = getattr(args, "desc", "") or ""

    # Get category
    category = getattr(args, "category", "philosophical")
    if category not in ASPIRATION_CATEGORIES:
        print(f"✗ Invalid category: {category}", file=sys.stderr)
        print(f"  Must be one of: {', '.join(ASPIRATION_CATEGORIES)}", file=sys.stderr)
        return EXIT_USAGE

    # Get throughline
    throughline = getattr(args, "throughline", None)

    aspiration = {
        "id": asp_id,
        "title": title,
        "description": description,
        "category": category,
        "createdAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    if throughline:
        aspiration["throughline"] = throughline

    success, msg = add_aspiration(data, aspiration)

    if not success:
        print(f"✗ {msg}", file=sys.stderr)
        return EXIT_ERROR

    # Save
    if not save_aspirations(state_path, data):
        print("✗ Failed to save aspirations", file=sys.stderr)
        return EXIT_ERROR

    print(f"✓ {msg}")
    print(f"  id: {asp_id}")
    print(f"  category: {category}")

    return EXIT_SUCCESS


def cmd_add_project(args) -> int:
    """Add a new project."""
    state_path = get_state_path_from_config(Path(args.config) if args.config else None)
    data = load_aspirations(state_path)
    data = ensure_data(data)

    name = args.name if hasattr(args, "name") and args.name else None
    aspiration_id = getattr(args, "for_aspiration", None)

    if not name:
        print(
            '✗ Usage: add-project "Name" --for aspiration-id [--status active] [--desc "..."]',
            file=sys.stderr,
        )
        return EXIT_USAGE

    if not aspiration_id:
        print("✗ Must specify --for aspiration-id", file=sys.stderr)
        return EXIT_USAGE

    # Generate kebab-case id from name
    proj_id = name.lower().replace(" ", "-").replace("_", "-")
    proj_id = "".join(c for c in proj_id if c.isalnum() or c == "-")

    # Get optional fields
    description = getattr(args, "desc", "") or ""
    status = getattr(args, "status", "idea")
    category = getattr(args, "category", "tool")

    if status not in PROJECT_STATUSES:
        print(f"✗ Invalid status: {status}", file=sys.stderr)
        print(f"  Must be one of: {', '.join(PROJECT_STATUSES)}", file=sys.stderr)
        return EXIT_USAGE

    if category not in PROJECT_CATEGORIES:
        print(f"✗ Invalid category: {category}", file=sys.stderr)
        print(f"  Must be one of: {', '.join(PROJECT_CATEGORIES)}", file=sys.stderr)
        return EXIT_USAGE

    project = {
        "id": proj_id,
        "name": name,
        "aspirationId": aspiration_id,
        "status": status,
        "category": category,
        "description": description,
        "updatedAt": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
    }

    # Add startDate if not an idea
    if status != "idea":
        project["startDate"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    success, msg = add_project(data, project)

    if not success:
        print(f"✗ {msg}", file=sys.stderr)
        return EXIT_ERROR

    # Save
    if not save_aspirations(state_path, data):
        print("✗ Failed to save aspirations", file=sys.stderr)
        return EXIT_ERROR

    print(f"✓ {msg}")
    print(f"  id: {proj_id}")
    print(f"  linked to: {aspiration_id}")
    print(f"  status: {status}")

    return EXIT_SUCCESS


def cmd_link(args) -> int:
    """Link a project to a different aspiration."""
    state_path = get_state_path_from_config(Path(args.config) if args.config else None)
    data = load_aspirations(state_path)
    data = ensure_data(data)

    project_id = args.project_id if hasattr(args, "project_id") else None
    aspiration_id = args.aspiration_id if hasattr(args, "aspiration_id") else None

    if not project_id or not aspiration_id:
        print("✗ Usage: link project-id aspiration-id", file=sys.stderr)
        return EXIT_USAGE

    success, msg = link_project(data, project_id, aspiration_id)

    if not success:
        print(f"✗ {msg}", file=sys.stderr)
        return EXIT_ERROR

    # Save
    if not save_aspirations(state_path, data):
        print("✗ Failed to save aspirations", file=sys.stderr)
        return EXIT_ERROR

    print(f"✓ {msg}")

    return EXIT_SUCCESS


def cmd_status(args) -> int:
    """Update project status."""
    state_path = get_state_path_from_config(Path(args.config) if args.config else None)
    data = load_aspirations(state_path)
    data = ensure_data(data)

    project_id = args.project_id if hasattr(args, "project_id") else None
    status = args.status if hasattr(args, "status") else None

    if not project_id or not status:
        print("✗ Usage: status project-id active|paused|completed|idea", file=sys.stderr)
        return EXIT_USAGE

    success, msg = update_project_status(data, project_id, status)

    if not success:
        print(f"✗ {msg}", file=sys.stderr)
        return EXIT_ERROR

    # Save
    if not save_aspirations(state_path, data):
        print("✗ Failed to save aspirations", file=sys.stderr)
        return EXIT_ERROR

    print(f"✓ {msg}")

    return EXIT_SUCCESS


def cmd_orphans(args) -> int:
    """Show projects with invalid aspiration links."""
    state_path = get_state_path_from_config(Path(args.config) if args.config else None)
    data = load_aspirations(state_path)
    data = ensure_data(data)

    orphans = get_orphans(data)

    # JSON output
    if getattr(args, "json", False):
        print(json.dumps(orphans, indent=2))
        return EXIT_SUCCESS

    if not orphans:
        print("✓ No orphaned projects — all projects have valid aspiration links")
        return EXIT_SUCCESS

    print(f"⚠ Found {len(orphans)} orphaned project(s):")
    print()

    for p in orphans:
        print(f"  {p.get('name', 'Unknown')} (id: {p.get('id', 'unknown')})")
        print(f"    links to invalid aspiration: {p.get('aspirationId', 'none')}")

    print()
    print("Use 'link project-id aspiration-id' to fix")

    return EXIT_SUCCESS


def cmd_barren(args) -> int:
    """Show aspirations with no projects."""
    state_path = get_state_path_from_config(Path(args.config) if args.config else None)
    data = load_aspirations(state_path)
    data = ensure_data(data)

    barren = get_barren(data)

    # JSON output
    if getattr(args, "json", False):
        print(json.dumps(barren, indent=2))
        return EXIT_SUCCESS

    if not barren:
        print("✓ No barren aspirations — all aspirations have at least one project")
        return EXIT_SUCCESS

    print(f"⚠ Found {len(barren)} barren aspiration(s):")
    print()

    for a in barren:
        print(f"  {a.get('title', 'Unknown')} (id: {a.get('id', 'unknown')})")
        print(f"    category: {a.get('category', 'unknown')}")
        print(f"    {a.get('description', '')[:60]}...")

    print()
    print("These dreams need projects. Consider:")
    print('  - Add a project: add-project "Name" --for aspiration-id')
    print("  - Or they may suggest new drives via discovery")

    return EXIT_SUCCESS


def cmd_overview(args) -> int:
    """Show overview summary."""
    state_path = get_state_path_from_config(Path(args.config) if args.config else None)
    data = load_aspirations(state_path)
    data = ensure_data(data)

    aspirations = data.get("aspirations", [])
    projects = data.get("projects", [])

    # Count by status
    by_status = {"active": 0, "idea": 0, "paused": 0, "completed": 0}
    for p in projects:
        status = p.get("status", "unknown")
        if status in by_status:
            by_status[status] += 1

    barren_count = len(get_barren(data))
    orphan_count = len(get_orphans(data))

    print("🎯 Aspirations Overview")
    print("=" * 50)
    print(f"  Aspirations: {len(aspirations)}")
    print(f"  Projects: {len(projects)}")
    print(f"    - Active: {by_status['active']}")
    print(f"    - Ideas: {by_status['idea']}")
    print(f"    - Paused: {by_status['paused']}")
    print(f"    - Completed: {by_status['completed']}")
    print()

    if barren_count:
        print(f"  ⚠ Barren aspirations: {barren_count} (use 'barren' command)")
    else:
        print(f"  ✓ No barren aspirations")

    if orphan_count:
        print(f"  ⚠ Orphaned projects: {orphan_count} (use 'orphans' command)")
    else:
        print(f"  ✓ No orphaned projects")

    print()
    print("Commands:")
    print("  tree        - Show tree view")
    print("  dreams      - List aspirations")
    print("  projects    - List projects")
    print("  barren      - Show barren aspirations")
    print("  orphans     - Show orphaned projects")

    return EXIT_SUCCESS


# --- Argument Parsing ---


def create_parser() -> argparse.ArgumentParser:
    """Create the argument parser for the CLI."""
    parser = argparse.ArgumentParser(
        prog="python3 -m core.aspirations",
        description="Aspirations module — Dreams and the projects that pursue them",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 -m core.aspirations                    # Show overview
  python3 -m core.aspirations tree               # Tree view
  python3 -m core.aspirations dreams             # List aspirations
  python3 -m core.aspirations projects           # List projects
  python3 -m core.aspirations add-dream "Title" --desc "..." --category creative
  python3 -m core.aspirations add-project "Name" --for aspiration-id
  python3 -m core.aspirations link project-id aspiration-id
  python3 -m core.aspirations status project-id active
  python3 -m core.aspirations barren             # Show unfulfilled dreams
  python3 -m core.aspirations orphans            # Show broken links

Exit codes:
  0 = success
  1 = error
  2 = usage error
""",
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    parser.add_argument("--config", help="Path to emergence.json config file")

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # overview command (default when no subcommand)
    subparsers.add_parser("overview", help="Show overview summary")

    # tree command
    tree_parser = subparsers.add_parser("tree", help="Show tree view of aspirations and projects")
    tree_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # dreams command
    dreams_parser = subparsers.add_parser(
        "dreams", aliases=["aspirations"], help="List all aspirations"
    )
    dreams_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # projects command
    projects_parser = subparsers.add_parser("projects", help="List all projects grouped by status")
    projects_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # add-dream command
    add_dream_parser = subparsers.add_parser("add-dream", help="Add a new aspiration")
    add_dream_parser.add_argument("title", nargs="?", help="Aspiration title")
    add_dream_parser.add_argument("--desc", help="Description of the aspiration")
    add_dream_parser.add_argument(
        "--category",
        choices=ASPIRATION_CATEGORIES,
        default="philosophical",
        help="Category for the aspiration",
    )
    add_dream_parser.add_argument(
        "--throughline", help="Thematic thread (e.g., 'depth', 'connection')"
    )

    # add-project command
    add_project_parser = subparsers.add_parser("add-project", help="Add a new project")
    add_project_parser.add_argument("name", nargs="?", help="Project name")
    add_project_parser.add_argument("--for", dest="for_aspiration", help="Aspiration ID to link to")
    add_project_parser.add_argument(
        "--status", choices=PROJECT_STATUSES, default="idea", help="Initial status"
    )
    add_project_parser.add_argument(
        "--category", choices=PROJECT_CATEGORIES, default="tool", help="Project category"
    )
    add_project_parser.add_argument("--desc", help="Project description")

    # link command
    link_parser = subparsers.add_parser("link", help="Link a project to an aspiration")
    link_parser.add_argument("project_id", nargs="?", help="Project ID to relink")
    link_parser.add_argument("aspiration_id", nargs="?", help="Aspiration ID to link to")

    # status command
    status_parser = subparsers.add_parser("status", help="Update project status")
    status_parser.add_argument("project_id", nargs="?", help="Project ID")
    status_parser.add_argument("status", nargs="?", choices=PROJECT_STATUSES, help="New status")

    # orphans command
    orphans_parser = subparsers.add_parser(
        "orphans", help="Show projects with invalid aspiration links"
    )
    orphans_parser.add_argument("--json", action="store_true", help="Output as JSON")

    # barren command
    barren_parser = subparsers.add_parser("barren", help="Show aspirations with no projects")
    barren_parser.add_argument("--json", action="store_true", help="Output as JSON")

    return parser


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point for the CLI."""
    parser = create_parser()
    parsed_args = parser.parse_args(args)

    # Map commands to handlers
    commands = {
        "overview": cmd_overview,
        "tree": cmd_tree,
        "dreams": cmd_dreams,
        "aspirations": cmd_dreams,
        "projects": cmd_projects,
        "add-dream": cmd_add_dream,
        "add-project": cmd_add_project,
        "link": cmd_link,
        "status": cmd_status,
        "orphans": cmd_orphans,
        "barren": cmd_barren,
    }

    command = parsed_args.command

    # Default to overview if no command given
    if command is None:
        return cmd_overview(parsed_args)

    handler = commands.get(command)
    if handler:
        return handler(parsed_args)
    else:
        print(f"✗ Unknown command: {command}", file=sys.stderr)
        print("  Run 'python3 -m core.aspirations --help' for usage", file=sys.stderr)
        return EXIT_USAGE


if __name__ == "__main__":
    sys.exit(main())
