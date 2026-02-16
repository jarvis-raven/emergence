#!/usr/bin/env python3
"""Self-History Snapshots — Versioned identity preservation.

Creates timestamped copies of SELF.md before nightly updates, enabling
tracking of identity evolution over time. Simple: read, copy, done.

Triggered by: Nightly Build (F012)
CLI: snapshot [--date YYYY-MM-DD], list
"""

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# --- Constants ---
VERSION = "1.0.0"
DEFAULT_CONFIG = Path("emergence.json")
SNAPSHOT_SUBDIR = "memory/self-history"
SELF_FILENAME = "SELF.md"


# --- Configuration ---


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from emergence.json."""
    defaults = {
        "agent": {"name": "My Agent"},
        "memory": {
            "self_history_dir": "memory/self-history",
        },
        "paths": {"workspace": ".", "identity": "."},
    }

    if config_path is None:
        config_path = DEFAULT_CONFIG

    if not config_path.exists():
        return defaults

    try:
        content = config_path.read_text(encoding="utf-8")
        lines = [ln for ln in content.split("\n") if not ln.strip().startswith(("//", "#"))]
        loaded = json.loads("\n".join(lines))

        merged = defaults.copy()
        for key, value in loaded.items():
            if isinstance(value, dict) and key in merged:
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        return merged
    except (json.JSONDecodeError, IOError):
        return defaults


def get_identity_dir(config: dict) -> Path:
    """Resolve identity directory from config."""
    workspace = config.get("paths", {}).get("workspace", ".")
    identity = config.get("paths", {}).get("identity", ".")
    return Path(workspace) / identity


def get_snapshot_dir(config: dict) -> Path:
    """Resolve snapshot directory from config."""
    workspace = config.get("paths", {}).get("workspace", ".")
    snapshot_dir = config.get("memory", {}).get("self_history_dir", SNAPSHOT_SUBDIR)
    return Path(workspace) / snapshot_dir


def get_self_path(config: dict) -> Path:
    """Resolve SELF.md path from config."""
    return get_identity_dir(config) / SELF_FILENAME


# --- Snapshot Operations ---


def calculate_hash(content: str) -> str:
    """Calculate SHA256 hash of content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def snapshot_exists(snapshot_dir: Path, date_str: str) -> bool:
    """Check if a snapshot already exists for the given date.

    Args:
        snapshot_dir: Directory for snapshots
        date_str: Date in YYYY-MM-DD format

    Returns:
        True if snapshot exists
    """
    snapshot_path = snapshot_dir / f"SELF-{date_str}.md"
    return snapshot_path.exists()


def create_snapshot(  # noqa: C901
    config: dict, date_str: Optional[str] = None, dry_run: bool = False, verbose: bool = False
) -> Optional[Path]:
    """Create a snapshot of SELF.md.

    Args:
        config: Configuration dictionary
        date_str: Optional date override (YYYY-MM-DD), defaults to today
        dry_run: If True, don't actually write
        verbose: If True, print progress

    Returns:
        Path to created snapshot, or None if skipped/failed
    """
    # Determine date
    if date_str is None:
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Resolve paths
    self_path = get_self_path(config)
    snapshot_dir = get_snapshot_dir(config)
    snapshot_path = snapshot_dir / f"SELF-{date_str}.md"

    # Check if SELF.md exists
    if not self_path.exists():
        if verbose:
            print(f"✗ SELF.md not found: {self_path}")
        return None

    # Check if snapshot already exists
    if snapshot_path.exists():
        if verbose:
            print(f"⚠ Snapshot already exists: {snapshot_path.name}")
        return None

    # Read SELF.md content
    try:
        content = self_path.read_text(encoding="utf-8")
    except IOError as e:
        if verbose:
            print(f"✗ Error reading SELF.md: {e}")
        return None

    # Build snapshot with header
    timestamp = datetime.now(timezone.utc).isoformat()
    content_hash = calculate_hash(content)

    header = f"""<!--
SELF-HISTORY SNAPSHOT
Original: SELF.md
Snapshot date: {timestamp}
Date: {date_str}
Hash: sha256:{content_hash}
-->

"""

    snapshot_content = header + content

    if dry_run:
        if verbose:
            print(f"[DRY RUN] Would create: {snapshot_path.name}")
            print(f"          Size: {len(snapshot_content)} bytes")
        return snapshot_path

    # Write snapshot atomically
    try:
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        tmp_file = snapshot_path.with_suffix(".tmp")
        tmp_file.write_text(snapshot_content, encoding="utf-8")
        tmp_file.replace(snapshot_path)

        if verbose:
            print(f"✓ Created snapshot: {snapshot_path.name}")
            print(f"  Size: {len(snapshot_content)} bytes")
            print(f"  Hash: {content_hash}")

        return snapshot_path
    except IOError as e:
        if verbose:
            print(f"✗ Error writing snapshot: {e}")
        return None


