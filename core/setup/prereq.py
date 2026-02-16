#!/usr/bin/env python3
"""Prerequisite check for Emergence — validates environment before setup.

This module provides comprehensive dependency checking for the Emergence
agent architecture, including hard dependencies (Python, Node, OpenClaw)
and soft dependencies (Ollama for embeddings).
"""

import argparse
import http.client
import json
import os
import platform
import socket
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

# Try to import branding for styled output
try:
    from .branding import console, HAS_RICH
except ImportError:
    HAS_RICH = False
    console = None

# --- Constants ---
DEFAULT_OPENCLAW_PORT = 6969
DEFAULT_OLLAMA_MODEL = "nomic-embed-text"
REQUIRED_PYTHON_MAJOR = 3
REQUIRED_PYTHON_MINOR = 9
REQUIRED_NODE_MAJOR = 18


# --- Helper Functions ---


def _print_check(ok: bool, message: str, is_warning: bool = False):
    """Print a check result with consistent styling.

    Args:
        ok: Whether the check passed
        message: The message to display
        is_warning: If True, use warning style (!) instead of error (✗)
    """
    if HAS_RICH and console:
        if ok:
            console.print(f"  [aurora_mint]✓[/] {message}")
        elif is_warning:
            console.print(f"  [bold soft_violet]![/] [dim_gray]{message}[/]")
        else:
            console.print(f"  [bold soft_violet]✗[/] {message}")
    else:
        symbol = "✓" if ok else ("!" if is_warning else "✗")
        print(f"  {symbol} {message}")


def _parse_node_version(version_str: str) -> int:
    """Extract major version number from Node version string.

    Handles formats like 'v18.19.0' or '18.19.0'.

    Args:
        version_str: The version string from node --version

    Returns:
        The major version number as an integer
    """
    cleaned = version_str.strip().lstrip("v")
    return int(cleaned.split(".")[0])


def _read_emergence_config() -> dict[str, Any]:
    """Read emergence.json config file if it exists.

    Returns:
        Dict with config contents, or empty dict if file not found
    """
    config_path = Path("emergence.json")
    if not config_path.exists():
        return {}

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def _try_parse_port(value: Any) -> Optional[int]:
    """Try to parse a port value as integer.

    Args:
        value: Value to parse

    Returns:
        Port number if valid, None otherwise
    """
    try:
        return int(value) if value else None
    except (ValueError, TypeError):
        return None


def _get_port_from_openclaw_config() -> Optional[int]:
    """Try to read port from OpenClaw's own config file.

    Returns:
        Port number if found, None otherwise
    """
    openclaw_config_path = Path.home() / ".openclaw" / "openclaw.json"
    try:
        if openclaw_config_path.exists():
            with open(openclaw_config_path, "r") as f:
                oc_config = json.load(f)
            return _try_parse_port(oc_config.get("gateway", {}).get("port"))
    except (json.JSONDecodeError, IOError):
        pass
    return None


def _get_openclaw_port() -> int:
    """Determine OpenClaw gateway port.

    Checks environment variable OPENCLAW_GATEWAY_PORT first,
    then falls back to config file, then default.

    Returns:
        The port number to use for gateway checks
    """
    # Check environment variable first
    env_port = _try_parse_port(os.environ.get("OPENCLAW_GATEWAY_PORT"))
    if env_port:
        return env_port

    # Check emergence config
    config = _read_emergence_config()
    config_port = _try_parse_port(config.get("openclaw", {}).get("port"))
    if config_port:
        return config_port

    # Check OpenClaw's own config
    oc_port = _get_port_from_openclaw_config()
    if oc_port:
        return oc_port

    # Default fallback
    return DEFAULT_OPENCLAW_PORT


# --- Version Check Functions ---


def check_python_version() -> tuple[bool, str]:
    """Verify Python 3.9+ is available.

    Returns:
        Tuple of (success: bool, message: str)
    """
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"

    if version.major < REQUIRED_PYTHON_MAJOR:
        return (
            False,
            f"Python {REQUIRED_PYTHON_MAJOR}.{REQUIRED_PYTHON_MINOR}+ required, found {version_str}",
        )

    if version.major == REQUIRED_PYTHON_MAJOR and version.minor < REQUIRED_PYTHON_MINOR:
        return (
            False,
            f"Python {REQUIRED_PYTHON_MAJOR}.{REQUIRED_PYTHON_MINOR}+ required, found {version_str}",
        )

    return True, f"Python {version_str} ✓"


