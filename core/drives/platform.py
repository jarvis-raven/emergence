from typing import Optional

"""Platform detection and daemon installation for different operating systems.

Provides cross-platform support for running the drive daemon as a
background service via macOS LaunchAgent, Linux systemd, or cron fallback.
"""

import platform
import subprocess
import sys
from pathlib import Path


def detect_platform() -> str:
    """Detect the current operating system platform.

    Returns:
        One of: "macos", "linux", "generic"

    Examples:
        >>> plat = detect_platform()
        >>> plat in ("macos", "linux", "generic")
        True
    """
    system = platform.system().lower()

    if system == "darwin":
        return "macos"
    elif system == "linux":
        return "linux"
    else:
        return "generic"


def get_launchagent_dir() -> Path:
    """Get the LaunchAgents directory path for macOS.

    Returns:
        Path to ~/Library/LaunchAgents
    """
    return Path.home() / "Library" / "LaunchAgents"


def get_launchagent_path(config: dict) -> Path:
    """Get the LaunchAgent plist file path.

    Args:
        config: Configuration dictionary

    Returns:
        Path to the plist file
    """
    return get_launchagent_dir() / "com.emergence.drives.plist"


def generate_launchagent_plist(config: dict, daemon_script_path: Optional[str] = None) -> str:
    """Generate macOS LaunchAgent plist XML content.

    Args:
        config: Configuration dictionary
        daemon_script_path: Optional path to daemon script (auto-detected if None)

    Returns:
        XML plist content as string
    """
    tick_interval = config.get("drives", {}).get("tick_interval", 900)
    workspace = config.get("paths", {}).get("workspace", ".")

    # Find the emergence project root (parent of core/)
    emergence_root = Path(__file__).parent.parent.parent.resolve()

    plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.emergence.drives</string>

    <key>ProgramArguments</key>
    <array>
        <string>{sys.executable}</string>
        <string>-m</string>
        <string>core.drives.daemon</string>
        <string>--foreground</string>
    </array>

    <key>WorkingDirectory</key>
    <string>{emergence_root}</string>

    <key>StartInterval</key>
    <integer>{tick_interval}</integer>

    <key>RunAtLoad</key>
    <true/>

    <key>StandardOutPath</key>
    <string>{Path(workspace).resolve()}/.emergence/logs/daemon.log</string>

    <key>StandardErrorPath</key>
    <string>{Path(workspace).resolve()}/.emergence/logs/daemon.log</string>

    <key>EnvironmentVariables</key>
    <dict>
        <key>PYTHONPATH</key>
        <string>{':'.join(sys.path)}</string>
    </dict>
</dict>
</plist>"""

    return plist_content


def install_launchagent(config: dict) -> dict:
    """Install macOS LaunchAgent for the drive daemon.

    Creates the plist file in ~/Library/LaunchAgents/ and loads it.

    Args:
        config: Configuration dictionary

    Returns:
        Result dict with success status and details
    """
    result = {"success": False, "platform": "macos", "errors": []}

    # Ensure LaunchAgents directory exists
    launchagent_dir = get_launchagent_dir()
    try:
        launchagent_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        result["errors"].append(f"Failed to create LaunchAgents directory: {e}")
        return result

    plist_path = get_launchagent_path(config)
    plist_content = generate_launchagent_plist(config)

    # Write plist file
    try:
        with open(plist_path, "w", encoding="utf-8") as f:
            f.write(plist_content)
        result["plist_path"] = str(plist_path)
    except IOError as e:
        result["errors"].append(f"Failed to write plist file: {e}")
        return result

    # Unload if already exists (ignore errors)
    try:
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True, timeout=5)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Load the LaunchAgent
    try:
        subprocess.run(
            ["launchctl", "load", str(plist_path)], capture_output=True, check=True, timeout=5
        )
        result["success"] = True
        result["status"] = "loaded"
    except subprocess.CalledProcessError as e:
        result["errors"].append(f"Failed to load LaunchAgent: {e}")
    except FileNotFoundError:
        result["errors"].append("launchctl not found - is this macOS?")
    except subprocess.TimeoutExpired:
        result["errors"].append("Timeout while loading LaunchAgent")

    return result


def uninstall_launchagent(config: dict) -> dict:
    """Uninstall macOS LaunchAgent.

    Unloads and removes the plist file.

    Args:
        config: Configuration dictionary

    Returns:
        Result dict with success status and details
    """
    result = {"success": False, "platform": "macos", "errors": []}

    plist_path = get_launchagent_path(config)

    # Unload if loaded
    try:
        subprocess.run(["launchctl", "unload", str(plist_path)], capture_output=True, timeout=5)
        result["status"] = "unloaded"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Remove plist file
    try:
        if plist_path.exists():
            plist_path.unlink()
            result["plist_removed"] = True
    except OSError as e:
        result["errors"].append(f"Failed to remove plist file: {e}")

    result["success"] = len(result["errors"]) == 0
    return result


def get_systemd_dir() -> Path:
    """Get the systemd user directory path.

    Returns:
        Path to ~/.config/systemd/user
    """
    return Path.home() / ".config" / "systemd" / "user"


def generate_systemd_service(config: dict, daemon_script_path: Optional[str] = None) -> str:
    """Generate systemd service file content.

    Args:
        config: Configuration dictionary
        daemon_script_path: Optional path to daemon script

    Returns:
        systemd service file content
    """
    workspace = config.get("paths", {}).get("workspace", ".")

    # Find the emergence project root (parent of core/)
    emergence_root = Path(__file__).parent.parent.parent.resolve()

    service_content = f"""[Unit]
