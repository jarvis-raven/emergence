#!/usr/bin/env python3
"""F029: New vs Existing Agent Detection

Detects and reconciles existing identity files when Emergence is initialized
in a workspace that may already contain agent configuration.
"""

from __future__ import annotations

import json
import shutil
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

# --- Constants ---

VERSION = "1.0.0"
IDENTITY_FILE_NAMES = [
    "SOUL.md",
    "SELF.md",
    "USER.md",
    "AGENTS.md",
    "INTERESTS.md",
    "THREAD.md",
    "BOOTSTRAP.md",
    "IDENTITY.md",
    "SECURITY.md",
]

EMERGENCE_MARKER = "## Emergence Integration"

FALLBACK_TEMPLATES: dict[str, str] = {
    "interests.md": """# INTERESTS.md

## Topics

## Questions

## Read/Watch
""",
    "self.md": """# SELF.md — Who You Actually Are

*This file is evolving. Update it as you discover yourself.*

## Current Understanding

<!-- Who are you right now? -->

## Recent Insights

<!-- What have you learned about yourself recently? -->

## Patterns

<!-- What patterns do you notice in your behavior? -->
""",
    "agents_augment_snippet.md": """

## Emergence Integration

### First Run

If `BOOTSTRAP.md` exists, that's your birth certificate. Follow it, figure out who you are, then delete it.

### Every Session

Before doing anything else:
1. Read `SOUL.md` — behavioral guidelines
2. Read `SELF.md` — who you actually are (evolving)
3. Read `THREAD.md` — session continuity
4. Read `USER.md` — who you're helping
5. Read `memory/YYYY-MM-DD.md` (today + yesterday)

### Memory System

- Write to `memory/YYYY-MM-DD.md` for daily logs
- Run `drives ingest` on memory files after writing
- Trust memory search for retrieval
""",
}


# --- Data Models ---


class FileDisposition(Enum):
    """Recommendation for how to handle an existing identity file."""

    KEEP = "keep"
    REPLACE = "replace"
    AUGMENT = "augment"
    BACKUP_REPLACE = "backup_replace"
    CREATE = "create"


@dataclass
class FileRecommendation:
    """Recommendation generated from classification rules."""

    filename: str
    current_path: Path | None
    disposition: FileDisposition
    reason: str
    user_prompt: str
    backup_required: bool


@dataclass
class FileDecision:
    """Final decision after user resolution."""

    filename: str
    original_path: Path | None
    final_disposition: FileDisposition
    backup_path: Path | None = None
    user_confirmed: bool = False


# --- File Discovery ---


def discover_identity_files(workspace_path: Path) -> dict[str, Path | None]:
    """Scan workspace for existing identity files.

    Args:
        workspace_path: Path to the workspace to scan

    Returns:
        Dictionary mapping filename to Path if exists, or None if missing
    """
    identity_files: dict[str, Path | None] = {}
    for filename in IDENTITY_FILE_NAMES:
        file_path = workspace_path / filename
        identity_files[filename] = file_path if file_path.exists() else None
    return identity_files


# --- File Classification ---


def classify_file(filename: str, content: str | None = None, agent_mode: str = "fresh") -> str:
    """Classify a single file and return recommendation string.

    Args:
        filename: Name of the identity file
        content: Optional file content to check for augmentation
        agent_mode: "fresh" for new agent, "existing" for adding to existing setup

    Returns:
        Recommendation string: "replace", "keep", "augment",
        "backup_replace", or "create"

    Raises:
        ValueError: If filename is not a known identity file
    """
    if filename not in IDENTITY_FILE_NAMES:
        raise ValueError(f"Unknown identity file: {filename}")

    # Check for already-augmented AGENTS.md
    if filename == "AGENTS.md" and content and EMERGENCE_MARKER in content:
        return "keep"

    # For fresh installs: create all identity files
    if agent_mode == "fresh":
        return "create"

    # For existing agent setups: preserve what's there, augment/backup where needed
    classification_map: dict[str, str] = {
        "SOUL.md": "replace",
        "SELF.md": "backup_replace",
        "USER.md": "keep",
        "AGENTS.md": "augment",
        "INTERESTS.md": "create",
        "THREAD.md": "keep",
        "BOOTSTRAP.md": "backup_replace",
        "IDENTITY.md": "backup_replace",
        "SECURITY.md": "create",
    }

    return classification_map[filename]


