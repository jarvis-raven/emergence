#!/usr/bin/env python3
"""Consolidation Engine — Periodic insight extraction from session files.

Scans memory/sessions/ for unconsolidated session files, extracts insights
using LLM analysis, and appends formatted summaries to daily memory files.
This bridges the gap between granular session records and readable daily logs.

Designed to run as a cron job (default: every 2 hours).
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone
from glob import glob
from pathlib import Path
from typing import Optional

# --- Constants ---
VERSION = "1.0.0"
DEFAULT_CONFIG = Path("emergence.json")
STATE_FILE = Path("memory/.consolidation-state.json")
SESSION_PATTERN = "*.md"

# LLM endpoints and models
OLLAMA_DEFAULT_URL = "http://localhost:11434/api/generate"
OPENROUTER_DEFAULT_URL = "https://openrouter.ai/api/v1/chat/completions"
OLLAMA_DEFAULT_MODEL = "llama3.2:3b"
OPENROUTER_DEFAULT_MODEL = "mistralai/mistral-nemo"


# --- Configuration ---

def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from emergence.json.
    
    Args:
        config_path: Optional explicit path to config file
        
    Returns:
        Configuration dictionary with defaults applied
    """
    defaults = {
        "agent": {"name": "My Agent", "model": "anthropic/claude-sonnet-4-20250514"},
        "memory": {
            "daily_dir": "memory",
            "session_dir": "memory/sessions",
        },
        "lifecycle": {
            "consolidation_model": "mistralai/mistral-nemo",
        },
        "paths": {"workspace": ".", "state": ".emergence/state"},
    }
    
    if config_path is None:
        config_path = DEFAULT_CONFIG
    
    if not config_path.exists():
        return defaults
    
    try:
        content = config_path.read_text(encoding="utf-8")
        # Strip comment lines (// or # at start)
        lines = [ln for ln in content.split("\n") 
                 if not ln.strip().startswith(("//", "#"))]
        loaded = json.loads("\n".join(lines))
        
        # Merge with defaults
        merged = defaults.copy()
        for key, value in loaded.items():
            if isinstance(value, dict) and key in merged:
                merged[key] = {**merged[key], **value}
            else:
                merged[key] = value
        return merged
    except (json.JSONDecodeError, IOError):
        return defaults


def get_session_dir(config: dict) -> Path:
    """Resolve session directory from config."""
    workspace = config.get("paths", {}).get("workspace", ".")
    session_dir = config.get("memory", {}).get("session_dir", "memory/sessions")
    return Path(workspace) / session_dir


def get_daily_dir(config: dict) -> Path:
    """Resolve daily memory directory from config."""
    workspace = config.get("paths", {}).get("workspace", ".")
    daily_dir = config.get("memory", {}).get("daily_dir", "memory")
    return Path(workspace) / daily_dir


def get_state_file(config: dict) -> Path:
    """Resolve consolidation state file path."""
    workspace = config.get("paths", {}).get("workspace", ".")
    return Path(workspace) / STATE_FILE


# --- YAML Frontmatter Parsing ---