Description=Emergence Drive Daemon
After=network.target

[Service]
Type=simple
WorkingDirectory={emergence_root}
ExecStart={sys.executable} -m core.drives.daemon --foreground
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
"""

    return service_content


def generate_systemd_timer(config: dict) -> str:
    """Generate systemd timer file content.

    Args:
        config: Configuration dictionary

    Returns:
        systemd timer file content
    """
    tick_interval = config.get("drives", {}).get("tick_interval", 900)

    timer_content = f"""[Unit]
Description=Emergence Drive Daemon Timer

[Timer]
OnBootSec=1min
OnUnitInactiveSec={tick_interval}s
Unit=emergence-drives.service

[Install]
WantedBy=timers.target
"""

    return timer_content


def install_systemd(config: dict) -> dict:
    """Install systemd user service for the drive daemon.

    Creates service and timer files in ~/.config/systemd/user/

    Args:
        config: Configuration dictionary

    Returns:
        Result dict with success status and details
    """
    result = {"success": False, "platform": "linux", "errors": []}

    # Ensure systemd directory exists
    systemd_dir = get_systemd_dir()
    try:
        systemd_dir.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        result["errors"].append(f"Failed to create systemd directory: {e}")
        return result

    service_path = systemd_dir / "emergence-drives.service"
    timer_path = systemd_dir / "emergence-drives.timer"

    # Write service file
    try:
        with open(service_path, "w", encoding="utf-8") as f:
            f.write(generate_systemd_service(config))
        result["service_path"] = str(service_path)
    except IOError as e:
        result["errors"].append(f"Failed to write service file: {e}")
        return result

    # Write timer file
    try:
        with open(timer_path, "w", encoding="utf-8") as f:
            f.write(generate_systemd_timer(config))
        result["timer_path"] = str(timer_path)
    except IOError as e:
        result["errors"].append(f"Failed to write timer file: {e}")
        return result

    # Reload systemd daemon
    try:
        subprocess.run(
            ["systemctl", "--user", "daemon-reload"], capture_output=True, check=True, timeout=10
        )
    except subprocess.CalledProcessError as e:
        result["errors"].append(f"Failed to reload systemd: {e}")
        return result
    except FileNotFoundError:
        result["errors"].append("systemctl not found - is this Linux?")
        return result
    except subprocess.TimeoutExpired:
        result["errors"].append("Timeout while reloading systemd")
        return result

    # Enable and start timer
    try:
        subprocess.run(
            ["systemctl", "--user", "enable", "emergence-drives.timer"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        subprocess.run(
            ["systemctl", "--user", "start", "emergence-drives.timer"],
            capture_output=True,
            check=True,
            timeout=5,
        )
        result["success"] = True
        result["status"] = "enabled and started"
    except subprocess.CalledProcessError as e:
        result["errors"].append(f"Failed to enable/start timer: {e}")
    except subprocess.TimeoutExpired:
        result["errors"].append("Timeout while enabling timer")

    return result


def uninstall_systemd(config: dict) -> dict:
    """Uninstall systemd user service.

    Stops, disables, and removes the service and timer files.

    Args:
        config: Configuration dictionary

    Returns:
        Result dict with success status and details
    """
    result = {"success": False, "platform": "linux", "errors": []}

    systemd_dir = get_systemd_dir()
    service_path = systemd_dir / "emergence-drives.service"
    timer_path = systemd_dir / "emergence-drives.timer"

    # Stop and disable timer
    try:
        subprocess.run(
            ["systemctl", "--user", "stop", "emergence-drives.timer"],
            capture_output=True,
            timeout=5,
        )
        subprocess.run(
            ["systemctl", "--user", "disable", "emergence-drives.timer"],
            capture_output=True,
            timeout=5,
        )
        result["status"] = "stopped and disabled"
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    # Remove files
    try:
        if service_path.exists():
            service_path.unlink()
            result["service_removed"] = True
        if timer_path.exists():
            timer_path.unlink()
            result["timer_removed"] = True
    except OSError as e:
        result["errors"].append(f"Failed to remove service files: {e}")

    # Reload systemd
    try:
        subprocess.run(["systemctl", "--user", "daemon-reload"], capture_output=True, timeout=5)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    result["success"] = len(result["errors"]) == 0
    return result


def generate_cron_entry(config: dict, command_path: Optional[str] = None) -> str:
    """Generate crontab entry for the drive tick command.

    Args:
        config: Configuration dictionary
        command_path: Optional path to the drives command

    Returns:
        Cron entry string
    """
    tick_interval = config.get("drives", {}).get("tick_interval", 900)
    workspace = config.get("paths", {}).get("workspace", ".")

    # Convert seconds to minutes, round to nearest
    interval_minutes = max(1, round(tick_interval / 60))

    if command_path is None:
        # Use module execution
        cmd = f"cd {Path(workspace).resolve()} && {sys.executable} -m emergence.core.drives tick"
    else:
        cmd = f"cd {Path(workspace).resolve()} && {command_path} tick"

    log_path = Path(workspace).resolve() / ".emergence" / "logs" / "cron.log"

    # Generate cron expression
    if interval_minutes >= 60:
        hours = interval_minutes // 60
        cron_expr = f"0 */{hours} * * *"
    else:
        cron_expr = f"*/{interval_minutes} * * * *"

    return f"{cron_expr} {cmd} >> {log_path} 2>&1"


def install_cron(config: dict) -> dict:
    """Install cron job for drive ticks.

    Adds an entry to the user's crontab.

    Args:
        config: Configuration dictionary

    Returns:
        Result dict with success status and details
    """
    result = {"success": False, "platform": "generic", "errors": []}

    # Get current crontab
    try:
        proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        current_crontab = proc.stdout if proc.returncode == 0 else ""
    except FileNotFoundError:
        result["errors"].append("crontab not found - is cron installed?")
        return result
    except subprocess.TimeoutExpired:
        result["errors"].append("Timeout while reading crontab")
        return result

    # Remove existing emergence entry if present
    lines = current_crontab.split("\n")
    lines = [l for l in lines if "emergence" not in l.lower() or "emergence.core.drives" not in l]

    # Add new entry
    cron_entry = generate_cron_entry(config)
    lines.append(cron_entry)
    lines.append("")  # Trailing newline

    new_crontab = "\n".join(lines)

    # Install new crontab
    try:
        proc = subprocess.run(
            ["crontab", "-"], input=new_crontab, capture_output=True, text=True, timeout=5
        )
        if proc.returncode == 0:
            result["success"] = True
            result["status"] = "installed"
            result["cron_entry"] = cron_entry
        else:
            result["errors"].append(f"crontab install failed: {proc.stderr}")
    except subprocess.TimeoutExpired:
        result["errors"].append("Timeout while installing crontab")
    except FileNotFoundError:
        result["errors"].append("crontab command not found")

    return result


def uninstall_cron(config: dict) -> dict:
    """Uninstall cron job for drive ticks.

    Removes emergence entries from the user's crontab.

    Args:
        config: Configuration dictionary

    Returns:
        Result dict with success status and details
    """
    result = {"success": False, "platform": "generic", "errors": []}

    # Get current crontab
    try:
        proc = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=5)
        current_crontab = proc.stdout if proc.returncode == 0 else ""
    except FileNotFoundError:
        result["success"] = True  # Nothing to remove
        result["status"] = "not installed"
        return result
    except subprocess.TimeoutExpired:
        result["errors"].append("Timeout while reading crontab")
        return result

    # Remove emergence entries
    lines = current_crontab.split("\n")
    original_count = len(lines)
    lines = [l for l in lines if "emergence" not in l.lower() or "emergence.core.drives" not in l]

    if len(lines) == original_count:
        result["success"] = True
        result["status"] = "not found"
        return result

    new_crontab = "\n".join(lines)

    # Install new crontab
    try:
        proc = subprocess.run(
            ["crontab", "-"], input=new_crontab, capture_output=True, text=True, timeout=5
        )
        if proc.returncode == 0:
            result["success"] = True
            result["status"] = "removed"
        else:
            result["errors"].append(f"crontab update failed: {proc.stderr}")
    except subprocess.TimeoutExpired:
        result["errors"].append("Timeout while updating crontab")

    return result


def install_platform(config: dict, platform_name: Optional[str] = None) -> dict:
    """Install daemon for the specified or detected platform.

    Args:
        config: Configuration dictionary
        platform_name: Platform to install for, or None to auto-detect

    Returns:
        Result dict with success status and details
    """
    if platform_name is None:
        platform_name = detect_platform()

    if platform_name == "macos":
        return install_launchagent(config)
    elif platform_name == "linux":
        return install_systemd(config)
    else:
        return install_cron(config)


def uninstall_platform(config: dict, platform_name: Optional[str] = None) -> dict:
    """Uninstall daemon for the specified or detected platform.

    Args:
        config: Configuration dictionary
        platform_name: Platform to uninstall from, or None to auto-detect

    Returns:
        Result dict with success status and details
    """
    if platform_name is None:
        platform_name = detect_platform()

    if platform_name == "macos":
        return uninstall_launchagent(config)
    elif platform_name == "linux":
        return uninstall_systemd(config)
    else:
        return uninstall_cron(config)


def get_install_status(config: dict) -> dict:
    """Get installation status for all platforms.

    Args:
        config: Configuration dictionary

    Returns:
        Dict with status for each platform
    """
    status = {"platform": detect_platform(), "installations": {}}

    # Check macOS LaunchAgent
    plist_path = get_launchagent_path(config)
    if plist_path.exists():
        # Check if loaded
        try:
            result = subprocess.run(
                ["launchctl", "list", "com.emergence.drives"], capture_output=True, timeout=2
            )
            loaded = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            loaded = False

        status["installations"]["macos"] = {
            "installed": True,
            "loaded": loaded,
            "path": str(plist_path),
        }
    else:
        status["installations"]["macos"] = {"installed": False}

    # Check Linux systemd
    service_path = get_systemd_dir() / "emergence-drives.service"
    if service_path.exists():
        try:
            result = subprocess.run(
                ["systemctl", "--user", "is-active", "emergence-drives.timer"],
                capture_output=True,
                timeout=2,
            )
            active = result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            active = False

        status["installations"]["linux"] = {
            "installed": True,
            "active": active,
            "path": str(service_path),
        }
    else:
        status["installations"]["linux"] = {"installed": False}

    # Check cron (generic)
    try:
        result = subprocess.run(["crontab", "-l"], capture_output=True, text=True, timeout=2)
        has_cron = result.returncode == 0 and "emergence" in result.stdout.lower()
        status["installations"]["cron"] = {"installed": has_cron}
    except (subprocess.TimeoutExpired, FileNotFoundError):
        status["installations"]["cron"] = {"installed": False}

    return status
