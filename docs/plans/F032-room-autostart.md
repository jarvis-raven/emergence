# F032: Room Auto-Start Implementation Plan

## Overview
Implement automatic startup for the Room dashboard server so it launches on system boot. Support macOS (launchd) and Linux (systemd) platforms.

---

## 1. File Structure

```
core/setup/
├── __init__.py
├── init_wizard.py          # ← Hook auto-start prompt here
├── autostart/
│   ├── __init__.py         # Module exports
│   ├── installer.py        # Main install/uninstall logic
│   ├── templates/
│   │   ├── __init__.py
│   │   ├── launchd.plist   # macOS launchd template
│   │   └── systemd.service # Linux systemd template
│   └── platforms/
│       ├── __init__.py
│       ├── base.py         # Abstract base class
│       ├── macos.py        # macOS launchd implementation
│       └── linux.py        # Linux systemd implementation
```

---

## 2. Templates

### 2.1 macOS launchd Plist (`templates/launchd.plist`)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <!-- Service Identifier -->
    <key>Label</key>
    <string>com.emergence.room.{{AGENT_NAME_SLUG}}</string>
    
    <!-- Run at login/boot -->
    <key>RunAtLoad</key>
    <true/>
    
    <!-- Keep alive -->
    <key>KeepAlive</key>
    <dict>
        <key>SuccessfulExit</key>
        <false/>
        <key>Crashed</key>
        <true/>
    </dict>
    
    <!-- Throttle respawn to prevent crash loops -->
    <key>ThrottleInterval</key>
    <integer>60</integer>
    
    <!-- Working directory -->
    <key>WorkingDirectory</key>
    <string>{{WORKSPACE_PATH}}</string>
    
    <!-- Environment variables -->
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>NODE_ENV</key>
        <string>production</string>
        <key>EMERGENCE_STATE</key>
        <string>{{STATE_PATH}}</string>
    </dict>
    
    <!-- Program to run -->
    <key>ProgramArguments</key>
    <array>
        <string>{{NODE_PATH}}</string>
        <string>{{SERVER_PATH}}</string>
    </array>
    
    <!-- Standard output/error logging -->
    <key>StandardOutPath</key>
    <string>{{LOG_DIR}}/room.out.log</string>
    
    <key>StandardErrorPath</key>
    <string>{{LOG_DIR}}/room.err.log</string>
    
    <!-- Run as user (not root) -->
    <key>UserName</key>
    <string>{{USER_NAME}}</string>
</dict>
</plist>
```

### 2.2 Linux systemd Service (`templates/systemd.service`)

```ini
[Unit]
Description=Emergence Room Dashboard ({{AGENT_NAME}})
Documentation=https://github.com/openclaw/emergence
After=network.target
Wants=network.target

[Service]
Type=simple
User={{USER_NAME}}
WorkingDirectory={{WORKSPACE_PATH}}

# Node.js execution
ExecStart={{NODE_PATH}} {{SERVER_PATH}}
ExecReload=/bin/kill -HUP $MAINPID
Restart=on-failure
RestartSec=10

# Environment
Environment="NODE_ENV=production"
Environment="EMERGENCE_STATE={{STATE_PATH}}"
Environment="PORT={{ROOM_PORT}}"

# Resource limits (generous defaults)
LimitNOFILE=65535

# Logging
StandardOutput=append:{{LOG_DIR}}/room.out.log
StandardError=append:{{LOG_DIR}}/room.err.log
SyslogIdentifier=emergence-room

# Security hardening
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=false
ReadWritePaths={{WORKSPACE_PATH}} {{STATE_PATH}}