def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.
    
    Args:
        content: Full markdown content with optional frontmatter
        
    Returns:
        Tuple of (metadata dict, body content)
        
    Example:
        >>> content = "---\\ndrive: CURIOSITY\\ntimestamp: 2026-02-07T14:30:00Z\\n---\\nBody"
        >>> meta, body = parse_frontmatter(content)
        >>> meta["drive"]
        'CURIOSITY'
    """
    if not content.startswith("---"):
        return {}, content
    
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content
    
    fm_text = parts[1].strip()
    body = parts[2].strip()
    
    # Simple key: value parsing (sufficient for our frontmatter)
    metadata = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" in line:
            key, val = line.split(":", 1)
            key = key.strip()
            val = val.strip().strip('"').strip("'")
            metadata[key] = val
    
    return metadata, body


# --- State Management ---

def load_state(state_file: Path) -> dict:
    """Load consolidation state from JSON file."""
    if not state_file.exists():
        return {"version": "1.0", "consolidated": []}
    
    try:
        content = state_file.read_text(encoding="utf-8")
        return json.loads(content)
    except (json.JSONDecodeError, IOError):
        return {"version": "1.0", "consolidated": []}


def save_state(state_file: Path, state: dict) -> bool:
    """Save consolidation state atomically (write .tmp, then rename).
    
    Args:
        state_file: Path to state file
        state: State dictionary to save
        
    Returns:
        True if saved successfully
    """
    try:
        state_file.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = state_file.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp_file.replace(state_file)
        return True
    except IOError:
        return False


def is_consolidated(state: dict, filepath: Path) -> bool:
    """Check if a session file has already been consolidated."""
    consolidated = state.get("consolidated", [])
    # Check by absolute path string
    return str(filepath.resolve()) in consolidated


def mark_consolidated(state: dict, filepath: Path) -> dict:
    """Mark a session file as consolidated."""
    if "consolidated" not in state:
        state["consolidated"] = []
    path_str = str(filepath.resolve())
    if path_str not in state["consolidated"]:
        state["consolidated"].append(path_str)
    return state


# --- File Discovery ---

def discover_sessions(session_dir: Path, state: dict) -> list[Path]:
    """Discover unconsolidated session files.
    
    Args:
        session_dir: Directory containing session files
        state: Current consolidation state
        
    Returns:
        List of Path objects for unconsolidated session files
    """
    if not session_dir.exists():
        return []
    
    pattern = str(session_dir / SESSION_PATTERN)
    files = [Path(f) for f in glob(pattern)]
    
    # Filter out already consolidated and non-markdown files
    unconsolidated = [
        f for f in files 
        if f.suffix == ".md" and not is_consolidated(state, f)
    ]
    
    # Sort by filename (which includes timestamp) for chronological order
    unconsolidated.sort(key=lambda p: p.name)
    return unconsolidated


def get_target_date(metadata: dict) -> str:
    """Determine target daily memory date from session metadata.
    
    Args:
        metadata: Session metadata dict with optional timestamp
        
    Returns:
        Date string in YYYY-MM-DD format
    """
    timestamp_str = metadata.get("timestamp", "")
    if timestamp_str:
        try:
            # Parse ISO timestamp
            dt = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            pass
    
    # Default to today
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


# --- LLM Analysis ---

def build_consolidation_prompt(metadata: dict, body: str) -> str:
    """Build the LLM prompt for insight extraction.
    
    Args:
        metadata: Session metadata (drive, timestamp, pressure, etc.)
        body: Session body content
        
    Returns:
        Formatted prompt string
    """
    drive = metadata.get("drive", "UNKNOWN")
    timestamp = metadata.get("timestamp", "unknown time")
    pressure = metadata.get("pressure", "unknown")
    trigger = metadata.get("trigger", "unknown")
    
    # Truncate body to stay within token limits (approx 8000 chars)
    truncated_body = body[:8000] if len(body) > 8000 else body
    if len(body) > 8000:
        truncated_body += "\n\n[... content truncated ...]"
    
    return f"""Summarize this autonomous session for daily memory consolidation.

SESSION METADATA:
- Drive: {drive}
- Timestamp: {timestamp}
- Pressure at trigger: {pressure}
- Trigger type: {trigger}

SESSION CONTENT:
{truncated_body}

Provide a concise summary (2-4 paragraphs) covering:
1. What the agent did during this session
2. Key insights, realizations, or learnings (if any)
3. Artifacts created, modified, or discovered
4. Whether the drive was satisfied and how

