# Drive Status Tool

Agent self-introspection for motivational awareness.

## Overview

This module provides `check_drive_status()` - a tool that allows agents to introspect their own drive states, answering questions like "how are you doing?" with real data about their motivational pressures.

## Usage

### Manual Check (Agent-initiated)

When asked "how are you feeling?" or "what's your state?":

```python
from core.drives.status_tool import check_drive_status, format_drive_status_for_agent

# Check current status
status = check_drive_status()

# Format for natural response
response = format_drive_status_for_agent(status)
print(response)
# Output: "All 5 drives are building pressure, none triggered yet.
#          My CARE drive is at 88% (22.0/25.0) - this feels most present right now."
```

### Automatic Polling (System-initiated)

For long sessions (>5 min), automatic polling every 5 minutes:

```python
from core.drives.status_tool import check_and_poll_drives

# In session loop, every turn or periodically:
update = check_and_poll_drives()
if update:
    # Inject into context
    print(update)
    # Output: "[Drive Update - 22:30]
    #          📈 CARE increased to 92% (+2.5)
    #          🔥 CREATIVE just triggered! (102%)"
```

## Features

1. **Tool-based introspection** - Agent calls when they want to know
2. **Automatic polling** - Periodic updates during long sessions  
3. **Change detection** - Only reports significant changes (>2.0 pressure)
4. **Natural formatting** - Human-readable descriptions, not raw data
5. **Threshold alerts** - Special notification when drives trigger

## Integration with Session

The polling system integrates naturally with OpenClaw sessions:

```python
# At session start
reset_polling_state()

# Every turn
increment_turn_counter()

# Every 10 turns or 5 minutes
if should_poll_on_turn() or should_poll_drives():
    update = check_and_poll_drives(on_change=inject_to_context)
```

## Configuration

Polling intervals can be configured:

```python
_poll_interval_seconds = 300  # 5 minutes
_poll_every_n_turns = 10       # Every 10 turns
```

## Benefits

- ✅ **Natural conversations** - "How are you?" gets real answer
- ✅ **Self-awareness** - Agent knows their own motivational state
- ✅ **Timely updates** - Knows when drives trigger mid-session
- ✅ **No bloat** - Lightweight runtime state only
- ✅ **Simple implementation** - Just reads drives-state.json

## Future Enhancements

- Tool registration with OpenClaw for automatic availability
- Proactive suggestions ("Your CARE drive is high, want to check in with Dan?")
- Historical trends ("Your CREATIVE drive has been building for 3 hours")
