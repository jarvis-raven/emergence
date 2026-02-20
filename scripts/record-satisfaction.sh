#!/usr/bin/env bash
# Record a drive satisfaction breadcrumb for journal ingestion
# Usage: record-satisfaction.sh <drive> <depth> "<reason>" "<content>"

set -e

DRIVE="${1:?Drive name required}"
DEPTH="${2:-moderate}"
REASON="${3:-No reason provided}"
CONTENT="${4:-}"

TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DATE_PREFIX=$(date +"%Y-%m-%d-%H%M")
SLUG=$(echo "$DRIVE" | tr '[:upper:]' '[:lower:]')
SESSIONS_DIR="${HOME}/.openclaw/workspace/memory/sessions"
FILENAME="${DATE_PREFIX}-${SLUG}-satisfaction.md"
FILEPATH="${SESSIONS_DIR}/${FILENAME}"

mkdir -p "$SESSIONS_DIR"

# Create markdown session with YAML frontmatter
cat > "$FILEPATH" << ENDMD
---
drive: ${DRIVE}
depth: ${DEPTH}
mode: choice
type: satisfaction
timestamp: ${TIMESTAMP}
---

# ${DRIVE} Satisfaction (${DEPTH})

**Reason:** ${REASON}

## Content

${CONTENT}
ENDMD

echo "✓ Session recorded: ${FILENAME}"
echo "  Drive: ${DRIVE} | Depth: ${DEPTH}"