def check_node_version() -> tuple[bool, str]:
    """Verify Node.js 18+ is installed.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        result = subprocess.run(["node", "--version"], capture_output=True, text=True, timeout=5)

        if result.returncode != 0:
            return False, "Node.js not found (required for The Room dashboard)"

        version_str = result.stdout.strip()
        major = _parse_node_version(version_str)

        if major < REQUIRED_NODE_MAJOR:
            return (
                False,
                f"Node.js {REQUIRED_NODE_MAJOR}+ required, found {version_str.lstrip('v')}",
            )

        return True, f"Node.js {version_str.lstrip('v')} ✓"

    except FileNotFoundError:
        return False, "Node.js not found (required for The Room dashboard)"
    except subprocess.TimeoutExpired:
        return False, "Node.js check timed out"


def check_openclaw_gateway() -> tuple[bool, str]:
    """Verify OpenClaw gateway is running via HTTP health check.

    Port is determined from OPENCLAW_GATEWAY_PORT env var,
    emergence.json config, or defaults to 6969.

    Returns:
        Tuple of (success: bool, message: str)
    """
    port = _get_openclaw_port()

    try:
        conn = http.client.HTTPConnection("localhost", port, timeout=5)
        conn.request("GET", "/health")
        response = conn.getresponse()
        conn.close()

        if response.status == 200:
            return True, f"OpenClaw gateway running on port {port} ✓"

        return False, f"OpenClaw gateway returned status {response.status}"

    except ConnectionRefusedError:
        return False, f"OpenClaw gateway not running on localhost:{port}"
    except (socket.timeout, TimeoutError):
        return False, "OpenClaw gateway check timed out"
    except Exception as e:
        return False, f"OpenClaw gateway check failed: {e}"


# --- Ollama Check Functions ---


def check_ollama_installed() -> tuple[bool, str]:
    """Check if Ollama CLI is available.

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        result = subprocess.run(["ollama", "--version"], capture_output=True, text=True, timeout=5)

        if result.returncode == 0:
            version = result.stdout.strip()
            return True, f"Ollama installed ({version}) ✓"

        return False, "Ollama not found"

    except FileNotFoundError:
        return False, "Ollama not installed"
    except subprocess.TimeoutExpired:
        return False, "Ollama check timed out"


def check_ollama_model(model: str = DEFAULT_OLLAMA_MODEL) -> tuple[bool, str]:
    """Check if specified Ollama model is available.

    Args:
        model: The model name to check for (default: nomic-embed-text)

    Returns:
        Tuple of (success: bool, message: str)
    """
    try:
        result = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=10)

        if result.returncode != 0:
            return False, f"Could not list Ollama models: {result.stderr}"

        lines = result.stdout.strip().split("\n")
        if len(lines) < 2:
            return False, f"Model '{model}' not pulled"

        # Parse output: NAME\tID\tSIZE\tMODIFIED
        for line in lines[1:]:  # Skip header
            parts = line.split("\t")
            if parts and parts[0].startswith(model):
                return True, f"Model '{model}' available ✓"

        return False, f"Model '{model}' not pulled"

    except FileNotFoundError:
        return False, "Ollama not installed"
    except subprocess.TimeoutExpired:
        return False, "Ollama model check timed out"


# --- Platform Detection ---


def detect_platform() -> str:
    """Detect the current operating system.

    Returns:
        'macos', 'linux', or 'unknown'
    """
    system = platform.system().lower()

    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"

    return "unknown"


# --- Installation Functions ---


def offer_ollama_install(platform_name: str) -> bool:
    """Display Ollama installation instructions for the platform.

    Args:
        platform_name: The detected platform ('macos', 'linux', or 'unknown')

    Returns:
        True if installation was offered, False otherwise
    """
    if platform_name == "macos":
        print("  Ollama can be installed with: brew install ollama")
        print("  Or download from https://ollama.com/download")
    elif platform_name == "linux":
        print("  Ollama can be installed with:")
        print("    curl -fsSL https://ollama.com/install.sh | sh")
    else:
        print("  Visit https://ollama.com/download for installation instructions")

    return True


