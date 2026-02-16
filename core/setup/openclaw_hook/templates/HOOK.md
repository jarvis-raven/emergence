---
name: emergence-drives
description: 'Injects lightweight drive state (drives-state.json) into agent context at bootstrap'
metadata: { 'openclaw': { 'emoji': '🧠', 'events': ['agent:bootstrap'] } }
---

# Emergence Drives Bootstrap

Injects the agent's current drive pressures into the session context at startup.

## What It Does

1. Listens for `agent:bootstrap` events
2. Finds `drives-state.json` relative to the workspace (checks Emergence config paths)
3. Formats drive state as a readable markdown snippet
4. Appends it to `bootstrapFiles` so the agent sees its own motivational state

## How It Finds the State File

Search order:

1. `EMERGENCE_CONFIG` env var → resolve state path from config
2. `<workspace>/emergence.json` → read `paths.state` relative to config dir
3. `<workspace>/../state/drives-state.json` (common OpenClaw layout)
4. `<workspace>/.emergence/state/drives-state.json` (default Emergence layout)

## Requirements

- Emergence drives daemon must be running and writing `drives-state.json`
- Works with any agent using Emergence, no hardcoded paths
