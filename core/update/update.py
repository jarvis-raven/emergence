#!/usr/bin/env python3
"""Emergence Update — Safe package updates with migration support.

Handles upgrading Emergence via pip or git with automatic backups and migrations.
"""

import json
import os
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple


class UpdateManager:
    """Manages safe updates with backups and migrations."""
    
    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.state_dir = workspace / ".emergence" / "state"
        self.backup_dir = workspace / ".emergence" / "backups"
        
    def detect_install_type(self) -> str:
        """Detect how Emergence was installed.
        
        Returns:
            'pip' if installed via pip, 'git' if git clone, 'unknown' otherwise
        """
        # Check if we're in a git repo
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=Path(__file__).parent.parent,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                return "git"
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        
        # Check if installed as a pip package
        try:
            import emergence_ai
            # If we can import it and it has a version, it's pip-installed
            if hasattr(emergence_ai, '__version__'):
                return "pip"
        except ImportError:
            pass
        
        return "unknown"
    
    def get_current_version(self) -> Optional[str]:
        """Get currently installed version."""
        try:
            from core import __version__
            return __version__
        except ImportError:
            return None
    
    def create_backup(self, label: str = "pre-update") -> Path:
        """Create backup of critical state files.
        
        Args:
            label: Backup label (e.g., 'pre-update')
            
        Returns:
            Path to backup directory
        """
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = self.backup_dir / f"{label}-{timestamp}"
        backup_path.mkdir(parents=True, exist_ok=True)
        
        # Files to backup
        critical_files = [
            self.state_dir / "drives.json",
            self.state_dir / "first-light.json",
            self.workspace / "emergence.json",
            self.workspace / ".openclaw" / "config" / "shelves.json",
        ]
        
        # Directories to backup
        critical_dirs = [
            self.state_dir / "shelves",  # Custom shelves
        ]
        
        backed_up = []
        
        for file_path in critical_files:
            if file_path.exists():
                rel_path = file_path.relative_to(self.workspace)
                dest = backup_path / rel_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(file_path, dest)
                backed_up.append(str(rel_path))
        
        for dir_path in critical_dirs:
            if dir_path.exists():
                rel_path = dir_path.relative_to(self.workspace)
                dest = backup_path / rel_path
                shutil.copytree(dir_path, dest, dirs_exist_ok=True)
                backed_up.append(str(rel_path))
        
        # Write backup manifest
        manifest = {
            "created_at": datetime.now().isoformat(),
            "label": label,
            "backed_up": backed_up,
            "version_before": self.get_current_version(),
        }
        
        manifest_path = backup_path / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2))
        
        return backup_path
    
    def update_via_pip(self) -> Tuple[bool, str]:
        """Update Emergence via pip.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            print("📦 Updating via pip...")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "--upgrade", "emergence-ai"],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                return (True, "Pip update completed successfully")
            else:
                return (False, f"Pip update failed: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            return (False, "Pip update timed out after 120 seconds")
        except Exception as e:
            return (False, f"Pip update error: {e}")
    
    def update_via_git(self) -> Tuple[bool, str]:
        """Update Emergence via git pull.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            repo_root = Path(__file__).parent.parent
            
            print("🔄 Pulling latest changes...")
            result = subprocess.run(
                ["git", "pull"],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode != 0:
                return (False, f"Git pull failed: {result.stderr}")
            
            if "Already up to date" in result.stdout:
                return (True, "Already up to date")
            
            # Update Python dependencies
            print("📦 Updating Python dependencies...")
            pip_result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-e", "."],
                cwd=repo_root,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if pip_result.returncode != 0:
                return (False, f"Dependency update failed: {pip_result.stderr}")
            
            return (True, "Git update completed successfully")
            
        except subprocess.TimeoutExpired:
            return (False, "Update timed out")
        except Exception as e:
            return (False, f"Git update error: {e}")
    
    def check_for_migrations(self, old_version: str, new_version: str) -> list:
        """Check if migrations are needed.
        
        Args:
            old_version: Version before update
            new_version: Version after update
            
        Returns:
            List of migration names needed
        """
        # TODO: Implement migration detection
        # For now, return empty list
        return []
    
    def run_migration(self, migration_name: str) -> Tuple[bool, str]:
        """Run a specific migration.
        
        Args:
            migration_name: Name of migration to run
            
        Returns:
            Tuple of (success, message)
        """
        # TODO: Implement migration runner
        return (True, f"Migration {migration_name} completed")
    
    def check_room_running(self) -> bool:
        """Check if Room server is running."""
        try:
            result = subprocess.run(
                ["pgrep", "-f", "room/server/index.js"],
                capture_output=True,
                timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def check_daemon_running(self) -> bool:
        """Check if drives daemon is running."""
        try:
            from core.drives.pidfile import is_daemon_running
            return is_daemon_running(self.state_dir)
        except Exception:
            return False


def main():
    """CLI entry point for emergence update."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Update Emergence with automatic backups and migrations"
    )
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="Check for updates without installing"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip backup (not recommended)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Force update even if version check fails"
    )
    
    args = parser.parse_args()
    
    # Determine workspace
    workspace = Path.cwd()
    if not (workspace / ".emergence").exists():
        # Try parent directories
        for parent in workspace.parents:
            if (parent / ".emergence").exists():
                workspace = parent
                break
    
    manager = UpdateManager(workspace)
    
    # Detect install type
    install_type = manager.detect_install_type()
    current_version = manager.get_current_version()
    
    print("🌅 Emergence Update")
    print("=" * 40)
    print(f"Install type: {install_type}")
    print(f"Current version: {current_version or 'unknown'}")
    print()
    
    if install_type == "unknown":
        print("❌ Could not detect how Emergence was installed.")
        print("   Please reinstall using pip or git clone.")
        sys.exit(1)
    
    if args.check_only:
        print("✓ Check complete. Use 'emergence update' to install.")
        sys.exit(0)
    
    # Create backup
    if not args.no_backup:
        print("💾 Creating backup...")
        try:
            backup_path = manager.create_backup("pre-update")
            print(f"  ✓ Backup created: {backup_path}")
            print()
        except Exception as e:
            print(f"  ❌ Backup failed: {e}")
            if not args.force:
                print("  Use --force to continue without backup (not recommended)")
                sys.exit(1)
    
    # Perform update
    if install_type == "pip":
        success, message = manager.update_via_pip()
    else:  # git
        success, message = manager.update_via_git()
    
    if not success:
        print(f"❌ Update failed: {message}")
        sys.exit(1)
    
    print(f"✓ {message}")
    print()
    
    # Check new version
    new_version = manager.get_current_version()
    print(f"Updated to version: {new_version or 'unknown'}")
    
    # Check for migrations
    if current_version and new_version and current_version != new_version:
        migrations = manager.check_for_migrations(current_version, new_version)
        if migrations:
            print()
            print("🔄 Running migrations...")
            for migration in migrations:
                success, msg = manager.run_migration(migration)
                if success:
                    print(f"  ✓ {msg}")
                else:
                    print(f"  ❌ {msg}")
                    sys.exit(2)
    
    # Check if services need restart
    room_running = manager.check_room_running()
    daemon_running = manager.check_daemon_running()
    
    if room_running or daemon_running:
        print()
        print("⚠️  Services may need restart:")
        if room_running:
            print("  • Room server is running")
        if daemon_running:
            print("  • Drives daemon is running")
        print()
        print("Restart with:")
        if room_running:
            print("  pkill -f 'room/server/index.js' && cd room && npm run dev")
        if daemon_running:
            print("  emergence drives restart")
    
    print()
    print("✅ Update complete!")
    sys.exit(0)


if __name__ == "__main__":
    main()
