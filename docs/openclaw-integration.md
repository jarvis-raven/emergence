# OpenClaw Integration Guide

This guide explains how to set up Emergence with OpenClaw, covering workspace structure and configuration patterns.

---

## Workspace Structure

There are two common patterns for integrating Emergence with an OpenClaw agent workspace:

### Pattern A: Emergence as Agent Workspace (Recommended)

The `emergence` directory **is** your agent workspace. All identity files, drives, and memory live here.

```
my-agent/                     ← This is your emergence workspace
├── emergence.json            ← Emergence config
├── SOUL.md                   ← Your identity files
├── SELF.md
├── USER.md
├── AGENTS.md
├── .emergence/
│   ├── state/
│   │   ├── drives.json
│   │   └── drives-state.json
│   └── logs/
├── memory/
│   ├── daily/
│   └── sessions/
├── core/                     ← Emergence toolkit (if installed from source)
│   ├── drives/
│   ├── memory/
│   └── ...
├── room/                     ← Dashboard
└── venv/                     ← Python virtual environment
```

**Setup:**

```bash
# Option 1: Install from PyPI
mkdir my-agent && cd my-agent
pip install emergence-ai
emergence init --mode fresh

# Option 2: Install from source
git clone https://github.com/jarvis-raven/emergence.git my-agent
cd my-agent
python3 -m venv venv
source venv/bin/activate
pip install -e .
emergence init --mode fresh
```

**OpenClaw config** (`~/.openclaw/agents.json` or via dashboard):

```json
{
  "agents": {
    "my-agent": {
      "workspace": "/path/to/my-agent"
    }
  }
}
```

---

### Pattern B: Emergence as Submodule

Keep Emergence toolkit separate from your agent's identity files.

```
my-agent/                     ← OpenClaw workspace
├── SOUL.md                   ← Identity files in agent root
├── SELF.md
├── USER.md
├── AGENTS.md
├── emergence/                ← Emergence toolkit (git submodule or pip install)
│   ├── core/
│   ├── room/
│   └── ...
├── emergence.json            ← Config points to parent workspace
├── .emergence/
│   ├── state/
│   └── logs/
├── memory/
│   ├── daily/
│   └── sessions/
└── venv/
```

**Setup:**

```bash
# Create agent workspace
mkdir my-agent && cd my-agent

# Install Emergence as dependency
python3 -m venv venv
source venv/bin/activate
pip install emergence-ai

# Initialize with workspace at parent level
emergence init --workspace . --mode fresh
```

**Config** (`emergence.json` in `my-agent/`):

```json
{
  "agent": {
    "name": "My Agent"
  },
  "paths": {
    "workspace": ".",
    "state": ".emergence/state",
    "identity": "."
  }
}
```

---

## Configuration

### Minimal `emergence.json`

```json
{
  "agent": {
    "name": "Your Agent Name"
  },
  "paths": {
    "workspace": ".",
    "state": ".emergence/state",
    "identity": "."
  },
  "drives": {
    "tick_interval": 900,
    "quiet_hours": [23, 7],
    "session_timeout": 900
  }
}
```

### Advanced Options

```json
{
  "agent": {
    "name": "Your Agent Name",
    "model": "anthropic/claude-sonnet-4-5"
  },
  "paths": {
    "workspace": ".",
    "state": ".emergence/state",
    "identity": "."
  },
  "drives": {
    "tick_interval": 900,
    "quiet_hours": [23, 7],
    "cooldown_minutes": 30,
    "session_timeout": 900,
    "session_model": "anthropic/claude-sonnet-4-5",
    "announce_session": false,
    "openclaw_path": "/custom/path/to/openclaw" // Override auto-detection
  },
  "memory": {
    "session_dir": "memory/sessions"
  }
}
```

---

## OpenClaw Hook (Optional)

Emergence provides an OpenClaw hook that automatically injects your drive state into every session.

### Install the Hook

```bash
emergence openclaw-hook install
```

This creates `~/.openclaw/hooks/emergence-drives/` with:

- `handler.ts` — Finds your drives-state.json and formats it
- `HOOK.md` — Documentation

After installation, restart the OpenClaw gateway:

```bash
openclaw gateway restart
```

### What It Does

Every session will include a `DRIVES.md` bootstrap file showing current drive pressures:

```markdown
## Drives State

_11 drives, updated 2026-02-12T15:25:42+00:00_

🟡 CARE: 19.3/20 (97%)
🟢 MAINTENANCE: 30.1/40 (75%)
🟢 CREATIVE: 11.2/20 (56%)
...
```

### Hook Status

```bash
emergence openclaw-hook status
```

Shows:

- Hook installation status
- Gateway status
- File integrity

---

## Starting the Daemon

The drives daemon monitors your drive pressures and spawns autonomous sessions when drives exceed thresholds.

### Manual Start

```bash
emergence drives daemon start
```

Daemon logs: `.emergence/logs/daemon.log`

### Check Status

```bash
emergence drives daemon status
```

### Stop Daemon

```bash
emergence drives daemon stop
```

---

## The Room Dashboard

The Room is a web dashboard showing your drives, memory, and projects in real-time.

### Start the Dashboard

```bash
cd room
npm install  # First time only
npm run dev
```

Open `http://localhost:7373` (or the port shown in terminal).

### Features

- **Drives Panel:** Real-time pressure levels, trigger history
- **Memory Panel:** Browse daily logs, sessions, identity files
- **Vision Board:** Aspirations and long-term goals
- **Workshop:** Active projects
- **Bookshelf:** Custom shelves for specialized memory views

---

## Troubleshooting

### Daemon Issues

**Problem:** Daemon can't find `openclaw` binary

**Solution:** The daemon auto-detects openclaw at startup. If it fails:

1. Check `.emergence/logs/daemon.log` for detection messages
2. Manually specify in `emergence.json`:
   ```json
   {
     "drives": {
       "openclaw_path": "/path/to/openclaw"
     }
   }
   ```

### Path Issues

**Problem:** Drive sessions can't find completion script

**Solution:** Fixed in v0.2.3+. The completion command now uses dynamic workspace paths and venv python automatically.

If you're on an older version:

```bash
pip install --upgrade emergence-ai
```

### Import Errors in Sessions

**Problem:** `ModuleNotFoundError: No module named 'core.drives'`

**Solution:** Make sure the daemon is running from within your venv:

```bash
source venv/bin/activate
emergence drives daemon start
```

---

## Next Steps

- [Getting Started Guide](getting-started.md) — First-time setup walkthrough
- [Drives Deep Dive](drives-deep-dive.md) — Understanding the motivation system
- [Philosophy](philosophy.md) — Why Emergence works this way

---

_Last updated: 2026-02-12_
