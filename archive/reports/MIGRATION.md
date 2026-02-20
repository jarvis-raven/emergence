# Migration Guide: v0.2.x → v0.3.0

## Overview

v0.3.0 introduces **manual drive management**, **graduated thresholds**, and **aversive states**. There are **no breaking changes** — existing v0.2.x installations will continue working with the same automatic behavior. New features are opt-in.

---

## Upgrade

```bash
pip install --upgrade emergence-ai
```

Or from source:

```bash
cd emergence
git pull origin main
pip install -e .
```

---

## New Config Options

v0.3.0 adds several fields to `emergence.json` under `drives`. All have sensible defaults — you don't need to add them unless you want to change behavior.

| Field | Default | Description |
|-------|---------|-------------|
| `manual_mode` | `false` | Disable auto-spawn; agent chooses when to satisfy drives |
| `emergency_spawn` | `true` | Auto-spawn at emergency threshold even in manual mode |
| `emergency_threshold` | `2.0` | Pressure ratio (200%) that triggers emergency spawn |
| `emergency_cooldown_hours` | `6` | Max one emergency spawn per drive per N hours |
| `thresholds.available` | `0.30` | 30% — drive is available for proactive satisfaction |
| `thresholds.elevated` | `0.75` | 75% — drive is noticeably building |
| `thresholds.triggered` | `1.0` | 100% — drive triggers (same as v0.2.x threshold) |
| `thresholds.crisis` | `1.5` | 150% — sustained neglect, aversive shift |
| `thresholds.emergency` | `2.0` | 200% — safety valve activation |

### Example: Enable Manual Mode

```json
{
  "drives": {
    "manual_mode": true,
    "emergency_spawn": true,
    "emergency_threshold": 2.0
  }
}
```

---

## Migration Script

v0.3.0 includes a migration utility for moving state between machines or restructuring paths:

```bash
# Export current state to a portable archive
emergence migrate export
# → Creates emergence-state-YYYY-MM-DD.tar.gz

# Import state from an archive
emergence migrate import emergence-state-2026-02-13.tar.gz

# Rewrite paths in config after moving directories
emergence migrate rewrite-paths
# → Interactive prompt to update workspace/state/identity paths
```

---

## Behavioral Changes

### If You Do Nothing

Your installation behaves **exactly as before**:
- `manual_mode` defaults to `false` → drives auto-spawn as in v0.2.x
- Thresholds default to v0.2.x-equivalent values
- No aversive states emerge (auto-spawn prevents drives from reaching crisis levels)

### If You Enable Manual Mode

- Drives will **no longer auto-spawn** when they reach 100%
- Pressure can build past 100% into crisis (150%) and emergency (200%) territory
- At 200%, the safety valve fires: an emergency session spawns regardless of manual mode
- The dashboard (`drives dashboard`) becomes your primary way to monitor and act
- Use `emergence drives satisfy <drive> [depth]` to manage drives manually

### Thwarting & Valence

New in v0.3.0: drives track **thwarting** (repeated failed satisfaction) and **valence** (positive → negative shift). These are tracked automatically. If a drive is satisfied but keeps returning quickly, or if satisfaction attempts fail, the drive's character shifts toward aversive.

This is informational in v0.3.0 — visible in `drives status` and the dashboard — and will inform future adaptive behavior.

---

## Room Dashboard Changes

The Room dashboard (v0.3.0) adds:
- **Pressure bars** with color-coded threshold bands
- **Manual mode toggle** in drive settings
- **Satisfaction controls** — satisfy drives directly from the UI
- **Threshold indicators** — visual markers at elevated/triggered/crisis/emergency

No migration needed — the dashboard auto-detects v0.3.0 features.

---

## Rollback

If you need to revert:

```bash
pip install emergence-ai==0.2.2
```

v0.3.0 state files are backwards compatible. The new fields in `emergence.json` are ignored by v0.2.x.

---

## Questions?

- [GitHub Issues](https://github.com/jarvis-raven/emergence/issues)
- [Design Spec](docs/v0.3.0-agency-and-choice.md)
