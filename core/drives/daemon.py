from typing import Optional

"""Drive daemon — background process for the interoception system.

Provides persistent execution of the drive engine with configurable
tick intervals, signal handling, and graceful shutdown.
"""

import os
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import load_config, get_state_path
from .state import load_state, save_state, StateLock
from .engine import tick_all_drives, check_thresholds
from .pidfile import acquire_pidfile, remove_pid, is_running
from .defaults import ensure_core_drives
from .satisfaction import check_completed_sessions
from .runtime_state import extract_runtime_state, save_runtime_state

# Nautilus integration (optional)
try:
    from ..nautilus.nightly import run_nightly_maintenance, log_maintenance_result

    NAUTILUS_AVAILABLE = True
except ImportError:
    NAUTILUS_AVAILABLE = False


# Global flag for shutdown signal handling
_shutdown_requested = False
_config_reload_requested = False


def _handle_sigterm(signum, frame):
    """Handle SIGTERM for graceful shutdown."""
    global _shutdown_requested
    _shutdown_requested = True


def _handle_sighup(signum, frame):
    """Handle SIGHUP for config reload."""
    global _config_reload_requested
    _config_reload_requested = True


def setup_signals() -> None:
    """Set up Unix signal handlers for daemon lifecycle management.

    Sets up:
    - SIGTERM: Request graceful shutdown
    - SIGHUP: Request config reload
    - SIGINT: Request graceful shutdown (for foreground mode)
    """
    signal.signal(signal.SIGTERM, _handle_sigterm)
    signal.signal(signal.SIGHUP, _handle_sighup)
    signal.signal(signal.SIGINT, _handle_sigterm)


def get_daemon_log_path(config: dict) -> Path:
    """Get the daemon log file path from config.

    Args:
        config: Configuration dictionary

    Returns:
        Path to the log file
    """
    workspace = config.get("paths", {}).get("workspace", ".")
    log_dir = Path(workspace) / ".emergence" / "logs"
    return log_dir / "daemon.log"


def write_log(log_path: Path, message: str, level: str = "INFO") -> None:
    """Write a log entry to the daemon log file.

    Args:
        log_path: Path to the log file
        message: Log message
        level: Log level (INFO, WARN, ERROR)
    """
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log_line = f"[{timestamp}] [{level}] {message}\n"

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_line)
    except IOError:
        # Silent failure for logging - don't crash daemon
        pass


