#!/usr/bin/env python3
"""Auto-start installer for Emergence Room dashboard.

Handles platform detection, service file generation, installation,
and lifecycle management for launchd (macOS) and systemd (Linux).

Example:
    from core.setup.autostart import get_installer
    
    installer = get_installer(Path("/workspace"), "MyAgent", 7373)
    if installer:
        success, message = installer.install()
        print(message)
"""

import os
import platform
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, Tuple


class PlatformInstaller(ABC):
    """Abstract base for platform-specific installers."""

    def __init__(self, workspace: Path, agent_name: str, room_port: int = 7373):
        self.workspace = Path(workspace).resolve()
        self.agent_name = agent_name
        self.room_port = room_port
        self.state_path = self.workspace / ".emergence" / "state"
        self.log_dir = self.workspace / ".emergence" / "logs"

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Platform identifier."""
        pass

    @abstractmethod
    def is_installed(self) -> bool:
        """Check if auto-start is already configured."""
        pass

    @abstractmethod
    def install(self) -> Tuple[bool, str]:
        """Install the auto-start service. Returns (success, message)."""
        pass

    @abstractmethod
    def uninstall(self) -> Tuple[bool, str]:
        """Remove the auto-start service. Returns (success, message)."""
        pass

    @abstractmethod
    def status(self) -> Tuple[bool, str]:
        """Check service status. Returns (is_running, status_message)."""
        pass

    @abstractmethod
    def start(self) -> Tuple[bool, str]:
        """Start the service now. Returns (success, message)."""
        pass

    @abstractmethod
    def stop(self) -> Tuple[bool, str]:
        """Stop the service. Returns (success, message)."""
        pass

    def _get_node_path(self) -> Optional[str]:
        """Find the Node.js executable path."""
        return shutil.which("node")

    def _get_server_path(self) -> Path:
        """Get the path to the Room server entry point."""
        return self.workspace / "room" / "server" / "index.js"

    def _ensure_log_dir(self) -> None:
        """Create log directory if it doesn't exist."""
        self.log_dir.mkdir(parents=True, exist_ok=True)

    def _agent_name_slug(self) -> str:
        """Generate a filesystem-safe slug from agent name."""
        return "".join(c if c.isalnum() else "-" for c in self.agent_name.lower()).strip("-")


