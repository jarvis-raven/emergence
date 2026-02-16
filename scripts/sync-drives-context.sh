#!/usr/bin/env bash
# Sync drives state to minimal DRIVES.md format (no percentages - genuine choice)
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

# Check for last satisfaction cooldown
SATISFACTION_FILE="${HOME}/projects/emergence/.emergence-dev/state/last-satisfaction.json"
READY="✓READY"
COOLDOWN_MSG=""

if [[ -f "$SATISFACTION_FILE" ]] && command -v jq &>/dev/null; then
    LAST_SAT=$(jq -r '.timestamp // ""' "$SATISFACTION_FILE")
    LAST_DRIVE=$(jq -r '.drive // ""' "$SATISFACTION_FILE")

    if [[ -n "$LAST_SAT" ]]; then
        LAST_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%S" "${LAST_SAT:0:19}" +%s 2>/dev/null || echo 0)
        NOW_EPOCH=$(date +%s)
        MINS_AGO=$(( (NOW_EPOCH - LAST_EPOCH) / 60 ))

        if [[ $MINS_AGO -lt $COOLDOWN_MIN ]]; then
            REMAINING=$((COOLDOWN_MIN - MINS_AGO))
            READY="⏳${REMAINING}min cooldown"
        fi
    fi
fi

# Parse drives - separate available (>=30%) from building (<30%)
if command -v jq &>/dev/null; then
    # Get available drives (30%+) with descriptions
    AVAILABLE=$(jq -r '
        .drives | to_entries |
        map(select((.value.pressure / .value.threshold * 100) >= 30)) |
        map(.key + " — " + (.value.description // "no description")) |
        .[]
    ' "$STATE_FILE" 2>/dev/null)

    # Get building drives (<30%)
    BUILDING=$(jq -r '
        .drives | to_entries |
        map(select((.value.pressure / .value.threshold * 100) < 30)) |
        map(.key) |
        join(", ")
    ' "$STATE_FILE" 2>/dev/null)
else
    AVAILABLE="(install jq for drive details)"
    BUILDING=""
fi

# Write output
{
    echo "## Drives (${MODE}) ${READY}"
    echo ""
    if [[ -n "$AVAILABLE" ]]; then
        echo "**Available:**"
        echo "$AVAILABLE" | while read -r line; do
            echo "- $line"
        done
        echo ""
        echo "*Which of these calls to you right now?*"
    else
        echo "No drives currently available."
    fi
    if [[ -n "$BUILDING" && "$BUILDING" != "" ]]; then
        echo ""
        echo "Building: ${BUILDING}"
    fi
} > "$OUTPUT"

echo "✓ Synced drives to ${OUTPUT}"