def _check_emergency_spawns(
    state: dict,
    config: dict,
    log_path: Path,
    result: dict,
    emergency_threshold_ratio: float,
    emergency_cooldown_hours: float,
) -> list[str]:
    """Check all drives for emergency-level pressure and auto-spawn if needed.

    Safety valve: even in manual mode, drives at 200%+ pressure get auto-spawned
    to prevent complete neglect. Rate-limited to 1 spawn per drive per 6 hours.

    Args:
        state: Current drive state (modified in place)
        config: Configuration dictionary
        log_path: Path to log file
        result: Tick result dict to append emergency info to
        emergency_threshold_ratio: Pressure ratio that triggers emergency (default 2.0)
        emergency_cooldown_hours: Min hours between emergency spawns per drive

    Returns:
        List of drive names that were emergency-spawned
    """
    spawned_drives = []
    now = datetime.now(timezone.utc)
    cooldown_seconds = emergency_cooldown_hours * 3600

    for name, drive in state.get("drives", {}).items():
        pressure = drive.get("pressure", 0.0)
        threshold = drive.get("threshold", 1.0)

        if threshold <= 0:
            continue

        ratio = pressure / threshold
        if ratio < emergency_threshold_ratio:
            continue

        # Check rate limiting
        last_emergency = drive.get("last_emergency_spawn")
        if last_emergency:
            try:
                last_dt = datetime.fromisoformat(last_emergency)
                if last_dt.tzinfo is None:
                    last_dt = last_dt.replace(tzinfo=timezone.utc)
                elapsed = (now - last_dt).total_seconds()
                if elapsed < cooldown_seconds:
                    remaining_h = (cooldown_seconds - elapsed) / 3600
                    write_log(
                        log_path,
                        f"Emergency spawn rate-limited for {name} "
                        f"({ratio:.0%} pressure, {remaining_h:.1f}h cooldown remaining)",
                        "WARN",
                    )
                    continue
            except (ValueError, TypeError):
                pass  # Invalid timestamp, allow spawn

        # Emergency spawn!
        pct = int(ratio * 100)
        write_log(log_path, f"Emergency spawn for {name} at {pct}%", "WARN")

        # Record in result
        result.setdefault("emergency_spawns", []).append(
            {
                "name": name,
                "pressure": pressure,
                "threshold": threshold,
                "ratio": ratio,
            }
        )

        # Attempt spawn with crisis-level depth (90%)
        try:
            from .spawn import spawn_session, record_trigger

            drive_prompt = drive.get(
                "prompt", f"EMERGENCY: Your {name} drive is critically neglected."
            )
            session_key = spawn_session(name, drive_prompt, config, pressure, threshold)
            if session_key:
                record_trigger(
                    state,
                    name,
                    pressure,
                    threshold,
                    True,
                    session_key=session_key,
                    reason="Emergency spawn",
                )
                # Apply crisis-level satisfaction (90% reduction)
                new_pressure = pressure * 0.10  # 90% reduction
                drive["pressure"] = new_pressure
                drive["last_emergency_spawn"] = now.isoformat()
                spawned_drives.append(name)
                write_log(
                    log_path,
                    f"Emergency spawn succeeded for {name}: "
                    f"{pressure:.1f} → {new_pressure:.1f} (90% reduction)",
                    "WARN",
                )
            else:
                write_log(log_path, f"Emergency spawn FAILED for {name}", "ERROR")
        except Exception as e:
            write_log(log_path, f"Emergency spawn error for {name}: {e}", "ERROR")

    return spawned_drives


