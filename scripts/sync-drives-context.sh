#!/bin/bash
# sync-drives-context.sh - Update DRIVES.md with current drive pressures
# Called by heartbeat to keep workspace context in sync with drives state

set -e

WORKSPACE="${OPENCLAW_WORKSPACE:-$HOME/.openclaw/workspace}"
DRIVES_MD="$WORKSPACE/DRIVES.md"
EMERGENCE_DIR="$(cd "$(dirname "$0")/.." && pwd)"

cd "$EMERGENCE_DIR"

# Get all drive info directly from drives.json
PYTHONPATH="$EMERGENCE_DIR:$PYTHONPATH" python3 << 'PYEOF' > "$DRIVES_MD"
import subprocess
import json
from datetime import datetime, timezone
import os
import re

emergence_dir = os.environ.get('PWD', os.getcwd())

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

# Load full drive definitions from drives.json
drives_json_path = os.path.expanduser("~/.openclaw/state/drives.json")
with open(drives_json_path) as f:
    drives_config = json.load(f)
    all_drives = drives_config.get("drives", {})

def extract_preview(prompt):
    """Extract actionable preview from drive prompt."""
    if not prompt:
        return ""

    lines = [l.strip() for l in prompt.split("\n") if l.strip()]

    # Skip generic header lines
    skip_patterns = [
        r"^Your \w+ drive triggered",
        r"^Time (for|to)",
        r"^This is your time",
        r"^## Instructions$"
    ]

    actions = []
    for line in lines:
        # Skip pure headers
        if any(re.match(pat, line, re.I) for pat in skip_patterns):
            continue

        # Extract from markdown section headers: "### 1. Check your calendar"
        section_match = re.match(r'^###?\s*\d+\.\s*(.+)$', line)
        if section_match:
            action = section_match.group(1).strip()
            actions.append(action)
            if len(actions) >= 4:
                break
            continue

        # Look for bulleted/numbered action items
        action_match = re.match(r'^(?:\d+\.|[-*])\s*(.+)$', line)
        if action_match:
            action = action_match.group(1).strip()
            # Skip sub-items under headers (usually implementation details)
            if action.startswith("Run:") or action.startswith("Note:"):
                continue
            # Extract core action (before colon or em-dash)
            core = re.split(r'[:\-]', action)[0].strip()
            if len(core) > 8 and len(actions) < 4:
                actions.append(core)

        # Direct instruction lines
        elif re.match(r'^(Check|Run|Read|Review|Update|Create|Write|Explore|Pick)', line, re.I):
            core = re.split(r'[:\.\-]', line)[0].strip()
            if len(core) > 8 and len(actions) < 4:
                actions.append(core)

        if len(actions) >= 4 or sum(len(a) for a in actions) > 90:
            break

    if actions:
        # Join with commas, lowercase except first
        preview_parts = [actions[0]] + [a[0].lower() + a[1:] for a in actions[1:]]
        preview = ", ".join(preview_parts)
        return preview[:100] + ("..." if len(preview) > 100 else "")

    # Fallback: first substantial line
    for line in lines:
        if len(line) > 20 and not any(re.match(pat, line, re.I) for pat in skip_patterns):
            return line[:100] + ("..." if len(line) > 100 else "")

    return ""

# Build drives data
drives_data = []
for drive_info in drives_list:
    name = drive_info.get("name", "?")
    drive_def = all_drives.get(name, {})

    description = drive_def.get("description", "")
    prompt = drive_def.get("prompt", "")
    prompt_preview = extract_preview(prompt)

    drives_data.append({
        "name": name,
        "pressure": drive_info.get("pressure", 0),
        "threshold": drive_info.get("threshold", 100),
        "ratio": drive_info.get("ratio", 0),
        "description": description,
        "prompt_preview": prompt_preview,
        "full_prompt": prompt
    })

# Sort by ratio descending
sorted_drives = sorted(drives_data, key=lambda x: x["ratio"], reverse=True)

lines = ["## Drives State"]
lines.append(f"*{len(drives_data)} drives, updated {datetime.now(timezone.utc).isoformat()}*")
lines.append("")

# Check cooldown
is_ready = cooldown.get("ready", True)
if is_ready:
    lines.append("**✓READY** - Can satisfy drives")
else:
    remaining = cooldown.get("remaining_minutes", 0)
    lines.append(f"**⏳COOLDOWN** - {remaining:.0f}m remaining")
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
        line += f" - {desc}"
    lines.append(line)

    # For triggered drives (≥75%), include FULL prompt for informed decisions
    # For elevated drives (30-75%), show preview only
    full_prompt = d.get("full_prompt", "")
    if full_prompt and ratio >= 0.75:
        # Include full prompt, indented
        prompt_lines = [l.rstrip() for l in full_prompt.split("\n")]
        for pline in prompt_lines:
            if pline:  # Skip empty lines
                safe_line = pline.replace('`', "'")
                lines.append(f"    {safe_line}")
        lines.append("")  # Blank line after full prompt
    elif prompt and ratio >= 0.30:
        # Show preview only for elevated but not triggered
        safe_prompt = prompt.replace('`', "'")
        lines.append(f"    ↳ {safe_prompt}")

print("\n".join(lines))
PYEOF

echo "Updated $DRIVES_MD"
