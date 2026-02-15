"""
Nautilus Nightly Maintenance - Daemon Integration

Provides nightly maintenance tasks for the Nautilus memory system:
- Classify files into chambers (atrium → corridor → vault)
- Auto-tag contexts
- Apply gravity decay
- Link mirrors
- Promote important memories

Safe for daemon integration: logs errors without crashing.
"""

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .config import get_workspace, get_nautilus_config, get_gravity_db_path
from .session_hooks import register_recent_writes


def run_nightly_maintenance(
    register_recent: bool = True, recent_hours: int = 24, verbose: bool = False
) -> dict:
    """Run full nightly Nautilus maintenance cycle.

    Executes the full maintenance pipeline:
    1. Register recent file writes
    2. Classify chambers
    3. Auto-tag contexts
    4. Apply gravity decay
    5. Link mirrors
    6. Generate summary

    Args:
        register_recent: If True, register files modified in last N hours
        recent_hours: How many hours back to look for recent writes
        verbose: If True, print detailed progress

    Returns:
        Dictionary with maintenance results and statistics
    """
    result = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "enabled": False,
        "steps": {},
        "errors": [],
        "summary": {},
    }

    # Check if Nautilus is enabled
    config = get_nautilus_config()
    if not config.get("enabled", False):
        result["errors"].append("Nautilus disabled in config")
        return result

    result["enabled"] = True

    # Step 0: Register recent writes
    if register_recent:
        try:
            if verbose:
                print("📝 Registering recent writes...", file=sys.stderr)

            reg_result = register_recent_writes(hours=recent_hours)
            result["steps"]["register_recent"] = reg_result

            if verbose:
                print(f"   {reg_result.get('registered', 0)} files registered", file=sys.stderr)
        except Exception as e:
            error_msg = f"Failed to register recent writes: {e}"
            result["errors"].append(error_msg)
            if verbose:
                print(f"   ❌ {error_msg}", file=sys.stderr)

    # Step 1: Classify chambers
    try:
        if verbose:
            print("📂 Classifying chambers...", file=sys.stderr)

        classify_result = subprocess.run(
            [sys.executable, "-m", "core.nautilus.chambers", "classify"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if classify_result.returncode == 0:
            classify_data = json.loads(classify_result.stdout)
            result["steps"]["classify"] = classify_data

            classified = classify_data.get("classified", {})
            total = sum(classified.values())
            result["summary"]["chambers_classified"] = total

            if verbose:
                print(f"   {json.dumps(classified)}", file=sys.stderr)
        else:
            error_msg = f"Chamber classification failed: {classify_result.stderr}"
            result["errors"].append(error_msg)
            if verbose:
                print(f"   ❌ {error_msg}", file=sys.stderr)

    except Exception as e:
        error_msg = f"Chamber classification error: {e}"
        result["errors"].append(error_msg)
        if verbose:
            print(f"   ❌ {error_msg}", file=sys.stderr)

    # Step 2: Auto-tag contexts
    try:
        if verbose:
            print("🏷️  Auto-tagging contexts...", file=sys.stderr)

        tags_result = subprocess.run(
            [sys.executable, "-m", "core.nautilus.doors", "auto-tag"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if tags_result.returncode == 0:
            tags_data = json.loads(tags_result.stdout)
            result["steps"]["auto_tag"] = tags_data

            tagged = tags_data.get("files_tagged", 0)
            result["summary"]["files_tagged"] = tagged

            if verbose:
                print(f"   {tagged} files tagged", file=sys.stderr)
        else:
            error_msg = f"Auto-tagging failed: {tags_result.stderr}"
            result["errors"].append(error_msg)
            if verbose:
                print(f"   ❌ {error_msg}", file=sys.stderr)

    except Exception as e:
        error_msg = f"Auto-tagging error: {e}"
        result["errors"].append(error_msg)
        if verbose:
            print(f"   ❌ {error_msg}", file=sys.stderr)

    # Step 3: Apply gravity decay
    try:
        if verbose:
            print("⚖️  Running gravity decay...", file=sys.stderr)

        decay_result = subprocess.run(
            [sys.executable, "-m", "core.nautilus.gravity", "decay"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if decay_result.returncode == 0:
            decay_data = json.loads(decay_result.stdout)
            result["steps"]["decay"] = decay_data

            decayed = decay_data.get("decayed", 0)
            result["summary"]["chunks_decayed"] = decayed

            if verbose:
                print(f"   {decayed} chunks decayed", file=sys.stderr)
        else:
            error_msg = f"Gravity decay failed: {decay_result.stderr}"
            result["errors"].append(error_msg)
            if verbose:
                print(f"   ❌ {error_msg}", file=sys.stderr)

    except Exception as e:
        error_msg = f"Gravity decay error: {e}"
        result["errors"].append(error_msg)
        if verbose:
            print(f"   ❌ {error_msg}", file=sys.stderr)

    # Step 4: Promote important memories (chamber advancement)
    try:
        if verbose:
            print("📈 Promoting memories...", file=sys.stderr)

        promote_result = subprocess.run(
            [sys.executable, "-m", "core.nautilus.chambers", "promote"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if promote_result.returncode == 0:
            promote_data = json.loads(promote_result.stdout)
            result["steps"]["promote"] = promote_data

            promoted = promote_data.get("promoted", 0)
            result["summary"]["memories_promoted"] = promoted

            if verbose:
                print(f"   {promoted} memories promoted", file=sys.stderr)
        else:
            # Promotion might not exist yet, skip error
            if verbose:
                print(
                    f"   ⚠️  Promotion not available (chamber advancement coming soon)",
                    file=sys.stderr,
                )

    except Exception as e:
        # Non-critical, skip
        if verbose:
            print(f"   ⚠️  Promotion skipped: {e}", file=sys.stderr)

    # Step 5: Link mirrors
    try:
        if verbose:
            print("🔗 Auto-linking mirrors...", file=sys.stderr)

        mirrors_result = subprocess.run(
            [sys.executable, "-m", "core.nautilus.mirrors", "auto-link"],
            capture_output=True,
            text=True,
            timeout=120,
        )

        if mirrors_result.returncode == 0:
            mirrors_data = json.loads(mirrors_result.stdout)
            result["steps"]["mirrors"] = mirrors_data

            linked = mirrors_data.get("linked", 0)
            result["summary"]["mirrors_linked"] = linked

            if verbose:
                print(f"   {linked} mirrors linked", file=sys.stderr)
        else:
            error_msg = f"Mirror linking failed: {mirrors_result.stderr}"
            result["errors"].append(error_msg)
            if verbose:
                print(f"   ❌ {error_msg}", file=sys.stderr)

    except Exception as e:
        error_msg = f"Mirror linking error: {e}"
        result["errors"].append(error_msg)
        if verbose:
            print(f"   ❌ {error_msg}", file=sys.stderr)

    # Generate summary
    if verbose:
        print("\n✅ Nautilus maintenance complete", file=sys.stderr)
        if result["errors"]:
            print(f"⚠️  {len(result['errors'])} errors occurred", file=sys.stderr)

    return result


def should_run_maintenance(config: Optional[dict] = None) -> bool:
    """Check if nightly maintenance should run.

    Args:
        config: Optional config dict (loaded if not provided)

    Returns:
        True if maintenance should run, False otherwise
    """
    if config is None:
        config = get_nautilus_config()

    # Check if enabled
    if not config.get("enabled", False):
        return False

    # Could add additional checks here:
    # - Time-based scheduling (only run during quiet hours)
    # - Rate limiting (don't run more than once per day)
    # - Resource checks (disk space, system load)

    return True


def log_maintenance_result(result: dict, log_path: Optional[Path] = None) -> None:
    """Log maintenance result to daemon log.

    Args:
        result: Maintenance result dictionary
        log_path: Optional path to log file
    """
    if log_path is None:
        # Use default emergence log location
        workspace = get_workspace()
        log_path = workspace / ".emergence" / "logs" / "daemon.log"

    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)

        timestamp = result.get("timestamp", datetime.now(timezone.utc).isoformat())
        summary = result.get("summary", {})
        errors = result.get("errors", [])

        log_line = f"[{timestamp}] [NAUTILUS] Maintenance: "

        if not result.get("enabled"):
            log_line += "disabled\n"
        elif errors:
            log_line += f"completed with {len(errors)} errors - {summary}\n"
        else:
            log_line += f"success - {summary}\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)

            # Log errors
            for error in errors:
                f.write(f"[{timestamp}] [NAUTILUS] ERROR: {error}\n")

    except Exception:
        # Silent failure for logging
        pass


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Nautilus Nightly Maintenance")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--register-recent", action="store_true", default=True, help="Register recent writes"
    )
    parser.add_argument(
        "--recent-hours", type=int, default=24, help="Hours to look back for recent writes"
    )
    parser.add_argument("--json", action="store_true", help="Output JSON only")

    args = parser.parse_args()

    result = run_nightly_maintenance(
        register_recent=args.register_recent,
        recent_hours=args.recent_hours,
        verbose=args.verbose and not args.json,
    )

    if args.json or not args.verbose:
        print(json.dumps(result, indent=2))

    # Exit with error code if there were errors
    sys.exit(1 if result["errors"] else 0)
