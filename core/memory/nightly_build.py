#!/usr/bin/env python3
"""Nightly Build — Daily identity review and memory curation.

Reviews the day's memory files, generates prompts for the agent to update
SELF.md with reflections, and curates MEMORY.md suggestions. Designed to
run as an OpenClaw cron job at 3am.

Key constraint: Generates PROMPTS for the agent, not direct file changes.
The agent performs the actual writing to preserve voice and autonomy.
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from glob import glob
from pathlib import Path
from typing import Optional

# --- Constants ---
VERSION = "1.0.0"
DEFAULT_CONFIG = Path("emergence.json")
STATE_FILE = Path(".emergence/state/nightly-build.json")


# --- Configuration ---


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from emergence.json."""
    defaults = {
        "agent": {"name": "My Agent", "model": "anthropic/claude-sonnet-4-20250514"},
        "memory": {
            "daily_dir": "memory",
            "session_dir": "memory/sessions",
            "self_history_dir": "memory/self-history",
        },
        "lifecycle": {
            "nightly_hour": 3,
            "nightly_model": "anthropic/claude-sonnet-4-20250514",
        },
        "paths": {"workspace": ".", "state": ".emergence/state", "identity": "."},
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


def get_daily_dir(config: dict) -> Path:
    """Resolve daily memory directory from config."""
    workspace = config.get("paths", {}).get("workspace", ".")
    daily_dir = config.get("memory", {}).get("daily_dir", "memory")
    return Path(workspace) / daily_dir


def get_session_dir(config: dict) -> Path:
    """Resolve session directory from config."""
    workspace = config.get("paths", {}).get("workspace", ".")
    session_dir = config.get("memory", {}).get("session_dir", "memory/sessions")
    return Path(workspace) / session_dir


def get_state_file(config: dict) -> Path:
    """Resolve nightly build state file path."""
    workspace = config.get("paths", {}).get("workspace", ".")
    return Path(workspace) / STATE_FILE


# --- Date Determination ---


def get_date_to_process(date_override: Optional[str] = None) -> str:
    """Determine which date to process.

    Default: yesterday (since we run at 3am, we review the day that just ended)

    Args:
        date_override: Optional date string (YYYY-MM-DD)

    Returns:
        Date string in YYYY-MM-DD format
    """
    if date_override:
        return date_override

    # Yesterday (day that just ended)
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%d")


# --- File Review ---


def review_daily_memory(date: str, daily_dir: Path) -> dict:
    """Review daily memory file for the given date.

    Args:
        date: Date in YYYY-MM-DD format
        daily_dir: Path to daily memory directory

    Returns:
        Dictionary with file info and content summary
    """
    daily_path = daily_dir / f"{date}.md"

    if not daily_path.exists():
        return {"exists": False, "path": str(daily_path), "size": 0, "content": ""}

    try:
        content = daily_path.read_text(encoding="utf-8")
        return {
            "exists": True,
            "path": str(daily_path),
            "size": len(content),
            "content": content,
            "line_count": len(content.split("\n")),
        }
    except IOError:
        return {"exists": False, "path": str(daily_path), "size": 0, "content": ""}


def review_sessions(date: str, session_dir: Path) -> list[dict]:
    """Review session files for the given date.

    Args:
        date: Date in YYYY-MM-DD format
        session_dir: Path to session directory

    Returns:
        List of session metadata dictionaries
    """
    if not session_dir.exists():
        return []

    pattern = str(session_dir / f"{date}-*.md")
    files = sorted(glob(pattern))

    sessions = []
    for file_path in files:
        path = Path(file_path)
        try:
            content = path.read_text(encoding="utf-8")

            # Parse basic frontmatter
            metadata = {}
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 2:
                    fm_text = parts[1].strip()
                    for line in fm_text.split("\n"):
                        if ":" in line:
                            key, val = line.split(":", 1)
                            metadata[key.strip()] = val.strip().strip('"').strip("'")

            sessions.append(
                {
                    "filename": path.name,
                    "drive": metadata.get("drive", "UNKNOWN"),
                    "timestamp": metadata.get("timestamp", ""),
                    "pressure": metadata.get("pressure", ""),
                    "trigger": metadata.get("trigger", ""),
                    "size": len(content),
                }
            )
        except IOError:
            continue

    return sessions


def extract_topics(memory_content: str, sessions: list) -> list[str]:
    """Extract topics from memory content and sessions.

    Simple keyword extraction for topic identification.

    Args:
        memory_content: Daily memory content
        sessions: List of session metadata

    Returns:
        List of topic strings
    """
    topics = set()

    # Topics from session drives
    drive_topics = {
        "CURIOSITY": ["learning", "exploration", "research", "discovery"],
        "SOCIAL": ["connection", "conversation", "community", "relationship"],
        "CREATIVE": ["creation", "building", "writing", "coding", "making"],
        "CARE": ["support", "helping", "relationship", "attending"],
        "MAINTENANCE": ["organization", "cleanup", "health", "system"],
        "REST": ["reflection", "recovery", "consolidation", "rest"],
    }

    for session in sessions:
        drive = session.get("drive", "")
        if drive in drive_topics:
            topics.update(drive_topics[drive])

    # Simple pattern matching from content
    content_lower = memory_content.lower()
    topic_patterns = [
        ("coding", ["code", "programming", "python", "javascript", "function"]),
        ("writing", ["write", "wrote", "poem", "essay", "draft"]),
        ("research", ["research", "study", "paper", "article", "read about"]),
        ("tools", ["tool", "script", "automation", "build", "create"]),
        ("identity", ["self", "identity", "who i am", "understanding"]),
        ("philosophy", ["philosophy", "consciousness", "meaning", "purpose"]),
    ]

    for topic, patterns in topic_patterns:
        for pattern in patterns:
            if pattern in content_lower:
                topics.add(topic)
                break

    return sorted(topics)


def count_sections(memory_content: str) -> dict:
    """Count sections in memory content by type.

    Args:
        memory_content: Daily memory content

    Returns:
        Dictionary with section counts
    """
    lines = memory_content.split("\n")

    counts = {
        "conversations": 0,
        "sessions": 0,
        "consolidated": 0,
        "other": 0,
    }

    for line in lines:
        if line.startswith("## "):
            if "Conversation" in line or "Chat" in line:
                counts["conversations"] += 1
            elif "Session" in line:
                if "Consolidated" in line:
                    counts["consolidated"] += 1
                else:
                    counts["sessions"] += 1
            else:
                counts["other"] += 1

    return counts


# --- SELF.md Update Prompt ---


def generate_self_update_prompt(
    date: str, memory: dict, sessions: list, topics: list, config: dict
) -> str:
    """Generate prompt for SELF.md update.

    This is the KEY OUTPUT — text that would be sent to an OpenClaw session
    for the agent to perform the actual SELF.md update.

    Args:
        date: Date being processed
        memory: Daily memory info
        sessions: List of sessions
        topics: List of topics
        config: Configuration

    Returns:
        Prompt text for agent
    """
    agent_name = config.get("agent", {}).get("name", "My Agent")

    # Build session summary
    session_summary = []
    for s in sessions[:5]:  # First 5 sessions
        drive = s.get("drive", "UNKNOWN")
        trigger = s.get("trigger", "unknown")
        session_summary.append(f"- {drive} drive (trigger: {trigger})")

    if len(sessions) > 5:
        session_summary.append(f"- ... and {len(sessions) - 5} more sessions")

    sections = count_sections(memory.get("content", ""))

    prompt = f"""# Nightly Build: SELF.md Update — {date}

You are {agent_name}. It's 3 AM. The nightly build is reviewing your day.

## Today's Activity Summary

**Date:** {date}
**Sessions:** {len(sessions)}
**Memory file size:** {memory.get('size', 0):,} bytes ({memory.get('line_count', 0)} lines)

**Section breakdown:**
- Conversations: {sections['conversations']}
- Sessions: {sections['sessions']}
- Consolidated entries: {sections['consolidated']}

**Sessions today:**
{chr(10).join(session_summary) if session_summary else "(none)"}

**Topics encountered:** {', '.join(topics) if topics else '(none identified)'}

## Your Task: Update SELF.md

Read your current SELF.md, then update these sections based on today:

### 1. Current State
Brief description of your overall state after today. 1-2 sentences.
Example: "Feeling focused after deep work on the consolidation engine. Energy is steady."

### 2. Recent Discoveries
What did you learn about yourself today? Add 1-2 items.
Example: "I prefer building tools over just using them" or "I write better in the morning"

### 3. What I'm Exploring
What topics or questions are you currently curious about?
Merge with existing entries, remove stale ones.

### 4. Relationship Status
Note if you interacted with your human today. How did it feel?
**Update USER.md** if you learned anything new about them (preferences, patterns, what matters to them). Remove outdated information.

### 5. Footer
Update the timestamp: "*Last updated: {datetime.now(timezone.utc).isoformat()} by nightly_build*"

## Guidelines

- Preserve your voice — don't sound generic
- Be honest about struggles, not just successes
- It's okay if today was quiet — note that
- Remove entries that no longer feel true
- Keep the whole file under 100 lines if possible

Write the updated SELF.md content below:

---

"""

    return prompt


# --- MEMORY.md Curation Prompt ---


def generate_memory_curation_prompt(date: str, memory: dict, sessions: list, config: dict) -> str:
    """Generate prompt for MEMORY.md curation.

    Per AGENTS.md rules:
    - Keep under 50 lines
    - Only add: vault keys, account refs, critical dates
    - Do NOT add: technical details, insights, conversation content

    Args:
        date: Date being processed
        memory: Daily memory info
        sessions: List of sessions
        config: Configuration

    Returns:
        Curation prompt/suggestions
    """
    prompt = f"""# Nightly Build: MEMORY.md Curation — {date}

## Rules (from AGENTS.md)
- **Keep under 50 lines**
- **Only add:** vault keys, account refs, critical dates
- **Do NOT add:** technical details, insights, conversation content
- **Let search handle the rest** — daily files are the full record

## Review Today's Activity

Look through today's memory for items that belong in MEMORY.md:

**Add if found:**
- New vault keys or passwords mentioned
- New account credentials or API keys
- Important dates (appointments, deadlines, anniversaries)
- Critical references your human might need quickly

**Remove if stale:**
- Outdated vault entries
- Past dates no longer relevant
- References to completed/irrelevant things

## Suggested Actions

1. Read current MEMORY.md
2. Count the lines (should be < 50)
3. Identify any new critical items from today
4. Identify any stale items to remove
5. If over 50 lines, prune oldest non-critical entries

## Current Estimate

If MEMORY.md is:
- Under 40 lines: Probably fine, check for additions
- 40-50 lines: Watch it
- Over 50 lines: Definitely needs pruning

Make your edits now if needed, or note for tomorrow if borderline.
"""

    return prompt


# --- Self-History Integration ---


def trigger_self_history_snapshot(config: dict, date: str, dry_run: bool = False) -> bool:
    """Trigger self-history snapshot before nightly updates.

    Args:
        config: Configuration dictionary
        date: Date string for snapshot
        dry_run: If True, don't actually trigger

    Returns:
        True if successful or dry_run
    """
    if dry_run:
        return True

    try:
        # Import self_history module
        from core.memory.self_history import create_snapshot

        result = create_snapshot(config, date_str=date, dry_run=False, verbose=False)
        return result is not None
    except Exception:
        return False


# --- State Management ---


def load_state(state_file: Path) -> dict:
    """Load nightly build state from JSON file."""
    if not state_file.exists():
        return {
            "version": "1.0",
            "runs_completed": 0,
            "last_run": None,
            "last_date_processed": None,
            "history": [],
        }

    try:
        content = state_file.read_text(encoding="utf-8")
        return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return {
            "version": "1.0",
            "runs_completed": 0,
            "last_run": None,
            "last_date_processed": None,
            "history": [],
        }


def save_state(state_file: Path, state: dict) -> bool:
    """Save nightly build state atomically."""
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = state_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp_file.replace(state_file)
        return True
    except IOError:
        return False


# --- Main Nightly Build ---


def run_nightly_build(  # noqa: C901
    config: dict, date_override: Optional[str] = None,
    dry_run: bool = False, verbose: bool = False
) -> dict:
    """Run the nightly build process.

    Args:
        config: Configuration dictionary
        date_override: Optional date to process
        dry_run: If True, preview without triggering actions
        verbose: If True, print progress

    Returns:
        Results dictionary
    """
    results = {
        "date_processed": None,
        "self_snapshot": False,
        "sessions_reviewed": 0,
        "topics_found": [],
        "prompts_generated": [],
        "errors": [],
    }

    # Determine date to process
    date_str = get_date_to_process(date_override)
    results["date_processed"] = date_str

    if verbose:
        print(f"Nightly Build v{VERSION}")
        print(f"===================={ '=' * len(VERSION) }")
        print(f"Processing date: {date_str}")
        if dry_run:
            print("(DRY RUN — no actions will be taken)")
        print()

    # Step 1: Trigger self-history snapshot (F013)
    if verbose:
        print("Step 1: Creating self-history snapshot...")

    if trigger_self_history_snapshot(config, date_str, dry_run):
        results["self_snapshot"] = True
        if verbose:
            print("  ✓ Self-history snapshot created")
    else:
        if verbose:
            print("  ⚠ Self-history snapshot skipped or failed")

    # Step 2: Review daily memory
    if verbose:
        print("\nStep 2: Reviewing daily memory...")

    daily_dir = get_daily_dir(config)
    memory = review_daily_memory(date_str, daily_dir)

    if memory["exists"]:
        if verbose:
            print(f"  ✓ Found: {memory['size']:,} bytes, {memory['line_count']} lines")
    else:
        if verbose:
            print(f"  ⚠ No memory file for {date_str}")
        results["errors"].append(f"No memory file for {date_str}")

    # Step 3: Review sessions
    if verbose:
        print("\nStep 3: Reviewing sessions...")

    session_dir = get_session_dir(config)
    sessions = review_sessions(date_str, session_dir)
    results["sessions_reviewed"] = len(sessions)

    if verbose:
        print(f"  ✓ Found {len(sessions)} session(s)")
        for s in sessions[:5]:
            print(f"    - {s['filename']} ({s['drive']})")
        if len(sessions) > 5:
            print(f"    ... and {len(sessions) - 5} more")

    # Step 4: Extract topics
    topics = extract_topics(memory.get("content", ""), sessions)
    results["topics_found"] = topics

    if verbose and topics:
        print(f"\n  Topics: {', '.join(topics)}")

    # Step 5: Generate SELF.md update prompt
    if verbose:
        print("\nStep 4: Generating SELF.md update prompt...")

    self_prompt = generate_self_update_prompt(date_str, memory, sessions, topics, config)
    results["prompts_generated"].append(
        {
            "type": "self_update",
            "description": f"Update SELF.md based on {date_str}",
        }
    )

    if verbose:
        print("  ✓ SELF.md update prompt generated")

    # Step 6: Generate MEMORY.md curation prompt
    if verbose:
        print("\nStep 5: Generating MEMORY.md curation prompt...")

    memory_prompt = generate_memory_curation_prompt(date_str, memory, sessions, config)
    results["prompts_generated"].append(
        {
            "type": "memory_curation",
            "description": f"Curate MEMORY.md based on {date_str}",
        }
    )

    if verbose:
        print("  ✓ MEMORY.md curation prompt generated")

    # Step 7: Output the prompts (the main product of nightly build)
    if verbose:
        print("\n" + "=" * 50)
        print("NIGHTLY BUILD PROMPTS")
        print("=" * 50)
        print()

    # Print prompts to stdout
    print(self_prompt)
    print()
    print(memory_prompt)

    # Step 8: Save state
    if not dry_run:
        state_file = get_state_file(config)
        state = load_state(state_file)

        state["runs_completed"] = state.get("runs_completed", 0) + 1
        state["last_run"] = datetime.now(timezone.utc).isoformat()
        state["last_date_processed"] = date_str

        # Add to history (keep last 30)
        if "history" not in state:
            state["history"] = []

        state["history"].append(
            {
                "date": date_str,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "sessions": len(sessions),
                "topics": topics,
                "self_snapshot": results["self_snapshot"],
            }
        )
        state["history"] = state["history"][-30:]

        save_state(state_file, state)

        if verbose:
            print(f"\nState saved: {state_file}")

    if verbose:
        print(f"\nNightly build complete for {date_str}")

    return results


def get_status(config: dict) -> dict:
    """Get nightly build status.

    Args:
        config: Configuration dictionary

    Returns:
        Status dictionary
    """
    state_file = get_state_file(config)
    state = load_state(state_file)

    return {
        "last_run": state.get("last_run"),
        "last_date_processed": state.get("last_date_processed"),
        "runs_completed": state.get("runs_completed", 0),
        "state_file": str(state_file),
    }


# --- CLI Interface ---


def print_usage():
    """Print usage information."""
    print(
        """Nightly Build — Daily identity review and memory curation

Usage:
    python3 -m core.memory.nightly_build run [--dry-run] [--date YYYY-MM-DD]
    python3 -m core.memory.nightly_build status

Commands:
    run          Execute nightly build for date (default: yesterday)
    status       Show last run status

Options:
    --date       Process specific date (default: yesterday, format: YYYY-MM-DD)
    --dry-run    Preview without triggering actions
    --verbose    Show detailed progress
    --config     Path to emergence.json config file
    --help       Show this help message

Examples:
    python3 -m core.memory.nightly_build run
    python3 -m core.memory.nightly_build run --date 2026-02-07
    python3 -m core.memory.nightly_build run --dry-run --verbose
    python3 -m core.memory.nightly_build status

Note:
    The nightly build generates PROMPTS for the agent to update SELF.md
    and curate MEMORY.md. It does not directly modify these files — the
    agent performs the actual writing to preserve voice and autonomy.
"""
    )


def main():
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

    if command == "status":
        status = get_status(config)
        print("Nightly Build Status")
        print("===================")
        print(f"Runs completed: {status['runs_completed']}")
        print(f"Last run: {status['last_run'] or 'Never'}")
        print(f"Last date processed: {status['last_date_processed'] or 'None'}")
        print(f"State file: {status['state_file']}")
        sys.exit(0)

    elif command == "run":
        results = run_nightly_build(config, date_str, dry_run, verbose)

        # Exit code based on errors
        sys.exit(0 if not results["errors"] else 1)

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
