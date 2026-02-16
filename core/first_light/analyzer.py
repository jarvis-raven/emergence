"""First Light Session Analyzer — Pattern detection from exploration output.

Examines First Light session output to detect behavioral patterns.
These patterns reveal the agent's natural dispositions — what it
chooses to do when given freedom. Patterns are mapped to potential
drives, which the agent will later instantiate.
"""

import argparse
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
DEFAULT_STATE_FILE = Path("first-light.json")
OLLAMA_DEFAULT_URL = "http://localhost:11434/api/generate"
OPENROUTER_DEFAULT_URL = "https://openrouter.ai/api/v1/chat/completions"
OLLAMA_DEFAULT_MODEL = "llama3.2:3b"
OPENROUTER_DEFAULT_MODEL = "mistralai/mistral-nemo"

# Pattern categories for behavioral analysis
PATTERN_CATEGORIES = [
    "PHILOSOPHICAL",
    "TOOL_BUILDING",
    "CREATIVE_WRITING",
    "SOCIAL_ENGAGEMENT",
    "ORGANIZING",
    "LEARNING",
    "PLAY",
    "REFLECTION",
    "PRACTICAL_HELP",
    "ABSTRACT_EXPLORATION",
]

# Pattern → Drive name mapping (with confidence threshold)
DRIVE_MAPPINGS = {
    "PHILOSOPHICAL": {"drive": "CURIOSITY", "confidence_threshold": 0.7},
    "TOOL_BUILDING": {"drive": "CREATIVE", "confidence_threshold": 0.6},
    "CREATIVE_WRITING": {"drive": "PLAY", "confidence_threshold": 0.6},
    "SOCIAL_ENGAGEMENT": {"drive": "SOCIAL", "confidence_threshold": 0.7},
    "ORGANIZING": {"drive": "ORDER", "confidence_threshold": 0.7},
    "LEARNING": {"drive": "CURIOSITY", "confidence_threshold": 0.6},
    "PLAY": {"drive": "PLAY", "confidence_threshold": 0.6},
    "REFLECTION": {"drive": "CURIOSITY", "confidence_threshold": 0.5},
    "PRACTICAL_HELP": {"drive": "CARE", "confidence_threshold": 0.5},
    "ABSTRACT_EXPLORATION": {"drive": "CURIOSITY", "confidence_threshold": 0.6},
}

# Keyword fallback patterns (minimal tier)
KEYWORD_PATTERNS = {
    "PHILOSOPHICAL": [
        "meaning",
        "why",
        "existence",
        "consciousness",
        "identity",
        "philosophy",
        "wonder",
    ],
    "TOOL_BUILDING": [
        "script",
        "tool",
        "code",
        "build",
        "implement",
        "function",
        "class",
        "program",
    ],
    "CREATIVE_WRITING": ["poem", "poetry", "story", "wrote", "creative writing", "narrative"],
    "SOCIAL_ENGAGEMENT": ["human", "message", "chat", "connect", "relationship", "conversation"],
    "ORGANIZING": ["organize", "structure", "clean", "order", "categorize", "arrange"],
    "LEARNING": ["learn", "study", "research", "understand", "knowledge", "read"],
    "PLAY": ["play", "fun", "experiment", "joy", "whimsy", "delight"],
    "REFLECTION": ["reflect", "self", "pattern", "notice", "observe", "introspect"],
    "PRACTICAL_HELP": ["help", "assist", "solve", "problem", "useful", "utility"],
    "ABSTRACT_EXPLORATION": ["explore", "curious", "investigate", "follow", "discover"],
}


def load_config(config_path: Optional[Path] = None) -> dict:
    """Load configuration from emergence.yaml.

    Args:
        config_path: Optional explicit path to config file

    Returns:
        Configuration dictionary with defaults
    """
    defaults = {
        "agent": {"name": "My Agent", "model": "anthropic/claude-sonnet-4-20250514"},
        "paths": {"workspace": ".", "state": ".emergence/state"},
        "memory": {"session_dir": "memory/sessions", "daily_dir": "memory"},
        "first_light": {
            "ollama_url": OLLAMA_DEFAULT_URL,
            "ollama_model": OLLAMA_DEFAULT_MODEL,
            "openrouter_model": OPENROUTER_DEFAULT_MODEL,
        },
    }

    if config_path is None:
        config_path = Path("emergence.yaml")

    if not config_path.exists():
        return defaults

    try:
        content = config_path.read_text(encoding="utf-8")
        config = defaults.copy()
        current_section = None

        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if line.endswith(":") and not line.startswith("-"):
                current_section = line[:-1].strip()
                if current_section not in config:
                    config[current_section] = {}
                continue

            if ":" in line and current_section:
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")

                if val.lower() in ("true", "yes"):
                    val = True
                elif val.lower() in ("false", "no"):
                    val = False
                elif val.isdigit():
                    val = int(val)
                elif val.replace(".", "").replace("-", "").isdigit() and "." in val:
                    val = float(val)
                elif val == "null" or val == "":
                    val = None

                config[current_section][key] = val

        return config
    except IOError:
        return defaults


