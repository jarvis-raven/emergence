#!/usr/bin/env python3
"""Config Generation — Interactive wizard for creating emergence.json configuration.

Feature F030: Generates validated, commented JSON configuration for Emergence agents.
Uses Python 3.9+ stdlib only — zero pip dependencies.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Union

# Import branding for styled output
try:
    from .branding import (
        print_header,
        print_subheader,
        print_success,
        print_warning,
        print_dim,
        console,
    )
    from .model_pricing import get_suggested_budget

    HAS_RICH_BRANDING = True
except ImportError:
    # Fallback if branding module not available
    def print_header(text):
        print(f"\n=== {text} ===")

    def print_subheader(text):
        print(f"\n▸ {text}")

    def print_success(text):
        print(f"✓ {text}")

    def print_warning(text):
        print(f"⚠ {text}")

    def print_dim(text):
        print(text)

    console = None
    HAS_RICH_BRANDING = False

# --- Constants ---
VERSION = "1.0.0"

# Default model per critical correction #1
DEFAULT_MODEL = "anthropic/claude-sonnet-4-20250514"

# Valid model provider prefixes
VALID_MODEL_PREFIXES = [
    "anthropic/",
    "openai/",
    "openrouter/",
    "google/",
    "mistral/",
    "cohere/",
    "meta-llama/",
    "moonshotai/",
    "ollama/",
]

# Token estimates per session size
SESSION_SIZE_TOKENS = {
    "small": 2000,
    "medium": 8000,
    "large": 32000,
}

# Preset configurations for First Light
FIRST_LIGHT_PRESETS = {
    "patient": {"sessions_per_day": 1, "session_size": "small"},
    "balanced": {"sessions_per_day": 3, "session_size": "medium"},
    "accelerated": {"sessions_per_day": 6, "session_size": "large"},
}

# Rough cost per 1K tokens (input + output averaged) by model family
MODEL_COST_PER_1K = {
    "kimi": 0.002,
    "haiku": 0.003,
    "sonnet": 0.015,
    "opus": 0.075,
    "gpt-4o": 0.015,
    "ollama": 0.0,
    "local": 0.0,
    "llama": 0.0,
}

# Legacy constant kept for backward compatibility
COST_PER_1K_TOKENS = 0.015


# --- Comment Stripping ---


def strip_json_comments(text: str) -> str:
    """Remove // and # style comments from JSON content.

    Supports:
    - // single-line comments
    - # single-line comments (but NOT inside strings)

    Args:
        text: Raw JSON content potentially containing comments

    Returns:
        Clean JSON string suitable for json.loads()
    """
    lines = []

    for line in text.split("\n"):
        # Handle // comments (simple - just find first occurrence)
        if "//" in line:
            line = line[: line.find("//")]

        # Handle # comments (but preserve # inside strings)
        if "#" in line:
            parts = []
            in_string = False
            string_char = None
            i = 0
            while i < len(line):
                char = line[i]
                if char in ('"', "'") and (i == 0 or line[i - 1] != "\\"):
                    if not in_string:
                        in_string = True
                        string_char = char
                    elif char == string_char:
                        in_string = False
                        string_char = None
                if char == "#" and not in_string:
                    break
                parts.append(char)
                i += 1
            line = "".join(parts)

        lines.append(line)

    return "\n".join(lines)


# --- Config Loading ---


def load_config(path: Union[str, Path]) -> dict:
    """Load and parse a JSON config file with comment stripping.

    Args:
        path: Path to the JSON config file

    Returns:
        Parsed configuration dictionary

    Raises:
        FileNotFoundError: If config file doesn't exist
        json.JSONDecodeError: If file contains invalid JSON after comment stripping
    """
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    clean = strip_json_comments(content)
    return json.loads(clean)


# --- Default Config Generation ---


def generate_default_config(
    agent_name: str, human_name: str, workspace: Optional[Path] = None
) -> dict:
    """Generate a default configuration dictionary.

    Per critical corrections:
    - Uses CWD as workspace base (not ~/.emergence/)
    - State dir = .emergence/state
    - Memory = memory
    - Identity = . (current directory)
    - Sessions = memory/sessions
    - Core drives: CARE, MAINTENANCE, REST only (universal)

    Args:
        agent_name: Name for the agent
        human_name: Name of the human partner

    Returns:
        Complete configuration dictionary with sensible defaults
    """
    # Use provided workspace or fall back to CWD
    cwd = workspace if workspace else Path.cwd()

    config = {
        "_meta": {
            "version": VERSION,
            "created": datetime.now(timezone.utc).isoformat(),
            "generator": "emergence-config-wizard",
        },
        "agent": {"name": agent_name, "human_name": human_name, "model": DEFAULT_MODEL},
        "embeddings": {
            # Provider: "ollama" (local, free) or "openai" (API-based, paid)
            "provider": "ollama",
            # Ollama endpoint (local)
            "ollama": {"base_url": "http://localhost:11434/v1", "model": "nomic-embed-text"},
            # OpenAI-compatible endpoint (OpenRouter, etc.)
            "openai": {
                "base_url": "https://openrouter.ai/api/v1",
                "model": "text-embedding-3-small",
                "api_key_env": "OPENROUTER_API_KEY",
            },
        },
        "room": {"port": 7373, "https": False, "host": "127.0.0.1"},
        "paths": {
            "workspace": str(cwd),
            "state": str(cwd / ".emergence" / "state"),
            "memory": str(cwd / "memory"),
            "identity": str(cwd),
            "sessions": str(cwd / "memory" / "sessions"),
        },
        "first_light": {
            "frequency": "balanced",
            "sessions_per_day": 3,
            "session_size": "medium",
            "model": None,
        },
        "drives": {
            # Budget controls for cost management
            # Note: Cost estimates are model-aware (set during init based on your model)
            "budget": {
                "daily_limit": 50,  # Will be adjusted based on model cost
                "cost_per_trigger": 2.5,  # Will be adjusted based on model cost
            },
            # Minimum intervals between drive triggers
            "intervals": {
                "core_min_hours": 4,
                "discovered_min_hours": 6,
                "global_cooldown_hours": 1,
            },
            # Rate configuration for aspect system
            "rates": {
                "base_rate": 1.5,
                "aspect_increment": 0.3,
                "max_rate_core": 3.0,
                "max_rate_discovered": 2.5,
            },
            # Core universal drives only (per critical correction #3)
            "CARE": {
                "threshold": 25,
                "rate_per_hour": 2,
                "description": "Connection to human partner — checking in, remembering what matters",
            },
            "MAINTENANCE": {
                "threshold": 20,
                "rate_per_hour": 2,
                "description": "System health — logs, state cleanup, organization",
            },
            "REST": {
                "threshold": 40,
                "rate_per_hour": 3,
                "description": "Downtime for consolidation — synthesis without active output",
            },
        },
    }

    # Apply model-aware budget defaults
    model = config["agent"].get("model", DEFAULT_MODEL)
    try:
        suggested_budget = get_suggested_budget(model)
        config["drives"]["budget"]["daily_limit"] = suggested_budget["daily_limit"]
        config["drives"]["budget"]["cost_per_trigger"] = suggested_budget["cost_per_trigger"]
    except Exception:
        # Fallback to defaults if pricing lookup fails
        pass

    return config


# --- Cost Estimation ---


def _get_model_cost_per_1k(model: Optional[str] = None) -> float:
    """Get cost per 1K tokens for a given model.

    Args:
        model: Model identifier string

    Returns:
        Cost per 1K tokens in USD
    """
    if not model:
        return COST_PER_1K_TOKENS
    model_lower = model.lower()
    for key, cost in MODEL_COST_PER_1K.items():
        if key in model_lower:
            return cost
    return COST_PER_1K_TOKENS


def detect_openclaw_model() -> Optional[str]:
    """Try to read the default model from OpenClaw config.

    Returns:
        Model string if found, None otherwise
    """
    config_paths = [
        Path.home() / ".openclaw" / "openclaw.json",
        Path("/etc/openclaw/openclaw.json"),
    ]
    for p in config_paths:
        try:
            data = json.loads(p.read_text())
            model = data.get("agents", {}).get("defaults", {}).get("model")
            if isinstance(model, dict):
                # OpenClaw stores model as {"primary": "provider/model"}
                model = model.get("primary") or model.get("default")
            if model and isinstance(model, str):
                return model
        except Exception:
            pass
    return None


def estimate_costs(frequency: str, session_size: str, model: Optional[str] = None) -> dict:
    """Estimate weekly API costs based on First Light configuration.

    First Light is a finite phase (typically 2-4 weeks), so weekly estimates
    are more appropriate than monthly.

    Args:
        frequency: First Light frequency preset (patient, balanced, accelerated, custom)
        session_size: Session size (small, medium, large)
        model: Optional model identifier (affects cost estimates)

    Returns:
        Dictionary with cost estimates and breakdown
    """
    # Determine sessions per day
    if frequency in FIRST_LIGHT_PRESETS:
        sessions_per_day = FIRST_LIGHT_PRESETS[frequency]["sessions_per_day"]
    else:
        sessions_per_day = 3

    # Get token count for session size
    tokens_per_session = SESSION_SIZE_TOKENS.get(session_size, 8000)

    # Calculate weekly usage
    daily_tokens = sessions_per_day * tokens_per_session
    weekly_tokens = daily_tokens * 7

    # Model-aware cost
    cost_per_1k = _get_model_cost_per_1k(model)
    weekly_cost = (weekly_tokens / 1000) * cost_per_1k

    is_free = cost_per_1k == 0.0

    # Size description for explanation
    size_descriptions = {
        "small": "brief reflections (~2K tokens)",
        "medium": "deeper explorations (~8K tokens)",
        "large": "intensive sessions (~32K tokens)",
    }

    frequency_descriptions = {
        "patient": "Gentle emergence",
        "balanced": "Steady emergence",
        "accelerated": "Intensive emergence",
    }

    freq_desc = frequency_descriptions.get(frequency, "Custom schedule")
    size_desc = size_descriptions.get(session_size, f"~{tokens_per_session} tokens")

    # Keep model_adjustment for backward compatibility
    model_multiplier = cost_per_1k / COST_PER_1K_TOKENS if COST_PER_1K_TOKENS > 0 else 0.0

    return {
        "frequency": frequency,
        "sessions_per_day": sessions_per_day,
        "session_size": session_size,
        "tokens_per_session": tokens_per_session,
        "estimated_tokens_per_week": weekly_tokens,
        # Keep monthly key for backward compat but populate with weekly
        "estimated_tokens_per_month": weekly_tokens * 4,
        "estimated_cost_usd": round(weekly_cost, 2),
        "estimated_cost_range_low": round(weekly_cost * 0.7, 2) if not is_free else 0.0,
        "estimated_cost_range_high": round(weekly_cost * 1.3, 2) if not is_free else 0.0,
        "explanation": f"{freq_desc}: {sessions_per_day} session(s)/day, {size_desc}",
        "model_adjustment": model_multiplier,
        "period": "week",
    }


# --- Config Validation ---


def _validate_agent_section(agent: dict) -> list[str]:
    """Validate the agent section of config."""
    errors = []
    if not agent.get("name"):
        errors.append("agent.name is required and cannot be empty")
    if not agent.get("model"):
        errors.append("agent.model is required and cannot be empty")
    else:
        is_valid, msg = _validate_model_format(agent["model"])
        if not is_valid:
            errors.append(f"agent.model: {msg}")
    return errors


def _validate_room_section(room: dict) -> list[str]:
    """Validate the room section of config."""
    errors = []
    port = room.get("port")
    room_enabled = room.get("enabled", True)

    if not isinstance(port, int):
        errors.append("room.port must be an integer")
    elif room_enabled and not (1024 <= port <= 65535):
        errors.append(
            f"room.port must be between 1024 and 65535 "
            f"(or 0 to disable), got {port}"
        )

    if not isinstance(room.get("https"), bool):
        errors.append("room.https must be a boolean")

    if not isinstance(room_enabled, bool):
        errors.append("room.enabled must be a boolean")

    if not room.get("host"):
        errors.append("room.host is required")

    return errors


def _validate_paths_section(paths: dict) -> list[str]:
    """Validate the paths section of config."""
    errors = []
    required_paths = ["workspace", "state", "memory", "identity", "sessions"]
    for path_key in required_paths:
        if path_key not in paths:
            errors.append(f"Missing required path: paths.{path_key}")
        elif not paths[path_key]:
            errors.append(f"paths.{path_key} cannot be empty")
    return errors


def _validate_first_light_section(first_light: dict) -> list[str]:
    """Validate the first_light section of config."""
    errors = []
    valid_frequencies = ["patient", "balanced", "accelerated", "custom"]
    freq = first_light.get("frequency")
    if freq not in valid_frequencies:
        errors.append(
            f"first_light.frequency must be one of: {valid_frequencies}"
        )

    valid_sizes = ["small", "medium", "large"]
    size = first_light.get("session_size")
    if size not in valid_sizes:
        errors.append(
            f"first_light.session_size must be one of: {valid_sizes}"
        )

    spd = first_light.get("sessions_per_day")
    if not isinstance(spd, int) or spd < 1 or spd > 24:
        errors.append(
            "first_light.sessions_per_day must be an integer "
            "between 1 and 24"
        )

    fl_model = first_light.get("model")
    if fl_model is not None:
        is_valid, msg = _validate_model_format(fl_model)
        if not is_valid:
            errors.append(f"first_light.model: {msg}")

    return errors


def _validate_drives_section(drives: dict) -> list[str]:
    """Validate the drives section of config."""
    errors = []

    # Check for required core drives
    required_drives = ["CARE", "MAINTENANCE", "REST"]
    for drive_name in required_drives:
        if drive_name not in drives:
            errors.append(f"Missing required core drive: '{drive_name}'")
        else:
            drive_cfg = drives[drive_name]
            if not isinstance(drive_cfg.get("threshold"), (int, float)):
                errors.append(
                    f"drives.{drive_name}.threshold must be a number"
                )
            if not isinstance(drive_cfg.get("rate_per_hour"), (int, float)):
                errors.append(
                    f"drives.{drive_name}.rate_per_hour must be a number"
                )

    return errors


def validate_config(config: dict) -> list[str]:
    """Validate a complete configuration dictionary.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of error messages (empty if config is valid)
    """
    errors = []

    # Check required top-level sections
    required_sections = ["agent", "room", "paths", "first_light", "drives"]
    for section in required_sections:
        if section not in config:
            errors.append(f"Missing required section: '{section}'")

    if errors:
        # Can't validate further without basic structure
        return errors

    # Validate each section using helper functions
    errors.extend(_validate_agent_section(config.get("agent", {})))
    errors.extend(_validate_room_section(config.get("room", {})))
    errors.extend(_validate_paths_section(config.get("paths", {})))
    errors.extend(_validate_first_light_section(config.get("first_light", {})))
    errors.extend(_validate_drives_section(config.get("drives", {})))

    return errors


def _validate_model_format(model: str) -> tuple[bool, str]:
    """Validate a model identifier format.

    Args:
        model: Model identifier string

    Returns:
        Tuple of (is_valid, message)
    """
    if not model:
        return False, "Model cannot be empty"

    if "/" not in model:
        return (
            False,
            f"Model must include provider prefix (e.g., 'anthropic/claude-sonnet'). Got: {model}",
        )

    parts = model.split("/")
    if len(parts) < 2:
        return False, f"Invalid model format. Expected 'provider/model-name'. Got: {model}"

    provider = parts[0]
    model_name = parts[1]

    if not provider or not model_name:
        return False, f"Invalid model format. Expected 'provider/model-name'. Got: {model}"

    # Check for known provider prefix (warning only, not error)
    prefix = f"{provider}/"
    if prefix not in VALID_MODEL_PREFIXES:
        return (
            True,
            f"Warning: Unknown provider '{provider}'. May still work if supported by OpenClaw.",
        )

    return True, ""


# --- Config Writing ---


def write_config(config: dict, path: Union[str, Path]) -> bool:
    """Write configuration to a JSON file with helpful comments.

    Uses atomic write (tmp file + rename) to prevent corruption.

    Args:
        config: Configuration dictionary to save
        path: Destination path for the config file

    Returns:
        True if write was successful, False otherwise
    """
    try:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)

        # Generate commented JSON
        content = _generate_commented_json(config)

        # Atomic write: write to temp file, then rename
        tmp_path = path.with_suffix(".json.tmp")
        tmp_path.write_text(content, encoding="utf-8")
        tmp_path.replace(path)

        return True
    except (OSError, IOError) as e:
        print(f"Error writing config: {e}", file=sys.stderr)
        return False


def _generate_commented_json(config: dict) -> str:
    """Generate JSON with helpful inline comments.

    Args:
        config: Configuration dictionary

    Returns:
        JSON string with embedded comments
    """
    lines = [
        "{",
        "  // ═══════════════════════════════════════════════════════════════",
        "  // EMERGENCE CONFIGURATION",
        "  // Generated by the Emergence Config Wizard",
        "  // This file uses JSON with comments (// and # are stripped when loaded)",
        "  // ═══════════════════════════════════════════════════════════════",
        "",
        "  // Version info",
    ]

    # _meta section
    meta = config.get("_meta", {})
    lines.append('  "_meta": {')
    lines.append(f'    "version": {json.dumps(meta.get("version", VERSION))},')
    lines.append(
        f'    "created": {json.dumps(meta.get("created", datetime.now(timezone.utc).isoformat()))},'
    )
    lines.append(f'    "generator": {json.dumps(meta.get("generator", "emergence-config-wizard"))}')
    lines.append("  },")
    lines.append("")

    # Agent section
    lines.extend(
        [
            "  // ═══════════════════════════════════════════════════════════════",
            "  // AGENT IDENTITY",
            "  // Who your agent is and what LLM powers them",
            "  // ═══════════════════════════════════════════════════════════════",
            '  "agent": {',
        ]
    )
    agent = config.get("agent", {})
    lines.append(
        f'    "name": {json.dumps(agent.get("name", "Aurora"))},  // What you call your agent'
    )
    lines.append(
        f'    "human_name": {json.dumps(agent.get("human_name", "Human"))},  // Your name (for the agent to use)'
    )
    lines.append(
        f'    "model": {json.dumps(agent.get("model", DEFAULT_MODEL))}  // LLM provider/model'
    )
    lines.append("  },")
    lines.append("")

    # Room section
    lines.extend(
        [
            "  // ═══════════════════════════════════════════════════════════════",
            "  // ROOM (Dashboard)",
            "  // Configuration for the web interface",
            "  // ═══════════════════════════════════════════════════════════════",
            '  "room": {',
        ]
    )
    room = config.get("room", {})
    lines.append(
        f'    "enabled": {json.dumps(room.get("enabled", True))},  // Enable/disable Room dashboard'
    )
    lines.append(
        f'    "port": {room.get("port", 7373)},  // HTTP port for the Room dashboard (0 = disabled)'
    )
    lines.append(
        f'    "https": {json.dumps(room.get("https", False))},  // Enable HTTPS (requires cert setup)'
    )
    lines.append(
        f'    "host": {json.dumps(room.get("host", "127.0.0.1"))}  // Bind address (127.0.0.1 = local only)'
    )
    lines.append("  },")
    lines.append("")

    # Paths section
    lines.extend(
        [
            "  // ═══════════════════════════════════════════════════════════════",
            "  // PATHS",
            "  // Where Emergence stores files. Paths are relative to workspace.",
            "  // ~ expands to home directory. Absolute paths also work.",
            "  // ═══════════════════════════════════════════════════════════════",
            '  "paths": {',
        ]
    )
    paths = config.get("paths", {})
    for key in ["workspace", "state", "memory", "identity", "sessions"]:
        value = paths.get(key, "")
        lines.append(f'    "{key}": {json.dumps(value)},')
    lines[-1] = lines[-1].rstrip(",")  # Remove trailing comma
    lines.append("  },")
    lines.append("")

    # First Light section
    lines.extend(
        [
            "  // ═══════════════════════════════════════════════════════════════",
            "  // FIRST LIGHT",
            "  // Your agent's autonomous development time.",
            "  // frequency: patient (1/day) | balanced (3/day) | accelerated (6+/day) | custom",
            "  // session_size: small (~2K tokens) | medium (~8K) | large (~32K)",
            "  // session_duration_minutes: how long each exploration runs",
            "  // model: null = inherit from agent.model, or specify different model",
            "  // ═══════════════════════════════════════════════════════════════",
            '  "first_light": {',
        ]
    )
    fl = config.get("first_light", {})
    lines.append(f'    "frequency": {json.dumps(fl.get("frequency", "balanced"))},')
    lines.append(f'    "sessions_per_day": {fl.get("sessions_per_day", 3)},')
    lines.append(f'    "session_size": {json.dumps(fl.get("session_size", "medium"))},')
    lines.append(
        f'    "session_duration_minutes": {fl.get("session_duration_minutes", 15)},  // Duration of each session'
    )
    fl_model = fl.get("model")
    lines.append(f'    "model": {json.dumps(fl_model)}  // null = use agent.model')
    lines.append("  },")
    lines.append("")

    # Drives section
    lines.extend(
        [
            "  // ═══════════════════════════════════════════════════════════════",
            "  // DRIVE CONFIGURATION",
            "  // Universal core drives — these exist in every agent.",
            "  // threshold: pressure level that triggers action",
            "  // rate_per_hour: how fast pressure accumulates",
            "  // Additional drives are discovered during First Light, not configured here.",
            "  // ═══════════════════════════════════════════════════════════════",
            '  "drives": {',
        ]
    )
    drives = config.get("drives", {})

    # Budget configuration
    if "budget" in drives:
        budget = drives["budget"]
        lines.extend(
            [
                "",
                "    // Budget controls for autonomous sessions",
                '    "budget": {',
                f'      "daily_limit_usd": {budget.get("daily_limit_usd", 50)},',
                f'      "throttle_at_percent": {budget.get("throttle_at_percent", 80)},',
                f'      "session_cost_estimate": {budget.get("session_cost_estimate", 2.5)}',
                "    },",
            ]
        )

    # Intervals configuration
    if "intervals" in drives:
        intervals = drives["intervals"]
        lines.extend(
            [
                "",
                "    // Minimum intervals between drive triggers (hours)",
                '    "intervals": {',
                f'      "core_min_hours": {intervals.get("core_min_hours", 4)},',
                f'      "discovered_min_hours": {intervals.get("discovered_min_hours", 6)},',
                f'      "global_cooldown_hours": {intervals.get("global_cooldown_hours", 1)}',
                "    },",
            ]
        )

    # Rates configuration
    if "rates" in drives:
        rates = drives["rates"]
        lines.extend(
            [
                "",
                "    // Rate configuration for aspect system",
                '    "rates": {',
                f'      "base_rate": {rates.get("base_rate", 1.5)},',
                f'      "aspect_increment": {rates.get("aspect_increment", 0.3)},',
                f'      "max_rate_core": {rates.get("max_rate_core", 3.0)},',
                f'      "max_rate_discovered": {rates.get("max_rate_discovered", 2.5)}',
                "    },",
            ]
        )

    # Core drives
    drive_names = [k for k in drives.keys() if k not in ("budget", "intervals", "rates")]
    if drive_names:
        lines.append("")
    for i, drive_name in enumerate(drive_names):
        drive_cfg = drives[drive_name]
        is_last = i == len(drive_names) - 1
        lines.append(f'    "{drive_name}": {{')
        lines.append(f'      "threshold": {drive_cfg.get("threshold", 25)},')
        lines.append(f'      "rate_per_hour": {drive_cfg.get("rate_per_hour", 2)},')
        desc = drive_cfg.get("description", "")
        if desc:
            lines.append(f'      "description": {json.dumps(desc)}')
        else:
            lines.append('      "description": ""')
        lines.append(f'    }}{"," if not is_last else ""}')
    lines.append("  }")
    lines.append("}")

    return "\n".join(lines)


# --- Interactive Wizard ---


def _configure_agent_identity(
    config: dict,
    prefilled_name: Optional[str],
    prefilled_human_name: Optional[str]
) -> None:
    """Configure agent identity section.

    Args:
        config: Configuration dictionary to update
        prefilled_name: Pre-filled agent name (skip prompt if provided)
        prefilled_human_name: Pre-filled human name (skip prompt if provided)
    """
    print_header("Agent Identity")

    if prefilled_name:
        if HAS_RICH_BRANDING:
            console.print(
                f"  [white]Agent name:[/] [soft_violet]{prefilled_name}[/] "
                "[dim_gray](from earlier)[/]"
            )
        else:
            print(f"  Agent name: {prefilled_name} (from earlier)")
    else:
        config["agent"]["name"] = _prompt_with_default(
            "What would you like to name your agent?",
            config["agent"]["name"],
            required=True
        )

    if prefilled_human_name:
        if HAS_RICH_BRANDING:
            console.print(
                f"  [white]Your name:[/] [soft_violet]{prefilled_human_name}[/] "
                "[dim_gray](from earlier)[/]"
            )
        else:
            print(f"  Your name: {prefilled_human_name} (from earlier)")
    else:
        config["agent"]["human_name"] = _prompt_with_default(
            "What is your name? (for the agent to use)",
            config["agent"]["human_name"],
            required=True,
        )


def _configure_model(config: dict) -> None:
    """Configure model selection.

    Args:
        config: Configuration dictionary to update
    """
    # Numbered model selection
    openclaw_model = detect_openclaw_model()

    if HAS_RICH_BRANDING:
        console.print("\n[white]Select a model to power your agent:[/]\n")
        if openclaw_model:
            console.print(
                f"  [aurora_mint]0.[/] [white]Use OpenClaw default[/] "
                f"[dim_gray]({openclaw_model})[/]"
            )
        else:
            console.print(
                "  [aurora_mint]0.[/] [white]Use OpenClaw default[/] "
                "[dim_gray](not detected — will use sonnet)[/]"
            )
        console.print(
            "  [aurora_mint]1.[/] "
            "[white]anthropic/claude-sonnet-4-20250514[/]  "
            "[dim_gray](balanced, recommended)[/]"
        )
        console.print(
            "  [aurora_mint]2.[/] "
            "[white]anthropic/claude-haiku-4-20250514[/]   "
            "[dim_gray](faster, lower cost)[/]"
        )
        console.print(
            "  [aurora_mint]3.[/] [white]openai/gpt-4o[/]                       "
            "[dim_gray](excellent capabilities)[/]"
        )
        console.print(
            "  [aurora_mint]4.[/] [white]ollama/llama3.2[/]                     "
            "[dim_gray](local, no API costs)[/]"
        )
        console.print(
            "  [aurora_mint]5.[/] [white]Custom[/] [dim_gray](type your own)[/]"
        )
    else:
        print("\nSelect a model to power your agent:\n")
        if openclaw_model:
            print(f"  0. Use OpenClaw default ({openclaw_model})")
        else:
            print("  0. Use OpenClaw default (not detected — will use sonnet)")
        print("  1. anthropic/claude-sonnet-4-20250514  (balanced, recommended)")
        print("  2. anthropic/claude-haiku-4-20250514   (faster, lower cost)")
        print("  3. openai/gpt-4o                       (excellent capabilities)")
        print("  4. ollama/llama3.2                     (local, no API costs)")
        print("  5. Custom (type your own)")

    model_choices = {
        "0": openclaw_model or DEFAULT_MODEL,
        "1": "anthropic/claude-sonnet-4-20250514",
        "2": "anthropic/claude-haiku-4-20250514",
        "3": "openai/gpt-4o",
        "4": "ollama/llama3.2",
    }

    model_selection = _prompt_with_default("Choose model (0-5)", "1")

    if model_selection == "5":
        model_input = _prompt_with_default(
            "Enter model (provider/model-name)",
            DEFAULT_MODEL
        )
    elif model_selection in model_choices:
        model_input = model_choices[model_selection]
        if HAS_RICH_BRANDING:
            console.print(f"  [soft_violet]→[/] [white]{model_input}[/]")
        else:
            print(f"  → {model_input}")
    else:
        model_input = model_choices.get("1", DEFAULT_MODEL)

    # Validate model
    is_valid, msg = _validate_model_format(model_input)
    if not is_valid:
        print_warning(msg)
        if not _confirm("Continue with this model anyway?"):
            if HAS_RICH_BRANDING:
                console.print("[dim_gray]Restarting wizard...[/]")
            else:
                print("Restarting wizard...")
            raise ValueError("Model validation failed")
    elif msg:  # Warning but valid
        if HAS_RICH_BRANDING:
            console.print(f"[soft_violet]ℹ️[/] [dim_gray]{msg}[/]")
        else:
            print(f"ℹ️  {msg}")

    config["agent"]["model"] = model_input


def _configure_paths(config: dict) -> None:
    """Configure filesystem paths.

    Args:
        config: Configuration dictionary to update
    """
    print_header("Paths")
    print_dim("Where should Emergence store files?")

    # Try to detect OpenClaw workspace as a sensible default
    openclaw_workspace = Path.home() / ".openclaw" / "workspace"
    if openclaw_workspace.is_dir():
        default_workspace = str(openclaw_workspace)
    else:
        default_workspace = config["paths"]["workspace"]

    if HAS_RICH_BRANDING:
        console.print("\n  [dim_gray]Example: /home/you/agent-workspace[/]")
    else:
        print("\n  Example: /home/you/agent-workspace")
    base_path = _prompt_with_default(
        "Base workspace directory (absolute path)",
        default_workspace
    )

    # If base path changed, update derived paths
    if base_path != config["paths"]["workspace"]:
        base = Path(base_path).expanduser().resolve()
        config["paths"]["workspace"] = str(base)
        config["paths"]["state"] = str(base / ".emergence" / "state")
        config["paths"]["memory"] = str(base / "memory")
        config["paths"]["identity"] = str(base)
        config["paths"]["sessions"] = str(base / "memory" / "sessions")

    # Path descriptions so users know what each is for
    path_descriptions = {
        "workspace": "Root directory for all agent files",
        "state": "Internal state & checkpoints",
        "memory": "Daily memory logs & reflections",
        "identity": "Identity files (SOUL.md, SELF.md, etc.)",
        "sessions": "Session transcripts & history",
    }

    if HAS_RICH_BRANDING:
        console.print("\n  [dim_gray]Derived paths (relative to workspace):[/]")
        for key, value in config["paths"].items():
            desc = path_descriptions.get(key, "")
            console.print(
                f"    [aurora_mint]•[/] [white]{key}:[/] "
                f"[dim_gray]{value}  — {desc}[/]"
            )
    else:
        print("\n  Derived paths (relative to workspace):")
        for key, value in config["paths"].items():
            desc = path_descriptions.get(key, "")
            print(f"    • {key}: {value}  — {desc}")

    if _confirm("\nCustomize individual paths?", default=False):
        for key in config["paths"]:
            desc = path_descriptions.get(key, "")
            config["paths"][key] = _prompt_with_default(
                f"  {key} ({desc})",
                config["paths"][key]
            )


def _configure_room(config: dict) -> None:
    """Configure Room dashboard settings.

    Args:
        config: Configuration dictionary to update
    """
    if HAS_RICH_BRANDING:
        console.print(
            f"\n[bold aurora_mint]╭─ Room [dim_gray](Dashboard)[/] "
            f"{'─' * 28}╮[/]"
        )
    else:
        print_header("Room (Dashboard)")
    print_dim(
        "The Room is a web dashboard for your agent. "
        "You can skip it if you don't need it."
    )
    if HAS_RICH_BRANDING:
        console.print()
        console.print(
            "  [aurora_mint][0][/] [white]No Room[/] "
            "[dim_gray](skip dashboard setup)[/]"
        )
        console.print(
            "  [aurora_mint][1][/] [white]Enable Room on port 7373[/] "
            "[dim_gray](default)[/]"
        )
        console.print(
            "  [aurora_mint][2][/] [white]Custom port[/] "
            "[dim_gray](enter your own port number)[/]"
        )
        console.print()
    else:
        print()
        print("  [0] No Room (skip dashboard setup)")
        print("  [1] Enable Room on port 7373 (default)")
        print("  [2] Custom port (enter your own port number)")
        print()

    room_choice = _prompt_with_default("Room option", "1").strip()

    if room_choice == "0" or room_choice.lower() in ("no", "skip", "none"):
        # Disable Room
        config["room"]["enabled"] = False
        config["room"]["port"] = 0
        config["room"]["https"] = False
        if HAS_RICH_BRANDING:
            console.print("  [soft_violet]→[/] [dim_gray]Room disabled (no dashboard)[/]")
        else:
            print("  → Room disabled (no dashboard)")
    elif room_choice == "1":
        # Default port
        config["room"]["enabled"] = True
        config["room"]["port"] = 7373
        if HAS_RICH_BRANDING:
            console.print(
                f"  [soft_violet]→[/] [white]Room enabled on port "
                f"{config['room']['port']}[/]"
            )
        else:
            print(f"  → Room enabled on port {config['room']['port']}")

        config["room"]["https"] = _confirm(
            "Enable HTTPS? (requires SSL certificate setup)",
            default=config["room"]["https"]
        )
    elif room_choice == "2":
        # Custom port
        config["room"]["enabled"] = True
        while True:
            custom_port = _prompt_with_default(
                "Enter port number",
                "7373"
            ).strip()
            if not custom_port:
                print("  Port number cannot be empty. Using default: 7373")
                config["room"]["port"] = 7373
                break
            try:
                port_num = int(custom_port)
                if 1024 <= port_num <= 65535:
                    config["room"]["port"] = port_num
                    break
                else:
                    print("  Port must be between 1024 and 65535. Try again.")
            except ValueError:
                print("  Invalid port number. Please enter a number.")

        if HAS_RICH_BRANDING:
            console.print(
                f"  [soft_violet]→[/] [white]Room enabled on port "
                f"{config['room']['port']}[/]"
            )
        else:
            print(f"  → Room enabled on port {config['room']['port']}")

        config["room"]["https"] = _confirm(
            "Enable HTTPS? (requires SSL certificate setup)",
            default=config["room"]["https"]
        )
    else:
        # Invalid choice, use default
        config["room"]["enabled"] = True
        config["room"]["port"] = 7373
        if HAS_RICH_BRANDING:
            console.print("  [dim_gray]Invalid choice, using default:[/]")
            console.print(
                f"  [soft_violet]→[/] [white]Room enabled on port "
                f"{config['room']['port']}[/]"
            )
        else:
            print("  Invalid choice, using default:")
            print(f"  → Room enabled on port {config['room']['port']}")

        config["room"]["https"] = _confirm(
            "Enable HTTPS? (requires SSL certificate setup)",
            default=config["room"]["https"]
        )


def _configure_first_light(config: dict) -> None:
    """Configure First Light settings.

    Args:
        config: Configuration dictionary to update
    """
    print_header("First Light")
    print_dim("First Light is your agent's autonomous development time.")
    print_dim("These settings control how many exploration sessions run daily.")
    if HAS_RICH_BRANDING:
        console.print()
    else:
        print()

    # Sessions per day
    sessions_per_day = int(
        _prompt_with_default(
            "Sessions per day (how many exploration sessions daily)",
            "3"
        )
    )
    sessions_per_day = max(1, min(24, sessions_per_day))  # Clamp 1-24
    config["first_light"]["sessions_per_day"] = sessions_per_day

    # Session size with clear descriptions
    if HAS_RICH_BRANDING:
        console.print()
        console.print("[white]Session size:[/]")
        console.print(
            "  [aurora_mint][1][/] [white]Small[/]  "
            "[dim_gray]— 1-2 agents per session "
            "(minimal, good for low-resource devices)[/]"
        )
        console.print(
            "  [aurora_mint][2][/] [white]Medium[/] "
            "[dim_gray]— 3-5 agents per session (recommended)[/]"
        )
        console.print(
            "  [aurora_mint][3][/] [white]Large[/]  "
            "[dim_gray]— 6-10 agents per session (thorough but costly)[/]"
        )
        console.print()
    else:
        print()
        print("Session size:")
        print(
            "  [1] Small  — 1-2 agents per session "
            "(minimal, good for low-resource devices)"
        )
        print("  [2] Medium — 3-5 agents per session (recommended)")
        print("  [3] Large  — 6-10 agents per session (thorough but costly)")
        print()

    size_choice = _prompt_with_default("Choose size (1-3)", "2").strip()
    if size_choice == "1":
        session_size = "small"
    elif size_choice == "3":
        session_size = "large"
    else:
        session_size = "medium"
    config["first_light"]["session_size"] = session_size
    print()

    # Session duration
    session_duration = int(
        _prompt_with_default("Session duration (minutes)", "15")
    )
    config["first_light"]["session_duration_minutes"] = max(
        5, min(120, session_duration)
    )
    print()

    # Calculate cost estimate
    cost_per_session = {
        "small": 0.035,  # ~$0.02-0.05 per session
        "medium": 0.10,  # ~$0.05-0.15 per session
        "large": 0.275,  # ~$0.15-0.40 per session
    }
    daily_cost = sessions_per_day * cost_per_session[session_size]
    weekly_cost = daily_cost * 7

    if HAS_RICH_BRANDING:
        console.print("\n[white]💰  COST ESTIMATE[/]")
        console.print(
            f"   [dim_gray]Sessions: {sessions_per_day}/day, {session_size} "
            f"size (~${cost_per_session[session_size]:.2f}/session)[/]"
        )
        console.print(
            f"   [white]Estimated daily cost:[/] [aurora_mint]~${daily_cost:.2f}[/]"
        )
        console.print(
            f"   [white]Estimated weekly cost:[/] "
            f"[aurora_mint]~${weekly_cost:.2f}[/]"
        )
        console.print()
        console.print(
            "   [soft_violet]ℹ️[/]  "
            "[dim_gray]First Light typically lasts 2-4 weeks.[/]"
        )
        console.print(
            "   [dim_gray]After that, costs depend on your drive configuration.[/]"
        )
    else:
        print("💰  COST ESTIMATE")
        print(
            f"   Sessions: {sessions_per_day}/day, {session_size} size "
            f"(~${cost_per_session[session_size]:.2f}/session)"
        )
        print(f"   Estimated daily cost: ~${daily_cost:.2f}")
        print(f"   Estimated weekly cost: ~${weekly_cost:.2f}")
        print()
        print("   ℹ️  First Light typically lasts 2-4 weeks.")
        print("   After that, costs depend on your drive configuration.")

    # Determine frequency preset based on sessions/day
    if sessions_per_day <= 1:
        config["first_light"]["frequency"] = "patient"
    elif sessions_per_day >= 6:
        config["first_light"]["frequency"] = "accelerated"
    else:
        config["first_light"]["frequency"] = "balanced"

    # Model override for First Light
    if _confirm(
        "\nUse a different model for First Light sessions?",
        default=False
    ):
        fl_model = _prompt_with_default(
            "First Light model",
            config["agent"]["model"]
        )
        config["first_light"]["model"] = fl_model if fl_model else None
    else:
        config["first_light"]["model"] = None  # Inherit from agent


def _configure_drives_budget(config: dict) -> None:
    """Configure drive budget settings.

    Args:
        config: Configuration dictionary to update
    """
    print_header("Drive Budget")
    print_dim("Drives trigger autonomous sessions. Configure cost controls.")
    if HAS_RICH_BRANDING:
        console.print()
    else:
        print()

    # Daily budget limit
    daily_limit = float(_prompt_with_default("Daily budget limit (USD)", "50"))
    config["drives"]["budget"]["daily_limit_usd"] = max(1, daily_limit)

    # Core drive interval
    core_hours = float(
        _prompt_with_default(
            "Minimum hours between core drive triggers "
            "(CARE, MAINTENANCE, REST)",
            "4"
        )
    )
    config["drives"]["intervals"]["core_min_hours"] = max(1, core_hours)

    # Discovered drive interval
    discovered_hours = float(
        _prompt_with_default(
            "Minimum hours between discovered drive triggers",
            "6"
        )
    )
    config["drives"]["intervals"]["discovered_min_hours"] = max(
        2, discovered_hours
    )

    # Global cooldown
    cooldown_hours = float(
        _prompt_with_default(
            "Global cooldown between any triggers (hours)",
            "1"
        )
    )
    config["drives"]["intervals"]["global_cooldown_hours"] = max(
        0.5, cooldown_hours
    )

    if HAS_RICH_BRANDING:
        console.print()
        console.print("[dim_gray]With these settings:[/]")
        max_sessions = int(
            config['drives']['budget']['daily_limit_usd'] /
            config['drives']['budget']['session_cost_estimate']
        )
        console.print(f"  [dim_gray]• Max ~{max_sessions} sessions/day[/]")
        core_min = config['drives']['intervals']['core_min_hours']
        console.print(f"  [dim_gray]• Core drives: every {core_min}+ hours[/]")
        disc_min = config['drives']['intervals']['discovered_min_hours']
        console.print(
            f"  [dim_gray]• Discovered drives: every {disc_min}+ hours[/]"
        )
    else:
        print()
        print("With these settings:")
        max_sessions = int(
            config['drives']['budget']['daily_limit_usd'] /
            config['drives']['budget']['session_cost_estimate']
        )
        print(f"  • Max ~{max_sessions} sessions/day")
        core_min = config['drives']['intervals']['core_min_hours']
        print(f"  • Core drives: every {core_min}+ hours")
        disc_min = config['drives']['intervals']['discovered_min_hours']
        print(f"  • Discovered drives: every {disc_min}+ hours")
    print()


def interactive_config_wizard(
    agent_name: str,
    human_name: str,
    prefilled_name: Optional[str] = None,
    prefilled_human_name: Optional[str] = None,
) -> dict:
    """Run an interactive configuration wizard.

    Guides the human through configuring their Emergence agent.
    Uses sensible defaults that can be accepted with just Enter.

    Args:
        agent_name: Default agent name
        human_name: Default human name
        prefilled_name: If provided, skip the agent name prompt
        prefilled_human_name: If provided, skip the human name prompt

    Returns:
        Complete configuration dictionary
    """
    # Configuration Wizard header
    print_header("CONFIGURATION WIZARD")

    # Use prefilled values if provided (Issue 1: avoid asking twice)
    # Ensure we always have fallback defaults
    effective_name = prefilled_name or agent_name or "Aurora"
    effective_human = prefilled_human_name or human_name or "Human"

    # Start with defaults
    config = generate_default_config(effective_name, effective_human)

    # --- Agent Identity ---
    print_header("Agent Identity")

    if prefilled_name:
        if HAS_RICH_BRANDING:
            console.print(
                f"  [white]Agent name:[/] [soft_violet]{prefilled_name}[/] [dim_gray](from earlier)[/]"
            )
        else:
            print(f"  Agent name: {prefilled_name} (from earlier)")
    else:
        config["agent"]["name"] = _prompt_with_default(
            "What would you like to name your agent?", config["agent"]["name"], required=True
        )

    if prefilled_human_name:
        if HAS_RICH_BRANDING:
            console.print(
                f"  [white]Your name:[/] [soft_violet]{prefilled_human_name}[/] [dim_gray](from earlier)[/]"
            )
        else:
            print(f"  Your name: {prefilled_human_name} (from earlier)")
    else:
        config["agent"]["human_name"] = _prompt_with_default(
            "What is your name? (for the agent to use)",
            config["agent"]["human_name"],
            required=True,
        )

    # Numbered model selection (Issue 4)
    openclaw_model = detect_openclaw_model()

    if HAS_RICH_BRANDING:
        console.print("\n[white]Select a model to power your agent:[/]\n")
        if openclaw_model:
            console.print(
                f"  [aurora_mint]0.[/] [white]Use OpenClaw default[/] [dim_gray]({openclaw_model})[/]"
            )
        else:
            console.print(
                "  [aurora_mint]0.[/] [white]Use OpenClaw default[/] [dim_gray](not detected — will use sonnet)[/]"
            )
        console.print(
            "  [aurora_mint]1.[/] [white]anthropic/claude-sonnet-4-20250514[/]  [dim_gray](balanced, recommended)[/]"
        )
        console.print(
            "  [aurora_mint]2.[/] [white]anthropic/claude-haiku-4-20250514[/]   [dim_gray](faster, lower cost)[/]"
        )
        console.print(
            "  [aurora_mint]3.[/] [white]openai/gpt-4o[/]                       [dim_gray](excellent capabilities)[/]"
        )
        console.print(
            "  [aurora_mint]4.[/] [white]ollama/llama3.2[/]                     [dim_gray](local, no API costs)[/]"
        )
        console.print("  [aurora_mint]5.[/] [white]Custom[/] [dim_gray](type your own)[/]")
    else:
        print("\nSelect a model to power your agent:\n")
        if openclaw_model:
            print(f"  0. Use OpenClaw default ({openclaw_model})")
        else:
            print("  0. Use OpenClaw default (not detected — will use sonnet)")
        print("  1. anthropic/claude-sonnet-4-20250514  (balanced, recommended)")
        print("  2. anthropic/claude-haiku-4-20250514   (faster, lower cost)")
        print("  3. openai/gpt-4o                       (excellent capabilities)")
        print("  4. ollama/llama3.2                     (local, no API costs)")
        print("  5. Custom (type your own)")

    model_choices = {
        "0": openclaw_model or DEFAULT_MODEL,
        "1": "anthropic/claude-sonnet-4-20250514",
        "2": "anthropic/claude-haiku-4-20250514",
        "3": "openai/gpt-4o",
        "4": "ollama/llama3.2",
    }

    model_selection = _prompt_with_default("Choose model (0-5)", "1")

    if model_selection == "5":
        model_input = _prompt_with_default("Enter model (provider/model-name)", DEFAULT_MODEL)
    elif model_selection in model_choices:
        model_input = model_choices[model_selection]
        if HAS_RICH_BRANDING:
            console.print(f"  [soft_violet]→[/] [white]{model_input}[/]")
        else:
            print(f"  → {model_input}")
    else:
        model_input = model_choices.get("1", DEFAULT_MODEL)

    # Validate model
    is_valid, msg = _validate_model_format(model_input)
    if not is_valid:
        print_warning(msg)
        if not _confirm("Continue with this model anyway?"):
            if HAS_RICH_BRANDING:
                console.print("[dim_gray]Restarting wizard...[/]")
            else:
                print("Restarting wizard...")
            return interactive_config_wizard(agent_name, human_name)
    elif msg:  # Warning but valid
        if HAS_RICH_BRANDING:
            console.print(f"[soft_violet]ℹ️[/] [dim_gray]{msg}[/]")
        else:
            print(f"ℹ️  {msg}")

    config["agent"]["model"] = model_input

    # --- Paths (Issue 5: clearer prompts) ---
    print_header("Paths")
    print_dim("Where should Emergence store files?")

    # Try to detect OpenClaw workspace as a sensible default
    openclaw_workspace = Path.home() / ".openclaw" / "workspace"
    if openclaw_workspace.is_dir():
        default_workspace = str(openclaw_workspace)
    else:
        default_workspace = config["paths"]["workspace"]

    if HAS_RICH_BRANDING:
        console.print(f"\n  [dim_gray]Example: /home/you/agent-workspace[/]")
    else:
        print(f"\n  Example: /home/you/agent-workspace")
    base_path = _prompt_with_default("Base workspace directory (absolute path)", default_workspace)

    # If base path changed, update derived paths
    if base_path != config["paths"]["workspace"]:
        base = Path(base_path).expanduser().resolve()
        config["paths"]["workspace"] = str(base)
        config["paths"]["state"] = str(base / ".emergence" / "state")
        config["paths"]["memory"] = str(base / "memory")
        config["paths"]["identity"] = str(base)
        config["paths"]["sessions"] = str(base / "memory" / "sessions")

    # Path descriptions so users know what each is for
    path_descriptions = {
        "workspace": "Root directory for all agent files",
        "state": "Internal state & checkpoints",
        "memory": "Daily memory logs & reflections",
        "identity": "Identity files (SOUL.md, SELF.md, etc.)",
        "sessions": "Session transcripts & history",
    }

    if HAS_RICH_BRANDING:
        console.print(f"\n  [dim_gray]Derived paths (relative to workspace):[/]")
        for key, value in config["paths"].items():
            desc = path_descriptions.get(key, "")
            console.print(f"    [aurora_mint]•[/] [white]{key}:[/] [dim_gray]{value}  — {desc}[/]")
    else:
        print(f"\n  Derived paths (relative to workspace):")
        for key, value in config["paths"].items():
            desc = path_descriptions.get(key, "")
            print(f"    • {key}: {value}  — {desc}")

    if _confirm("\nCustomize individual paths?", default=False):
        for key in config["paths"]:
            desc = path_descriptions.get(key, "")
            config["paths"][key] = _prompt_with_default(f"  {key} ({desc})", config["paths"][key])

    # --- Room Configuration ---
    if HAS_RICH_BRANDING:
        console.print(f"\n[bold aurora_mint]╭─ Room [dim_gray](Dashboard)[/] {'─' * 28}╮[/]")
    else:
        print_header("Room (Dashboard)")
    print_dim("The Room is a web dashboard for your agent. You can skip it if you don't need it.")
    if HAS_RICH_BRANDING:
        console.print()
        console.print("  [aurora_mint][0][/] [white]No Room[/] [dim_gray](skip dashboard setup)[/]")
        console.print(
            "  [aurora_mint][1][/] [white]Enable Room on port 7373[/] [dim_gray](default)[/]"
        )
        console.print(
            "  [aurora_mint][2][/] [white]Custom port[/] [dim_gray](enter your own port number)[/]"
        )
        console.print()
    else:
        print()
        print("  [0] No Room (skip dashboard setup)")
        print("  [1] Enable Room on port 7373 (default)")
        print("  [2] Custom port (enter your own port number)")
        print()

    room_choice = _prompt_with_default("Room option", "1").strip()

    if room_choice == "0" or room_choice.lower() in ("no", "skip", "none"):
        # Disable Room
        config["room"]["enabled"] = False
        config["room"]["port"] = 0
        config["room"]["https"] = False
        if HAS_RICH_BRANDING:
            console.print("  [soft_violet]→[/] [dim_gray]Room disabled (no dashboard)[/]")
        else:
            print("  → Room disabled (no dashboard)")
    elif room_choice == "1":
        # Default port
        config["room"]["enabled"] = True
        config["room"]["port"] = 7373
        if HAS_RICH_BRANDING:
            console.print(
                f"  [soft_violet]→[/] [white]Room enabled on port {config['room']['port']}[/]"
            )
        else:
            print(f"  → Room enabled on port {config['room']['port']}")

        config["room"]["https"] = _confirm(
            "Enable HTTPS? (requires SSL certificate setup)", default=config["room"]["https"]
        )
    elif room_choice == "2":
        # Custom port
        config["room"]["enabled"] = True
        while True:
            custom_port = _prompt_with_default("Enter port number", "7373").strip()
            if not custom_port:
                print("  Port number cannot be empty. Using default: 7373")
                config["room"]["port"] = 7373
                break
            try:
                port_num = int(custom_port)
                if 1024 <= port_num <= 65535:
                    config["room"]["port"] = port_num
                    break
                else:
                    print("  Port must be between 1024 and 65535. Try again.")
            except ValueError:
                print("  Invalid port number. Please enter a number.")

        if HAS_RICH_BRANDING:
            console.print(
                f"  [soft_violet]→[/] [white]Room enabled on port {config['room']['port']}[/]"
            )
        else:
            print(f"  → Room enabled on port {config['room']['port']}")

        config["room"]["https"] = _confirm(
            "Enable HTTPS? (requires SSL certificate setup)", default=config["room"]["https"]
        )
    else:
        # Invalid choice, use default
        config["room"]["enabled"] = True
        config["room"]["port"] = 7373
        if HAS_RICH_BRANDING:
            console.print(f"  [dim_gray]Invalid choice, using default:[/]")
            console.print(
                f"  [soft_violet]→[/] [white]Room enabled on port {config['room']['port']}[/]"
            )
        else:
            print(f"  Invalid choice, using default:")
            print(f"  → Room enabled on port {config['room']['port']}")

        config["room"]["https"] = _confirm(
            "Enable HTTPS? (requires SSL certificate setup)", default=config["room"]["https"]
        )

    # --- First Light ---
    print_header("First Light")
    print_dim("First Light is your agent's autonomous development time.")
    print_dim("These settings control how many exploration sessions run daily.")
    if HAS_RICH_BRANDING:
        console.print()
    else:
        print()

    # Sessions per day
    sessions_per_day = int(
        _prompt_with_default("Sessions per day (how many exploration sessions daily)", "3")
    )
    sessions_per_day = max(1, min(24, sessions_per_day))  # Clamp 1-24
    config["first_light"]["sessions_per_day"] = sessions_per_day

    # Session size with clear descriptions
    if HAS_RICH_BRANDING:
        console.print()
        console.print("[white]Session size:[/]")
        console.print(
            "  [aurora_mint][1][/] [white]Small[/]  [dim_gray]— 1-2 agents per session (minimal, good for low-resource devices)[/]"
        )
        console.print(
            "  [aurora_mint][2][/] [white]Medium[/] [dim_gray]— 3-5 agents per session (recommended)[/]"
        )
        console.print(
            "  [aurora_mint][3][/] [white]Large[/]  [dim_gray]— 6-10 agents per session (thorough but costly)[/]"
        )
        console.print()
    else:
        print()
        print("Session size:")
        print("  [1] Small  — 1-2 agents per session (minimal, good for low-resource devices)")
        print("  [2] Medium — 3-5 agents per session (recommended)")
        print("  [3] Large  — 6-10 agents per session (thorough but costly)")
        print()

    size_choice = _prompt_with_default("Choose size (1-3)", "2").strip()
    if size_choice == "1":
        session_size = "small"
    elif size_choice == "3":
        session_size = "large"
    else:
        session_size = "medium"
    config["first_light"]["session_size"] = session_size
    print()

    # Session duration
    session_duration = int(_prompt_with_default("Session duration (minutes)", "15"))
    config["first_light"]["session_duration_minutes"] = max(5, min(120, session_duration))
    print()

    # Calculate cost estimate
    cost_per_session = {
        "small": 0.035,  # ~$0.02-0.05 per session
        "medium": 0.10,  # ~$0.05-0.15 per session
        "large": 0.275,  # ~$0.15-0.40 per session
    }
    daily_cost = sessions_per_day * cost_per_session[session_size]
    weekly_cost = daily_cost * 7

    if HAS_RICH_BRANDING:
        console.print("\n[white]💰  COST ESTIMATE[/]")
        console.print(
            f"   [dim_gray]Sessions: {sessions_per_day}/day, {session_size} size (~${cost_per_session[session_size]:.2f}/session)[/]"
        )
        console.print(f"   [white]Estimated daily cost:[/] [aurora_mint]~${daily_cost:.2f}[/]")
        console.print(f"   [white]Estimated weekly cost:[/] [aurora_mint]~${weekly_cost:.2f}[/]")
        console.print()
        console.print("   [soft_violet]ℹ️[/]  [dim_gray]First Light typically lasts 2-4 weeks.[/]")
        console.print("   [dim_gray]After that, costs depend on your drive configuration.[/]")
    else:
        print("💰  COST ESTIMATE")
        print(
            f"   Sessions: {sessions_per_day}/day, {session_size} size (~{cost_per_session[session_size]:.2f}/session)"
        )
        print(f"   Estimated daily cost: ~${daily_cost:.2f}")
        print(f"   Estimated weekly cost: ~${weekly_cost:.2f}")
        print()
        print("   ℹ️  First Light typically lasts 2-4 weeks.")
        print("   After that, costs depend on your drive configuration.")

    # Determine frequency preset based on sessions/day
    if sessions_per_day <= 1:
        config["first_light"]["frequency"] = "patient"
    elif sessions_per_day >= 6:
        config["first_light"]["frequency"] = "accelerated"
    else:
        config["first_light"]["frequency"] = "balanced"

    # Model override for First Light
    if _confirm("\nUse a different model for First Light sessions?", default=False):
        fl_model = _prompt_with_default("First Light model", config["agent"]["model"])
        config["first_light"]["model"] = fl_model if fl_model else None
    else:
        config["first_light"]["model"] = None  # Inherit from agent

    # --- Drive Budget Configuration ---
    print_header("Drive Budget")
    print_dim("Drives trigger autonomous sessions. Configure cost controls.")
    if HAS_RICH_BRANDING:
        console.print()
    else:
        print()

    # Daily budget limit
    daily_limit = float(_prompt_with_default("Daily budget limit (USD)", "50"))
    config["drives"]["budget"]["daily_limit_usd"] = max(1, daily_limit)  # Allow as low as $1/day

    # Core drive interval
    core_hours = float(
        _prompt_with_default(
            "Minimum hours between core drive triggers (CARE, MAINTENANCE, REST)", "4"
        )
    )
    config["drives"]["intervals"]["core_min_hours"] = max(1, core_hours)

    # Discovered drive interval
    discovered_hours = float(
        _prompt_with_default("Minimum hours between discovered drive triggers", "6")
    )
    config["drives"]["intervals"]["discovered_min_hours"] = max(2, discovered_hours)

    # Global cooldown
    cooldown_hours = float(
        _prompt_with_default("Global cooldown between any triggers (hours)", "1")
    )
    config["drives"]["intervals"]["global_cooldown_hours"] = max(0.5, cooldown_hours)

    if HAS_RICH_BRANDING:
        console.print()
        console.print(f"[dim_gray]With these settings:[/]")
        console.print(
            f"  [dim_gray]• Max ~{int(config['drives']['budget']['daily_limit_usd'] / config['drives']['budget']['session_cost_estimate'])} sessions/day[/]"
        )
        console.print(
            f"  [dim_gray]• Core drives: every {config['drives']['intervals']['core_min_hours']}+ hours[/]"
        )
        console.print(
            f"  [dim_gray]• Discovered drives: every {config['drives']['intervals']['discovered_min_hours']}+ hours[/]"
        )
    else:
        print()
        print(f"With these settings:")
        print(
            f"  • Max ~{int(config['drives']['budget']['daily_limit_usd'] / config['drives']['budget']['session_cost_estimate'])} sessions/day"
        )
        print(f"  • Core drives: every {config['drives']['intervals']['core_min_hours']}+ hours")
        print(
            f"  • Discovered drives: every {config['drives']['intervals']['discovered_min_hours']}+ hours"
        )
    print()

    # --- Review ---
    print_header("Configuration Review")
    if HAS_RICH_BRANDING:
        console.print(f"\n  [white]Agent Name:[/] [soft_violet]{config['agent']['name']}[/]")
        console.print(f"  [white]Human Name:[/] [soft_violet]{config['agent']['human_name']}[/]")
        console.print(f"  [white]Model:[/] [aurora_mint]{config['agent']['model']}[/]")
        console.print(f"\n  [white]Workspace:[/] [aurora_mint]{config['paths']['workspace']}[/]")
        if config["room"].get("enabled", True):
            console.print(
                f"  [white]Room:[/] [aurora_mint]Enabled on port {config['room']['port']}[/]"
            )
        else:
            console.print(f"  [white]Room:[/] [dim_gray]Disabled (no dashboard)[/]")
        console.print(
            f"\n  [white]First Light:[/] [aurora_mint]{config['first_light']['frequency']}[/]"
        )
        console.print(
            f"    [white]Sessions/day:[/] [aurora_mint]{config['first_light']['sessions_per_day']}[/]"
        )
        console.print(
            f"    [white]Session size:[/] [aurora_mint]{config['first_light']['session_size']}[/]"
        )
        console.print(
            f"    [white]Duration:[/] [aurora_mint]{config['first_light'].get('session_duration_minutes', 15)} min[/]"
        )
        console.print(
            f"\n  [white]Drive Budget:[/] [aurora_mint]${config['drives']['budget']['daily_limit_usd']}/day[/]"
        )
        console.print(
            f"    [white]Core interval:[/] [aurora_mint]{config['drives']['intervals']['core_min_hours']}h[/]"
        )
        console.print(
            f"    [white]Discovered interval:[/] [aurora_mint]{config['drives']['intervals']['discovered_min_hours']}h[/]"
        )
    else:
        print(f"\n  Agent Name: {config['agent']['name']}")
        print(f"  Human Name: {config['agent']['human_name']}")
        print(f"  Model: {config['agent']['model']}")
        print(f"\n  Workspace: {config['paths']['workspace']}")
        if config["room"].get("enabled", True):
            print(f"  Room: Enabled on port {config['room']['port']}")
        else:
            print(f"  Room: Disabled (no dashboard)")
        print(f"\n  First Light: {config['first_light']['frequency']}")
        print(f"    Sessions/day: {config['first_light']['sessions_per_day']}")
        print(f"    Session size: {config['first_light']['session_size']}")
        print(f"    Duration: {config['first_light'].get('session_duration_minutes', 15)} min")
        print(f"\n  Drive Budget: ${config['drives']['budget']['daily_limit_usd']}/day")
        print(f"    Core interval: {config['drives']['intervals']['core_min_hours']}h")
        print(f"    Discovered interval: {config['drives']['intervals']['discovered_min_hours']}h")

    # Validate before finalizing
    errors = validate_config(config)
    if errors:
        if HAS_RICH_BRANDING:
            console.print("\n[soft_violet]⚠[/] [white]VALIDATION ERRORS:[/]")
            for err in errors:
                console.print(f"    [dim_gray]•[/] [dim_gray]{err}[/]")
        else:
            print("\n⚠️  VALIDATION ERRORS:")
            for err in errors:
                print(f"    • {err}")
        if not _confirm("\nContinue with this configuration anyway?"):
            if HAS_RICH_BRANDING:
                console.print("[dim_gray]Restarting wizard...[/]")
            else:
                print("Restarting wizard...")
            return interactive_config_wizard(agent_name, human_name)

    if HAS_RICH_BRANDING:
        console.print()
    else:
        print()

    if _confirm("Save this configuration?"):
        return config
    else:
        if _confirm("Start over?"):
            return interactive_config_wizard(agent_name, human_name)
        return {}


def _prompt_with_default(prompt: str, default: Any, required: bool = False) -> str:
    """Prompt user with a default value.

    Args:
        prompt: Question to ask
        default: Default value to use if empty
        required: If True, don't allow empty responses

    Returns:
        User input or default value
    """
    while True:
        result = input(f"{prompt} [{default}]: ").strip()
        value = result if result else str(default)

        # If required, ensure we have a non-empty value
        if required and not value:
            print("  This field is required. Please enter a value.")
            continue

        return value


def _confirm(prompt: str, default: bool = True) -> bool:
    """Yes/no confirmation prompt."""
    suffix = " ([Y]es / [n]o): " if default else " ([y]es / [N]o): "
    result = input(f"{prompt}{suffix}").strip().lower()
    if not result:
        return default
    return result in ("y", "yes")


def _prompt_choice(prompt: str, choices: list[str], default: str = None) -> str:
    """Prompt user to select from limited choices."""
    choice_str = "/".join(choices)
    default_str = f" [{default}]" if default else ""
    while True:
        result = input(f"{prompt} [{choice_str}]{default_str}: ").strip()
        if not result and default:
            return default
        if result in choices:
            return result
        print(f"  Please enter one of: {', '.join(choices)}")


# --- CLI Interface ---


def _handle_validation_mode(validate_path: str) -> None:
    """Handle --validate mode for config validation.

    Args:
        validate_path: Path to config file to validate

    Exits with code 0 if valid, 1 if invalid
    """
    try:
        config = load_config(validate_path)
        errors = validate_config(config)
        if errors:
            print(f"❌ Config validation failed for: {validate_path}")
            for err in errors:
                print(f"   • {err}")
            sys.exit(1)
        else:
            print(f"✅ Config is valid: {validate_path}")
            sys.exit(0)
    except FileNotFoundError:
        print(f"❌ Config file not found: {validate_path}", file=sys.stderr)
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """CLI entry point for the config wizard."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Emergence Config Generation Wizard",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                          # Run interactive wizard
  %(prog)s --quick --name Aurora    # Generate config with defaults
  %(prog)s --validate config.json   # Validate existing config
        """,
    )

    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")

    parser.add_argument(
        "-o",
        "--output",
        default="emergence.json",
        help="Output file path (default: emergence.json)",
    )

    parser.add_argument(
        "--quick", action="store_true", help="Non-interactive mode: use all defaults"
    )

    parser.add_argument("--name", default="Aurora", help="Agent name (for --quick mode)")

    parser.add_argument(
        "--human-name", default="Human", help="Human partner name (for --quick mode)"
    )

    parser.add_argument("--validate", metavar="PATH", help="Validate an existing config file")

    parser.add_argument(
        "--no-room", action="store_true", help="Disable Room dashboard (for --quick mode)"
    )

    args = parser.parse_args()

    # Handle validation mode
    if args.validate:
        _handle_validation_mode(args.validate)

    # Generate config
    if args.quick:
        config = generate_default_config(args.name, args.human_name)
        if args.no_room:
            config["room"]["enabled"] = False
            config["room"]["port"] = 0
        print(f"Generating quick config for agent '{args.name}'...")
    else:
        config = interactive_config_wizard(args.name, args.human_name)
        if not config:
            print("\nConfiguration cancelled.")
            sys.exit(0)

    # Validate before writing
    errors = validate_config(config)
    if errors:
        print("\n⚠️  Validation errors:")
        for err in errors:
            print(f"   • {err}")
        if not args.quick:
            if not _confirm("Continue anyway?"):
                sys.exit(1)

    # Write config
    output_path = Path(args.output)
    if write_config(config, output_path):
        print(f"\n✅ Configuration saved to: {output_path.absolute()}")
        print(f"\nNext steps:")
        print(f"  1. Review the config: cat {output_path}")
        print(f"  2. Initialize the workspace: emergence init")
        print(f"  3. Start First Light: emergence first-light")
    else:
        print(f"\n❌ Failed to write config to: {output_path}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