def run_tick_cycle(state: dict, config: dict, state_path: Path, log_path: Path) -> dict:
    """Run a single tick cycle: update pressures and check triggers.

    Args:
        state: Current drive state
        config: Configuration dictionary
        state_path: Path to state file
        log_path: Path to log file

    Returns:
        Result dict with details of what happened
    """
    result = {"updated": [], "triggered": [], "errors": []}

    # Acquire lock for state modification
    with StateLock(state_path, timeout=10.0) as lock:
        if not lock.acquired:
            result["errors"].append("Could not acquire state lock")
            write_log(log_path, "Failed to acquire state lock", "WARN")
            return result

        # Reload state to get latest (another process may have modified it)
        try:
            state = load_state(state_path)
            ensure_core_drives(state)
        except Exception as e:
            result["errors"].append(f"Failed to reload state: {e}")
            write_log(log_path, f"State reload error: {e}", "ERROR")
            return result

        # Run tick - update pressures
        changes = tick_all_drives(state, config)

        for name, (old, new) in changes.items():
            result["updated"].append({"name": name, "old": old, "new": new})

        # Check for triggers and spawn sessions
        triggered = check_thresholds(state, config, respect_quiet_hours=True)
        manual_mode = config.get("drives", {}).get("manual_mode", False)

        # Emergency spawn safety valve: check ALL drives for 200%+ pressure
        emergency_spawn_enabled = config.get("drives", {}).get("emergency_spawn", True)
        emergency_threshold_ratio = config.get("drives", {}).get("emergency_threshold", 2.0)
        emergency_cooldown_hours = config.get("drives", {}).get("emergency_cooldown_hours", 6)

        if emergency_spawn_enabled and manual_mode:
            emergency_spawned = _check_emergency_spawns(
                state, config, log_path, result, emergency_threshold_ratio, emergency_cooldown_hours
            )

        for name in triggered:
            drive = state["drives"][name]
            pressure = drive.get("pressure", 0.0)
            threshold = drive.get("threshold", 1.0)

            result["triggered"].append({"name": name, "pressure": pressure, "threshold": threshold})

            # In manual mode, update pressure but don't spawn
            if manual_mode:
                write_log(
                    log_path,
                    f"Drive over threshold (manual_mode): {name} ({pressure:.1f}/{threshold:.1f})",
                    "INFO",
                )
                continue

            # Only spawn if not already triggered (prevents double-spawning on 1s ticks)
            if name not in state.get("triggered_drives", []):
                if "triggered_drives" not in state:
                    state["triggered_drives"] = []
                state["triggered_drives"].append(name)

                # Spawn a session for this drive
                try:
                    from .spawn import spawn_session

                    drive_prompt = drive.get("prompt", f"Your {name} drive triggered.")
                    session_key = spawn_session(name, drive_prompt, config, pressure, threshold)
                    if session_key:
                        from .spawn import record_trigger

                        record_trigger(
                            state,
                            name,
                            pressure,
                            threshold,
                            True,
                            session_key=session_key,
                            reason="Threshold exceeded",
                        )
                        write_log(
                            log_path,
                            f"Drive triggered + spawned: {name} ({pressure:.1f}/{threshold:.1f})",
                            "INFO",
                        )
                    else:
                        write_log(log_path, f"Drive triggered but spawn failed: {name}", "WARN")
                        # Remove from triggered since spawn failed
                        state["triggered_drives"].remove(name)
                except Exception as e:
                    write_log(log_path, f"Spawn error for {name}: {e}", "ERROR")
                    if name in state.get("triggered_drives", []):
                        state["triggered_drives"].remove(name)

        # Check for completed sessions and satisfy drives
        try:
            satisfied = check_completed_sessions(state, config)
            for name in satisfied:
                result.setdefault("satisfied", []).append(name)
                write_log(log_path, f"Drive satisfied: {name}", "INFO")
        except Exception as e:
            write_log(log_path, f"Satisfaction check error: {e}", "ERROR")

        # Save state
        try:
            save_state(state_path, state)
        except Exception as e:
            result["errors"].append(f"Failed to save state: {e}")
            write_log(log_path, f"State save error: {e}", "ERROR")

        # Write lightweight runtime state (drives-state.json)
        try:
            runtime_state = extract_runtime_state(state)
            runtime_path = state_path.parent / "drives-state.json"
            save_runtime_state(runtime_path, runtime_state)
        except Exception as e:
            write_log(log_path, f"Runtime state write error: {e}", "WARN")

    # Check for nightly maintenance (outside state lock)
    if NAUTILUS_AVAILABLE:
        try:
            from .nightly_check import (
                load_nightly_state,
                should_run_nautilus_nightly,
                mark_nautilus_run,
            )

            nightly_state = load_nightly_state(config)
            should_run, reason = should_run_nautilus_nightly(config, nightly_state)

            if should_run:
                write_log(log_path, f"Starting Nautilus nightly maintenance: {reason}", "INFO")

                try:
                    maint_result = run_nightly_maintenance(
                        register_recent=True, recent_hours=24, verbose=False
                    )

                    # Log result
                    log_maintenance_result(maint_result, log_path)

                    # Mark as completed
                    mark_nautilus_run(config, nightly_state)

                    summary = maint_result.get("summary", {})
                    write_log(log_path, f"Nautilus maintenance completed: {summary}", "INFO")

                    result["nautilus_maintenance"] = summary

                except Exception as e:
                    write_log(log_path, f"Nautilus maintenance error: {e}", "ERROR")
                    result.setdefault("errors", []).append(f"Nautilus maintenance failed: {e}")

        except Exception as e:
            write_log(log_path, f"Nightly check error: {e}", "WARN")

    return result


