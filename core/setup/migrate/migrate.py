#!/usr/bin/env python3
"""Emergence Migration — safely move an agent between machines.

Handles export/import of agent bundles with critical path rewriting
to prevent the hardcoded-path bug that broke Aurora's sessions.json.

Usage:
    emergence migrate export [--workspace /path/to/agent] [--output bundle.tar.gz]
    emergence migrate import <bundle.tar.gz> [--workspace /path/to/new/home]
    emergence migrate rewrite-paths --old /home/dan --new /home/aurora [--workspace .]
    emergence migrate validate [--workspace .]
"""

import argparse
import json
import os
import re
import shutil
import sqlite3
import sys
import tarfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

# Files that are part of agent identity/config and should be bundled
IDENTITY_FILES = [
    "SOUL.md",
    "SELF.md",
    "MEMORY.md",
    "USER.md",
    "TOOLS.md",
    "AGENTS.md",
    "ASPIRATIONS.md",
    "INTERESTS.md",
    "DRIVES.md",
    "HEARTBEAT.md",
    "BOOTSTRAP.md",
]

CONFIG_FILES = [
    "emergence.json",
]

STATE_FILES = [
    "drives.json",
    "drives-state.json",
    "drives-history.json",
    "aspirations.json",
]

# Directories to include in bundle
BUNDLE_DIRS = [
    "memory",
    ".emergence",
]

# File extensions that may contain absolute paths needing rewriting
TEXT_EXTENSIONS = {
    ".json",
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
    ".ini",
    ".sh",
    ".bash",
    ".zsh",
    ".conf",
    ".log",
}

# Files that should NEVER be modified
SKIP_FILES = {".git", "__pycache__", "node_modules", ".venv", "venv"}


def _is_text_file(path: Path) -> bool:
    """Check if a file is likely a text file we should scan."""
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    # Check for no extension but common text files
    if path.suffix == "" and path.name in IDENTITY_FILES:
        return True
    return False


def _should_skip(path: Path) -> bool:
    """Check if path should be skipped during scanning."""
    parts = set(path.parts)
    return bool(parts & SKIP_FILES)


def scan_for_paths(
    workspace: Path,
    old_path: str,
    *,
    include_binary: bool = False,
) -> List[Tuple[Path, int, str]]:
    """Scan all files in workspace for occurrences of old_path.

    Returns list of (file_path, line_number, line_content) tuples.
    Line number is 0 for binary/non-line-based matches.
    """
    matches: List[Tuple[Path, int, str]] = []
    old_path_normalized = old_path.rstrip("/")

    for root, dirs, files in os.walk(workspace):
        # Filter out skip dirs in-place
        dirs[:] = [d for d in dirs if d not in SKIP_FILES]

        for fname in files:
            fpath = Path(root) / fname
            if _should_skip(fpath):
                continue

            if _is_text_file(fpath):
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                    for i, line in enumerate(content.splitlines(), 1):
                        if old_path_normalized in line:
                            matches.append((fpath, i, line.strip()))
                except (OSError, UnicodeDecodeError):
                    continue

            elif include_binary and fpath.suffix == ".db":
                # Check SQLite databases
                try:
                    conn = sqlite3.connect(str(fpath))
                    cursor = conn.cursor()
                    # Get all tables
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    for (table,) in cursor.fetchall():
                        cursor.execute(f"SELECT * FROM [{table}]")
                        for row in cursor:
                            row_str = str(row)
                            if old_path_normalized in row_str:
                                matches.append((fpath, 0, f"table={table}: {row_str[:200]}"))
                    conn.close()
                except (sqlite3.Error, OSError):
                    continue

    return matches


