# API Reference

> CLI commands, configuration fields, and Room endpoints for Emergence v0.3.0.

---

## CLI Commands

### `emergence drives satisfy <drive> [depth]`

Manually satisfy a drive at a chosen depth.

**Arguments:**

- `<drive>` — Drive name (case-insensitive, fuzzy-matched)
- `[depth]` — Satisfaction depth: `light`, `moderate`, or `deep` (default: auto-scaled based on current pressure)

**Depths:**
| Depth | Pressure Reduction | Use Case |
|-------|-------------------|----------|
| `light` | 30% | Quick acknowledgment |
| `moderate` | 60% | Meaningful engagement |
| `deep` | 90% | Full satisfaction |

**Examples:**

```bash
emergence drives satisfy CARE light
emergence drives satisfy creative moderate
emergence drives satisfy SOCIAL deep
emergence drives satisfy REST          # Auto-selects depth based on pressure
```

**Auto-scaling logic:** If no depth is specified, the engine selects based on current pressure ratio:

- Below elevated (< 70%): light
- Elevated to triggered (70–100%): moderate
- Above triggered (> 100%): deep

---

### `emergence drives dashboard`

Launch the interactive terminal dashboard showing all drives with live pressure bars, threshold markers, and satisfaction controls.

**Features:**

- Real-time pressure bars with color-coded bands
- Manual mode toggle
- Keyboard-driven satisfaction (select drive → choose depth)
- Thwarting/valence indicators

---

### `emergence drives status`

Show current drive levels. v0.3.0 adds:

- Threshold band labels (available/elevated/triggered/crisis/emergency)
- Thwarting indicators (🔄 when drive is thwarted)
- Valence display (positive ↔ negative shift)

**Flags:**

- `--json` — Output as JSON
- `--show-latent` — Include inactive drives
- `--verbose` — Show thwarting details and satisfaction history

---

### `emergence migrate export`

Export current state (drives, config, identity files) to a portable archive.

```bash
emergence migrate export
# → emergence-state-YYYY-MM-DD.tar.gz
```

### `emergence migrate import <file>`

Import state from a previously exported archive.

```bash
emergence migrate import emergence-state-2026-02-13.tar.gz
```

### `emergence migrate rewrite-paths`

Interactive utility to update `workspace`, `state`, and `identity` paths in `emergence.json`. Useful after moving directories or migrating between machines.

```bash
emergence migrate rewrite-paths
```

---

## Configuration Fields

All fields in `emergence.json` under the `drives` key:

### Existing (v0.2.x)

| Field                | Type       | Default   | Description                                                        |
| -------------------- | ---------- | --------- | ------------------------------------------------------------------ |
| `tick_interval`      | int        | `900`     | Seconds between pressure ticks                                     |
| `quiet_hours`        | [int, int] | `[23, 7]` | Start/end hours for quiet mode                                     |
| `daemon_mode`        | bool       | `true`    | Enable background daemon                                           |
| `cooldown_minutes`   | int        | `30`      | Minimum minutes between triggers                                   |
| `max_pressure_ratio` | float      | `1.5`     | Pressure cap (v0.2.x; superseded by emergency threshold in v0.3.0) |

### New (v0.3.0)

| Field                      | Type   | Default   | Description                                       |
| -------------------------- | ------ | --------- | ------------------------------------------------- |
| `manual_mode`              | bool   | `false`   | Disable auto-spawn; agent controls satisfaction   |
| `emergency_spawn`          | bool   | `true`    | Allow emergency auto-spawn at emergency threshold |
| `emergency_threshold`      | float  | `2.0`     | Pressure ratio triggering emergency spawn         |
| `emergency_cooldown_hours` | int    | `6`       | Hours between emergency spawns per drive          |
| `thresholds`               | object | See below | Graduated threshold configuration                 |

### Thresholds Object

```json
{
  "thresholds": {
    "available": 0.3,
    "elevated": 0.75,
    "triggered": 1.0,
    "crisis": 1.5,
    "emergency": 2.0
  }
}
```

Thresholds can be set globally (under `drives.thresholds`) or per-drive in the drive's JSON config.

---

## Room HTTP Endpoints

The Room dashboard server (default `http://localhost:7373`) exposes these new endpoints:

### `POST /api/drives/satisfy`

Satisfy a drive from the dashboard UI.

**Request body:**

```json
{
  "drive": "CARE",
  "depth": "moderate"
}
```

**Response:**

```json
{
  "success": true,
  "drive": "CARE",
  "pressure_before": 18.5,
  "pressure_after": 7.4,
  "depth": "moderate",
  "reduction_ratio": 0.6
}
```

### `POST /api/drives/manual-mode`

Toggle manual mode from the dashboard.

**Request body:**

```json
{
  "enabled": true
}
```

**Response:**

```json
{
  "success": true,
  "manual_mode": true
}
```

### `GET /api/drives/status`

Returns full drive status including v0.3.0 fields (thresholds, thwarting, valence).

**Response:** Array of drive objects with:

- `name`, `pressure`, `threshold`, `ratio`
- `band` — current threshold band (available/elevated/triggered/crisis/emergency)
- `thwarted` — boolean
- `thwarting_count` — number of failed satisfactions
- `valence` — positive/negative/neutral

### Existing Endpoints (unchanged)

| Endpoint                      | Method | Description           |
| ----------------------------- | ------ | --------------------- |
| `/api/drives`                 | GET    | All drives (basic)    |
| `/api/drives/:name`           | GET    | Single drive details  |
| `/api/drives/:name/aspects`   | GET    | Drive aspects         |
| `/api/budget/status`          | GET    | Daily spend/limit     |
| `/api/first-light/status`     | GET    | First Light progress  |
| `/api/drives/pending-reviews` | GET    | Consolidation reviews |
| `/api/drives/latent`          | GET    | Inactive drives       |

---

## WebSocket Events

The Room uses WebSocket for live drive updates. v0.3.0 adds:

| Event                     | Payload                           | Description                        |
| ------------------------- | --------------------------------- | ---------------------------------- |
| `drive:threshold-crossed` | `{ drive, band, pressure }`       | Drive entered a new threshold band |
| `drive:thwarted`          | `{ drive, count }`                | Drive thwarting detected           |
| `drive:emergency`         | `{ drive, pressure }`             | Emergency spawn triggered          |
| `drive:satisfied`         | `{ drive, depth, before, after }` | Drive was satisfied                |
