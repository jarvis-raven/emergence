#!/usr/bin/env bash
# Sync drives state to minimal DRIVES.md format
# Usage: ./sync-drives-context.sh [output-path]

set -e

STATE_FILE="${HOME}/projects/emergence/.emergence-dev/state/drives-state.json"
OUTPUT="${1:-${HOME}/.openclaw/workspace/DRIVES.md}"
CONFIG_FILE="${HOME}/projects/emergence/emergence.json"

if [[ ! -f "$STATE_FILE" ]]; then
    echo "## Drives — No state file" > "$OUTPUT"
    exit 0
fi

# Read mode from config
MODE="CHOICE"
if command -v jq &>/dev/null && [[ -f "$CONFIG_FILE" ]]; then
    DAEMON_MODE=$(jq -r '.drives.daemon_mode // false' "$CONFIG_FILE")
    [[ "$DAEMON_MODE" == "true" ]] && MODE="AUTO"
fi

# Get cooldown from config (default 30)
COOLDOWN_MIN=30
if command -v jq &>/dev/null && [[ -f "$CONFIG_FILE" ]]; then
    COOLDOWN_MIN=$(jq -r '.drives.cooldown_minutes // 30' "$CONFIG_FILE")
fi

# Current timestamp
TIMESTAMP=$(date +"%H:%M")

# Parse drives and format
if command -v jq &>/dev/null; then
    DRIVES=$(jq -r '
        .drives | to_entries |
        map({
            name: .key,
            pct: ((.value.pressure / .value.threshold * 100) | floor),
            pressure: .value.pressure,
            threshold: .value.threshold
        }) |
        sort_by(-.pct) |
        map(
            .name + " " + (.pct | tostring) + "%" +
            (if .pct >= 100 then "🔴" elif .pct >= 75 then "🟠" elif .pct >= 30 then "🟡" else "" end)
        ) |
        join(" | ")
    ' "$STATE_FILE")

    LAST_TICK=$(jq -r '.last_tick // "unknown"' "$STATE_FILE")
else
    DRIVES="(install jq for drive details)"
    LAST_TICK="unknown"
fi

# Check for last satisfaction (stored in state or separate file)
SATISFACTION_FILE="${HOME}/projects/emergence/.emergence-dev/state/last-satisfaction.json"
READY="✓READY"

if [[ -f "$SATISFACTION_FILE" ]] && command -v jq &>/dev/null; then
    LAST_SAT=$(jq -r '.timestamp // ""' "$SATISFACTION_FILE")
    LAST_DRIVE=$(jq -r '.drive // ""' "$SATISFACTION_FILE")

    if [[ -n "$LAST_SAT" ]]; then
        # Calculate minutes since last satisfaction
        LAST_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${LAST_SAT:0:19}" +%s 2>/dev/null || echo 0)
        NOW_EPOCH=$(date +%s)
        MINS_AGO=$(( (NOW_EPOCH - LAST_EPOCH) / 60 ))

        if [[ $MINS_AGO -lt $COOLDOWN_MIN ]]; then
            REMAINING=$((COOLDOWN_MIN - MINS_AGO))
            READY="Satisfied: ${LAST_DRIVE}@${LAST_SAT:11:5} | ⏳${REMAINING}min"
        fi
    fi
fi

# Write output
cat > "$OUTPUT" << DRIVES_EOF
## Drives (${MODE}) ${TIMESTAMP} | ${READY}
${DRIVES}
DRIVES_EOF

echo "✓ Synced drives to ${OUTPUT}"