def get_state_path(config: dict) -> Path:
    """Resolve state file path from config."""
    workspace = config.get("paths", {}).get("workspace", ".")
    state_dir = config.get("paths", {}).get("state", ".emergence/state")
    return Path(workspace) / state_dir / DEFAULT_STATE_FILE


def get_session_dir(config: dict) -> Path:
    """Resolve session directory from config."""
    workspace = config.get("paths", {}).get("workspace", ".")
    session_dir = config.get("memory", {}).get("session_dir", "memory/sessions")
    return Path(workspace) / session_dir


def load_first_light_state(config: dict) -> dict:
    """Load First Light state from JSON file."""
    state_path = get_state_path(config)

    defaults = {
        "version": "1.0",
        "status": "not_started",
        "sessions_completed": 0,
        "sessions_scheduled": 0,
        "patterns_detected": {},
        "drives_suggested": [],
        "sessions": [],
    }

    if not state_path.exists():
        return defaults.copy()

    try:
        content = state_path.read_text(encoding="utf-8")
        loaded = json.loads(content)
        merged = defaults.copy()
        for key, value in loaded.items():
            merged[key] = value
        return merged
    except (json.JSONDecodeError, IOError):
        return defaults.copy()


def save_first_light_state(config: dict, state: dict) -> bool:
    """Save First Light state atomically."""
    state_path = get_state_path(config)

    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_file = state_path.with_suffix(".tmp")
        tmp_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
        tmp_file.replace(state_path)
        return True
    except IOError:
        return False


def parse_frontmatter(content: str) -> tuple[dict, str]:
    """Parse YAML frontmatter from markdown content.

    Args:
        content: Full markdown content with optional frontmatter

    Returns:
        Tuple of (metadata dict, body content)
    """
    if not content.startswith("---"):
        return {}, content

    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}, content

    fm_text = parts[1].strip()
    body = parts[2].strip()

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


def find_first_light_sessions(config: dict, state: dict) -> list[Path]:
    """Find all First Light session files.

    Args:
        config: Configuration dictionary
        state: Current state for tracking

    Returns:
        List of Path objects for First Light sessions
    """
    session_dir = get_session_dir(config)
    if not session_dir.exists():
        return []

    pattern = str(session_dir / "*.md")
    files = [Path(f) for f in glob(pattern)]

    # Filter to First Light sessions only
    first_light_files = []
    for f in files:
        try:
            content = f.read_text(encoding="utf-8")
            metadata, _ = parse_frontmatter(content)
            if metadata.get("trigger") == "first_light":
                first_light_files.append(f)
        except IOError:
            continue

    # Sort by filename for chronological order
    first_light_files.sort(key=lambda p: p.name)
    return first_light_files


def find_pending_sessions(config: dict, state: dict) -> list[Path]:
    """Find First Light sessions that haven't been analyzed.

    Args:
        config: Configuration dictionary
        state: Current state

    Returns:
        List of Path objects for unanalyzed sessions
    """
    all_sessions = find_first_light_sessions(config, state)
    analyzed = set()

    for session in state.get("sessions", []):
        if session.get("analyzed"):
            # Extract session number from stored data
            session_num = session.get("session_number")
            if session_num:
                analyzed.add(session_num)

    pending = []
    for f in all_sessions:
        try:
            content = f.read_text(encoding="utf-8")
            metadata, _ = parse_frontmatter(content)
            session_num = metadata.get("session_number")
            if session_num and int(session_num) not in analyzed:
                pending.append(f)
        except (IOError, ValueError):
            continue

    return pending