def rewrite_openclaw_state(
    openclaw_root: Path,
    old_path: str,
    new_path: str,
    *,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Rewrite hardcoded paths inside OpenClaw state files.

    Targets sessions.json files under ~/.openclaw/agents/*/sessions/
    which store absolute paths that break after migration.  This is the
    exact bug that broke Aurora's communication after her first migration.

    Args:
        openclaw_root: Root of the OpenClaw state directory (e.g. ~/.openclaw)
        old_path: Old absolute path prefix to replace
        new_path: New absolute path prefix
        dry_run: If True, report changes without writing

    Returns:
        Dict with rewrite stats matching the rewrite_paths format.
    """
    old_normalized = old_path.rstrip("/")
    new_normalized = new_path.rstrip("/")

    stats: Dict[str, Any] = {
        "files_scanned": 0,
        "files_modified": 0,
        "replacements": 0,
        "modified_files": [],
        "errors": [],
        "dry_run": dry_run,
    }

    openclaw_root = openclaw_root.resolve()
    if not openclaw_root.is_dir():
        stats["errors"].append(f"OpenClaw root not found: {openclaw_root}")
        return stats

    # Scan agents/*/sessions/sessions.json and any other text files
    agents_dir = openclaw_root / "agents"
    if not agents_dir.is_dir():
        return stats

    # Collect all text files under the openclaw root that may contain paths
    target_patterns = [
        agents_dir.glob("*/sessions/sessions.json"),
        agents_dir.glob("*/sessions/*.json"),
        openclaw_root.glob("*.json"),
        openclaw_root.glob("config/*.json"),
        openclaw_root.glob("state/*.json"),
    ]

    seen: Set[Path] = set()
    for pattern in target_patterns:
        for fpath in pattern:
            if fpath in seen or not fpath.is_file():
                continue
            seen.add(fpath)
            stats["files_scanned"] += 1
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                if old_normalized not in content:
                    continue
                count = content.count(old_normalized)
                new_content = content.replace(old_normalized, new_normalized)
                if not dry_run:
                    fpath.write_text(new_content, encoding="utf-8")
                stats["files_modified"] += 1
                stats["replacements"] += count
                stats["modified_files"].append(
                    {
                        "path": str(fpath),
                        "replacements": count,
                    }
                )
            except (OSError, UnicodeDecodeError) as e:
                stats["errors"].append(f"{fpath}: {e}")

    return stats


def rewrite_paths(
    workspace: Path,
    old_path: str,
    new_path: str,
    *,
    dry_run: bool = False,
    include_sqlite: bool = True,
    openclaw_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Rewrite all occurrences of old_path to new_path in workspace files.

    This is the critical function that prevents the Aurora sessions.json bug.

    Args:
        workspace: Root directory to scan
        old_path: Old absolute path prefix (e.g., /home/dan)
        new_path: New absolute path prefix (e.g., /home/aurora)
        dry_run: If True, report changes without making them
        include_sqlite: If True, also rewrite paths in SQLite databases
        openclaw_root: If provided, also rewrite paths in OpenClaw state dir

    Returns:
        Dict with stats: files_scanned, files_modified, replacements, errors
    """
    old_normalized = old_path.rstrip("/")
    new_normalized = new_path.rstrip("/")

    stats: Dict[str, Any] = {
        "files_scanned": 0,
        "files_modified": 0,
        "replacements": 0,
        "modified_files": [],
        "errors": [],
        "dry_run": dry_run,
    }

    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in SKIP_FILES]

        for fname in files:
            fpath = Path(root) / fname
            if _should_skip(fpath):
                continue

            # Text files
            if _is_text_file(fpath):
                stats["files_scanned"] += 1
                try:
                    content = fpath.read_text(encoding="utf-8", errors="replace")
                    if old_normalized not in content:
                        continue

                    count = content.count(old_normalized)
                    new_content = content.replace(old_normalized, new_normalized)

                    if not dry_run:
                        fpath.write_text(new_content, encoding="utf-8")

                    stats["files_modified"] += 1
                    stats["replacements"] += count
                    stats["modified_files"].append(
                        {
                            "path": str(fpath.relative_to(workspace)),
                            "replacements": count,
                        }
                    )
                except (OSError, UnicodeDecodeError) as e:
                    stats["errors"].append(f"{fpath}: {e}")

            # SQLite databases
            elif include_sqlite and fpath.suffix == ".db":
                stats["files_scanned"] += 1
                try:
                    conn = sqlite3.connect(str(fpath))
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cursor.fetchall()]

                    db_modified = False
                    db_count = 0

                    for table in tables:
                        # Get column info
                        cursor.execute(f"PRAGMA table_info([{table}])")
                        columns = cursor.fetchall()
                        text_cols = [
                            col[1]
                            for col in columns
                            if col[2].upper() in ("TEXT", "VARCHAR", "BLOB")
                        ]

                        for col in text_cols:
                            cursor.execute(
                                f"SELECT rowid, [{col}] FROM [{table}] " f"WHERE [{col}] LIKE ?",
                                (f"%{old_normalized}%",),
                            )
                            rows = cursor.fetchall()
                            for rowid, value in rows:
                                if isinstance(value, str) and old_normalized in value:
                                    new_value = value.replace(old_normalized, new_normalized)
                                    count = value.count(old_normalized)
                                    if not dry_run:
                                        cursor.execute(
                                            f"UPDATE [{table}] SET [{col}] = ? " f"WHERE rowid = ?",
                                            (new_value, rowid),
                                        )
                                    db_modified = True
                                    db_count += count

                    if db_modified:
                        if not dry_run:
                            conn.commit()
                        stats["files_modified"] += 1
                        stats["replacements"] += db_count
                        stats["modified_files"].append(
                            {
                                "path": str(fpath.relative_to(workspace)),
                                "replacements": db_count,
                                "type": "sqlite",
                            }
                        )
                    conn.close()
                except (sqlite3.Error, OSError) as e:
                    stats["errors"].append(f"{fpath}: {e}")

    # Also rewrite paths in OpenClaw state directory if specified
    if openclaw_root is not None:
        oc_stats = rewrite_openclaw_state(
            openclaw_root,
            old_path,
            new_path,
            dry_run=dry_run,
        )
        stats["files_scanned"] += oc_stats["files_scanned"]
        stats["files_modified"] += oc_stats["files_modified"]
        stats["replacements"] += oc_stats["replacements"]
        stats["modified_files"].extend(oc_stats["modified_files"])
        stats["errors"].extend(oc_stats["errors"])
        stats["openclaw_stats"] = oc_stats

    return stats


def export_bundle(
    workspace: Path,
    output: Optional[Path] = None,
) -> Path:
    """Create a migration bundle from an agent workspace.

    Args:
        workspace: Path to the agent's workspace root
        output: Output path for the tar.gz bundle (auto-generated if None)

    Returns:
        Path to the created bundle file

    Raises:
        FileNotFoundError: If workspace doesn't exist
        ValueError: If workspace doesn't look like an Emergence workspace
    """
    workspace = workspace.resolve()

    if not workspace.is_dir():
        raise FileNotFoundError(f"Workspace not found: {workspace}")

    # Validate it's an emergence workspace
    config_path = workspace / "emergence.json"
    if not config_path.exists():
        # Check for identity files as fallback
        has_identity = any((workspace / f).exists() for f in IDENTITY_FILES[:3])
        if not has_identity:
            raise ValueError(
                f"Not an Emergence workspace: {workspace}\n"
                "Expected emergence.json or identity files (SOUL.md, SELF.md)"
            )

    # Generate output filename
    if output is None:
        agent_name = "agent"
        if config_path.exists():
            try:
                cfg = json.loads(config_path.read_text())
                agent_name = cfg.get("agent", {}).get("name", "agent")
                agent_name = re.sub(r"[^a-zA-Z0-9_-]", "_", agent_name).lower()
            except (json.JSONDecodeError, OSError):
                pass
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        output = Path(f"emergence-{agent_name}-{timestamp}.tar.gz")

    output = output.resolve()

    # Build file list
    files_to_bundle: List[Path] = []

    # Add identity files
    for fname in IDENTITY_FILES:
        fpath = workspace / fname
        if fpath.exists():
            files_to_bundle.append(fpath)

    # Add config files
    for fname in CONFIG_FILES:
        fpath = workspace / fname
        if fpath.exists():
            files_to_bundle.append(fpath)

    # Add state directory files
    state_dir = workspace / ".emergence" / "state"
    if state_dir.is_dir():
        for fname in STATE_FILES:
            fpath = state_dir / fname
            if fpath.exists():
                files_to_bundle.append(fpath)
        # Also grab any .db files
        for db in state_dir.glob("*.db"):
            files_to_bundle.append(db)

    # Also check workspace root for state files (some setups)
    for fname in STATE_FILES:
        fpath = workspace / fname
        if fpath.exists() and fpath not in files_to_bundle:
            files_to_bundle.append(fpath)

    # Add directories recursively
    for dirname in BUNDLE_DIRS:
        dirpath = workspace / dirname
        if dirpath.is_dir():
            for root, dirs, files in os.walk(dirpath):
                dirs[:] = [d for d in dirs if d not in SKIP_FILES]
                for fname in files:
                    fpath = Path(root) / fname
                    if fpath not in files_to_bundle:
                        files_to_bundle.append(fpath)

    if not files_to_bundle:
        raise ValueError("No files found to bundle. Is this an Emergence workspace?")

    # Create the bundle
    # Include a manifest with both absolute and relative paths for robustness.
    # The relative openclaw_root_rel lets import reconstruct the OpenClaw location
    # even when the new machine has a different home directory structure.
    home = Path.home()
    openclaw_default = home / ".openclaw"

    # Capture relative path of OpenClaw root from workspace perspective
    try:
        openclaw_root_rel = str(os.path.relpath(openclaw_default, workspace))
    except ValueError:
        # On Windows, relpath fails across drives
        openclaw_root_rel = None

    # Capture relative path of workspace from home
    try:
        workspace_rel_home = str(os.path.relpath(workspace, home))
    except ValueError:
        workspace_rel_home = None

    manifest = {
        "version": "1.1",
        "created": datetime.now(timezone.utc).isoformat(),
        "source_workspace": str(workspace),
        "source_home": str(home),
        "workspace_rel_home": workspace_rel_home,
        "openclaw_root": str(openclaw_default),
        "openclaw_root_rel": openclaw_root_rel,
        "file_count": len(files_to_bundle),
        "files": [str(f.relative_to(workspace)) for f in files_to_bundle],
    }

    with tarfile.open(str(output), "w:gz") as tar:
        # Write manifest
        manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")
        import io

        manifest_info = tarfile.TarInfo(name="__manifest__.json")
        manifest_info.size = len(manifest_bytes)
        tar.addfile(manifest_info, io.BytesIO(manifest_bytes))

        # Add all files
        for fpath in files_to_bundle:
            arcname = str(fpath.relative_to(workspace))
            tar.add(str(fpath), arcname=arcname)

    return output


def import_bundle(
    bundle_path: Path,
    workspace: Path,
    *,
    old_home: Optional[str] = None,
    new_home: Optional[str] = None,
    openclaw_root: Optional[Path] = None,
    backup: bool = True,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Import a migration bundle into a workspace with path rewriting.

    Args:
        bundle_path: Path to the .tar.gz bundle
        workspace: Destination workspace directory
        old_home: Old home directory to replace (auto-detected from manifest)
        new_home: New home directory (defaults to current $HOME)
        openclaw_root: OpenClaw state directory to also rewrite (default: ~/.openclaw)
        backup: Create backup of existing workspace before import
        dry_run: Preview changes without applying

    Returns:
        Dict with import stats and rewrite info
    """
    bundle_path = bundle_path.resolve()
    workspace = workspace.resolve()

    if not bundle_path.exists():
        raise FileNotFoundError(f"Bundle not found: {bundle_path}")

    result: Dict[str, Any] = {
        "files_extracted": 0,
        "backup_path": None,
        "rewrite_stats": None,
        "warnings": [],
    }

    # Create workspace if needed
    if not dry_run:
        workspace.mkdir(parents=True, exist_ok=True)

    # Backup existing workspace
    if backup and workspace.exists() and any(workspace.iterdir()):
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
        backup_path = workspace.parent / f"{workspace.name}.backup-{timestamp}"
        if not dry_run:
            shutil.copytree(workspace, backup_path)
        result["backup_path"] = str(backup_path)

    # Extract bundle
    with tarfile.open(str(bundle_path), "r:gz") as tar:
        # Read manifest first
        try:
            manifest_member = tar.getmember("__manifest__.json")
            f = tar.extractfile(manifest_member)
            manifest = json.loads(f.read()) if f else {}
        except (KeyError, json.JSONDecodeError):
            manifest = {}
            result["warnings"].append("No manifest found in bundle")

        # Security: check for path traversal
        for member in tar.getmembers():
            if member.name.startswith("/") or ".." in member.name:
                raise ValueError(f"Unsafe path in bundle: {member.name}")

        # Extract all files except manifest
        members = [m for m in tar.getmembers() if m.name != "__manifest__.json"]
        if not dry_run:
            tar.extractall(path=str(workspace), members=members)
        result["files_extracted"] = len(members)

    # Determine paths for rewriting
    if old_home is None:
        old_home = manifest.get("source_home")
        if not old_home:
            # Try to detect from source_workspace
            src = manifest.get("source_workspace", "")
            if src:
                # Guess home as the first 3 path components (e.g. /home/user)
                parts = Path(src).parts
                if len(parts) >= 3:
                    old_home = str(Path(*parts[:3]))

    if new_home is None:
        new_home = str(Path.home())

    # Resolve OpenClaw root — use manifest's relative path if available
    if openclaw_root is None:
        oc_rel = manifest.get("openclaw_root_rel")
        if oc_rel and new_home:
            # Re-evaluate relative path against new home
            openclaw_root = Path(new_home) / ".openclaw"
        else:
            openclaw_root = Path.home() / ".openclaw"

    # Rewrite paths if we have both old and new
    if old_home and new_home and old_home != new_home:
        if not dry_run:
            rewrite_stats = rewrite_paths(
                workspace,
                old_home,
                new_home,
                openclaw_root=openclaw_root,
            )
        else:
            rewrite_stats = rewrite_paths(
                workspace,
                old_home,
                new_home,
                dry_run=True,
                openclaw_root=openclaw_root,
            )
        result["rewrite_stats"] = rewrite_stats
    elif old_home == new_home:
        result["warnings"].append(
            f"Old and new home are identical ({old_home}), skipping path rewrite"
        )

    return result


def validate_workspace(workspace: Path) -> Dict[str, Any]:
    """Validate that a workspace is healthy after migration.

    Checks:
    - Required files exist
    - emergence.json is valid JSON
    - No remaining references to common old paths
    - State files are valid
    - Directories are writable

    Returns:
        Dict with validation results
    """
    workspace = workspace.resolve()
    results: Dict[str, Any] = {
        "valid": True,
        "checks": [],
        "warnings": [],
        "errors": [],
    }

    def check(name: str, passed: bool, detail: str = ""):
        results["checks"].append({"name": name, "passed": passed, "detail": detail})
        if not passed:
            results["valid"] = False
            results["errors"].append(f"{name}: {detail}")

    def warn(name: str, detail: str):
        results["warnings"].append(f"{name}: {detail}")

    # Check workspace exists
    check("workspace_exists", workspace.is_dir(), str(workspace))

    if not workspace.is_dir():
        return results

    # Check writable
    check("workspace_writable", os.access(workspace, os.W_OK), str(workspace))

    # Check emergence.json
    config_path = workspace / "emergence.json"
    if config_path.exists():
        try:
            content = config_path.read_text()
            # Strip comments before parsing
            lines = []
            for line in content.splitlines():
                stripped = line.lstrip()
                if stripped.startswith("//") or stripped.startswith("#"):
                    continue
                # Remove inline comments (naive but handles most cases)
                if "//" in line:
                    in_string = False
                    for i, c in enumerate(line):
                        if c == '"' and (i == 0 or line[i - 1] != "\\"):
                            in_string = not in_string
                        if not in_string and line[i : i + 2] == "//":
                            line = line[:i]
                            break
                lines.append(line)
            cfg = json.loads("\n".join(lines))
            check("config_valid_json", True, "emergence.json parses correctly")

            # Check paths in config point to real dirs
            paths = cfg.get("paths", {})
            ws_path = paths.get("workspace", ".")
            if os.path.isabs(ws_path):
                exists = Path(ws_path).is_dir()
                check("config_workspace_path", exists, ws_path)
            state_path = paths.get("state", ".emergence/state")
            if os.path.isabs(state_path):
                exists = Path(state_path).is_dir()
                check("config_state_path", exists, state_path)

        except (json.JSONDecodeError, OSError) as e:
            check("config_valid_json", False, str(e))
    else:
        warn("config_exists", "emergence.json not found (may be OK for some setups)")

    # Check identity files
    found_identity = False
    for fname in IDENTITY_FILES[:3]:  # SOUL, SELF, MEMORY
        if (workspace / fname).exists():
            found_identity = True
            break
    check("identity_files", found_identity, "At least one of SOUL.md/SELF.md/MEMORY.md")

    # Check memory directory
    mem_dir = workspace / "memory"
    if mem_dir.is_dir():
        check("memory_dir_writable", os.access(mem_dir, os.W_OK))
    else:
        warn("memory_dir", "memory/ directory not found")

    # Scan for suspicious absolute paths (common /home patterns)
    suspicious_homes = set()
    for root, dirs, files in os.walk(workspace):
        dirs[:] = [d for d in dirs if d not in SKIP_FILES]
        for fname in files:
            fpath = Path(root) / fname
            if not _is_text_file(fpath):
                continue
            try:
                content = fpath.read_text(encoding="utf-8", errors="replace")
                # Find /home/<user>/ patterns that don't match current home
                home_pattern = re.findall(r"/home/\w+", content)
                for match in home_pattern:
                    if match != str(Path.home()) and match not in suspicious_homes:
                        suspicious_homes.add(match)
                        warn(
                            "suspicious_path",
                            f"Found '{match}' in {fpath.relative_to(workspace)} "
                            f"(current home is {Path.home()})",
                        )
            except (OSError, UnicodeDecodeError):
                continue

    # Check state files are valid JSON
    state_dir = workspace / ".emergence" / "state"
    if state_dir.is_dir():
        for fname in STATE_FILES:
            fpath = state_dir / fname
            if fpath.exists():
                try:
                    json.loads(fpath.read_text())
                    check(f"state_{fname}", True, f"{fname} is valid JSON")
                except (json.JSONDecodeError, OSError) as e:
                    check(f"state_{fname}", False, f"{fname}: {e}")

    return results


# --- CLI Interface ---


def main(args: Optional[List[str]] = None):
    """CLI entry point for migration commands."""
    parser = argparse.ArgumentParser(
        prog="emergence migrate",
        description="Migrate an Emergence agent between machines",
    )
    sub = parser.add_subparsers(dest="subcommand", help="Migration action")

    # export
    p_export = sub.add_parser("export", help="Create a migration bundle")
    p_export.add_argument(
        "--workspace",
        "-w",
        type=Path,
        default=Path("."),
        help="Agent workspace directory (default: current dir)",
    )
    p_export.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output bundle path (auto-generated if omitted)",
    )

    # import
    p_import = sub.add_parser("import", help="Import a migration bundle")
    p_import.add_argument("bundle", type=Path, help="Path to bundle .tar.gz")
    p_import.add_argument(
        "--workspace",
        "-w",
        type=Path,
        default=Path("."),
        help="Destination workspace directory",
    )
    p_import.add_argument("--old-home", help="Override old home dir detection")
    p_import.add_argument("--new-home", help="Override new home dir (default: $HOME)")
    p_import.add_argument(
        "--openclaw-state",
        type=Path,
        default=None,
        help="OpenClaw state directory to also rewrite (default: ~/.openclaw)",
    )
    p_import.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup of existing workspace",
    )
    p_import.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without changes",
    )

    # rewrite-paths
    p_rewrite = sub.add_parser("rewrite-paths", help="Rewrite absolute paths in-place")
    p_rewrite.add_argument("--old", required=True, help="Old path prefix")
    p_rewrite.add_argument("--new", required=True, help="New path prefix")
    p_rewrite.add_argument(
        "--workspace",
        "-w",
        type=Path,
        default=Path("."),
        help="Workspace to scan",
    )
    p_rewrite.add_argument(
        "--openclaw-state",
        type=Path,
        default=None,
        help="Also rewrite paths in OpenClaw state dir (default: ~/.openclaw)",
    )
    p_rewrite.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview without changes",
    )

    # scan
    p_scan = sub.add_parser("scan", help="Scan for occurrences of a path")
    p_scan.add_argument("path_to_find", help="Path string to search for")
    p_scan.add_argument(
        "--workspace",
        "-w",
        type=Path,
        default=Path("."),
        help="Workspace to scan",
    )
    p_scan.add_argument(
        "--include-binary",
        action="store_true",
        help="Also scan SQLite databases",
    )

    # validate
    p_validate = sub.add_parser("validate", help="Validate workspace after migration")
    p_validate.add_argument(
        "--workspace",
        "-w",
        type=Path,
        default=Path("."),
        help="Workspace to validate",
    )

    parsed = parser.parse_args(args)

    if not parsed.subcommand:
        parser.print_help()
        sys.exit(1)

    if parsed.subcommand == "export":
        try:
            bundle = export_bundle(parsed.workspace, parsed.output)
            print(f"✅ Bundle created: {bundle}")
            print(f"   Size: {bundle.stat().st_size / 1024:.1f} KB")
            print()
            print("Next steps:")
            print(f"  1. Copy {bundle.name} to the destination machine")
            print(
                f"  2. Run: emergence migrate import {bundle.name} --workspace /path/to/new/workspace"
            )
        except (FileNotFoundError, ValueError) as e:
            print(f"❌ Export failed: {e}", file=sys.stderr)
            sys.exit(1)

    elif parsed.subcommand == "import":
        try:
            result = import_bundle(
                parsed.bundle,
                parsed.workspace,
                old_home=parsed.old_home,
                new_home=parsed.new_home,
                openclaw_root=parsed.openclaw_state,
                backup=not parsed.no_backup,
                dry_run=parsed.dry_run,
            )

            prefix = "[DRY RUN] " if parsed.dry_run else ""
            print(f"{prefix}✅ Import complete!")
            print(f"   Files extracted: {result['files_extracted']}")

            if result["backup_path"]:
                print(f"   Backup at: {result['backup_path']}")

            if result["rewrite_stats"]:
                rs = result["rewrite_stats"]
                print(f"   Path rewrites: {rs['replacements']} in {rs['files_modified']} files")
                if rs["modified_files"]:
                    for mf in rs["modified_files"]:
                        print(f"     - {mf['path']} ({mf['replacements']} replacements)")
                if rs["errors"]:
                    print(f"   ⚠️  Errors: {len(rs['errors'])}")
                    for err in rs["errors"]:
                        print(f"     - {err}")

            for w in result["warnings"]:
                print(f"   ⚠️  {w}")

            print()
            print("Next steps:")
            print(f"  1. Run: emergence migrate validate --workspace {parsed.workspace}")
            print("  2. Start the daemon: emergence drives daemon")
            print("  3. Test a drive tick: emergence drives tick")

        except (FileNotFoundError, ValueError) as e:
            print(f"❌ Import failed: {e}", file=sys.stderr)
            if not parsed.no_backup:
                print("   Your original workspace backup is preserved.", file=sys.stderr)
            sys.exit(1)

    elif parsed.subcommand == "rewrite-paths":
        stats = rewrite_paths(
            parsed.workspace,
            parsed.old,
            parsed.new,
            dry_run=parsed.dry_run,
            openclaw_root=parsed.openclaw_state,
        )
        prefix = "[DRY RUN] " if parsed.dry_run else ""
        print(f"{prefix}Path rewrite complete:")
        print(f"  Files scanned: {stats['files_scanned']}")
        print(f"  Files modified: {stats['files_modified']}")
        print(f"  Total replacements: {stats['replacements']}")
        if stats["modified_files"]:
            print("  Modified files:")
            for mf in stats["modified_files"]:
                print(f"    - {mf['path']} ({mf['replacements']} replacements)")
        if stats["errors"]:
            print(f"  Errors ({len(stats['errors'])}):")
            for err in stats["errors"]:
                print(f"    - {err}")

    elif parsed.subcommand == "scan":
        matches = scan_for_paths(
            parsed.workspace,
            parsed.path_to_find,
            include_binary=parsed.include_binary,
        )
        if not matches:
            print(f"✅ No occurrences of '{parsed.path_to_find}' found")
        else:
            print(f"Found {len(matches)} occurrences of '{parsed.path_to_find}':")
            for fpath, line_num, content in matches:
                rel = fpath.relative_to(parsed.workspace.resolve())
                if line_num:
                    print(f"  {rel}:{line_num}: {content[:120]}")
                else:
                    print(f"  {rel}: {content[:120]}")

    elif parsed.subcommand == "validate":
        results = validate_workspace(parsed.workspace)
        if results["valid"]:
            print("✅ Workspace validation passed!")
        else:
            print("❌ Workspace validation failed!")

        for c in results["checks"]:
            icon = "✅" if c["passed"] else "❌"
            detail = f" — {c['detail']}" if c.get("detail") else ""
            print(f"  {icon} {c['name']}{detail}")

        if results["warnings"]:
            print("\n  Warnings:")
            for w in results["warnings"]:
                print(f"    ⚠️  {w}")

        if not results["valid"]:
            print("\nTo fix path issues, run:")
            print("  emergence migrate rewrite-paths --old /old/home --new /new/home")
            sys.exit(1)


if __name__ == "__main__":
    main()
