#!/bin/bash
# sync-drives-context.sh — Update DRIVES.md with current drive pressures
# Called by heartbeat to keep workspace context in sync with drives state

set -e

WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
DRIVES_MD="$WORKSPACE/DRIVES.md"
EMERGENCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$EMERGENCE_DIR"

# Get drives status as JSON and format to markdown
python3 -m core.cli drives status --json 2>/dev/null | python3 -c '
import json
import sys
from datetime import datetime, timezone

try:
    status = json.load(sys.stdin)
except json.JSONDecodeError as e:
    print(f"Failed to parse drives status: {e}", file=sys.stderr)
    sys.exit(1)

drives_list = status.get("drives", [])
cooldown = status.get("cooldown", {})

# Sort drives by pressure ratio (descending)
sorted_drives = sorted(drives_list, key=lambda x: x.get("ratio", 0), reverse=True)

lines = ["## Drives State"]
lines.append(f"*{len(drives_list)} drives, updated {datetime.now(timezone.utc).isoformat()}*")
lines.append("")

# Check cooldown
is_ready = cooldown.get("ready", True)
if is_ready:
    lines.append("**✓READY** — Can satisfy drives")
else:
    remaining = cooldown.get("remaining_minutes", 0)
    lines.append(f"**⏳COOLDOWN** — {remaining:.0f}m remaining")
lines.append("")

# Triggered drives summary
triggered = [d for d in sorted_drives if d.get("ratio", 0) >= 1.0]
if triggered:
    lines.append("**🔥 Triggered:**")
    for d in triggered:
        name = d.get("name", "?")
        pct = int(d.get("ratio", 0) * 100)
        pressure = d.get("pressure", 0)
        threshold = d.get("threshold", 100)
        lines.append(f"- **{name}** at {pct}% ({pressure:.1f}/{threshold})")
    lines.append("")

# All drives
for d in sorted_drives:
    name = d.get("name", "?")
    pressure = d.get("pressure", 0)
    threshold = d.get("threshold", 100)
    ratio = d.get("ratio", 0)
    pct = int(ratio * 100)
    desc = d.get("description", "")

    # Status indicator
    if ratio >= 1.0:
        indicator = "🔴"
    elif ratio >= 0.75:
        indicator = "🟠"
    elif ratio >= 0.30:
        indicator = "🟡"
    else:
        indicator = "🟢"

    lines.append(f"{indicator} {name}: {pressure:.1f}/{threshold} ({pct}%) — {desc}")

print("\n".join(lines))
' > "$DRIVES_MD"

echo "Updated $DRIVES_MD"