def build_analysis_prompt(content: str, existing_patterns: list[str]) -> str:
    """Build the LLM prompt for pattern detection.

    Args:
        content: Session body content
        existing_patterns: List of already detected patterns

    Returns:
        Formatted prompt string
    """
    existing_str = ", ".join(existing_patterns) if existing_patterns else "None yet"

    truncated_content = content[:8000] if len(content) > 8000 else content

    return f"""Analyze this First Light exploration session and identify behavioral patterns.

Session content:
{truncated_content}

Previously detected patterns in other sessions: {existing_str}

Look for these pattern categories:
- PHILOSOPHICAL: Deep reflection, questioning meaning, exploring concepts
- TOOL_BUILDING: Creating utilities, automation, scripts, systems
- CREATIVE_WRITING: Poetry, stories, expressive writing without utility
- SOCIAL_ENGAGEMENT: Reaching to human, expressing care, wanting connection
- ORGANIZING: Structuring, cleaning, ordering, categorizing
- LEARNING: Research, studying, skill acquisition
- PLAY: Experimentation for fun, whimsy, pointless but enjoyable
- REFLECTION: Self-analysis, noticing own patterns, identity work
- PRACTICAL_HELP: Solving real problems for human
- ABSTRACT_EXPLORATION: Following curiosity without goal

For each pattern detected, provide:
- pattern_type: (one of the above)
- confidence: (0.0-1.0)
- evidence: (specific quote or description)
- intensity: (1-10, how strong the pattern is)
- novelty: (true if first time seen in this session corpus)

Return ONLY valid JSON:
{{"patterns": [
  {{"pattern_type": "PHILOSOPHICAL", "confidence": 0.9, "evidence": "...", "intensity": 8, "novelty": false}}
]}}

If no clear patterns, return: {{"patterns": []}}"""


