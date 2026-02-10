#!/usr/bin/env python3
"""Test F032 room auto-start on macOS.

This script tests the launchd installer without running the full init wizard.
"""

import sys
from pathlib import Path

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.setup.autostart import get_installer


def main():
    print("=" * 60)
    print("F032 Room Auto-Start Test (macOS)")
    print("=" * 60)
    print()
    
    # Test workspace (use emergence workspace itself)
    workspace = Path(__file__).parent.parent
    agent_name = "TestAgent"
    room_port = 8800
    
    print(f"Workspace: {workspace}")
    print(f"Agent Name: {agent_name}")
    print(f"Room Port: {room_port}")
    print()
    
    # Get installer
    print("Creating installer...")
    installer = get_installer(workspace, agent_name, room_port)
    
    if not installer:
        print("❌ Platform not supported (expected macOS)")
        return 1
    
    print(f"✓ Got installer: {installer.platform_name}")
    print()
    
    # Check if already installed
    if installer.is_installed():
        print("⚠️  Service already installed")
        print()
        
        # Check status
        print("Checking status...")
        is_running, status_msg = installer.status()
        print(f"  Status: {status_msg}")
        print(f"  Running: {'✓' if is_running else '✗'}")
        print()
        
        # Offer to uninstall
        response = input("Uninstall existing service? [y/N]: ").strip().lower()
        if response == 'y':
            print("Uninstalling...")
            success, msg = installer.uninstall()
            print(f"  {'✓' if success else '✗'} {msg}")
            print()
        else:
            print("Keeping existing service.")
            print()
            return 0
    
    # Install
    print("Installing service...")
    success, msg = installer.install()
    
    if success:
        print(f"✓ {msg}")
        print()
        
        # Check status
        print("Checking status...")
        is_running, status_msg = installer.status()
        print(f"  Status: {status_msg}")
        print(f"  Running: {'✓' if is_running else '✗'}")
        print()
        
        # Check plist file
        if hasattr(installer, 'plist_path'):
            print(f"Plist file: {installer.plist_path}")
            if installer.plist_path.exists():
                print("  ✓ File exists")
            else:
                print("  ✗ File not found")
        print()
        
        print("=" * 60)
        print("Installation successful!")
        print("=" * 60)
        print()
        print("The service will start automatically on next login.")
        print()
        print("To start it now:")
        print(f"  launchctl start {installer.service_id}")
        print()
        print("To check logs:")
        print(f"  tail -f {installer.log_dir}/room.out.log")
        print(f"  tail -f {installer.log_dir}/room.err.log")
        print()
        print("To uninstall:")
        print(f"  launchctl unload {installer.plist_path}")
        print(f"  rm {installer.plist_path}")
        print()
        
        return 0
    else:
        print(f"✗ {msg}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