def run_ollama_install(platform_name: str) -> bool:
    """Execute Ollama installation.

    Args:
        platform_name: The detected platform ('macos' or 'linux')

    Returns:
        True if installation succeeded, False otherwise
    """
    try:
        if platform_name == "macos":
            result = subprocess.run(
                ["brew", "install", "ollama"], capture_output=True, text=True, timeout=120
            )

            if result.returncode == 0:
                print("  ✓ Ollama installed successfully")
                return True

            print("  Brew install failed. Please install manually from https://ollama.com")
            return False

        elif platform_name == "linux":
            result = subprocess.run(
                ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
                capture_output=True,
                text=True,
                timeout=300,
            )

            if result.returncode == 0:
                print("  ✓ Ollama installed successfully")
                return True

            print(f"  Install failed: {result.stderr}")
            return False

        else:
            print("  Please install Ollama manually from https://ollama.com/download")
            return False

    except subprocess.TimeoutExpired:
        print("  Installation timed out")
        return False
    except Exception as e:
        print(f"  Installation failed: {e}")
        return False


def pull_ollama_model(model: str = DEFAULT_OLLAMA_MODEL) -> bool:
    """Pull the specified Ollama model.

    Args:
        model: The model name to pull (default: nomic-embed-text)

    Returns:
        True if model was pulled successfully, False otherwise
    """
    print(f"  Pulling {model} model (this may take a few minutes)...")

    try:
        result = subprocess.run(
            ["ollama", "pull", model],
            capture_output=True,
            text=True,
            timeout=600,  # Large models take time
        )

        if result.returncode == 0:
            print(f"  ✓ Model '{model}' pulled successfully")
            return True

        print(f"  Failed to pull model: {result.stderr}")
        return False

    except subprocess.TimeoutExpired:
        print("  Model pull timed out")
        return False
    except Exception as e:
        print(f"  Model pull failed: {e}")
        return False


# --- Orchestrator Functions ---


def _check_python_hard_dep() -> tuple[bool, str]:
    """Check Python version (hard dependency).

    Returns:
        Tuple of (success, error_message if failed)
    """
    ok, msg = check_python_version()
    _print_check(ok, msg)
    if not ok:
        if HAS_RICH and console:
            console.print(f"\n[bold soft_violet]Error:[/] [white]{msg}[/]")
            console.print("[dim_gray]Please upgrade Python to 3.9 or higher.[/]")
        else:
            print(f"\nError: {msg}")
            print("Please upgrade Python to 3.9 or higher.")
    return ok, msg


def _check_node_soft_dep() -> bool:
    """Check Node.js version (soft dependency).

    Returns:
        True if satisfied, False otherwise
    """
    ok, msg = check_node_version()
    _print_check(ok, msg, is_warning=True)
    if not ok:
        if HAS_RICH and console:
            console.print(
                "  [soft_violet]ℹ[/] [dim_gray]Node.js is optional — only needed for The Room dashboard[/]"
            )
            console.print(
                "  [soft_violet]ℹ[/] [dim_gray]Install Node.js 18+ from https://nodejs.org/ if you want the UI[/]"
            )
        else:
            print("  ℹ Node.js is optional — only needed for The Room dashboard")
            print("  ℹ Install Node.js 18+ from https://nodejs.org/ if you want the UI")
    return ok


def _check_openclaw_hard_dep() -> tuple[bool, str]:
    """Check OpenClaw gateway (hard dependency).

    Returns:
        Tuple of (success, error_message if failed)
    """
    ok, msg = check_openclaw_gateway()
    _print_check(ok, msg)
    if not ok:
        if HAS_RICH and console:
            console.print(f"\n[bold soft_violet]Error:[/] [white]{msg}[/]")
            console.print("[dim_gray]Start OpenClaw gateway: openclaw gateway start[/]")
        else:
            print(f"\nError: {msg}")
            print("Start OpenClaw gateway: openclaw gateway start")
    return ok, msg


def _check_and_install_ollama(auto_fix: bool, platform_name: str) -> bool:
    """Check Ollama installation and optionally install.

    Args:
        auto_fix: Whether to auto-install without prompting
        platform_name: Detected platform name

    Returns:
        True if Ollama is available, False otherwise
    """
    ollama_installed, msg = check_ollama_installed()
    _print_check(ollama_installed, msg, is_warning=True)

    if not ollama_installed:
        offer_ollama_install(platform_name)

        if auto_fix:
            return run_ollama_install(platform_name)
        elif sys.stdin.isatty():
            response = input("\n  Install Ollama now? ([y]es / [N]o): ").strip().lower()
            if response in ("y", "yes"):
                return run_ollama_install(platform_name)
    return ollama_installed