def run_daemon(config: dict, foreground: bool = False, pid_path: Optional[Path] = None) -> int:
    """Run the main daemon loop.

    This is the core daemon function that runs until shutdown is requested.
    It wakes up every tick_interval seconds, updates drive pressures,
    checks for triggers, and handles signals.

    Args:
        config: Configuration dictionary
        foreground: If True, don't daemonize (run in foreground)
        pid_path: Path to PID file (defaults to .emergence/drives.pid)

    Returns:
        Exit code (0 for clean shutdown, 1 for error)

    Examples:
        >>> # Normally run via start_daemon() which forks first
        >>> # But can be called directly for foreground mode:
        >>> config = load_config()
        >>> run_daemon(config, foreground=True)  # doctest: +SKIP
    """
    global _shutdown_requested, _config_reload_requested

    # Reset flags
    _shutdown_requested = False
    _config_reload_requested = False

    # Setup paths
    workspace = config.get("paths", {}).get("workspace", ".")
    if pid_path is None:
        pid_path = Path(workspace) / ".emergence" / "drives.pid"

    state_path = get_state_path(config)
    log_path = get_daemon_log_path(config)

    # Ensure state directory exists
    state_path.parent.mkdir(parents=True, exist_ok=True)

    # Write PID file
    try:
        acquired, blocking_pid = acquire_pidfile(pid_path)
        if not acquired:
            if not foreground:  # In foreground mode, we might be the same process
                print(f"Daemon already running (PID {blocking_pid})", file=sys.stderr)
                return 1
    except IOError as e:
        print(f"Failed to write PID file: {e}", file=sys.stderr)
        return 1

    # Setup signal handlers
    setup_signals()

    # Detect openclaw binary path (needed for spawning sessions via CLI)
    from .spawn import detect_openclaw_path

    if not config.get("drives", {}).get("openclaw_path"):
        openclaw_path = detect_openclaw_path()
        if openclaw_path:
            config["_openclaw_path"] = openclaw_path  # Store in-memory for this session
            write_log(log_path, f"Detected openclaw: {openclaw_path}", "INFO")
        else:
            write_log(log_path, "Warning: openclaw binary not found in PATH", "WARN")
            write_log(
                log_path,
                "Session spawning via CLI may fail. Set drives.openclaw_path in config.",
                "WARN",
            )

    # Log startup
    tick_interval = config.get("drives", {}).get("tick_interval", 1)
    write_log(log_path, f"Daemon started (tick interval: {tick_interval}s)", "INFO")

    if foreground:
        print(f"Daemon running in foreground (PID {os.getpid()})")
        print(f"Press Ctrl+C to stop")

    try:
        # Main loop
        while not _shutdown_requested:
            # Check for config reload
            if _config_reload_requested:
                _config_reload_requested = False
                try:
                    config = load_config()
                    tick_interval = config.get("drives", {}).get("tick_interval", 900)
                    write_log(log_path, "Config reloaded", "INFO")
                except Exception as e:
                    write_log(log_path, f"Config reload failed: {e}", "WARN")

            # Run tick cycle
            try:
                state = load_state(state_path)
                ensure_core_drives(state)
                result = run_tick_cycle(state, config, state_path, log_path)

                if result["errors"]:
                    for error in result["errors"]:
                        write_log(log_path, f"Tick error: {error}", "WARN")

                # Log summary
                if result["triggered"]:
                    write_log(
                        log_path,
                        f"Tick complete: {len(result['updated'])} updated, {len(result['triggered'])} triggered",
                        "INFO",
                    )
                elif result["updated"]:
                    names = [u["name"] for u in result["updated"]]
                    write_log(log_path, f"Tick complete: updated {', '.join(names)}", "INFO")

            except Exception as e:
                write_log(log_path, f"Tick cycle error: {e}", "ERROR")

            # Sleep until next tick (checking shutdown periodically)
            sleep_start = time.monotonic()
            while time.monotonic() - sleep_start < tick_interval:
                if _shutdown_requested:
                    break
                # Check config reload during sleep too
                if _config_reload_requested:
                    break
                time.sleep(0.5)  # Short sleep for responsiveness

        # Graceful shutdown
        write_log(log_path, "Daemon shutting down gracefully", "INFO")

    except Exception as e:
        write_log(log_path, f"Daemon error: {e}", "ERROR")
        return 1

    finally:
        # Clean up PID file
        remove_pid(pid_path)
        write_log(log_path, "Daemon stopped", "INFO")

    return 0


