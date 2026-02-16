"""Drive ingest — Learning from experience.

The ingest system reads session files and uses an LLM to determine which
drives were affected and by how much. This closes the loop between sessions
and drive state, allowing the interoception system to learn from experience.

The ingest stack (three tiers):
1. Default: Local Ollama — Free, private, decent accuracy
2. Upgrade: OpenRouter API — Costs pennies, better accuracy
3. Minimal: Keyword matching — Zero dependency fallback

TODO: Wire ingest into the satisfaction flow (satisfaction.py) for v2 depth
assessment. Currently satisfaction uses deterministic heuristics (error→shallow,
completed→moderate, completed+file writes→deep). Ingest could replace this with
LLM-based analysis of session transcripts for richer depth scoring.
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

from .models import DriveState


# --- Constants ---
OLLAMA_DEFAULT_URL = "http://localhost:11434/api/generate"
OPENROUTER_DEFAULT_URL = "https://openrouter.ai/api/v1/chat/completions"
OLLAMA_DEFAULT_MODEL = "llama3.2:3b"
OPENROUTER_DEFAULT_MODEL = "mistralai/mistral-nemo"

# Drive descriptions for prompt building
DRIVE_DESCRIPTIONS = {
    "CARE": "Attending to the human, relationship maintenance",
    "CURIOSITY": "Intellectual interest, encountering fascinating questions",
    "SOCIAL": "Meaningful human connection, community engagement",
    "CREATIVE": "Making things, building, writing, coding",
    "MAINTENANCE": "System upkeep, health checks, organization",
    "REST": "Recovery from work, consolidation, reflection",
}

# Keyword patterns for fallback analysis
DRIVE_KEYWORDS = {
    "CURIOSITY": [
        "curious",
        "wonder",
        "explore",
        "learn",
        "discover",
        "research",
        "interesting",
        "question",
    ],
    "SOCIAL": ["chat", "conversation", "human", "person", "connect", "talk", "discuss", "message"],
    "CREATIVE": ["write", "code", "build", "create", "make", "design", "implement", "develop"],
    "CARE": ["help", "support", "check in", "attend", "relationship", "assist", "care for"],
    "MAINTENANCE": ["fix", "repair", "clean", "organize", "health check", "update", "maintain"],
    "REST": ["rest", "relax", "recover", "reflect", "consolidate", "pause", "break"],
}


def get_ingest_state_path(config: dict) -> Path:
    """Get path to ingest state file.

    Args:
        config: Configuration dict

    Returns:
        Path to ingest_state.json

    Examples:
        >>> config = {"paths": {"workspace": ".", "state": ".emergence/state"}}
        >>> path = get_ingest_state_path(config)
        >>> "ingest_state.json" in str(path)
        True
    """
    state_dir = config.get("paths", {}).get("state", ".emergence/state")
    workspace = config.get("paths", {}).get("workspace", ".")
    return Path(workspace) / state_dir / "ingest_state.json"


def load_ingest_state(config: dict) -> dict:
    """Load last ingest timestamp from state file.

    Args:
        config: Configuration dict

    Returns:
        Dict with 'last_ingest' ISO timestamp and optional 'processed_files'

    Examples:
        >>> config = {"paths": {"workspace": ".", "state": ".emergence/state"}}
        >>> state = load_ingest_state(config)
        >>> "last_ingest" in state
        True
    """
    state_file = get_ingest_state_path(config)
    if state_file.exists():
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"last_ingest": None, "processed_files": {}}


def save_ingest_state(config: dict, timestamp: Optional[datetime] = None) -> None:
    """Save ingest timestamp after successful run.

    Args:
        config: Configuration dict
        timestamp: Timestamp to save (defaults to now)

    Examples:
        >>> config = {"paths": {"workspace": ".", "state": ".emergence/state"}}
        >>> save_ingest_state(config)
    """
    if timestamp is None:
        timestamp = datetime.now(timezone.utc)

    state_file = get_ingest_state_path(config)
    state_file.parent.mkdir(parents=True, exist_ok=True)

    state = {
        "last_ingest": timestamp.isoformat(),
        "processed_files": {},
    }

    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except IOError as e:
        print(f"⚠ Failed to save ingest state: {e}", file=sys.stderr)


def load_experience_content(
    file_path: Optional[Path] = None,
    recent: bool = False,
    config: Optional[dict] = None,
    since: Optional[datetime] = None,
) -> str:
    """Load experience content from memory files.

    Args:
        file_path: Specific file to load (optional)
        recent: If True, load today's memory files
        config: Configuration dict for path resolution (required if recent=True)
        since: Only include files modified after this timestamp (for deduplication)

    Returns:
        String containing loaded content

    Examples:
        >>> content = load_experience_content(Path("session.md"))
        >>> len(content) > 0
        True
        >>>
        >>> # Load today's files
        >>> content = load_experience_content(recent=True, config=config)
        >>>
        >>> # Load only new files since last ingest
        >>> from datetime import datetime, timezone
        >>> since = datetime.now(timezone.utc)
        >>> content = load_experience_content(recent=True, config=config, since=since)
    """
    if file_path:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except FileNotFoundError:
            print(f"✗ File not found: {file_path}", file=sys.stderr)
            return ""
        except IOError as e:
            print(f"✗ Error reading file: {e}", file=sys.stderr)
            return ""

    if recent:
        if config is None:
            print("✗ Config required for --recent", file=sys.stderr)
            return ""

        today = datetime.now().strftime("%Y-%m-%d")
        files = []

        # Daily memory files
        memory_dir = config.get("memory", {}).get("daily_dir", "memory")
        workspace = config.get("paths", {}).get("workspace", ".")
        daily_pattern = Path(workspace) / memory_dir / f"{today}*.md"
        files.extend(glob(str(daily_pattern)))

        # Session files
        session_dir = config.get("memory", {}).get("session_dir", "memory/sessions")
        session_pattern = Path(workspace) / session_dir / f"{today}*.md"
        files.extend(glob(str(session_pattern)))

        if not files:
            return ""

        # Filter files by modification time if `since` is provided
        if since is not None:
            since_timestamp = since.timestamp()
            filtered_files = []
            for f in files:
                try:
                    mtime = os.path.getmtime(f)
                    if mtime > since_timestamp:
                        filtered_files.append(f)
                except OSError:
                    continue
            files = filtered_files

        if not files:
            return ""

        # Sort by modification time (most recent last)
        files.sort(key=os.path.getmtime)

        content = []
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    text = fh.read()
                    # Take last 4000 chars of each file (most recent content)
                    if len(text) > 4000:
                        text = f"[...truncated...]\n\n{text[-4000:]}"
                    content.append(f"--- {os.path.basename(f)} ---\n{text}")
            except IOError:
                continue

        return "\n\n".join(content)

    return ""


def build_analysis_prompt(content: str, drives: dict) -> str:
    """Build the LLM prompt for drive impact analysis.

    Args:
        content: Experience content to analyze
        drives: Dictionary of drive name -> drive info

    Returns:
        Formatted prompt string for the LLM

    Examples:
        >>> prompt = build_analysis_prompt("Built a tool", {"CURIOSITY": {}})
        >>> "DRIVES:" in prompt
        True
    """
    drive_list = []
    for name in drives.keys():
        desc = DRIVE_DESCRIPTIONS.get(name, drives.get(name, {}).get("description", "Custom drive"))
        drive_list.append(f"- {name}: {desc}")

    drives_section = "\n".join(drive_list)

    # Truncate content to stay within token limits
    truncated_content = content[:6000] if len(content) > 6000 else content

    return f"""Analyze this experience log and determine which internal drives are affected.

