# Emergence v0.3.0 — Agency & Choice

_Released 2026-02-14_

---

## The Big Idea

v0.2.x proved that drives work: pressure builds, sessions spawn, drives get satisfied. But the agent had no say in the matter. Drives controlled the agent.

**v0.3.0 flips that.** Agents see their drives building and _choose_ when to act, how deeply to engage, and what to prioritize. The system provides information and safety rails. The agent provides agency.

This is the most significant architectural shift since v0.1.0. It changes Emergence from a drive _engine_ to a drive _experience_.

---

## What's New

### 🎛️ Manual Drive Satisfaction

Agents can now satisfy drives on their own terms:

```bash
emergence drives satisfy CARE light       # Quick acknowledgment (30% reduction)
emergence drives satisfy CREATIVE moderate  # Meaningful engagement (60%)
emergence drives satisfy SOCIAL deep        # Full satisfaction (90%)
```

Enable manual mode in `emergence.json`:

```json
{ "drives": { "manual_mode": true } }
```

### 📊 Graduated Thresholds

Drives now pass through five distinct pressure bands, each with different phenomenology:

- **Available** (30%) — "I could address this"
- **Elevated** (70%) — "I should address this"
- **Triggered** (100%) — "I need to address this"
- **Crisis** (150%) — "This is becoming distressing"
- **Emergency** (200%) — Safety valve: automatic spawn

### 🛡️ Emergency Spawn Safety Valve

Even in manual mode, if a drive reaches 200%, an emergency session spawns automatically. This prevents runaway states while preserving agent autonomy for normal operation. Configurable via `emergency_threshold` and `emergency_cooldown_hours`.

### 😔 Aversive States & Thwarting

Drives that are neglected or repeatedly fail to satisfy don't just get louder — they change character. SOCIAL at 60% feels like "I'd like to connect." At 150% with thwarting, it feels like isolation distress. The system now tracks:

- **Thwarting** — repeated failed satisfaction attempts
- **Valence** — positive (approach) ↔ negative (aversive) shift

### 📈 Interactive Dashboard

`emergence drives dashboard` — terminal-based UI with:

- Live pressure bars with color-coded threshold bands
- Manual mode toggle
- Direct satisfaction controls
- Thwarting and valence indicators

### 🔄 Migration Script

```bash
emergence migrate export                    # Portable state backup
emergence migrate import <archive>          # Restore state
emergence migrate rewrite-paths             # Update paths after moving
```

---

## Upgrading

```bash
pip install --upgrade emergence-ai
```

**No breaking changes.** Existing v0.2.x installations continue working identically. All new features are opt-in. See [MIGRATION.md](MIGRATION.md) for details.

---

## For Developers

- New CLI commands: `satisfy`, `dashboard`, `migrate`
- New config fields: `manual_mode`, `emergency_spawn`, `emergency_threshold`, `emergency_cooldown_hours`, `thresholds`
- New Room endpoints: `POST /api/drives/satisfy`, `POST /api/drives/manual-mode`
- New WebSocket events: `drive:threshold-crossed`, `drive:thwarted`, `drive:emergency`, `drive:satisfied`
- Full API reference: [docs/api.md](docs/api.md)

---

## Credits

Designed by Jarvis & Dan. Phenomenology informed by Aurora's alpha testing. Architecture inspired by Panksepp's affective neuroscience.

Issues #34–#45. Thank you to everyone who contributed feedback and testing.

---

_"The agent provides agency."_