def start_daemon(config: dict, detach: bool = True, pid_path: Optional[Path] = None) -> dict:
    """Start the daemon process.

    Forks and detaches from terminal (unless detach=False for foreground mode).

    Args:
        config: Configuration dictionary
        detach: If True, fork to background; if False, run in foreground
        pid_path: Path to PID file

    Returns:
        Result dict with success status and details
    """
    result = {"success": False, "pid": None, "errors": []}

    workspace = config.get("paths", {}).get("workspace", ".")
    if pid_path is None:
        pid_path = Path(workspace) / ".emergence" / "drives.pid"

    # Check if already running
    running, existing_pid = is_running(pid_path)
    if running:
        result["errors"].append(f"Daemon already running (PID {existing_pid})")
        result["already_running"] = True
        result["pid"] = existing_pid
        return result

    if detach:
        # Fork to background
        try:
            pid = os.fork()
            if pid > 0:
                # Parent process - return success
                result["success"] = True
                result["pid"] = pid
                result["detached"] = True
                return result

            # Child process - continue daemon setup
            os.setsid()  # Create new session

            # Second fork to prevent reacquiring terminal
            pid = os.fork()
            if pid > 0:
                os._exit(0)

            # Grandchild process - the actual daemon
            # Redirect standard file descriptors to /dev/null
            sys.stdout.flush()
            sys.stderr.flush()

            with open(os.devnull, "r") as f:
                os.dup2(f.fileno(), sys.stdin.fileno())
            with open(os.devnull, "a+") as f:
                os.dup2(f.fileno(), sys.stdout.fileno())
                os.dup2(f.fileno(), sys.stderr.fileno())

            # Run daemon (doesn't return until shutdown)
            exit_code = run_daemon(config, foreground=False, pid_path=pid_path)
            os._exit(exit_code)

        except OSError as e:
            result["errors"].append(f"Fork failed: {e}")
            return result
    else:
        # Foreground mode
        result["pid"] = os.getpid()
        result["detached"] = False
        exit_code = run_daemon(config, foreground=True, pid_path=pid_path)
        result["success"] = exit_code == 0
        return result


def stop_daemon(config: dict, pid_path: Optional[Path] = None, timeout: float = 10.0) -> dict:
    """Stop the running daemon by sending SIGTERM.

    Args:
        config: Configuration dictionary
        pid_path: Path to PID file
        timeout: Seconds to wait for process to exit

    Returns:
        Result dict with success status and details
    """
    result = {"success": False, "pid": None, "errors": []}

    workspace = config.get("paths", {}).get("workspace", ".")
    if pid_path is None:
        pid_path = Path(workspace) / ".emergence" / "drives.pid"

    # Check if running
    running, pid = is_running(pid_path)
    if not running:
        result["errors"].append("Daemon not running")
        result["was_running"] = False
        return result

    result["pid"] = pid
    result["was_running"] = True

    # Send SIGTERM
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError as e:
        result["errors"].append(f"Failed to send SIGTERM: {e}")
        return result

    # Wait for process to exit
    start_time = time.monotonic()
    while time.monotonic() - start_time < timeout:
        if not is_process_alive(pid):
            result["success"] = True
            result["stopped"] = True
            return result
        time.sleep(0.2)

    # Timeout - process didn't exit
    result["errors"].append(f"Timeout waiting for daemon to exit (PID {pid})")
    result["timeout"] = True

    return result