Keep it focused on what matters for future context. Write in third person."""


def extract_with_ollama(prompt: str, config: Optional[dict] = None) -> Optional[str]:
    """Extract insights using local Ollama model.
    
    Args:
        prompt: The consolidation prompt
        config: Configuration dictionary
        
    Returns:
        Extracted summary text, or None if Ollama unavailable
    """
    ollama_url = (config or {}).get("consolidation", {}).get("ollama_url", OLLAMA_DEFAULT_URL)
    model = (config or {}).get("consolidation", {}).get("ollama_model", OLLAMA_DEFAULT_MODEL)
    
    req_data = json.dumps({
        "model": model,
        "prompt": prompt,
        "stream": False,
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(
            ollama_url,
            data=req_data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result.get("response", "").strip()
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return None


def extract_with_openrouter(prompt: str, config: Optional[dict] = None) -> Optional[str]:
    """Extract insights using OpenRouter API.
    
    Args:
        prompt: The consolidation prompt
        config: Configuration dictionary
        
    Returns:
        Extracted summary text, or None if API unavailable/unconfigured
    """
    api_key = _get_openrouter_key(config)
    if not api_key:
        return None
    
    model = (config or {}).get("consolidation", {}).get(
        "openrouter_model", 
        config.get("lifecycle", {}).get("consolidation_model", OPENROUTER_DEFAULT_MODEL)
    )
    
    req_data = json.dumps({
        "model": model,
        "max_tokens": 1000,
        "temperature": 0.3,
        "messages": [{"role": "user", "content": prompt}]
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(
            OPENROUTER_DEFAULT_URL,
            data=req_data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            return result["choices"][0]["message"]["content"].strip()
    except (urllib.error.URLError, urllib.error.HTTPError, 
            json.JSONDecodeError, KeyError, TimeoutError):
        return None


def extract_with_keywords(metadata: dict, body: str) -> str:
    """Extract basic summary using keyword patterns (fallback).
    
    Args:
        metadata: Session metadata
        body: Session body content
        
    Returns:
        Simple formatted summary
    """
    drive = metadata.get("drive", "UNKNOWN")
    timestamp = metadata.get("timestamp", "unknown time")
    
    # Count some basic patterns
    code_blocks = len(re.findall(r'```', body)) // 2
    headers = len(re.findall(r'^##?\s+', body, re.MULTILINE))
    links = len(re.findall(r'\[.*?\]\(.*?\)', body))
    
    summary_parts = [f"Autonomous session driven by {drive} at {timestamp}."]
    
    if code_blocks > 0:
        summary_parts.append(f"Included {code_blocks} code blocks.")
    if headers > 0:
        summary_parts.append(f"Contained {headers} sections.")
    if links > 0:
        summary_parts.append(f"Referenced {links} external links.")
    
    # First line as preview if available
    first_line = body.strip().split("\n")[0][:100] if body.strip() else ""
    if first_line and not first_line.startswith("#"):
        summary_parts.append(f"Started with: {first_line}")
    
    return " ".join(summary_parts)


def extract_insights(metadata: dict, body: str, config: Optional[dict] = None,
                     verbose: bool = False) -> str:
    """Orchestrator: Try Ollama → OpenRouter → keywords.
    
    Args:
        metadata: Session metadata
        body: Session body content
        config: Configuration dictionary
        verbose: If True, print progress messages
        
    Returns:
        Extracted summary text (always returns something)
    """
    prompt = build_consolidation_prompt(metadata, body)
    
    # 1. Try Ollama first (local, free)
    if verbose:
        print("  🧠 Trying Ollama for insight extraction...")
    result = extract_with_ollama(prompt, config)
    if result:
        if verbose:
            print("  ✓ Ollama extraction successful")
        return result
    if verbose:
        print("  ⚠ Ollama not available")
    
    # 2. Try OpenRouter if configured
    if _get_openrouter_key(config):
        if verbose:
            print("  🧠 Trying OpenRouter fallback...")
        result = extract_with_openrouter(prompt, config)
        if result:
            if verbose:
                print("  ✓ OpenRouter extraction successful")
            return result
        if verbose:
            print("  ⚠ OpenRouter failed")
    elif verbose:
        print("  ⚠ OpenRouter not configured")
    
    # 3. Fallback to keyword extraction
    if verbose:
        print("  🧠 Using keyword fallback...")
    return extract_with_keywords(metadata, body)


def _get_openrouter_key(config: Optional[dict] = None) -> Optional[str]:
    """Get OpenRouter API key from various sources."""
    # 1. Config file
    if config:
        key = config.get("consolidation", {}).get("openrouter_api_key")
        if key:
            return key
        key = config.get("ingest", {}).get("openrouter_api_key")
        if key:
            return key
    
    # 2. Environment variable
    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key
    
    # 3. Key file
    key_file = Path.home() / ".openclaw" / "openrouter-key"
    if key_file.exists():
        try:
            return key_file.read_text().strip()
        except IOError:
            pass
    
    return None


# --- Daily Memory Appending ---

def format_consolidated_entry(metadata: dict, insights: str, source_file: Path) -> str:
    """Format a consolidated entry for daily memory.
    
    Args:
        metadata: Session metadata
        insights: Extracted insights/summary
        source_file: Original session file path
        
    Returns:
        Formatted markdown entry
    """
    drive = metadata.get("drive", "UNKNOWN")
    timestamp = metadata.get("timestamp", "")
    
    # Parse timestamp for display
    time_str = ""
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            time_str = dt.strftime("%H:%M GMT")
        except (ValueError, AttributeError):
            pass
    
    header = f"## Consolidated Session — {drive}"
    if time_str:
        header += f" ({time_str})"
    
    entry_parts = [
        "",
        header,
        "",
        insights,
        "",
        f"*Source: `{source_file.name}`*",
        "",
    ]
    
    return "\n".join(entry_parts)


def append_to_daily(daily_path: Path, entry: str, dry_run: bool = False) -> bool:
    """Append consolidated entry to daily memory file atomically.
    
    Args:
        daily_path: Path to daily memory file
        entry: Formatted entry to append
        dry_run: If True, don't actually write
        
    Returns:
        True if successful (or dry_run)
    """
    if dry_run:
        return True
    
    try:
        daily_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Append mode (create if doesn't exist)
        with open(daily_path, "a", encoding="utf-8") as f:
            f.write(entry)
        
        return True
    except IOError:
        return False


# --- Main Consolidation Logic ---

def consolidate_session(
    session_file: Path,
    config: dict,
    state: dict,
    dry_run: bool = False,
    verbose: bool = False
) -> bool:
    """Consolidate a single session file.
    
    Args:
        session_file: Path to session file
        config: Configuration dictionary
        state: Current consolidation state
        dry_run: If True, don't actually write
        verbose: If True, print progress
        
    Returns:
        True if successful
    """
    if verbose:
        print(f"Processing: {session_file.name}")
    
    # Read session file
    try:
        content = session_file.read_text(encoding="utf-8")
    except IOError as e:
        if verbose:
            print(f"  ✗ Error reading file: {e}")
        return False
    
    # Parse frontmatter and body
    metadata, body = parse_frontmatter(content)
    
    if not metadata and not body.strip():
        if verbose:
            print("  ✗ Empty or unparsable file")
        return False
    
    # Extract insights
    insights = extract_insights(metadata, body, config, verbose)
    
    # Determine target daily file
    target_date = get_target_date(metadata)
    daily_dir = get_daily_dir(config)
    daily_path = daily_dir / f"{target_date}.md"
    
    # Format entry
    entry = format_consolidated_entry(metadata, insights, session_file)
    
    # Append to daily memory
    if append_to_daily(daily_path, entry, dry_run):
        if verbose:
            print(f"  ✓ Appended to {daily_path.name}")
    else:
        if verbose:
            print(f"  ✗ Failed to append to {daily_path.name}")
        return False
    
    # Mark as consolidated
    if not dry_run:
        mark_consolidated(state, session_file)
    
    return True


def run_consolidation(
    config: dict,
    dry_run: bool = False,
    verbose: bool = False,
    specific_file: Optional[Path] = None
) -> dict:
    """Run the consolidation process.
    
    Args:
        config: Configuration dictionary
        dry_run: If True, preview without writing
        verbose: If True, print progress
        specific_file: If provided, only process this file
        
    Returns:
        Results dictionary with stats
    """
    results = {
        "processed": 0,
        "failed": 0,
        "skipped": 0,
        "sessions": [],
    }
    
    # Load state
    state_file = get_state_file(config)
    state = load_state(state_file)
    
    # Determine files to process
    if specific_file:
        if specific_file.exists():
            files = [specific_file]
        else:
            if verbose:
                print(f"Error: File not found: {specific_file}")
            results["failed"] += 1
            return results
    else:
        session_dir = get_session_dir(config)
        files = discover_sessions(session_dir, state)
    
    if verbose:
        count = len(files)
        print(f"Found {count} session(s) to consolidate")
        if dry_run:
            print("(DRY RUN — no files will be modified)")
        print()
    
    # Process each file
    for session_file in files:
        success = consolidate_session(session_file, config, state, dry_run, verbose)
        
        if success:
            results["processed"] += 1
            results["sessions"].append(session_file.name)
        else:
            results["failed"] += 1
        
        if verbose:
            print()
    
    # Save state
    if not dry_run and results["processed"] > 0:
        save_state(state_file, state)
        if verbose:
            print(f"State saved: {state_file}")
    
    return results


def get_status(config: dict) -> dict:
    """Get consolidation status (pending count, last run, etc.).
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Status dictionary
    """
    state_file = get_state_file(config)
    state = load_state(state_file)
    session_dir = get_session_dir(config)
    
    pending = discover_sessions(session_dir, state)
    
    return {
        "pending_count": len(pending),
        "session_dir": str(session_dir),
        "state_file": str(state_file),
        "pending_files": [p.name for p in pending[:10]],  # First 10
    }


# --- CLI Interface ---

def print_usage():
    """Print usage information."""
    print("""Consolidation Engine — Extract insights from session files