DRIVES:
{drives_section}

Rules:
- Positive delta = BUILDS pressure (unmet need, inspiration, encountering something that creates wanting)
- Negative delta = REDUCES pressure (need addressed, satisfaction, completion)
- Range: -30 to +20 per drive
- Only include drives meaningfully affected

SATISFACTION DEPTH — scale negative delta by quality:
- Shallow (token effort): -5 to -10
- Moderate (real work, decent output): -10 to -20
- Deep (meaningful creation, genuine connection): -20 to -30
- Hollow (going through motions): -2 to -5 max

Examples:
- Deep philosophical conversation with human → SOCIAL -25
- Quick browse, no engagement → SOCIAL -5
- Built working tool that solves problem → CREATIVE -25
- Encountered fascinating question → CURIOSITY +15

Return ONLY valid JSON with this structure, no explanation:
{{"impacts": [{{"drive": "NAME", "delta": <number>, "reason": "brief explanation"}}]}}

If nothing meaningfully affects drives, return: {{"impacts": []}}

EXPERIENCE LOG:
{truncated_content}
"""


def parse_impact_response(response_text: str) -> list[dict]:
    """Parse LLM response into structured impacts.

    Handles markdown code blocks and various JSON formats.

    Args:
        response_text: Raw LLM response

    Returns:
        List of impact dicts with drive, delta, and reason keys

    Examples:
        >>> parse_impact_response('{"impacts": [{"drive": "CURIOSITY", "delta": -5, "reason": "test"}]}')
        [{'drive': 'CURIOSITY', 'delta': -5, 'reason': 'test'}]
        >>>
        >>> # Handles markdown code blocks
        >>> text = '```json\\n[{"drive": "CARE", "delta": -10}]\\n```'
        >>> len(parse_impact_response(text)) > 0
        True
    """
    if not response_text:
        return []

    # Extract from markdown code block if present
    if "```" in response_text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", response_text)
        if match:
            response_text = match.group(1)

    response_text = response_text.strip()

    try:
        data = json.loads(response_text)

        # Handle {"impacts": [...]} format
        if isinstance(data, dict) and "impacts" in data:
            impacts = data["impacts"]
            if isinstance(impacts, list):
                return _validate_impacts(impacts)

        # Handle raw array format
        if isinstance(data, list):
            return _validate_impacts(data)

        return []
    except json.JSONDecodeError:
        return []


def _validate_impacts(impacts: list) -> list[dict]:
    """Validate and clean impact list.

    Args:
        impacts: Raw list of impact dicts

    Returns:
        Validated list with only valid impacts
    """
    valid = []
    for impact in impacts:
        if not isinstance(impact, dict):
            continue

        drive = impact.get("drive", "").upper()
        delta = impact.get("delta", 0)
        reason = impact.get("reason", "")

        # Validate required fields
        if not drive:
            continue

        # Validate delta is numeric
        try:
            delta = float(delta)
        except (TypeError, ValueError):
            continue

        # Clamp delta to valid range
        delta = max(-30, min(20, delta))

        valid.append(
            {
                "drive": drive,
                "delta": delta,
                "reason": str(reason) if reason else "No reason provided",
            }
        )

    return valid


def analyze_with_ollama(content: str, drives: dict, config: Optional[dict] = None) -> list[dict]:
    """Send to local Ollama model for drive impact analysis.

    This is the PRIMARY method - free, private, decent accuracy.

    Args:
        content: Experience content to analyze
        drives: Dictionary of drive name -> drive info
        config: Configuration dict with optional ollama_url and ollama_model

    Returns:
        List of impact dicts

    Raises:
        urllib.error.URLError: If Ollama is not available
        Exception: For other API errors

    Examples:
        >>> # Requires Ollama running locally
        >>> impacts = analyze_with_ollama("Built something", {"CREATIVE": {}})
    """
    prompt = build_analysis_prompt(content, drives)

    ollama_url = (config or {}).get("ingest", {}).get("ollama_url", OLLAMA_DEFAULT_URL)
    model = (config or {}).get("ingest", {}).get("ollama_model", OLLAMA_DEFAULT_MODEL)

    req_data = json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "format": "json"}
    ).encode("utf-8")

    req = urllib.request.Request(
        ollama_url, data=req_data, headers={"Content-Type": "application/json"}, method="POST"
    )

    with urllib.request.urlopen(req, timeout=120) as response:
        result = json.loads(response.read().decode("utf-8"))
        reply = result.get("response", "").strip()

    return parse_impact_response(reply)


def analyze_with_openrouter(
    content: str, drives: dict, config: Optional[dict] = None
) -> list[dict]:
    """Send to OpenRouter API for drive impact analysis.

    This is the UPGRADE option - costs money but better accuracy.
    Requires OPENROUTER_API_KEY env var or config.

    Args:
        content: Experience content to analyze
        drives: Dictionary of drive name -> drive info
        config: Configuration dict with optional openrouter_model

    Returns:
        List of impact dicts

    Raises:
        urllib.error.HTTPError: For API errors (401, 429, etc.)
        urllib.error.URLError: For network errors

    Examples:
        >>> # Requires OPENROUTER_API_KEY
        >>> impacts = analyze_with_openrouter("Built something", {"CREATIVE": {}})
    """
    prompt = build_analysis_prompt(content, drives)

    api_key = _get_openrouter_key(config)
    if not api_key:
        raise ValueError("OpenRouter API key not found")

    model = (config or {}).get("ingest", {}).get("openrouter_model", OPENROUTER_DEFAULT_MODEL)

    req_data = json.dumps(
        {
            "model": model,
            "max_tokens": 1000,
            "temperature": 0.1,
            "messages": [{"role": "user", "content": prompt}],
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        OPENROUTER_DEFAULT_URL,
        data=req_data,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )

    with urllib.request.urlopen(req, timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
        reply = result["choices"][0]["message"]["content"].strip()

    return parse_impact_response(reply)


def analyze_with_keywords(content: str, drives: dict) -> list[dict]:
    """Keyword/pattern matching fallback for drive impact analysis.

    This is the MINIMAL fallback - zero dependency, least accurate.
    Used when both Ollama and OpenRouter are unavailable.

    Args:
        content: Experience content to analyze
        drives: Dictionary of drive name -> drive info

    Returns:
        List of impact dicts based on keyword matching

    Examples:
        >>> impacts = analyze_with_keywords("I was curious and explored", {"CURIOSITY": {}})
        >>> len(impacts) > 0
        True
    """
    impacts = []
    content_lower = content.lower()

    for drive_name in drives.keys():
        keywords = DRIVE_KEYWORDS.get(drive_name, [])
        if not keywords:
            continue

        matches = sum(1 for kw in keywords if kw in content_lower)

        if matches > 0:
            # Simple heuristic: mentions suggest some satisfaction
            # Cap at -5 per drive for keyword fallback
            delta = max(-5 * matches, -10)
            impacts.append(
                {"drive": drive_name, "delta": delta, "reason": f"Keyword matches: {matches}"}
            )

    return impacts


def analyze_content(
    content: str, drives: dict, config: Optional[dict] = None, verbose: bool = False
) -> list[dict]:
    """Orchestrator: Try Ollama → OpenRouter → keywords.

    Args:
        content: Experience content to analyze
        drives: Dictionary of drive name -> drive info
        config: Configuration dict
        verbose: If True, print progress messages

    Returns:
        List of impact dicts (empty if all methods fail)

    Examples:
        >>> impacts = analyze_content("Built something", {"CREATIVE": {}}, verbose=True)
    """
    # 1. Try Ollama first (local, free)
    try:
        if verbose:
            print("🧠 Analyzing with Ollama...")
        return analyze_with_ollama(content, drives, config)
    except urllib.error.URLError as e:
        if verbose:
            print(f"⚠ Ollama not available: {e.reason}")
    except Exception as e:
        if verbose:
            print(f"⚠ Ollama analysis failed: {e}")

    # 2. Try OpenRouter if configured
    if _get_openrouter_key(config):
        try:
            if verbose:
                print("🧠 Trying OpenRouter fallback...")
            return analyze_with_openrouter(content, drives, config)
        except urllib.error.HTTPError as e:
            if verbose:
                print(f"⚠ OpenRouter API error (HTTP {e.code})")
        except Exception as e:
            if verbose:
                print(f"⚠ OpenRouter analysis failed: {e}")
    else:
        if verbose:
            print("⚠ OpenRouter not configured (no API key)")

    # 3. Fallback to keyword matching
    if verbose:
        print("🧠 Using keyword fallback...")
    return analyze_with_keywords(content, drives)


def apply_impacts(state: DriveState, impacts: list[dict]) -> tuple[DriveState, list[str]]:
    """Apply drive pressure changes from analysis.

    Args:
        state: Current drive state (modified in place)
        impacts: List of impact dicts with drive, delta, and reason

    Returns:
        Tuple of (updated_state, change_descriptions)

    Examples:
        >>> from .models import create_default_state
        >>> state = create_default_state()
        >>> impacts = [{"drive": "CARE", "delta": -5, "reason": "test"}]
        >>> state, changes = apply_impacts(state, impacts)
        >>> len(changes) > 0
        True
    """
    changes = []
    state_drives = state.get("drives", {})
    triggered = state.get("triggered_drives", [])
    max_ratio = 1.5  # Same cap as in engine.py

    for impact in impacts:
        drive_name = impact.get("drive", "").upper()
        delta = impact.get("delta", 0)
        reason = impact.get("reason", "")

        if drive_name not in state_drives:
            changes.append(f"⚠ Unknown drive: {drive_name}")
            continue

        drive = state_drives[drive_name]
        old_pressure = drive.get("pressure", 0.0)
        threshold = drive.get("threshold", 1.0)

        # Apply delta with bounds
        new_pressure = old_pressure + delta
        new_pressure = max(0.0, min(new_pressure, threshold * max_ratio))
        drive["pressure"] = new_pressure

        # Remove from triggered if significantly reduced
        if delta < -5 and drive_name in triggered:
            triggered.remove(drive_name)

        # Build change description
        direction = "↑" if delta > 0 else "↓" if delta < 0 else "→"
        changes.append(
            f"{direction} {drive_name}: {old_pressure:.1f} → {new_pressure:.1f} "
            f"({delta:+.0f}) — {reason}"
        )

    return state, changes


def _get_openrouter_key(config: Optional[dict] = None) -> Optional[str]:
    """Get OpenRouter API key from various sources.

    Search order:
    1. Config file (ingest.openrouter_api_key)
    2. Environment variable OPENROUTER_API_KEY
    3. Key file ~/.openclaw/openrouter-key

    Args:
        config: Configuration dict (optional)

    Returns:
        API key string or None if not found
    """
    # 1. Config file
    if config:
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


def log_ingest_event(
    drive_name: str,
    pressure: float,
    threshold: float,
    reason: str,
    delta: float,
    config: Optional[dict] = None,
) -> None:
    """Log an ingest event to the trigger log.

    Args:
        drive_name: Name of the affected drive
        pressure: New pressure level
        threshold: Drive threshold
        reason: Explanation for the impact
        delta: Pressure change amount
        config: Configuration dict for path resolution
    """
    from .history import add_trigger_event

    event_type = "INGEST-" + ("SAT" if delta < 0 else "STIM" if delta > 0 else "NEUT")

    add_trigger_event(
        drive=drive_name,
        pressure=pressure,
        threshold=threshold,
        reason=f"{event_type}: {reason} ({delta:+.0f})",
        config=config,
    )