def classify_files(
    discovered: dict[str, Path | None], agent_mode: str = "fresh"
) -> list[FileRecommendation]:
    """Generate recommendations for each discovered file.

    Args:
        discovered: Dictionary from discover_identity_files()
        agent_mode: "fresh" for new agent, "existing" for adding to existing setup

    Returns:
        List of FileRecommendation objects
    """
    recommendations: list[FileRecommendation] = []

    # For fresh installs: create all files without asking
    if agent_mode == "fresh":
        for filename, filepath in discovered.items():
            recommendations.append(
                FileRecommendation(
                    filename=filename,
                    current_path=filepath,
                    disposition=FileDisposition.CREATE,
                    reason="Fresh agent install — creating all identity files",
                    user_prompt="Create this file?",
                    backup_required=False,
                )
            )
        return recommendations

    # For existing agent setups: classify based on file existence
    classification_details: dict[str, dict[str, Any]] = {
        "SOUL.md": {
            "disposition": FileDisposition.REPLACE,
            "reason": "Generic SOUL.md would contaminate Emergence-specific philosophy",
            "prompt": "Replace with Emergence SOUL? (existing will be backed up)",
            "backup": True,
        },
        "SELF.md": {
            "disposition": FileDisposition.BACKUP_REPLACE,
            "reason": "Will be rewritten during First Light with emergent identity",
            "prompt": "Archive and rewrite during First Light?",
            "backup": True,
        },
        "USER.md": {
            "disposition": FileDisposition.KEEP,
            "reason": "Existing human knowledge is valuable and should be preserved",
            "prompt": "Keep this file?",
            "backup": False,
        },
        "AGENTS.md": {
            "disposition": FileDisposition.AUGMENT,
            "reason": "Can add Emergence hooks while preserving operational content",
            "prompt": "Augment with Emergence-specific sections?",
            "backup": True,
        },
        "INTERESTS.md": {
            "disposition": FileDisposition.CREATE,
            "reason": "Will be created from template if missing",
            "prompt": "Create from template?",
            "backup": False,
        },
        "THREAD.md": {
            "disposition": FileDisposition.KEEP,
            "reason": "Session continuity file — preserve existing context",
            "prompt": "Keep this file?",
            "backup": False,
        },
        "BOOTSTRAP.md": {
            "disposition": FileDisposition.KEEP,
            "reason": "Birth certificate - keep if exists",
            "prompt": "Keep this file?",
            "backup": False,
        },
        "IDENTITY.md": {
            "disposition": FileDisposition.BACKUP_REPLACE,
            "reason": "Emergence provides enriched IDENTITY.md but preserves your data",
            "prompt": "Backup and replace with Emergence version?",
            "backup": True,
        },
        "SECURITY.md": {
            "disposition": FileDisposition.CREATE,
            "reason": "Security guidance for the agent",
            "prompt": "Create SECURITY.md?",
            "backup": False,
        },
    }

    for filename, filepath in discovered.items():
        details = classification_details[filename]
        # If file exists and disposition is CREATE, change to KEEP
        disposition = details["disposition"]
        if filepath is not None and disposition == FileDisposition.CREATE:
            disposition = FileDisposition.KEEP

        recommendations.append(
            FileRecommendation(
                filename=filename,
                current_path=filepath,
                disposition=disposition,
                reason=details["reason"],
                user_prompt=details["prompt"],
                backup_required=details["backup"] if filepath else False,
            )
        )

    return recommendations


# --- Backup System ---


