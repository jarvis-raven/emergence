#!/usr/bin/env python3
"""OpenClaw hook installer for Emergence drives integration.

Installs an OpenClaw hook that injects DRIVES.md into session bootstrap,
providing real-time drive state visibility to agents.

Example:
    from core.setup.openclaw_hook import install_hook

    success, message = install_hook()
    print(message)
"""

import shutil
import subprocess
from pathlib import Path
from typing import Tuple


def get_hook_dir() -> Path:
    """Get the OpenClaw hooks directory path."""
    return Path.home() / ".openclaw" / "hooks" / "emergence-drives"


def is_openclaw_installed() -> bool:
    """Check if OpenClaw is installed."""
    return shutil.which("openclaw") is not None


def is_hook_installed() -> bool:
    """Check if the Emergence hook is already installed."""
    hook_dir = get_hook_dir()
    handler_path = hook_dir / "handler.ts"
    return handler_path.exists()


def install_hook(force: bool = False) -> Tuple[bool, str]:
    """Install the Emergence drives hook for OpenClaw.

    Args:
        force: Overwrite existing hook if present

    Returns:
        Tuple of (success: bool, message: str)
    """
    # Check if OpenClaw is installed
    if not is_openclaw_installed():
        return False, "OpenClaw not found. Install OpenClaw first: npm install -g openclaw"

    # Check if already installed
    if is_hook_installed() and not force:
        return True, f"Hook already installed at {get_hook_dir()}"

    # Get template directory
    template_dir = Path(__file__).parent / "templates"
    if not template_dir.exists():
        return False, f"Template directory not found: {template_dir}"

    # Create hook directory
    hook_dir = get_hook_dir()
    try:
        hook_dir.mkdir(parents=True, exist_ok=True)
    except (OSError, IOError) as e:
        return False, f"Failed to create hook directory: {e}"

    # Copy template files
    files_to_copy = ["handler.ts", "HOOK.md"]

    for filename in files_to_copy:
        src = template_dir / filename
        dst = hook_dir / filename

        if not src.exists():
            return False, f"Template file not found: {src}"

        try:
            shutil.copy2(src, dst)
        except (OSError, IOError) as e:
            return False, f"Failed to copy {filename}: {e}"

    # Suggest gateway restart
    restart_msg = "\n\nTo activate: openclaw gateway restart"

    return True, f"✓ Installed Emergence drives hook at {hook_dir}{restart_msg}"


def uninstall_hook() -> Tuple[bool, str]:
    """Remove the Emergence drives hook.

    Returns:
        Tuple of (success: bool, message: str)
    """
    hook_dir = get_hook_dir()

    if not hook_dir.exists():
        return True, "Hook not installed"

    try:
        shutil.rmtree(hook_dir)
    except (OSError, IOError) as e:
        return False, f"Failed to remove hook: {e}"

    return (
        True,
        f"✓ Removed hook from {hook_dir}\n\nRestart gateway to complete: openclaw gateway restart",
    )


def hook_status() -> Tuple[bool, str]:
    """Check the status of the OpenClaw hook.

    Returns:
        Tuple of (is_installed: bool, status_message: str)
    """
    if not is_openclaw_installed():
        return False, "OpenClaw: not installed"

    hook_dir = get_hook_dir()

    if not is_hook_installed():
        return False, f"Hook: not installed\nInstall with: emergence openclaw-hook install"

    # Check if files are present
    handler = hook_dir / "handler.ts"
    hook_md = hook_dir / "HOOK.md"

    files_ok = handler.exists() and hook_md.exists()

    status_lines = [
        f"Hook: installed at {hook_dir}",
        f"  handler.ts: {'✓' if handler.exists() else '✗'}",
        f"  HOOK.md: {'✓' if hook_md.exists() else '✗'}",
    ]

    # Check if gateway is running
    result = subprocess.run(["openclaw", "gateway", "status"], capture_output=True, text=True)

    if result.returncode == 0:
        status_lines.append("Gateway: running")
    else:
        status_lines.append("Gateway: not running")

    return files_ok, "\n".join(status_lines)