class MacOSInstaller(PlatformInstaller):
    """macOS launchd installer.

    Installs a LaunchAgent plist that starts the Room server at user login.
    Service files are stored in ~/Library/LaunchAgents/
    """

    LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"

    @property
    def platform_name(self) -> str:
        return "macOS"

    @property
    def plist_path(self) -> Path:
        """Path to the plist file."""
        slug = self._agent_name_slug()
        return self.LAUNCH_AGENTS_DIR / f"com.emergence.room.{slug}.plist"

    @property
    def service_id(self) -> str:
        """launchd service identifier."""
        return f"com.emergence.room.{self._agent_name_slug()}"

    def is_installed(self) -> bool:
        return self.plist_path.exists()

    def install(self) -> Tuple[bool, str]:
        """Install the launchd service.

        Returns:
            Tuple of (success: bool, message: str)
        """
        self._ensure_log_dir()

        node_path = self._get_node_path()
        if not node_path:
            return False, "Node.js not found in PATH. Install Node.js 18+ to use the Room."

        server_path = self._get_server_path()
        if not server_path.exists():
            return False, f"Room server not found: {server_path}"

        # Load template
        template = self._load_template("launchd.plist")

        # Substitute values
        plist_content = template.replace("{{AGENT_NAME_SLUG}}", self._agent_name_slug())
        plist_content = plist_content.replace("{{WORKSPACE_PATH}}", str(self.workspace))
        plist_content = plist_content.replace("{{STATE_PATH}}", str(self.state_path))
        plist_content = plist_content.replace("{{ROOM_PORT}}", str(self.room_port))
        plist_content = plist_content.replace("{{NODE_PATH}}", node_path)
        plist_content = plist_content.replace("{{SERVER_PATH}}", str(server_path))
        plist_content = plist_content.replace("{{LOG_DIR}}", str(self.log_dir))
        plist_content = plist_content.replace("{{USER_NAME}}", os.getenv("USER", "unknown"))

        # Write plist
        try:
            self.LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
            self.plist_path.write_text(plist_content, encoding="utf-8")
        except (OSError, IOError) as e:
            return False, f"Failed to write plist: {e}"

        # Load into launchd
        result = subprocess.run(
            ["launchctl", "load", str(self.plist_path)],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # Clean up on failure
            self.plist_path.unlink(missing_ok=True)
            return False, f"Failed to load service: {result.stderr}"

        return True, f"Installed {self.service_id} - Room will start on next login"

    def uninstall(self) -> Tuple[bool, str]:
        """Remove the launchd service.

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.is_installed():
            return True, "Auto-start not configured"

        # Unload first
        subprocess.run(
            ["launchctl", "unload", str(self.plist_path)],
            capture_output=True
        )

        # Remove plist
        try:
            self.plist_path.unlink()
        except (OSError, IOError) as e:
            return False, f"Failed to remove plist: {e}"

        return True, f"Removed {self.service_id}"

    def status(self) -> Tuple[bool, str]:
        """Check if the service is running.

        Returns:
            Tuple of (is_running: bool, status_message: str)
        """
        result = subprocess.run(
            ["launchctl", "list", self.service_id],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False, "Service not loaded"

        # Parse launchctl list output for PID
        lines = result.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split("\t")
            pid = parts[0] if len(parts) > 0 else "-"
            if pid and pid != "-":
                return True, f"Running (PID: {pid})"

        return False, "Loaded but not running"

    def start(self) -> Tuple[bool, str]:
        """Start the service immediately.

        Returns:
            Tuple of (success: bool, message: str)
        """
        result = subprocess.run(
            ["launchctl", "start", self.service_id],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False, f"Failed to start: {result.stderr}"

        return True, "Service started"

    def stop(self) -> Tuple[bool, str]:
        """Stop the service.

        Returns:
            Tuple of (success: bool, message: str)
        """
        result = subprocess.run(
            ["launchctl", "stop", self.service_id],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False, f"Failed to stop: {result.stderr}"

        return True, "Service stopped"

    def _load_template(self, name: str) -> str:
        """Load a template file."""
        template_path = Path(__file__).parent / "templates" / name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        return template_path.read_text(encoding="utf-8")


class LinuxInstaller(PlatformInstaller):
    """Linux systemd installer.

    Supports both user-mode (default, no sudo required) and system-wide
    (requires sudo) installation.

    User-mode services are stored in ~/.config/systemd/user/
    System-wide services are stored in /etc/systemd/system/
    """

    SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"

    def __init__(
        self,
        workspace: Path,
        agent_name: str,
        room_port: int = 7373,
        system_wide: bool = False
    ):
        super().__init__(workspace, agent_name, room_port)
        self.system_wide = system_wide

        if system_wide:
            self.SYSTEMD_DIR = Path("/etc/systemd/system")
        else:
            self.SYSTEMD_DIR = self.SYSTEMD_USER_DIR

    @property
    def platform_name(self) -> str:
        return "Linux" + (" (system)" if self.system_wide else " (user)")

    @property
    def service_file_path(self) -> Path:
        """Path to the service file."""
        slug = self._agent_name_slug()
        return self.SYSTEMD_DIR / f"emergence-room-{slug}.service"

    @property
    def service_name(self) -> str:
        """systemd service name."""
        return f"emergence-room-{self._agent_name_slug()}.service"

    def is_installed(self) -> bool:
        return self.service_file_path.exists()

    def install(self) -> Tuple[bool, str]:
        """Install the systemd service.

        Returns:
            Tuple of (success: bool, message: str)
        """
        self._ensure_log_dir()

        node_path = self._get_node_path()
        if not node_path:
            return False, "Node.js not found in PATH. Install Node.js 18+ to use the Room."

        server_path = self._get_server_path()
        if not server_path.exists():
            return False, f"Room server not found: {server_path}"

        # Load template
        template = self._load_template("systemd.service")

        # Substitute values
        service_content = template.replace("{{AGENT_NAME}}", self.agent_name)
        service_content = service_content.replace("{{USER_NAME}}", os.getenv("USER", "unknown"))
        service_content = service_content.replace("{{WORKSPACE_PATH}}", str(self.workspace))
        service_content = service_content.replace("{{STATE_PATH}}", str(self.state_path))
        service_content = service_content.replace("{{ROOM_PORT}}", str(self.room_port))
        service_content = service_content.replace("{{NODE_PATH}}", node_path)
        service_content = service_content.replace("{{SERVER_PATH}}", str(server_path))
        service_content = service_content.replace("{{LOG_DIR}}", str(self.log_dir))

        # Ensure directory exists
        try:
            self.service_file_path.parent.mkdir(parents=True, exist_ok=True)
        except (OSError, IOError) as e:
            if self.system_wide and os.geteuid() != 0:
                return False, f"Permission denied. Run with sudo for system-wide install: {e}"
            return False, f"Failed to create directory: {e}"

        # Write service file
        try:
            self.service_file_path.write_text(service_content, encoding="utf-8")
        except (OSError, IOError) as e:
            return False, f"Failed to write service file: {e}"

        # Reload systemd daemon
        scope = "--user" if not self.system_wide else "--system"
        subprocess.run(
            ["systemctl", scope, "daemon-reload"],
            capture_output=True
        )

        # Enable service (start on boot)
        result = subprocess.run(
            ["systemctl", scope, "enable", self.service_name],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            # Clean up on failure
            self.service_file_path.unlink(missing_ok=True)
            return False, f"Failed to enable service: {result.stderr}"

        scope_str = "system" if self.system_wide else "user"
        return True, f"Installed {self.service_name} ({scope_str}) - enabled for next boot"

    def uninstall(self) -> Tuple[bool, str]:
        """Remove the systemd service.

        Returns:
            Tuple of (success: bool, message: str)
        """
        if not self.is_installed():
            return True, "Auto-start not configured"

        scope = "--user" if not self.system_wide else "--system"

        # Disable first
        subprocess.run(
            ["systemctl", scope, "disable", self.service_name],
            capture_output=True
        )

        # Stop if running
        subprocess.run(
            ["systemctl", scope, "stop", self.service_name],
            capture_output=True
        )

        # Remove service file
        try:
            self.service_file_path.unlink()
        except (OSError, IOError) as e:
            return False, f"Failed to remove service file: {e}"

        # Reload daemon
        subprocess.run(
            ["systemctl", scope, "daemon-reload"],
            capture_output=True
        )

        return True, f"Removed {self.service_name}"

    def status(self) -> Tuple[bool, str]:
        """Check if the service is running.

        Returns:
            Tuple of (is_running: bool, status_message: str)
        """
        scope = "--user" if not self.system_wide else "--system"

        result = subprocess.run(
            ["systemctl", scope, "is-active", self.service_name],
            capture_output=True,
            text=True
        )

        is_active = result.returncode == 0
        status_output = result.stdout.strip()

        if not status_output:
            status_output = "running" if is_active else "inactive"

        return is_active, status_output

    def start(self) -> Tuple[bool, str]:
        """Start the service immediately.

        Returns:
            Tuple of (success: bool, message: str)
        """
        scope = "--user" if not self.system_wide else "--system"

        result = subprocess.run(
            ["systemctl", scope, "start", self.service_name],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False, f"Failed to start: {result.stderr}"

        return True, "Service started"

    def stop(self) -> Tuple[bool, str]:
        """Stop the service.

        Returns:
            Tuple of (success: bool, message: str)
        """
        scope = "--user" if not self.system_wide else "--system"

        result = subprocess.run(
            ["systemctl", scope, "stop", self.service_name],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            return False, f"Failed to stop: {result.stderr}"

        return True, "Service stopped"

    def _load_template(self, name: str) -> str:
        """Load a template file."""
        template_path = Path(__file__).parent / "templates" / name
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        return template_path.read_text(encoding="utf-8")


def get_installer(
    workspace: Path,
    agent_name: str,
    room_port: int = 7373
) -> Optional[PlatformInstaller]:
    """Factory function to get the appropriate installer for the current platform.

    Args:
        workspace: Path to the Emergence workspace
        agent_name: Name of the agent (for service identification)
        room_port: Port the Room server will listen on

    Returns:
        PlatformInstaller instance appropriate for the current platform,
        or None if the platform is not supported.

    Example:
        installer = get_installer(Path("/workspace"), "MyAgent", 7373)
        if installer:
            success, msg = installer.install()
    """
    system = platform.system().lower()

    if system == "darwin":
        return MacOSInstaller(workspace, agent_name, room_port)
    elif system == "linux":
        # Default to user-mode systemd (no sudo required)
        return LinuxInstaller(workspace, agent_name, room_port, system_wide=False)
    else:
        return None


def check_sudo() -> bool:
    """Check if we have passwordless sudo access.

    Returns:
        True if sudo -n succeeds (no password required), False otherwise.
    """
    result = subprocess.run(
        ["sudo", "-n", "true"],
        capture_output=True
    )
    return result.returncode == 0
