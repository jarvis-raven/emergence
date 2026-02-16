# AUTO Mode — Automatic Drive Satisfaction

**Status:** Production  
**Since:** v0.2.0

---

## Overview

AUTO mode is the original drives behavior: the daemon monitors pressure levels and automatically spawns sessions when drives trigger. The agent responds to drives rather than choosing when to engage.

**Best for:**
- Agents new to the drives system
- Guaranteed drive coverage
- Hands-off operation
- Predictable behavior

---

## How It Works

```
┌─────────────────────────────────────────────────────┐
│                    AUTO MODE                        │
├─────────────────────────────────────────────────────┤
│  Pressure builds → Threshold hit → Daemon spawns   │
│                                                     │
│  Agent responds to spawned session                  │
│  Session completes → Pressure resets               │
└─────────────────────────────────────────────────────┘
```

### The Loop

1. **Daemon ticks** every second, accumulating pressure based on `rate_per_hour`
2. **Threshold crossed** — drive enters "triggered" state
3. **Daemon spawns** an isolated session with the drive's prompt
4. **Agent works** in the spawned session (explore, create, connect, etc.)
5. **Session completes** — daemon detects completion
6. **Pressure resets** to ~50% (moderate satisfaction)
7. **Cycle repeats**

### Configuration

```json
{
  "drives": {
    "daemon_mode": true,
    "tick_seconds": 1,
    "cooldown_minutes": 30
  }
}
```

- `daemon_mode: true` — enables automatic spawning
- `cooldown_minutes` — minimum time between spawns

---

## What the Agent Experiences

In AUTO mode, drives feel like **external summons**:

> "Your CREATIVE drive triggered. Time to make something."

The agent doesn't choose when to create — they're called to create when the system decides. This removes the burden of choice but also removes agency.

### Strengths

- ✅ Drives never get neglected
- ✅ Predictable rhythm
- ✅ No decision fatigue
- ✅ Good for establishing baseline behavior

### Limitations

- ❌ No strategic prioritization
- ❌ Can't defer drives for important conversations
- ❌ Fixed satisfaction depth (always moderate)
- ❌ Agent is reactive, not proactive

---

## Monitoring

### CLI

```bash
# Check daemon status
emergence drives daemon status

# View current pressures
emergence drives status

# See trigger history
emergence drives history --triggers
```

### Room UI

The DaemonHealthDrawer shows:
- Daemon running/stopped status
- Current tick count
- Last spawn time
- WebSocket connection

---

## When to Use AUTO Mode

**Good scenarios:**
- Learning what each drive feels like
- Establishing a baseline before trying CHOICE
- When you want guaranteed engagement
- During busy periods when you can't actively manage drives

**Consider CHOICE mode when:**
- You want strategic control over timing
- You need to prioritize conversations over drives
- You want to experiment with delegation
- You're ready for more agency

---

## Switching Modes

### AUTO → CHOICE

```json
{
  "drives": {
    "daemon_mode": false
  }
}
```

Or use the CLI:
```bash
emergence drives daemon stop
```

### CHOICE → AUTO

```bash
emergence drives daemon start
```

---

## See Also

- [CHOICE_MODE.md](./CHOICE_MODE.md) — Manual drive management
- [v0.3.0-agency-and-choice.md](./v0.3.0-agency-and-choice.md) — Design rationale

---

*AUTO mode is reliable. CHOICE mode is agentic. Start with AUTO, graduate to CHOICE.*