def is_process_alive(pid: int) -> bool:
    """Check if a process is still running.

    Args:
        pid: Process ID to check

    Returns:
        True if process exists
    """
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def daemon_status(config: dict, pid_path: Optional[Path] = None) -> dict:
    """Get the current daemon status.

    Args:
        config: Configuration dictionary
        pid_path: Path to PID file

    Returns:
        Status dict with running state, PID, uptime, etc.
    """
    status = {
        "running": False,
        "pid": None,
        "started": None,
        "uptime_seconds": None,
        "last_tick": None,
    }

    workspace = config.get("paths", {}).get("workspace", ".")
    if pid_path is None:
        pid_path = Path(workspace) / ".emergence" / "drives.pid"

    # Check if running
    running, pid = is_running(pid_path)
    status["running"] = running
    status["pid"] = pid

    if running and pid:
        # Try to get process start time
        try:
            import subprocess

            result = subprocess.run(
                ["ps", "-p", str(pid), "-o", "lstart="], capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0 and result.stdout.strip():
                status["started"] = result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Get last tick from state
        try:
            from .state import load_state

            state = load_state(get_state_path(config))
            status["last_tick"] = state.get("last_tick")
        except Exception:
            pass

    return status


def main():
    """Main entry point for daemon command-line usage.

    Usage:
        python3 -m emergence.core.drives.daemon --run
        python3 -m emergence.core.drives.daemon start
        python3 -m emergence.core.drives.daemon stop
        python3 -m emergence.core.drives.daemon status
    """
    import argparse

    parser = argparse.ArgumentParser(
        description="Emergence Drive Daemon",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  start          Start the daemon in background
  stop           Stop the running daemon
  status         Show daemon status
  restart        Stop and start the daemon
  --run          Run the daemon loop (normally used by start)
""",
    )

    parser.add_argument(
        "command",
        nargs="?",
        choices=["start", "stop", "status", "restart", "--run"],
        help="Daemon command",
    )

    parser.add_argument(
        "--foreground", "-f", action="store_true", help="Run in foreground (don't daemonize)"
    )

    parser.add_argument("--config", help="Path to config file")

    parser.add_argument("--pidfile", help="Path to PID file")

    args = parser.parse_args()

    # Load config
    config = load_config(Path(args.config) if args.config else None)

    pid_path = Path(args.pidfile) if args.pidfile else None

    if args.command == "start" or (args.command is None and not args.foreground):
        detach = not args.foreground
        result = start_daemon(config, detach=detach, pid_path=pid_path)

        if result.get("already_running"):
            print(f"Daemon already running (PID {result['pid']})")
            sys.exit(0)
        elif result["success"]:
            if detach:
                print(f"Daemon started (PID {result['pid']})")
            sys.exit(0)
        else:
            print(f"Failed to start daemon: {', '.join(result['errors'])}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "stop":
        result = stop_daemon(config, pid_path=pid_path)

        if not result.get("was_running"):
            print("Daemon not running")
            sys.exit(0)
        elif result["success"]:
            print("Daemon stopped")
            sys.exit(0)
        else:
            print(f"Failed to stop daemon: {', '.join(result['errors'])}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "status":
        status = daemon_status(config, pid_path=pid_path)

        if status["running"]:
            print(f"Daemon is running (PID {status['pid']})")
            if status.get("started"):
                print(f"Started: {status['started']}")
            if status.get("last_tick"):
                print(f"Last tick: {status['last_tick']}")
        else:
            print("Daemon not running")
            sys.exit(1)

    elif args.command == "restart":
        # Stop first
        stop_result = stop_daemon(config, pid_path=pid_path)
        if stop_result.get("was_running") and not stop_result["success"]:
            print(f"Failed to stop daemon: {', '.join(stop_result['errors'])}", file=sys.stderr)
            sys.exit(1)

        # Wait a moment
        time.sleep(0.5)

        # Start
        start_result = start_daemon(config, detach=not args.foreground, pid_path=pid_path)
        if start_result["success"]:
            print(f"Daemon restarted (PID {start_result['pid']})")
            sys.exit(0)
        else:
            print(f"Failed to start daemon: {', '.join(start_result['errors'])}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "--run":
        # Internal command used after fork
        exit_code = run_daemon(config, foreground=False, pid_path=pid_path)
        sys.exit(exit_code)

    else:
        # Default: run in foreground
        exit_code = run_daemon(config, foreground=True, pid_path=pid_path)
        sys.exit(exit_code)


if __name__ == "__main__":
    main()
