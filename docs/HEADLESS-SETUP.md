# Headless Setup Guide

Running Emergence on a headless server (Raspberry Pi, VPS, remote Linux box)? This guide covers the unique considerations.

---

## What Changes on Headless Systems

1. **No GUI** — Room dashboard isn't directly viewable on the machine
2. **Remote access** — Need SSH or network access to view/manage
3. **Auto-start is essential** — No manual launch via desktop
4. **Logging is critical** — Can't see visual errors

---

## Installation

The init wizard works the same on headless systems:

```bash
cd ~/.openclaw/workspace/projects/emergence
python3 -m core.setup.init_wizard
```

When prompted about the Room dashboard:
- ✅ **Enable it** — even though you can't view it locally
- ✅ **Enable auto-start** — essential for headless operation

The wizard will detect Linux and create a systemd user service.

---

## Accessing the Room Dashboard

You have three options:

### Option 1: SSH Port Forward (Recommended, Most Secure)

From your local machine:

```bash
ssh -L 7373:localhost:7373 user@remote-host
# Keep terminal open
# Visit http://localhost:7373 in your browser
```

This creates an encrypted tunnel and exposes the remote port locally.

**Pros:**
- ✅ Encrypted (SSH tunnel)
- ✅ No network exposure
- ✅ Standard practice

**Cons:**
- ⚠️ Must keep SSH session open
- ⚠️ One connection at a time (without multiplexing)

### Option 2: Configure Room to Bind 0.0.0.0

Edit `emergence.json`:

```json
{
  "room": {
    "enabled": true,
    "port": 7373,
    "bind": "0.0.0.0"  // ← Add this
  }
}
```

Then access via:
- `http://<remote-ip>:7373`
- `http://<hostname>:7373` (if DNS/mDNS configured)

**Pros:**
- ✅ Accessible from any machine on the network
- ✅ No SSH required

**Cons:**
- ⚠️ HTTP (plaintext, unless you add HTTPS)
- ⚠️ Exposed to entire network
- ⚠️ Consider firewall rules

### Option 3: Reverse Proxy (Advanced)

Use nginx/caddy to:
- Add HTTPS
- Restrict access by IP/auth
- Proxy Room behind a standard web port (80/443)

Example nginx config:

```nginx
server {
    listen 443 ssl;
    server_name emergence.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    location / {
        proxy_pass http://localhost:7373;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }
}
```

**Pros:**
- ✅ HTTPS
- ✅ Standard ports
- ✅ Can add auth/restrictions

**Cons:**
- ⚠️ Requires web server setup
- ⚠️ More complex

---

## Verifying Auto-Start Works

After installation, verify the service is configured:

**On systemd (Linux):**

```bash
# Check service file exists
ls ~/.config/systemd/user/emergence-room-*.service

# Check status
systemctl --user status emergence-room-*.service

# Check it's enabled for auto-start
systemctl --user is-enabled emergence-room-*.service
```

**On macOS (launchd):**

```bash
# Check plist exists
ls ~/Library/LaunchAgents/com.emergence.room.*.plist

# Check if loaded
launchctl list | grep emergence
```

**Test reboot:**

Reboot the machine and verify the service starts automatically:

```bash
sudo reboot
# (after reboot, SSH back in)
systemctl --user status emergence-room-*.service  # Should be "active"
```

---

## Troubleshooting

### Service Isn't Running

Check logs:

```bash
tail ~/.openclaw/workspace/projects/emergence/.emergence/logs/room.out.log
tail ~/.openclaw/workspace/projects/emergence/.emergence/logs/room.err.log
```

Common issues:
- Node.js not in PATH
- Port already in use
- Workspace path incorrect

### SSH Port Forward Not Working

Check:
- ✅ SSH connection works: `ssh user@remote-host`
- ✅ Room service is running on remote: `systemctl --user status emergence-room-*`
- ✅ Port isn't already forwarded: `lsof -i :7373` (on local machine)

### Auto-Start Doesn't Work After Reboot

**Linux (systemd):**

Ensure the service is enabled:

```bash
systemctl --user enable emergence-room-*.service
```

Check if user services start on boot (may need `loginctl enable-linger <username>`):

```bash
sudo loginctl enable-linger $USER
```

**macOS (launchd):**

Check the plist has `RunAtLoad` set to `true`:

```bash
grep RunAtLoad ~/Library/LaunchAgents/com.emergence.room.*.plist
```

---

## Security Considerations

1. **SSH keys only** — Disable password authentication for SSH
2. **Firewall** — If binding to 0.0.0.0, use a firewall (ufw, iptables) to restrict access
3. **HTTPS** — If exposing publicly, use HTTPS (reverse proxy + Let's Encrypt)
4. **Tailscale** — Consider a VPN like Tailscale for secure remote access without port forwarding

---

## Raspberry Pi Specific Notes

- **RAM:** Room server uses ~100-200MB. Fine for Pi 4 (4GB+), tight on Pi Zero/3
- **Storage:** Room + Node modules ~50MB. Ensure SD card has space for logs
- **Performance:** Room works well on Pi 4. Pi 3 is slower but usable.
- **Cooling:** If running 24/7, consider a case with fan/heatsink

---

## Remote Management

Without GUI access, use CLI:

```bash
# Check service status
systemctl --user status emergence-room-*

# Restart service
systemctl --user restart emergence-room-*

# Stop service
systemctl --user stop emergence-room-*

# View logs
tail -f ~/.openclaw/workspace/projects/emergence/.emergence/logs/room.out.log
```

---

## Summary

**For most headless setups:**

1. Run `emergence init` — enable Room + auto-start
2. Use **SSH port forwarding** to view dashboard
3. Verify auto-start works after reboot
4. Monitor logs for errors

**Advanced users:**
- Bind to 0.0.0.0 with firewall rules
- Use reverse proxy for HTTPS
- Consider Tailscale for secure mesh networking

---

*Last updated: 2026-02-10*
