"""Auto-start installer for Emergence Room dashboard.

Provides cross-platform service installation for:
- macOS: launchd (user LaunchAgents)
- Linux: systemd (user services by default, system-wide optional)

Example:
    from core.setup.autostart import get_installer

    installer = get_installer(workspace, agent_name, room_port)
    if installer:
        success, message = installer.install()
        print(message)
"""

from .installer import (
    PlatformInstaller,
    MacOSInstaller,
    LinuxInstaller,
    get_installer,
    check_sudo,
)

__all__ = [
    "PlatformInstaller",
    "MacOSInstaller",
    "LinuxInstaller",
    "get_installer",
    "check_sudo",
]