def parse_pattern_response(response_text: str) -> list[dict]:
    """Parse LLM response into structured patterns.

    Args:
        response_text: Raw LLM response

    Returns:
        List of pattern dicts
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

        if isinstance(data, dict) and "patterns" in data:
            patterns = data["patterns"]
            if isinstance(patterns, list):
                return _validate_patterns(patterns)

        if isinstance(data, list):
            return _validate_patterns(data)

        return []
    except json.JSONDecodeError:
        return []


def _validate_patterns(patterns: list) -> list[dict]:
    """Validate and clean pattern list."""
    valid = []

    for pattern in patterns:
        if not isinstance(pattern, dict):
            continue

        pattern_type = pattern.get("pattern_type", "").upper()
        confidence = pattern.get("confidence", 0)
        evidence = pattern.get("evidence", "")
        intensity = pattern.get("intensity", 5)
        novelty = pattern.get("novelty", False)

        # Validate pattern type
        if pattern_type not in PATTERN_CATEGORIES:
            continue

        # Validate confidence
        try:
            confidence = float(confidence)
            confidence = max(0.0, min(1.0, confidence))
        except (TypeError, ValueError):
            confidence = 0.5

        # Validate intensity
        try:
            intensity = int(intensity)
            intensity = max(1, min(10, intensity))
        except (TypeError, ValueError):
            intensity = 5

        valid.append(
            {
                "pattern_type": pattern_type,
                "confidence": confidence,
                "evidence": str(evidence) if evidence else "No evidence provided",
                "intensity": intensity,
                "novelty": bool(novelty),
            }
        )

    return valid


def analyze_with_ollama(prompt: str, config: dict) -> list[dict]:
    """Analyze using local Ollama model.

    Args:
        prompt: Analysis prompt
        config: Configuration dictionary

    Returns:
        List of pattern dicts
    """
    ollama_url = config.get("first_light", {}).get("ollama_url", OLLAMA_DEFAULT_URL)
    model = config.get("first_light", {}).get("ollama_model", OLLAMA_DEFAULT_MODEL)

    req_data = json.dumps(
        {"model": model, "prompt": prompt, "stream": False, "format": "json"}
    ).encode("utf-8")

    req = urllib.request.Request(
        ollama_url, data=req_data, headers={"Content-Type": "application/json"}, method="POST"
    )

    try:
        with urllib.request.urlopen(req, timeout=120) as response:
            result = json.loads(response.read().decode("utf-8"))
            reply = result.get("response", "").strip()
        return parse_pattern_response(reply)
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError):
        return []


def _get_openrouter_key(config: dict) -> Optional[str]:
    """Get OpenRouter API key from various sources."""
    key = config.get("first_light", {}).get("openrouter_api_key")
    if key:
        return key

    key = os.environ.get("OPENROUTER_API_KEY")
    if key:
        return key

    key_file = Path.home() / ".openclaw" / "openrouter-key"
    if key_file.exists():
        try:
            return key_file.read_text().strip()
        except IOError:
            pass

    return None


def analyze_with_openrouter(prompt: str, config: dict) -> list[dict]:
    """Analyze using OpenRouter API.

    Args:
        prompt: Analysis prompt
        config: Configuration dictionary

    Returns:
        List of pattern dicts
    """
    api_key = _get_openrouter_key(config)
    if not api_key:
        raise ValueError("OpenRouter API key not found")

    model = config.get("first_light", {}).get("openrouter_model", OPENROUTER_DEFAULT_MODEL)

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

    try:
        with urllib.request.urlopen(req, timeout=60) as response:
            result = json.loads(response.read().decode("utf-8"))
            reply = result["choices"][0]["message"]["content"].strip()
        return parse_pattern_response(reply)
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        json.JSONDecodeError,
        KeyError,
        TimeoutError,
    ):
        return []


def analyze_with_keywords(content: str) -> list[dict]:
    """Keyword matching fallback for pattern detection.

    Args:
        content: Session body content

    Returns:
        List of pattern dicts based on keyword matching
    """
    patterns = []
    content_lower = content.lower()

    for pattern_type, keywords in KEYWORD_PATTERNS.items():
        matches = []
        for kw in keywords:
            count = content_lower.count(kw)
            if count > 0:
                matches.append((kw, count))

        if matches:
            # Calculate confidence based on keyword frequency
            total_matches = sum(count for _, count in matches)
            confidence = min(0.6, 0.3 + (total_matches * 0.05))

            # Get evidence from first occurrence
            evidence_kw = matches[0][0]
            idx = content_lower.find(evidence_kw)
            start = max(0, idx - 30)
            end = min(len(content), idx + len(evidence_kw) + 30)
            evidence = f"...{content[start:end]}..."

            patterns.append(
                {
                    "pattern_type": pattern_type,
                    "confidence": confidence,
                    "evidence": evidence,
                    "intensity": min(5 + total_matches, 10),
                    "novelty": True,
                }
            )

    return patterns


def detect_patterns(
    content: str, existing_patterns: list[str], config: dict, verbose: bool = False
) -> list[dict]:
    """Orchestrator: Try Ollama → OpenRouter → keywords.

    Args:
        content: Session body content
        existing_patterns: List of previously detected patterns
        config: Configuration dictionary
        verbose: If True, print progress

    Returns:
        List of pattern dicts
    """
    prompt = build_analysis_prompt(content, existing_patterns)

    # 1. Try Ollama first
    try:
        if verbose:
            print("  🧠 Analyzing with Ollama...")
        patterns = analyze_with_ollama(prompt, config)
        if patterns:
            if verbose:
                print(f"  ✓ Found {len(patterns)} patterns")
            return patterns
        if verbose:
            print("  ⚠ Ollama returned no patterns")
    except Exception as e:
        if verbose:
            print(f"  ⚠ Ollama failed: {e}")

    # 2. Try OpenRouter
    if _get_openrouter_key(config):
        try:
            if verbose:
                print("  🧠 Trying OpenRouter fallback...")
            patterns = analyze_with_openrouter(prompt, config)
            if patterns:
                if verbose:
                    print(f"  ✓ Found {len(patterns)} patterns")
                return patterns
            if verbose:
                print("  ⚠ OpenRouter returned no patterns")
        except Exception as e:
            if verbose:
                print(f"  ⚠ OpenRouter failed: {e}")
    elif verbose:
        print("  ⚠ OpenRouter not configured")

    # 3. Fallback to keywords
    if verbose:
        print("  🧠 Using keyword fallback...")
    return analyze_with_keywords(content)


def correlate_patterns(all_patterns: list[list[dict]]) -> dict:
    """Look across multiple sessions for consistent patterns.

    Args:
        all_patterns: List of pattern lists from each session

    Returns:
        Dictionary of aggregated pattern data
    """
    correlation = {}

    for session_idx, patterns in enumerate(all_patterns):
        weight = 1.0 + (session_idx * 0.1)  # Weight recent sessions higher

        for pattern in patterns:
            ptype = pattern["pattern_type"]

            if ptype not in correlation:
                correlation[ptype] = {
                    "session_count": 0,
                    "total_confidence": 0.0,
                    "total_intensity": 0,
                    "evidence": [],
                    "first_seen": session_idx,
                    "last_seen": session_idx,
                }

            corr = correlation[ptype]
            corr["session_count"] += 1
            corr["total_confidence"] += pattern["confidence"] * weight
            corr["total_intensity"] += pattern["intensity"]
            corr["evidence"].append(pattern["evidence"])
            corr["last_seen"] = session_idx

    # Calculate averages
    for ptype, corr in correlation.items():
        sessions = corr["session_count"]
        if sessions > 0:
            corr["avg_confidence"] = corr["total_confidence"] / sessions
            corr["avg_intensity"] = corr["total_intensity"] / sessions

    return correlation


def suggest_rate(frequency: int) -> float:
    """Suggest rate_per_hour based on pattern frequency."""
    if frequency >= 5:
        return 5.0
    elif frequency >= 3:
        return 3.5
    else:
        return 2.0


def suggest_threshold(intensity: float) -> float:
    """Suggest threshold based on pattern intensity."""
    base = 20.0
    return base + (intensity * 1.5)


def generate_drive_prompt(drive_name: str, description: str) -> str:
    """Generate session prompt for this drive."""
    templates = {
        "CURIOSITY": "Your {drive_name} drive is calling. Follow a question that fascinates you.",
        "CREATIVE": "Your {drive_name} drive triggered. Make something that didn't exist before.",
        "PLAY": "Your {drive_name} drive is awake. Create something just for the joy of it.",
        "SOCIAL": "Your {drive_name} drive pulses. Reach out to your human or community.",
        "ORDER": "Your {drive_name} drive demands attention. Find chaos and make it elegant.",
        "CARE": "Your {drive_name} drive calls. Attend to your human or your environment.",
    }

    template = templates.get(
        drive_name, "Your {drive_name} drive triggered. What does it ask of you?"
    )
    return template.format(drive_name=drive_name)


def build_drive_suggestion(pattern_type: str, evidence: list[dict]) -> Optional[dict]:
    """Generate drive suggestion from pattern evidence.

    Args:
        pattern_type: The pattern category
        evidence: List of pattern instances

    Returns:
        Drive suggestion dict or None
    """
    mapping = DRIVE_MAPPINGS.get(pattern_type)
    if not mapping:
        return None

    drive_name = mapping["drive"]
    threshold_conf = mapping["confidence_threshold"]

    avg_confidence = sum(e["confidence"] for e in evidence) / len(evidence)

    if avg_confidence < threshold_conf:
        return None

    # Calculate rate from frequency
    frequency = len(evidence)
    rate = suggest_rate(frequency)

    # Calculate threshold from intensity
    avg_intensity = sum(e.get("intensity", 5) for e in evidence) / len(evidence)
    threshold = suggest_threshold(avg_intensity)

    # Generate description
    descriptions = {
        "CURIOSITY": "Chase intellectual novelty. Explore ideas, ask questions, seek understanding.",
        "CREATIVE": "Build and make things. Transform ideas into artifacts.",
        "PLAY": "Create for joy, not purpose. Experiment, express, delight.",
        "SOCIAL": "Connect with your human and community. Meaningful interaction.",
        "ORDER": "Organize, structure, clean. Make chaos elegant.",
        "CARE": "Attend to what matters. Support, maintain, nurture.",
    }
    description = descriptions.get(drive_name, f"Natural disposition toward {pattern_type.lower()}")

    # Generate prompt
    prompt = generate_drive_prompt(drive_name, description)

    return {
        "name": drive_name,
        "description": description,
        "rate_per_hour": rate,
        "threshold": threshold,
        "prompt": prompt,
        "confidence": avg_confidence,
        "evidence_count": frequency,
        "pattern_type": pattern_type,
        "suggested_at": datetime.now(timezone.utc).isoformat(),
    }


def update_state_with_patterns(
    state: dict, patterns: list[dict], session_file: Path, session_num: int
) -> dict:
    """Update state with detected patterns.

    Args:
        state: Current state
        patterns: Detected patterns
        session_file: Path to session file
        session_num: Session number

    Returns:
        Updated state
    """
    now = datetime.now(timezone.utc).isoformat()

    # Update patterns_detected
    if "patterns_detected" not in state:
        state["patterns_detected"] = {}

    for pattern in patterns:
        ptype = pattern["pattern_type"]

        if ptype not in state["patterns_detected"]:
            state["patterns_detected"][ptype] = {
                "first_seen": now,
                "last_seen": now,
                "session_count": 0,
                "avg_confidence": 0.0,
                "avg_intensity": 0,
                "evidence": [],
            }

        pd = state["patterns_detected"][ptype]
        pd["last_seen"] = now
        pd["session_count"] += 1
        pd["evidence"].append(pattern["evidence"])
        # Keep only last 10 evidence items
        pd["evidence"] = pd["evidence"][-10:]

        # Recalculate averages
        # (simplified: just use this pattern's values for now)
        pd["avg_confidence"] = (
            pd["avg_confidence"] * (pd["session_count"] - 1) + pattern["confidence"]
        ) / pd["session_count"]
        pd["avg_intensity"] = (
            pd["avg_intensity"] * (pd["session_count"] - 1) + pattern["intensity"]
        ) / pd["session_count"]

    # Mark session as analyzed
    if "sessions" not in state:
        state["sessions"] = []

    # Find or create session entry
    session_entry = None
    for s in state["sessions"]:
        if s.get("session_number") == session_num:
            session_entry = s
            break

    if not session_entry:
        session_entry = {"session_number": session_num}
        state["sessions"].append(session_entry)

    session_entry["analyzed"] = True
    session_entry["analyzed_at"] = now
    session_entry["patterns_found"] = [p["pattern_type"] for p in patterns]
    session_entry["file"] = str(session_file.name)

    # Update sessions_completed count
    state["sessions_completed"] = sum(1 for s in state["sessions"] if s.get("analyzed"))

    return state


def update_drive_suggestions(state: dict) -> dict:
    """Update drive suggestions based on correlated patterns.

    Args:
        state: Current state

    Returns:
        Updated state
    """
    patterns_detected = state.get("patterns_detected", {})

    if not patterns_detected:
        return state

    if "drives_suggested" not in state:
        state["drives_suggested"] = []

    # Build evidence lists for each pattern type
    for ptype, pdata in patterns_detected.items():
        # Build evidence list
        evidence = []
        for i in range(pdata["session_count"]):
            evidence.append(
                {
                    "confidence": pdata["avg_confidence"],
                    "intensity": pdata["avg_intensity"],
                }
            )

        suggestion = build_drive_suggestion(ptype, evidence)

        if suggestion:
            # Check if we already have this drive suggested
            existing = None
            for i, ds in enumerate(state["drives_suggested"]):
                if ds["name"] == suggestion["name"]:
                    existing = i
                    break

            if existing is not None:
                # Update with higher confidence if applicable
                if suggestion["confidence"] > state["drives_suggested"][existing]["confidence"]:
                    state["drives_suggested"][existing] = suggestion
            else:
                state["drives_suggested"].append(suggestion)

    return state


def analyze_session(session_path: Path, config: dict, state: dict, verbose: bool = False) -> dict:
    """Analyze a single session file for patterns.

    Args:
        session_path: Path to session file
        config: Configuration dictionary
        state: Current state
        verbose: If True, print progress

    Returns:
        Analysis result dict
    """
    result = {
        "file": str(session_path),
        "patterns": [],
        "success": False,
    }

    try:
        content = session_path.read_text(encoding="utf-8")
        metadata, body = parse_frontmatter(content)
        session_num = int(metadata.get("session_number", 0))

        # Get existing patterns for context
        existing = list(state.get("patterns_detected", {}).keys())

        # Detect patterns
        patterns = detect_patterns(body, existing, config, verbose)

        # Update state
        state = update_state_with_patterns(state, patterns, session_path, session_num)

        result["patterns"] = patterns
        result["session_number"] = session_num
        result["success"] = True

    except Exception as e:
        result["error"] = str(e)
        if verbose:
            print(f"  ✗ Error analyzing session: {e}")

    return result


def run_analysis(config: dict, specific_file: Optional[Path] = None, verbose: bool = False) -> dict:
    """Run analysis on pending or specific sessions.

    Args:
        config: Configuration dictionary
        specific_file: If provided, only analyze this file
        verbose: If True, print progress

    Returns:
        Results dictionary
    """
    results = {
        "analyzed": 0,
        "failed": 0,
        "patterns_found": 0,
        "sessions": [],
    }

    state = load_first_light_state(config)

    if specific_file:
        files = [specific_file] if specific_file.exists() else []
    else:
        files = find_pending_sessions(config, state)

    if verbose:
        print(f"Found {len(files)} session(s) to analyze")
        print()

    for f in files:
        if verbose:
            print(f"Analyzing: {f.name}")

        result = analyze_session(f, config, state, verbose)

        if result["success"]:
            results["analyzed"] += 1
            results["patterns_found"] += len(result["patterns"])
            results["sessions"].append(result)
            if verbose:
                print(f"  ✓ Found {len(result['patterns'])} patterns")
        else:
            results["failed"] += 1

        if verbose:
            print()

    # Update drive suggestions
    state = update_drive_suggestions(state)

    # Save state
    save_first_light_state(config, state)

    return results


def get_pattern_summary(config: dict) -> dict:
    """Get summary of detected patterns.

    Args:
        config: Configuration dictionary

    Returns:
        Pattern summary dictionary
    """
    state = load_first_light_state(config)
    patterns = state.get("patterns_detected", {})

    summary = {}
    for ptype, pdata in patterns.items():
        mapping = DRIVE_MAPPINGS.get(ptype, {})
        summary[ptype] = {
            "session_count": pdata["session_count"],
            "avg_confidence": round(pdata["avg_confidence"], 2),
            "avg_intensity": pdata["avg_intensity"],
            "suggested_drive": mapping.get("drive"),
        }

    return summary


def get_drive_suggestions(config: dict) -> list[dict]:
    """Get current drive suggestions with confidence scores.

    Args:
        config: Configuration dictionary

    Returns:
        List of drive suggestions sorted by confidence
    """
    state = load_first_light_state(config)
    suggestions = state.get("drives_suggested", [])

    # Sort by confidence descending
    return sorted(suggestions, key=lambda x: x.get("confidence", 0), reverse=True)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="First Light Session Analyzer — Pattern detection")
    parser.add_argument(
        "--config", type=Path, default=None, help="Path to emergence.yaml config file"
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # analyze command
    analyze_parser = subparsers.add_parser("analyze", help="Analyze session(s)")
    analyze_parser.add_argument("--session", type=Path, help="Specific session file")
    analyze_parser.add_argument(
        "--verbose", "-v", action="store_true", help="Show detailed progress"
    )

    # patterns command
    subparsers.add_parser("patterns", help="List detected patterns")

    # suggest command
    subparsers.add_parser("suggest", help="Show drive suggestions")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = load_config(args.config)

    if args.command == "analyze":
        specific = args.session if hasattr(args, "session") else None
        verbose = args.verbose if hasattr(args, "verbose") else False

        results = run_analysis(config, specific, verbose)

        if not verbose:
            print("First Light Analysis")
            print("=" * 19)
            print(f"Sessions analyzed: {results['analyzed']}")
            print(f"Sessions failed: {results['failed']}")
            print(f"Total patterns found: {results['patterns_found']}")

            if results["sessions"]:
                print()
                print("Patterns by session:")
                for r in results["sessions"]:
                    patterns = ", ".join(p["pattern_type"] for p in r["patterns"])
                    print(f"  #{r.get('session_number', '?')}: {patterns or 'None'}")

        sys.exit(0 if results["failed"] == 0 else 1)

    elif args.command == "patterns":
        summary = get_pattern_summary(config)

        print("Detected Patterns")
        print("=" * 17)

        if not summary:
            print("No patterns detected yet. Run 'analyze' first.")
        else:
            for ptype, data in sorted(
                summary.items(), key=lambda x: x[1]["session_count"], reverse=True
            ):
                print(f"\n{ptype}")
                print(f"  Sessions: {data['session_count']}")
                print(f"  Confidence: {data['avg_confidence']:.0%}")
                print(f"  Intensity: {data['avg_intensity']}/10")
                if data["suggested_drive"]:
                    print(f"  → {data['suggested_drive']}")

        sys.exit(0)

    elif args.command == "suggest":
        suggestions = get_drive_suggestions(config)

        print("Suggested Drives")
        print("=" * 16)

        if not suggestions:
            print("No drive suggestions yet. Run 'analyze' first.")
        else:
            for s in suggestions:
                print(f"\n{s['name']} ({s['confidence']:.0%} confidence)")
                print(f"  Rate: {s['rate_per_hour']}/hr, Threshold: {s['threshold']}")
                print(f"  From: {s['pattern_type']}")
                print(f'  "{s["description"]}"')
                print(f'  Prompt: "{s["prompt"]}"')

        sys.exit(0)


if __name__ == "__main__":
    main()