Usage:
    python3 -m core.memory.consolidation run [--dry-run] [--verbose]
    python3 -m core.memory.consolidation status
    python3 -m core.memory.consolidation run --session FILE

Commands:
    run          Process all pending sessions
    status       Show pending count and status

Options:
    --dry-run    Preview without writing files
    --verbose    Show detailed progress
    --session    Process a specific session file only
    --config     Path to emergence.json config file
    --help       Show this help message

Examples:
    python3 -m core.memory.consolidation run
    python3 -m core.memory.consolidation run --dry-run --verbose
    python3 -m core.memory.consolidation status
    python3 -m core.memory.consolidation run --session memory/sessions/2026-02-07-1430-CURIOSITY.md
""")


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
    
    specific_file = None
    if "--session" in args:
        idx = args.index("--session")
        if idx + 1 < len(args):
            specific_file = Path(args[idx + 1])
    
    # Load config
    config = load_config(config_path)
    
    if command == "status":
        status = get_status(config)
        print(f"Consolidation Status")
        print(f"===================")
        print(f"Pending sessions: {status['pending_count']}")
        print(f"Session directory: {status['session_dir']}")
        print(f"State file: {status['state_file']}")
        if status['pending_files']:
            print(f"\nPending files (first 10):")
            for f in status['pending_files']:
                print(f"  - {f}")
        sys.exit(0)
    
    elif command == "run":
        if verbose:
            print(f"Consolidation Engine v{VERSION}")
            print(f"====================={ '=' * len(VERSION) }")
            print()
        
        results = run_consolidation(config, dry_run, verbose, specific_file)
        
        if verbose:
            print(f"Summary: {results['processed']} processed, "
                  f"{results['failed']} failed")
        
        sys.exit(0 if results["failed"] == 0 else 1)
    
    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        print_usage()
        sys.exit(1)


if __name__ == "__main__":
    main()