def list_snapshots(config: dict) -> list[dict]:
    """List all snapshots with metadata.

    Args:
        config: Configuration dictionary

    Returns:
        List of snapshot metadata dictionaries
    """
    snapshot_dir = get_snapshot_dir(config)

    if not snapshot_dir.exists():
        return []

    snapshots = []
    for file_path in sorted(snapshot_dir.glob("SELF-*.md")):
        try:
            stat = file_path.stat()
            # Parse date from filename
            date_match = file_path.stem.replace("SELF-", "")

            # Try to extract hash from header
            hash_str = "unknown"
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for line in content.split("\n")[:10]:
                    if "Hash:" in line:
                        hash_str = line.split("Hash:")[1].strip()
                        break
            except IOError:
                pass

            snapshots.append(
                {
                    "filename": file_path.name,
                    "date": date_match,
                    "size_bytes": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime, timezone.utc).isoformat(),
                    "hash": hash_str,
                    "path": str(file_path),
                }
            )
        except (IOError, OSError):
            continue

    return snapshots


def print_snapshot_list(snapshots: list[dict], verbose: bool = False):
    """Print formatted snapshot list.

    Args:
        snapshots: List of snapshot metadata
        verbose: If True, show detailed info
    """
    if not snapshots:
        print("No snapshots found.")
        return

    print(f"Self-History Snapshots ({len(snapshots)} total)")
    print("=" * 40)

    for snap in snapshots:
        if verbose:
            print(f"\n{snap['filename']}")
            print(f"  Date: {snap['date']}")
            print(f"  Size: {snap['size_bytes']:,} bytes")
            print(f"  Modified: {snap['modified']}")
            print(f"  Hash: {snap['hash']}")
        else:
            size_kb = snap["size_bytes"] / 1024
            print(f"  {snap['date']}  {size_kb:6.1f} KB  {snap['filename']}")


def get_status(config: dict) -> dict:
    """Get self-history status.

    Args:
        config: Configuration dictionary

    Returns:
        Status dictionary
    """
    snapshots = list_snapshots(config)
    snapshot_dir = get_snapshot_dir(config)
    self_path = get_self_path(config)

    total_size = sum(s["size_bytes"] for s in snapshots)

    return {
        "snapshot_count": len(snapshots),
        "snapshot_dir": str(snapshot_dir),
        "self_path": str(self_path),
        "self_exists": self_path.exists(),
        "total_storage_bytes": total_size,
        "snapshots": snapshots,
    }


# --- CLI Interface ---


def print_usage():
    """Print usage information."""
    print(
        """Self-History Snapshots — Versioned identity preservation

Usage:
    python3 -m core.memory.self_history snapshot [--date YYYY-MM-DD] [--dry-run]
    python3 -m core.memory.self_history list [--verbose]
    python3 -m core.memory.self_history status

Commands:
    snapshot     Create a new snapshot of SELF.md
    list         Show all snapshots
    status       Show status information

Options:
    --date       Date for snapshot (default: today, format: YYYY-MM-DD)
    --dry-run    Preview without creating files
    --verbose    Show detailed information
    --config     Path to emergence.json config file
    --help       Show this help message

Examples:
    python3 -m core.memory.self_history snapshot
    python3 -m core.memory.self_history snapshot --date 2026-02-07
    python3 -m core.memory.self_history list
    python3 -m core.memory.self_history list --verbose
    python3 -m core.memory.self_history status
"""
    )


def main():  # noqa: C901
    """CLI entry point."""
    args = sys.argv[1:]

    if not args or args[0] in ("--help", "-h"):
        print_usage()
        sys.exit(0)

    command = args[0]

    # Parse options
    dry_run = "--dry-run" in args
    verbose = "--verbose" in args or "-v" in args

    config_path = None
    if "--config" in args:
        idx = args.index("--config")
        if idx + 1 < len(args):
            config_path = Path(args[idx + 1])

    date_str = None
    if "--date" in args:
        idx = args.index("--date")
        if idx + 1 < len(args):
            date_str = args[idx + 1]

    # Load config
    config = load_config(config_path)

    if command == "snapshot":
        if verbose:
            print(f"Self-History Snapshots v{VERSION}")
            print("=" * 30)

        result = create_snapshot(config, date_str, dry_run, verbose)

        if result:
            sys.exit(0)
        else:
            # Snapshot may have been skipped (already exists) or failed
            sys.exit(0 if dry_run else 1)

    elif command == "list":
        snapshots = list_snapshots(config)
        print_snapshot_list(snapshots, verbose)
        sys.exit(0)

    elif command == "status":
        status = get_status(config)
        print("Self-History Status")
        print("==================")
        print(f"Snapshot directory: {status['snapshot_dir']}")
        print(f"SELF.md path: {status['self_path']}")
        print(f"SELF.md exists: {'Yes' if status['self_exists'] else 'No'}")
        print(f"Snapshot count: {status['snapshot_count']}")
        print(
            f"Total storage: {status['total_storage_bytes']:,} bytes "
            f"({status['total_storage_bytes'] / 1024:.1f} KB)"
        )

        if status["snapshots"]:
            print(f"\nLatest snapshot: {status['snapshots'][-1]['date']}")
            print(f"First snapshot: {status['snapshots'][0]['date']}")
        sys.exit(0)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
