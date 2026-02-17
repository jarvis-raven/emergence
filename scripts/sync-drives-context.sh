#!/bin/bash
# sync-drives-context.sh — Update DRIVES.md with current drive pressures
# Called by heartbeat to keep workspace context in sync with drives state

set -e

WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
DRIVES_MD="$WORKSPACE/DRIVES.md"
EMERGENCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$EMERGENCE_DIR"

# Get all drive info via CLI and combine into rich markdown
python3 << PYEOF > "$DRIVES_MD"
import subprocess
import json
from datetime import datetime, timezone
import os

emergence_dir = "$EMERGENCE_DIR"

# Get status JSON
status_result = subprocess.run(
    ["python3", "-m", "core.cli", "drives", "status", "--json"],
    capture_output=True,
    text=True,
    cwd=emergence_dir
)

if status_result.returncode != 0:
    print("## Drives State\n\n❌ Failed to load drives status")
    exit(1)

status = json.loads(status_result.stdout)
drives_list = status.get("drives", [])
cooldown = status.get("cooldown", {})

# For each drive, get detailed info
drives_data = []
for drive_info in drives_list:
    name = drive_info.get("name", "?")

    # Get full drive details
    info_result = subprocess.run(
        ["python3", "-m", "core.cli", "drives", "show", name],
        capture_output=True,
        text=True,
        cwd=emergence_dir
    )

    description = ""
    prompt_preview = ""

    if info_result.returncode == 0:
        # Parse the output for description and prompt preview
        lines = info_result.stdout.split("\n")
        for i, line in enumerate(lines):
            if line.startswith("Description:"):
                description = line.split("Description:", 1)[1].strip()
            elif line.startswith("Prompt preview:"):
                # Grab the next few non-empty lines as prompt preview
                preview_lines = []
                for j in range(i+1, min(i+5, len(lines))):
                    preview_line = lines[j].strip()
                    if preview_line and not preview_line.startswith("━"):
                        preview_lines.append(preview_line)
                    if len(preview_lines) >= 2 or (preview_lines and len(preview_lines[0]) > 50):
                        break
                if preview_lines:
                    prompt_preview = " ".join(preview_lines)[:120]

    drives_data.append({
        "name": name,
        "pressure": drive_info.get("pressure", 0),
        "threshold": drive_info.get("threshold", 100),
        "ratio": drive_info.get("ratio", 0),
        "description": description,
        "prompt_preview": prompt_preview
    })

# Sort by ratio descending
sorted_drives = sorted(drives_data, key=lambda x: x["ratio"], reverse=True)

lines = ["## Drives State"]
lines.append(f"*{len(drives_data)} drives, updated {datetime.now(timezone.utc).isoformat()}*")
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
triggered = [d for d in sorted_drives if d["ratio"] >= 1.0]
if triggered:
    lines.append("**🔥 Triggered:**")
    for d in triggered:
        name = d["name"]
        pct = int(d["ratio"] * 100)
        pressure = d["pressure"]
        threshold = d["threshold"]
        lines.append(f"- **{name}** at {pct}% ({pressure:.1f}/{threshold})")
    lines.append("")

# All drives with descriptions
for d in sorted_drives:
    name = d["name"]
    pressure = d["pressure"]
    threshold = d["threshold"]
    ratio = d["ratio"]
    pct = int(ratio * 100)
    desc = d["description"]
    prompt = d["prompt_preview"]

    # Status indicator
    if ratio >= 1.0:
        indicator = "🔴"
    elif ratio >= 0.75:
        indicator = "🟠"
    elif ratio >= 0.30:
        indicator = "🟡"
    else:
        indicator = "🟢"

    line = f"{indicator} {name}: {pressure:.1f}/{threshold} ({pct}%)"
    if desc:
        line += f" — {desc}"
    lines.append(line)

    # Add prompt preview indented if drive is elevated
    if prompt and ratio >= 0.75:
        lines.append(f"    ↳ {prompt}")

print("\n".join(lines))
PYEOF

echo "Updated $DRIVES_MD"
