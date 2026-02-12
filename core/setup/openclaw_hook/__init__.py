"""OpenClaw hook installer for Emergence."""

from .installer import (
    install_hook,
    uninstall_hook,
    hook_status,
    is_hook_installed,
    is_openclaw_installed,
)

__all__ = [
    "install_hook",
    "uninstall_hook",
    "hook_status",
    "is_hook_installed",
    "is_openclaw_installed",
]