[Install]
WantedBy=default.target
```

---

## 3. Install Script (`autostart/installer.py`)

```python
#!/usr/bin/env python3
"""Auto-start installer for Emergence Room dashboard.

Handles platform detection, service file generation, installation,
and lifecycle management for launchd (macOS) and systemd (Linux).
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
    """macOS launchd installer."""
    
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
        self._ensure_log_dir()
        
        node_path = self._get_node_path()
        if not node_path:
            return False, "Node.js not found in PATH"
        
        server_path = self._get_server_path()
        if not server_path.exists():
            return False, f"Room server not found: {server_path}"
        
        # Load template
        template = self._load_template("launchd.plist")
        
        # Substitute values
        plist_content = template.replace("{{AGENT_NAME_SLUG}}", self._agent_name_slug())
        plist_content = plist_content.replace("{{WORKSPACE_PATH}}", str(self.workspace))
        plist_content = plist_content.replace("{{STATE_PATH}}", str(self.state_path))
        plist_content = plist_content.replace("{{NODE_PATH}}", node_path)
        plist_content = plist_content.replace("{{SERVER_PATH}}", str(server_path))
        plist_content = plist_content.replace("{{LOG_DIR}}", str(self.log_dir))
        plist_content = plist_content.replace("{{USER_NAME}}", os.getenv("USER", "unknown"))
        
        # Write plist
        self.LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        self.plist_path.write_text(plist_content, encoding="utf-8")
        
        # Load into launchd
        result = subprocess.run(
            ["launchctl", "load", str(self.plist_path)],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return False, f"Failed to load service: {result.stderr}"
        
        return True, f"Installed {self.service_id} - Room will start on next login"
    
    def uninstall(self) -> Tuple[bool, str]:
        if not self.is_installed():
            return True, "Auto-start not configured"
        
        # Unload first
        subprocess.run(
            ["launchctl", "unload", str(self.plist_path)],
            capture_output=True
        )
        
        # Remove plist
        self.plist_path.unlink()
        
        return True, f"Removed {self.service_id}"
    
    def status(self) -> Tuple[bool, str]:
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
            if pid != "-" and pid != "":
                return True, f"Running (PID: {pid})"
        
        return False, "Loaded but not running"
    
    def start(self) -> Tuple[bool, str]:
        result = subprocess.run(
            ["launchctl", "start", self.service_id],
            capture_output=True,
            text=True
        )
        
        if result.returncode != 0:
            return False, f"Failed to start: {result.stderr}"
        
        return True, "Service started"
    
    def stop(self) -> Tuple[bool, str]:
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
        return template_path.read_text(encoding="utf-8")


class LinuxInstaller(PlatformInstaller):
    """Linux systemd installer (user mode)."""
    
    SYSTEMD_USER_DIR = Path.home() / ".config" / "systemd" / "user"
    SYSTEMD_SYSTEM_DIR = Path("/etc/systemd/system")
    
    def __init__(self, workspace: Path, agent_name: str, room_port: int = 7373, system_wide: bool = False):
        super().__init__(workspace, agent_name, room_port)
        self.system_wide = system_wide
    
    @property
    def platform_name(self) -> str:
        return "Linux" + (" (system)" if self.system_wide else " (user)")
    
    @property
    def service_file_path(self) -> Path:
        """Path to the service file."""
        slug = self._agent_name_slug()
        if self.system_wide:
            return self.SYSTEMD_SYSTEM_DIR / f"emergence-room-{slug}.service"
        return self.SYSTEMD_USER_DIR / f"emergence-room-{slug}.service"
    
    @property
    def service_name(self) -> str:
        """systemd service name."""
        return f"emergence-room-{self._agent_name_slug()}.service"
    
    def is_installed(self) -> bool:
        return self.service_file_path.exists()
    
    def install(self) -> Tuple[bool, str]:
        self._ensure_log_dir()
        
        node_path = self._get_node_path()
        if not node_path:
            return False, "Node.js not found in PATH"
        
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
        self.service_file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Write service file
        self.service_file_path.write_text(service_content, encoding="utf-8")
        
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
            return False, f"Failed to enable service: {result.stderr}"
        
        scope_str = "system" if self.system_wide else "user"
        return True, f"Installed {self.service_name} ({scope_str}) - Room will start on next boot"
    
    def uninstall(self) -> Tuple[bool, str]:
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
        self.service_file_path.unlink()
        
        # Reload daemon
        subprocess.run(
            ["systemctl", scope, "daemon-reload"],
            capture_output=True
        )
        
        return True, f"Removed {self.service_name}"
    
    def status(self) -> Tuple[bool, str]:
        scope = "--user" if not self.system_wide else "--system"
        
        result = subprocess.run(
            ["systemctl", scope, "is-active", self.service_name],
            capture_output=True,
            text=True
        )
        
        is_active = result.returncode == 0
        status_output = result.stdout.strip()
        
        return is_active, status_output if status_output else ("running" if is_active else "inactive")
    
    def start(self) -> Tuple[bool, str]:
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
        return template_path.read_text(encoding="utf-8")


def get_installer(workspace: Path, agent_name: str, room_port: int = 7373) -> Optional[PlatformInstaller]:
    """Factory function to get the appropriate installer for the current platform."""
    system = platform.system().lower()
    
    if system == "darwin":
        return MacOSInstaller(workspace, agent_name, room_port)
    elif system == "linux":
        # Default to user-mode systemd (no sudo required)
        return LinuxInstaller(workspace, agent_name, room_port, system_wide=False)
    else:
        return None


def check_sudo() -> bool:
    """Check if we have sudo access (for system-wide Linux install)."""
    result = subprocess.run(
        ["sudo", "-n", "true"],
        capture_output=True
    )
    return result.returncode == 0
```

---

## 4. Wizard Integration

### 4.1 Integration Point in `init_wizard.py`

Add after Room configuration section (around line 650-700, after config generation but before First Light kickoff):

```python
# --- Auto-start Setup (F032) ---
def ask_room_autostart(config: dict, workspace: Path) -> bool:
    """Ask user if they want Room to start automatically on boot.
    
    Args:
        config: The generated config dict
        workspace: Path to workspace
        
    Returns:
        True if auto-start was configured, False otherwise
    """
    from .autostart.installer import get_installer
    
    # Check if Room is enabled
    if not config.get("room", {}).get("enabled", True):
        return False
    
    room_port = config.get("room", {}).get("port", 7373)
    agent_name = config.get("agent", {}).get("name", "Emergence")
    
    # Get platform installer
    installer = get_installer(workspace, agent_name, room_port)
    
    if not installer:
        print_warning("Auto-start not available on this platform")
        return False
    
    # Check if already installed
    if installer.is_installed():
        print_success(f"Room auto-start already configured ({installer.platform_name})")
        return True
    
    # Prompt user
    print_subheader("Room Auto-Start")
    print(f"Would you like the Room dashboard to start automatically when you log in?")
    print(f"  • Platform: {installer.platform_name}")
    print(f"  • Port: {room_port}")
    print()
    
    if ask_confirm("Enable auto-start?", default=True):
        success, message = installer.install()
        
        if success:
            print_success(message)
            
            # Ask if they want to start it now
            if ask_confirm("Start Room now?", default=True):
                start_ok, start_msg = installer.start()
                if start_ok:
                    print_success(f"Room started - visit http://localhost:{room_port}")
                else:
                    print_warning(f"Could not start Room: {start_msg}")
                    print_dim("  You can start it manually with: emergence room start")
            
            return True
        else:
            print_error(f"Failed to install auto-start: {message}")
            return False
    
    return False
```

### 4.2 Call Site in `main()`

Insert call after config generation block:

```python
# F030: Config generation
print("Generating configuration...")
if parsed_args["interactive"]:
    config = interactive_config_wizard(
        answers.agent_name, answers.human_name,
        prefilled_name=answers.agent_name,
        prefilled_human_name=answers.human_name,
    )
    if not config:
        print("Configuration cancelled.", file=sys.stderr)
        return EXIT_ERROR
else:
    config = generate_default_config(answers.agent_name, answers.human_name, workspace=workspace)
    if parsed_args.get("model"):
        config["agent"]["model"] = parsed_args["model"]
    if parsed_args.get("no_room"):
        config["room"]["enabled"] = False
        config["room"]["port"] = 0

config_path = workspace / "emergence.json"
if not write_config(config, config_path):
    print("Failed to write configuration.", file=sys.stderr)
    return EXIT_ERROR

print(f"  ✓ Config saved: {config_path}")
print()

# F032: Room auto-start (prompt if interactive and Room enabled)
if parsed_args["interactive"] and config.get("room", {}).get("enabled", True):
    ask_room_autostart(config, workspace)
    print()

# Generate letter...
```

---

## 5. Uninstall Implementation

### 5.1 CLI Integration

Add to the main CLI (`emergence` command):

```python
# In the main CLI handler
def handle_room_subcommand(args):
    """Handle 'emergence room' subcommands."""
    from core.setup.autostart.installer import get_installer
    from core.setup.config_gen import load_config
    
    workspace = Path.cwd()
    config_path = workspace / "emergence.json"
    
    if not config_path.exists():
        print_error("No emergence.json found. Run 'emergence init' first.")
        sys.exit(1)
    
    config = load_config(config_path)
    agent_name = config.get("agent", {}).get("name", "Emergence")
    room_port = config.get("room", {}).get("port", 7373)
    
    installer = get_installer(workspace, agent_name, room_port)
    
    if not installer:
        print_error("Auto-start not supported on this platform")
        sys.exit(1)
    
    if args.room_command == "autostart-install":
        success, msg = installer.install()
        print_success(msg) if success else print_error(msg)
        sys.exit(0 if success else 1)
    
    elif args.room_command == "autostart-remove":
        success, msg = installer.uninstall()
        print_success(msg) if success else print_error(msg)
        sys.exit(0 if success else 1)
    
    elif args.room_command == "autostart-status":
        is_running, status = installer.status()
        print(f"Auto-start: {'✓ enabled' if installer.is_installed() else '✗ not configured'}")
        print(f"Status: {status}")
        sys.exit(0)
    
    elif args.room_command == "start":
        if installer.is_installed():
            success, msg = installer.start()
        else:
            # Fallback: start directly with node
            import subprocess
            server_path = workspace / "room" / "server" / "index.js"
            subprocess.Popen(
                ["node", str(server_path)],
                cwd=workspace,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True
            )
            success, msg = True, "Room started (manual mode)"
        print_success(msg) if success else print_error(msg)
        sys.exit(0 if success else 1)
    
    elif args.room_command == "stop":
        if installer.is_installed():
            success, msg = installer.stop()
        else:
            # Fallback: find and kill node process
            import subprocess
            subprocess.run(["pkill", "-f", "room/server/index.js"], capture_output=True)
            success, msg = True, "Room stopped (manual mode)"
        print_success(msg) if success else print_error(msg)
        sys.exit(0 if success else 1)
```

### 5.2 Usage Examples

```bash
# Install auto-start manually (post-init)
emergence room autostart-install

# Check status
emergence room autostart-status

# Remove auto-start
emergence room autostart-remove

# Manual control
emergence room start
emergence room stop
```

---

## 6. Testing Strategy

### 6.1 Test File Structure

```
core/setup/autostart/tests/
├── __init__.py
├── test_installer.py      # Unit tests for installer logic
├── test_platforms.py      # Platform-specific tests
└── test_integration.py    # Integration tests
```

### 6.2 macOS Testing (Local)

```python
# test_macos.py - Manual test script
"""Manual test for macOS auto-start implementation."""

import tempfile
import shutil
from pathlib import Path

def test_macos_install():
    """Test full install/uninstall cycle on macOS."""
    from core.setup.autostart.installer import MacOSInstaller
    
    # Use actual workspace
    workspace = Path("/Users/jarvis/.openclaw/workspace/projects/emergence")
    
    installer = MacOSInstaller(workspace, "TestAgent", 9999)
    
    # Pre-checks
    print(f"Platform: {installer.platform_name}")
    print(f"Is installed: {installer.is_installed()}")
    print(f"Plist path: {installer.plist_path}")
    
    # Install
    print("\n--- Installing ---")
    success, msg = installer.install()
    print(f"Success: {success}")
    print(f"Message: {msg}")
    
    if success:
        # Check file exists
        print(f"Plist exists: {installer.plist_path.exists()}")
        print(f"Content preview:\n{installer.plist_path.read_text()[:500]}...")
        
        # Check status
        print("\n--- Status ---")
        is_running, status = installer.status()
        print(f"Running: {is_running}, Status: {status}")
        
        # Uninstall
        print("\n--- Uninstalling ---")
        success, msg = installer.uninstall()
        print(f"Success: {success}")
        print(f"Message: {msg}")
        print(f"Plist exists: {installer.plist_path.exists()}")

if __name__ == "__main__":
    test_macos_install()
```

### 6.3 Linux Testing (Docker)

```dockerfile
# tests/docker/Dockerfile.linux-test
FROM ubuntu:22.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3.10 \
    python3-pip \
    nodejs \
    npm \
    systemd \
    && rm -rf /var/lib/apt/lists/*

# Create test user
RUN useradd -m -s /bin/bash testuser

# Set up workspace
WORKDIR /workspace
COPY . /workspace/

# Create fake emergence.json
RUN echo '{"agent": {"name": "DockerTest"}, "room": {"port": 7373}}' > emergence.json

# Run tests as testuser
USER testuser
CMD ["python3", "-m", "pytest", "core/setup/autostart/tests/", "-v"]
```

```python
# test_linux_docker.py - Docker-based integration test
"""Docker-based Linux testing for auto-start."""

import subprocess
import sys
from pathlib import Path

def run_docker_test():
    """Build and run Docker test container."""
    
    # Build image
    result = subprocess.run(
        ["docker", "build", "-f", "tests/docker/Dockerfile.linux-test", 
         "-t", "emergence-autostart-test", "."],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Docker build failed: {result.stderr}")
        sys.exit(1)
    
    # Run with systemd enabled (requires --privileged)
    result = subprocess.run(
        ["docker", "run", "--privileged", "--rm", 
         "-v", "/sys/fs/cgroup:/sys/fs/cgroup:ro",
         "emergence-autostart-test"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    if result.returncode != 0:
        print(f"Tests failed: {result.stderr}")
    
    sys.exit(result.returncode)

if __name__ == "__main__":
    run_docker_test()
```

### 6.4 GitHub Actions Workflow

```yaml
# .github/workflows/test-autostart.yml
name: Test Auto-Start

on:
  push:
    paths:
      - 'core/setup/autostart/**'
  pull_request:
    paths:
      - 'core/setup/autostart/**'

jobs:
  test-macos:
    runs-on: macos-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Run macOS tests
        run: |
          python -m pytest core/setup/autostart/tests/test_platforms.py -v -k macos
  
  test-linux:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Set up Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'
      
      - name: Install systemd
        run: |
          sudo apt-get update
          sudo apt-get install -y systemd
      
      - name: Run Linux tests
        run: |
          python -m pytest core/setup/autostart/tests/test_platforms.py -v -k linux
```

---

## 7. Implementation Checklist

### Phase 1: Core Implementation
- [ ] Create `core/setup/autostart/` directory structure
- [ ] Create `templates/launchd.plist` template
- [ ] Create `templates/systemd.service` template
- [ ] Implement `installer.py` with `PlatformInstaller` base class
- [ ] Implement `MacOSInstaller` class
- [ ] Implement `LinuxInstaller` class (user mode)
- [ ] Add unit tests for installer logic

### Phase 2: Wizard Integration
- [ ] Add `ask_room_autostart()` function to `init_wizard.py`
- [ ] Insert call in `main()` after config generation
- [ ] Test interactive flow on macOS
- [ ] Test interactive flow on Linux

### Phase 3: CLI Commands
- [ ] Add `emergence room autostart-install` command
- [ ] Add `emergence room autostart-remove` command
- [ ] Add `emergence room autostart-status` command
- [ ] Add `emergence room start/stop` manual commands

### Phase 4: Testing & Validation
- [ ] Run manual test on macOS (Jarvis's machine)
- [ ] Run Docker-based Linux test
- [ ] Add GitHub Actions workflow
- [ ] Document any platform-specific quirks

### Phase 5: Documentation
- [ ] Update README with auto-start instructions
- [ ] Add troubleshooting section for common issues
- [ ] Document how to view logs

---

## 8. Error Handling & Edge Cases

### 8.1 Common Issues

| Issue | Detection | Resolution |
|-------|-----------|------------|
| Node.js not found | Check `shutil.which("node")` | Prompt user to install Node |
| Port already in use | Check with `socket.connect()` | Suggest alternate port |
| Permission denied (Linux system mode) | Check `os.geteuid() != 0` | Fall back to user mode |
| Service file syntax error | Validate before writing | Template unit tests |
| launchd/systemd not available | Check command existence | Graceful failure with explanation |

### 8.2 Log Locations

| Platform | Log Location |
|----------|--------------|
| macOS | `~/.openclaw/workspace/projects/emergence/.emergence/logs/room.{out,err}.log` |
| Linux | Same as macOS, plus `journalctl --user -u emergence-room-{agent}` |

### 8.3 Viewing Logs

```bash
# macOS
tail -f ~/.openclaw/workspace/projects/emergence/.emergence/logs/room.out.log

# Linux
tail -f ~/.openclaw/workspace/projects/emergence/.emergence/logs/room.out.log
journalctl --user -u emergence-room-{agent} -f
```

---

## 9. Security Considerations

1. **User-mode execution**: Default to user-mode (not root) on all platforms
2. **Working directory isolation**: Service runs with `WorkingDirectory` set to workspace
3. **Minimal environment**: Only pass required env vars (PATH, NODE_ENV, EMERGENCE_STATE)
4. **No network exposure**: Default to `127.0.0.1` binding (localhost only)
5. **Log rotation**: Services should use append mode without unbounded growth

---

## 10. Future Enhancements

1. **Windows support**: Add Windows Service integration
2. **Per-user vs system-wide**: Option for system-wide install on Linux
3. **Auto-update**: Check for Room updates on service start
4. **Health checks**: Built-in HTTP health check before marking service as started
5. **Port conflict resolution**: Auto-detect and suggest alternative ports
