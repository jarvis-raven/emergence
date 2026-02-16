# CHOICE Mode — Agent-Driven Drive Satisfaction

When `daemon_mode: false` in emergence.json, the agent operates in CHOICE mode:
drives build pressure, but the agent **chooses** when and whether to engage.

## How It Works

### 1. Daemon Ticks

- Daemon runs every `tick_interval` seconds (default: 60)
- Each tick increases pressure based on `rate_per_hour`
- State written to `.emergence-dev/state/drives-state.json`

### 2. Context Injection

- Agent's heartbeat syncs drive state to workspace
- Minimal format to reduce token usage (~25 tokens)
- Example: `REST 67%🟡 WANDER 61%🟡 MAINT 21% CARE 17%`

### 3. Choice Prompt

When cooldown has expired and drives are available (>30%), agent is prompted:

> "Drives available. Do you want to engage with one? Which one calls to you?"

### 4. Agent Decides

- **Engage**: Run `drives satisfy <name> <depth>`, cooldown starts
- **Defer**: No penalty, asked again next heartbeat

### 5. Cooldown

- Duration: `cooldown_minutes` from config (default: 30)
- Only triggered by actual satisfaction, not deferral
- Purpose: Prevent token burn from rapid drive spawns

## Drive States

| State     | Pressure | Indicator | Meaning                |
| --------- | -------- | --------- | ---------------------- |
| Calm      | <30%     | 🟢        | Building quietly       |
| Available | 30-75%   | 🟡        | Ready for engagement   |
| Elevated  | 75-99%   | 🟠        | Strongly calling       |
| Triggered | 100%+    | 🔴        | Urgent, hard to ignore |

## DRIVES.md Format

Minimal context injection format:

```markdown
## Drives (CHOICE) 15:42 | ✓READY

REST 67%🟡 WANDER 61%🟡 MAINT 21% CARE 17%
```

Or during cooldown:

```markdown
## Drives (CHOICE) 15:42 | Satisfied: WANDER@15:10 | ⏳18min

REST 67%🟡 WANDER 61%🟡 MAINT 21% CARE 17%
```

## Sync Script

Use `drives context` to generate the minimal format:

```bash
emergence drives context [--workspace PATH]
```

This reads drives-state.json and outputs the DRIVES.md content.

## Heartbeat Integration

Add to HEARTBEAT.md:

```markdown
### Drive Awareness (every heartbeat)

1. Run: `emergence drives context > DRIVES.md`
2. If ✓READY shown, ask yourself: "Do I want to engage with a drive?"
3. If yes: `emergence drives satisfy <name> <depth> --reason "..."`
```

## vs AUTO Mode

| Aspect   | CHOICE Mode          | AUTO Mode                   |
| -------- | -------------------- | --------------------------- |
| Trigger  | Agent chooses        | System spawns automatically |
| Language | "calling"            | "pending spawn"             |
| Cooldown | Only on satisfaction | On every trigger            |
| Badge    | [CHOICE]             | [AUTO]                      |
