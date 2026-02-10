from typing import Optional
#!/usr/bin/env python3
"""Flush prompt template renderer for Emergence memory system.

Renders the flush prompt template with configuration values.
Used during OpenClaw compaction to teach agents how to remember.
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from string import Template

# --- Constants ---
DEFAULT_TEMPLATE_NAME = "flush-prompt.template.md"
DEFAULT_MEMORY_DIR = "memory"
DEFAULT_DRIVES_CLI = "drives"
DEFAULT_TIMEZONE = "GMT"


def get_template_path(config: Optional[dict] = None) -> Path:
    """Resolve the template path from config or use default.
    
    Args:
        config: Optional configuration dictionary with memory settings
        
    Returns:
        Path to the flush prompt template file
    """
    if config and "memory" in config:
        memory_config = config["memory"]
        if "flush_prompt_template" in memory_config:
            template_path = Path(memory_config["flush_prompt_template"])
            if template_path.is_absolute():
                return template_path
            # Relative to workspace
            workspace = _get_workspace_path(config)
            return workspace / template_path
    
    # Default: look in same directory as this module
    module_dir = Path(__file__).parent
    return module_dir / DEFAULT_TEMPLATE_NAME


def _get_workspace_path(config: Optional[dict] = None) -> Path:
    """Get workspace path from config or use current working directory."""
    if config and "paths" in config and "workspace" in config["paths"]:
        workspace = Path(config["paths"]["workspace"])
        if workspace.is_absolute():
            return workspace
        # If relative, assume relative to OpenClaw workspace
        return Path.cwd() / workspace
    return Path.cwd()


def _get_session_date() -> str:
    """Get the session date for file naming.
    
    Uses current date by default. In a real session context, this would
    use the session start date to handle midnight boundaries correctly.
    """
    # For now, use current date in UTC
    # In production with OpenClaw, this would be passed from the runtime
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _get_timezone() -> str:
    """Get the timezone string for display."""
    return DEFAULT_TIMEZONE


def _get_memory_dir(config: Optional[dict] = None) -> str:
    """Get memory directory path from config."""
    if config and "memory" in config:
        memory_config = config["memory"]
        if "daily_dir" in memory_config:
            return memory_config["daily_dir"]
    return DEFAULT_MEMORY_DIR


def _get_drives_cli(config: Optional[dict] = None) -> str:
    """Get drives CLI path from config."""
    if config and "paths" in config:
        paths_config = config["paths"]
        if "drives_cli" in paths_config:
            return paths_config["drives_cli"]
    return DEFAULT_DRIVES_CLI


def render_flush_prompt(
    config: Optional[dict] = None,
    session_date: Optional[str] = None,
    timezone: Optional[str] = None
) -> str:
    """Render the flush prompt template with configuration values.
    
    Args:
        config: Optional configuration dictionary
        session_date: Optional session date override (YYYY-MM-DD format)
        timezone: Optional timezone override
        
    Returns:
        The rendered flush prompt text
        
    Raises:
        FileNotFoundError: If template file doesn't exist
    """
    template_path = get_template_path(config)
    
    if not template_path.exists():
        raise FileNotFoundError(f"Flush prompt template not found: {template_path}")
    
    template_content = template_path.read_text(encoding="utf-8")
    
    # Prepare substitution values
    substitutions = {
        "memory_dir": _get_memory_dir(config),
        "session_date": session_date or _get_session_date(),
        "timezone": timezone or _get_timezone(),
        "drives_cli": _get_drives_cli(config),
    }
    
    # Use Template.safe_substitute to allow partial substitution
    # (some variables might be intentionally left for runtime)
    t = Template(template_content)
    return t.safe_substitute(substitutions)


def load_config(config_path=None) -> dict:
    """Load configuration from emergence.yaml or emergence.json.
    
    Args:
        config_path: Optional path to config file
        
    Returns:
        Configuration dictionary, or empty dict if no config found
    """
    if config_path:
        config_file = Path(config_path)
        if config_file.exists():
            return _parse_config(config_file)
        return {}
    
    # Search for config in standard locations
    workspace = Path.cwd()
    candidates = [
        workspace / "emergence.yaml",
        workspace / "emergence.json",
        workspace / ".emergence" / "config.yaml",
        workspace / ".emergence" / "config.json",
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return _parse_config(candidate)
    
    return {}


def _parse_config(config_file: Path) -> dict:
    """Parse a config file (YAML or JSON)."""
    content = config_file.read_text(encoding="utf-8")
    
    if config_file.suffix in (".yaml", ".yml"):
        # Simple YAML parsing for basic structures (no PyYAML dependency)
        return _simple_yaml_parse(content)
    elif config_file.suffix == ".json":
        return json.loads(content)
    
    # Try YAML first, then JSON
    try:
        return _simple_yaml_parse(content)
    except Exception:
        return json.loads(content)


def _simple_yaml_parse(content: str) -> dict:
    """Simple YAML parser for flat configs (no external deps).
    
    Handles basic YAML structures:
    - key: value
    - nested:
        key: value
    - Comments starting with #
    """
    result = {}
    current_section = None
    indent_stack = [result]
    
    for line in content.split("\n"):
        # Skip empty lines and comments
        stripped = line.lstrip()
        if not stripped or stripped.startswith("#"):
            continue
        
        # Calculate indent level
        indent = len(line) - len(line.lstrip())
        
        # Parse key: value
        if ":" in stripped:
            key, _, value = stripped.partition(":")
            key = key.strip()
            value = value.strip()
            
            # Remove quotes if present
            if value.startswith(("'", "\"")) and value.endswith(("'", "\"")):
                value = value[1:-1]
            
            # Handle nested sections
            if not value:  # Section header
                new_section = {}
                if isinstance(indent_stack[-1], dict):
                    indent_stack[-1][key] = new_section
                current_section = new_section
                indent_stack.append(new_section)
            else:
                # Try to parse as number or bool
                if value.lower() == "true":
                    value = True
                elif value.lower() == "false":
                    value = False
                elif value.isdigit():
                    value = int(value)
                elif re.match(r"^\d+\.\d+$", value):
                    value = float(value)
                
                if isinstance(indent_stack[-1], dict):
                    indent_stack[-1][key] = value
    
    return result


def main():
    """CLI entry point for rendering the flush prompt."""
    config = load_config()
    
    # Allow command-line overrides
    session_date = None
    timezone = None
    
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        if args[i] == "--date" and i + 1 < len(args):
            session_date = args[i + 1]
            i += 2
        elif args[i] == "--timezone" and i + 1 < len(args):
            timezone = args[i + 1]
            i += 2
        elif args[i] == "--config" and i + 1 < len(args):
            config = load_config(args[i + 1])
            i += 2
        else:
            i += 1
    
    try:
        prompt = render_flush_prompt(config, session_date, timezone)
        print(prompt)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error rendering flush prompt: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