def _check_and_pull_model(auto_fix: bool) -> bool:
    """Check Ollama model and optionally pull it.

    Args:
        auto_fix: Whether to auto-pull without prompting

    Returns:
        True if model is available, False otherwise
    """
    model_ok, msg = check_ollama_model(DEFAULT_OLLAMA_MODEL)
    _print_check(model_ok, msg, is_warning=True)

    if not model_ok:
        if auto_fix:
            return pull_ollama_model(DEFAULT_OLLAMA_MODEL)
        elif sys.stdin.isatty():
            response = (
                input(f"\n  Pull {DEFAULT_OLLAMA_MODEL} now? ([Y]es / [n]o): ").strip().lower()
            )
            if response in ("", "y", "yes"):
                return pull_ollama_model(DEFAULT_OLLAMA_MODEL)
    return model_ok


def run_prerequisite_check(auto_fix: bool = False) -> int:
    """Run all prerequisite checks with interactive prompts.

    Args:
        auto_fix: If True, automatically install soft deps without prompting

    Returns:
        0: All checks passed
        1: Hard dependency missing (blocking)
        2: Soft dependency missing (non-blocking, continue with warnings)
    """
    print("Checking prerequisites for Emergence...\n")

    # Hard dependency: Python
    python_ok, _ = _check_python_hard_dep()
    if not python_ok:
        return 1

    # Soft dependency: Node (only needed for Room dashboard)
    node_ok = _check_node_soft_dep()

    # Hard dependency: OpenClaw gateway
    openclaw_ok, _ = _check_openclaw_hard_dep()
    if not openclaw_ok:
        return 1

    print()  # Blank line before soft deps

    # Soft dependency: Ollama
    platform_name = detect_platform()
    ollama_ok = _check_and_install_ollama(auto_fix, platform_name)

    # Check/pull model if Ollama is available
    model_ok = False
    if ollama_ok:
        model_ok = _check_and_pull_model(auto_fix)

    print()  # Blank line before summary

    # Determine final status
    soft_deps_ok = node_ok and ollama_ok and model_ok

    if soft_deps_ok:
        return 0
    else:
        if HAS_RICH and console:
            console.print(
                "[bold white]▲ Hard dependencies met. Soft dependencies optional but recommended.[/]"
            )
            console.print(
                "  [dim_gray]Emergence will work without Ollama, but embeddings won't be available.[/]"
            )
        else:
            print("▲ Hard dependencies met. Soft dependencies optional but recommended.")
            print("  Emergence will work without Ollama, but embeddings won't be available.")
        return 2


def run_check_json() -> dict[str, Any]:
    """Run all checks and return results as a dictionary.

    Returns:
        Dict containing all check results
    """
    results: dict[str, Any] = {"hard_deps_ok": True, "soft_deps_ok": True, "checks": {}}

    # Hard dependencies
    ok, msg = check_python_version()
    results["checks"]["python"] = {"ok": ok, "message": msg}
    if not ok:
        results["hard_deps_ok"] = False

    ok, msg = check_node_version()
    results["checks"]["node"] = {"ok": ok, "message": msg}
    if not ok:
        results["hard_deps_ok"] = False

    ok, msg = check_openclaw_gateway()
    results["checks"]["openclaw_gateway"] = {"ok": ok, "message": msg}
    if not ok:
        results["hard_deps_ok"] = False

    # Soft dependencies
    ok, msg = check_ollama_installed()
    results["checks"]["ollama_installed"] = {"ok": ok, "message": msg}
    if not ok:
        results["soft_deps_ok"] = False
    else:
        ok, msg = check_ollama_model(DEFAULT_OLLAMA_MODEL)
        results["checks"]["ollama_model"] = {"ok": ok, "message": msg}
        if not ok:
            results["soft_deps_ok"] = False

    results["platform"] = detect_platform()

    return results


# --- CLI Entry Point ---


def main() -> None:
    """CLI entry point for emergence check."""
    parser = argparse.ArgumentParser(
        description="Check prerequisites for Emergence", prog="emergence check"
    )
    parser.add_argument(
        "--auto-fix",
        "-a",
        action="store_true",
        help="Automatically install soft dependencies without prompting",
    )
    parser.add_argument("--json", action="store_true", help="Output results as JSON")

    args = parser.parse_args()

    if args.json:
        results = run_check_json()
        print(json.dumps(results, indent=2))
        sys.exit(0 if results["hard_deps_ok"] else 1)

    exit_code = run_prerequisite_check(auto_fix=args.auto_fix)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