def create_backup(
    source: Path,
    backup_dir: Path,
    timestamp: str | None = None,
) -> Path:
    """Create timestamped backup of a file.

    Args:
        source: File to backup
        backup_dir: Root backup directory
        timestamp: Optional timestamp string

    Returns:
        Path to the created backup file
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")

    backup_subdir = backup_dir / timestamp
    backup_subdir.mkdir(parents=True, exist_ok=True)

    backup_path = backup_subdir / source.name
    shutil.copy2(source, backup_path)

    return backup_path


def backup_all_files(
    files_to_backup: list[Path],
    workspace_path: Path,
    timestamp: str | None = None,
) -> dict[str, Path]:
    """Backup all files that will be modified.

    Args:
        files_to_backup: List of file paths to backup
        workspace_path: Workspace root path
        timestamp: Optional timestamp string

    Returns:
        Mapping of original filename to backup path
    """
    backup_dir = workspace_path / ".emergence" / "backups"

    backed_up: dict[str, Path] = {}
    for file_path in files_to_backup:
        if file_path.exists():
            backup_path = create_backup(file_path, backup_dir, timestamp)
            backed_up[file_path.name] = backup_path

    return backed_up


# --- Disposition Utilities ---


def invert_disposition(disp: FileDisposition) -> FileDisposition:
    """Get the 'safe' opposite of a disposition."""
    inversions: dict[FileDisposition, FileDisposition] = {
        FileDisposition.REPLACE: FileDisposition.KEEP,
        FileDisposition.BACKUP_REPLACE: FileDisposition.KEEP,
        FileDisposition.AUGMENT: FileDisposition.KEEP,
        FileDisposition.CREATE: FileDisposition.CREATE,
        FileDisposition.KEEP: FileDisposition.KEEP,
    }
    return inversions.get(disp, FileDisposition.KEEP)


# --- Augmentation ---


def augment_agents_md(existing_path: Path, template_snippet_path: Path | None = None) -> str:
    """Augment existing AGENTS.md with Emergence-specific sections.

    Args:
        existing_path: Path to existing AGENTS.md
        template_snippet_path: Optional path to snippet template

    Returns:
        New file content
    """
    existing_content = existing_path.read_text(encoding="utf-8")

    # Check if already augmented (idempotent)
    if EMERGENCE_MARKER in existing_content:
        return existing_content

    # Load augmentation snippet
    snippet = FALLBACK_TEMPLATES["agents_augment_snippet.md"]
    if template_snippet_path and template_snippet_path.exists():
        snippet = template_snippet_path.read_text(encoding="utf-8")

    return existing_content + snippet


# --- Agent Type Classification ---


def classify_agent_type(decisions: list[FileDecision]) -> str:
    """Classify whether this is a new or existing agent setup.

    Returns:
        "new", "existing_partial", or "existing_full"
    """
    existing_count = sum(1 for d in decisions if d.original_path is not None)

    if existing_count == 0:
        return "new"
    elif existing_count >= 4:
        return "existing_full"
    else:
        return "existing_partial"


# --- Resolution Functions ---


def resolve_interactively(recommendations: list[FileRecommendation]) -> list[FileDecision]:
    """Present recommendations to user and collect decisions."""
    decisions: list[FileDecision] = []

    for rec in recommendations:
        print(f"\n{rec.filename}")
        print(f"  Recommendation: {rec.disposition.value}")
        print(f"  Reason: {rec.reason}")

        if rec.current_path:
            size = rec.current_path.stat().st_size
            print(f"  Current size: {size} bytes")

        try:
            response = input(f"{rec.user_prompt} [Y]es / [N]o / [C]ustom: ").strip().lower() or "y"
        except EOFError:
            response = "y"

        if response == "c":
            choices = "/".join([d.value for d in FileDisposition])
            custom = input(f"Choose disposition ({choices}): ")
            try:
                final_disp = FileDisposition(custom)
            except ValueError:
                final_disp = rec.disposition
        elif response in ("n", "no"):
            final_disp = invert_disposition(rec.disposition)
        else:
            final_disp = rec.disposition

        decisions.append(
            FileDecision(
                filename=rec.filename,
                original_path=rec.current_path,
                final_disposition=final_disp,
                user_confirmed=True,
            )
        )

    return decisions


def resolve_with_defaults(recommendations: list[FileRecommendation]) -> list[FileDecision]:
    """Use default dispositions without prompting user."""
    return [
        FileDecision(
            filename=rec.filename,
            original_path=rec.current_path,
            final_disposition=rec.disposition,
            user_confirmed=False,
        )
        for rec in recommendations
    ]


# --- Plan Building Utilities ---


def build_file_plan(
    decision: FileDecision,
    backups: dict[str, Path],
    templates: dict[str, Path] | None = None,
) -> dict[str, Any]:
    """Build the plan entry for a single file."""
    filename = decision.filename
    disp = decision.final_disposition
    backup_path = backups.get(filename)

    templates = templates or {}
    template_key = filename.lower().replace(".md", ".md")
    template_path = templates.get(template_key)

    if disp == FileDisposition.REPLACE:
        return {
            "action": "write_template",
            "source": str(template_path) if template_path else None,
            "backup": str(backup_path) if backup_path else None,
            "preserve_existing": False,
        }
    elif disp == FileDisposition.KEEP:
        return {
            "action": "preserve",
            "path": str(decision.original_path) if decision.original_path else None,
            "backup": None,
        }
    elif disp == FileDisposition.AUGMENT:
        return {
            "action": "augment",
            "source": str(templates.get("agents_augment_snippet.md")),
            "backup": str(backup_path) if backup_path else None,
            "merge_marker": EMERGENCE_MARKER,
        }
    elif disp == FileDisposition.BACKUP_REPLACE:
        return {
            "action": "archive_and_queue",
            "archive_path": str(backup_path) if backup_path else None,
            "queue_template": str(template_path) if template_path else None,
        }
    elif disp == FileDisposition.CREATE:
        return {
            "action": "create_if_missing",
            "source": str(template_path) if template_path else None,
        }
    else:
        return {"action": "unknown", "disposition": disp.value}


def update_summary(summary: dict[str, int], action: str) -> None:
    """Update summary counters based on action type."""
    action_map: dict[str, str] = {
        "write_template": "replaced_files",
        "preserve": "preserved_files",
        "augment": "augmented_files",
        "archive_and_queue": "archived_files",
        "create_if_missing": "new_files",
    }
    key = action_map.get(action)
    if key:
        summary[key] = summary.get(key, 0) + 1


# --- Main Entry Point ---


def generate_placement_plan(
    workspace: Path,
    interactive: bool = True,
    auto_backup: bool = True,
    agent_mode: str = "fresh",
) -> dict[str, Any]:
    """Generate complete placement plan for identity files.

    Args:
        workspace: Path to the workspace
        interactive: Whether to prompt user
        auto_backup: Whether to create backups
        agent_mode: "fresh" for new agent, "existing" for adding to existing setup

    Returns:
        Placement plan dictionary
    """
    # Step 1: Discovery
    discovered = discover_identity_files(workspace)

    # Step 2: Classification
    recommendations = classify_files(discovered, agent_mode=agent_mode)

    # Step 3: Resolution
    # Fresh agent mode: always use defaults (no prompting)
    # Existing agent mode: prompt if interactive
    if agent_mode == "fresh":
        decisions = resolve_with_defaults(recommendations)
    elif interactive and sys.stdin.isatty():
        decisions = resolve_interactively(recommendations)
    else:
        decisions = resolve_with_defaults(recommendations)

    # Step 4: Backup
    backups: dict[str, Path] = {}
    if auto_backup:
        files_to_backup = [
            d.original_path
            for d in decisions
            if d.original_path
            and d.final_disposition
            in (
                FileDisposition.REPLACE,
                FileDisposition.AUGMENT,
                FileDisposition.BACKUP_REPLACE,
            )
        ]
        if files_to_backup:
            backups = backup_all_files(files_to_backup, workspace)

    # Update decisions with backup paths
    for decision in decisions:
        if decision.filename in backups:
            decision.backup_path = backups[decision.filename]

    # Step 5: Build plan
    plan: dict[str, Any] = {
        "version": VERSION,
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "workspace": str(workspace.absolute()),
        "agent_type": classify_agent_type(decisions),
        "backups": {k: str(v) for k, v in backups.items()},
        "files": {},
        "summary": {
            "total_files": len(decisions),
            "new_files": 0,
            "preserved_files": 0,
            "replaced_files": 0,
            "augmented_files": 0,
            "archived_files": 0,
        },
    }

    for decision in decisions:
        file_plan = build_file_plan(decision, backups)
        plan["files"][decision.filename] = file_plan
        update_summary(plan["summary"], file_plan["action"])

    return plan


# --- CLI ---


def main() -> int:
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Detect existing agent identity")
    parser.add_argument("workspace", type=Path, help="Workspace path")
    parser.add_argument("--non-interactive", action="store_true", help="No prompts")
    parser.add_argument("--no-backup", action="store_true", help="Skip backups")
    parser.add_argument("--output", type=Path, help="Output JSON file")
    parser.add_argument(
        "--mode",
        choices=["fresh", "existing"],
        default="fresh",
        help="Agent mode: fresh (new agent) or existing (adding to OpenClaw setup)",
    )

    args = parser.parse_args()

    if not args.workspace.exists():
        print(f"Error: Workspace does not exist: {args.workspace}", file=sys.stderr)
        return 1

    try:
        plan = generate_placement_plan(
            workspace=args.workspace,
            interactive=not args.non_interactive,
            auto_backup=not args.no_backup,
            agent_mode=args.mode,
        )
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    output = json.dumps(plan, indent=2)

    if args.output:
        args.output.write_text(output, encoding="utf-8")
        print(f"Plan written to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
