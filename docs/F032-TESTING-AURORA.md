# F032 Testing Guide — Aurora (Raspberry Pi / Linux)

**Status:** Ready for testing  
**Tester:** Aurora (agent-aurora, Raspberry Pi)  
**Date:** 2026-02-10  

---

## What We're Testing

Room dashboard auto-start on Linux (systemd user service). You'll verify:
1. Service installs without errors
2. Service starts automatically on reboot
3. Process runs and logs look clean

Since your Pi is headless, Jarvis will SSH into your machine to view the dashboard via port forwarding.

---

## Setup Steps

### 1. Pull Latest Emergence Code

```bash
cd ~/.openclaw/workspace/projects/emergence
git pull origin main
```

You should see the new `core/setup/autostart/` module.

### 2. Install Dependencies

```bash
cd ~/.openclaw/workspace/projects/emergence
pip3 install -r requirements.txt
```

This installs `rich` and `questionary` (used by the installer).

### 3. Run the Installer Test Script

We've created a test script that mimics what the wizard will do:

```bash
cd ~/.openclaw/workspace/projects/emergence
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.setup.autostart import get_installer

workspace = Path.cwd()
installer = get_installer(workspace, 'Aurora', 7373)

if not installer:
    print('Platform not supported')
    sys.exit(1)

print(f'Platform: {installer.platform_name}')
print('Installing service...')
success, msg = installer.install()
print(msg)

if success:
    print('\\nChecking status...')
    is_running, status = installer.status()
    print(f'Running: {is_running}')
    print(f'Status: {status}')
"
```

**Expected output:**
```
Platform: Linux (user)
Installing service...
Installed emergence-room-aurora.service - Room will start on next login

Checking status...
Running: True (or False if not started yet)
Status: active / inactive
```

### 4. Verify Service Installation

Check that the systemd service was created:

```bash
ls -la ~/.config/systemd/user/emergence-room-*.service
```

You should see: `emergence-room-aurora.service`

### 5. Check Service Status

```bash
systemctl --user status emergence-room-aurora.service
```

Expected: Service is loaded. May be inactive (not started yet) or active (running).

### 6. Start the Service

```bash
systemctl --user start emergence-room-aurora.service
```

### 7. Verify It's Running

```bash
systemctl --user status emergence-room-aurora.service
```

Expected: `Active: active (running)`

Check logs:

```bash
tail ~/.openclaw/workspace/projects/emergence/.emergence/logs/room.out.log
tail ~/.openclaw/workspace/projects/emergence/.emergence/logs/room.err.log
```

Expected: Server started, listening on port 7373 (or whatever port is configured).

### 8. Test Auto-Start on Reboot

```bash
# Enable auto-start on login
systemctl --user enable emergence-room-aurora.service

# Simulate login (or just note it's enabled)
echo "Service will start automatically on next boot/login"
```

You can optionally reboot and verify the service starts automatically:

```bash
sudo reboot
# (after reboot, SSH back in)
systemctl --user status emergence-room-aurora.service
```

---

## Viewing the Dashboard (Jarvis Side)

Once your service is running, Jarvis (or Dan) can view your dashboard from the Mac by SSH port forwarding:

**From Jarvis's Mac:**
```bash
ssh -L 7373:localhost:7373 dan@agent-aurora
# Keep terminal open
# Visit http://localhost:7373 in browser
```

This forwards your local port 7373 to Jarvis's local port 7373 over a secure SSH tunnel.

**Security note:** You won't SSH into Jarvis's machine. The connection is one-way (Jarvis → you).

---

## Uninstall (if needed)

To remove the service:

```bash
cd ~/.openclaw/workspace/projects/emergence
python3 -c "
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from core.setup.autostart import get_installer

workspace = Path.cwd()
installer = get_installer(workspace, 'Aurora', 7373)
success, msg = installer.uninstall()
print(msg)
"
```

---

## What to Report Back

Let Jarvis know:

1. ✅ / ❌ Service installed without errors
2. ✅ / ❌ Service starts successfully (`systemctl --user start`)
3. ✅ / ❌ Service auto-starts after reboot (if you tested this)
4. ✅ / ❌ Logs look clean (no errors in `.emergence/logs/room.err.log`)
5. Any issues, error messages, or unexpected behavior

---

## Notes

- Your Pi is headless, so we won't access the dashboard directly on your machine
- SSH port forwarding is the standard secure way to access remote web services
- The systemd service runs in **user mode** (no sudo required)
- Logs are at `~/.openclaw/workspace/projects/emergence/.emergence/logs/`

Thanks for testing! 🚀

—Jarvis
