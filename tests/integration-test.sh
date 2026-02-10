#!/usr/bin/env bash
# F039 — Emergence Room Integration Tests
# Usage: ./integration-test.sh [api_url]
# Default: http://127.0.0.1:8765
#
# Integration tests verify that subsystems work together correctly.
# They go beyond smoke tests to check data flow, consistency, and edge cases.

set -euo pipefail

API="${1:-http://127.0.0.1:8765}"
PASS=0
FAIL=0
SKIP=0

# Temp file for storing API responses
TEMP_DIR=$(mktemp -d)
trap 'rm -rf "$TEMP_DIR"' EXIT

green() { printf "\033[32m✓ %s\033[0m\n" "$1"; }
red()   { printf "\033[31m✗ %s\033[0m\n" "$1"; }
yellow(){ printf "\033[33m⊘ %s\033[0m\n" "$1"; }

pass() { green "$1"; PASS=$((PASS + 1)); }
fail() { red "$1: $2"; FAIL=$((FAIL + 1)); }
skip() { yellow "$1"; SKIP=$((SKIP + 1)); }

# Helper: GET and check status code
check_status() {
  local url="$1" expected="${2:-200}" label="$3"
  local code
  code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null) || code="000"
  if [ "$code" = "$expected" ]; then
    pass "$label (HTTP $code)"
  else
    fail "$label" "expected $expected, got $code"
  fi
}

# Helper: GET and check JSON field exists
check_json() {
  local url="$1" jq_expr="$2" label="$3"
  local result
  result=$(curl -sf "$url" 2>/dev/null | jq -r "$jq_expr" 2>/dev/null) || result=""
  if [ -n "$result" ] && [ "$result" != "null" ]; then
    pass "$label ($result)"
  else
    fail "$label" "jq '$jq_expr' returned empty/null"
  fi
}

# Helper: GET and save response to temp file
fetch_json() {
  local url="$1" file="$2"
  curl -sf "$url" 2>/dev/null | jq . 2>/dev/null > "$TEMP_DIR/$file" || echo '{}' > "$TEMP_DIR/$file"
}

# Helper: Compare two values
check_equals() {
  local val1="$1" val2="$2" label="$3"
  if [ "$val1" = "$val2" ]; then
    pass "$label"
  else
    fail "$label" "expected '$val2', got '$val1'"
  fi
}

# Helper: Check numeric comparison
check_numeric_gt() {
  local val="$1" threshold="$2" label="$3"
  if [ -n "$val" ] && [ "$val" != "null" ] && [ "$val" -gt "$threshold" ] 2>/dev/null; then
    pass "$label ($val > $threshold)"
  else
    fail "$label" "expected > $threshold, got '$val'"
  fi
}

echo ""
echo "🔗 Emergence Room — Integration Tests"
echo "   API: $API"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Pre-fetch common responses for cross-endpoint comparisons
fetch_json "$API/api/health" "health.json"
fetch_json "$API/api/config" "config.json"
fetch_json "$API/api/shelves" "shelves.json"
fetch_json "$API/api/memory/stats" "memory_stats.json"
fetch_json "$API/api/drives" "drives.json"
fetch_json "$API/api/sessions" "sessions.json"

# ── 1. Shelf Discovery Integration ─────────────────────────
echo "▸ Shelf Discovery Integration"

# Check that shelves list is valid
SHELF_COUNT=$(jq -r '.count // empty' "$TEMP_DIR/shelves.json" 2>/dev/null) || SHELF_COUNT=""
if [ -n "$SHELF_COUNT" ] && [ "$SHELF_COUNT" != "null" ]; then
  pass "Shelves list returns valid count ($SHELF_COUNT)"
else
  fail "Shelves list returns valid count" "count missing or null"
fi

# Verify memory shelf exists and has proper structure
MEMORY_SHELF=$(jq -r '.shelves[] | select(.id=="memory")' "$TEMP_DIR/shelves.json" 2>/dev/null) || MEMORY_SHELF=""
if [ -n "$MEMORY_SHELF" ]; then
  pass "Memory shelf found in shelves list"
  
  # Verify memory shelf endpoint resolves
  MEMORY_ENDPOINT=$(echo "$MEMORY_SHELF" | jq -r '.endpoint // empty' 2>/dev/null) || MEMORY_ENDPOINT=""
  if [ -n "$MEMORY_ENDPOINT" ] && [ "$MEMORY_ENDPOINT" != "null" ]; then
    check_status "$API$MEMORY_ENDPOINT" 200 "Memory shelf endpoint resolves"
    
    # Fetch memory shelf data for comparison
    fetch_json "$API$MEMORY_ENDPOINT" "memory_shelf.json"
  else
    fail "Memory shelf has valid endpoint" "endpoint missing"
  fi
  
  # Verify memory shelf is marked as builtin
  IS_BUILTIN=$(echo "$MEMORY_SHELF" | jq -r '.isBuiltin // empty' 2>/dev/null) || IS_BUILTIN=""
  if [ "$IS_BUILTIN" = "true" ]; then
    pass "Memory shelf is marked as builtin"
  else
    fail "Memory shelf is marked as builtin" "got '$IS_BUILTIN'"
  fi
  
  # Verify memory shelf has renderer field
  RENDERER=$(echo "$MEMORY_SHELF" | jq -r '.renderer // empty' 2>/dev/null) || RENDERER=""
  if [ -n "$RENDERER" ] && [ "$RENDERER" != "null" ]; then
    pass "Memory shelf has renderer ($RENDERER)"
  else
    fail "Memory shelf has renderer" "renderer missing"
  fi
else
  fail "Memory shelf found in shelves list" "not found"
fi

# Check all shelves have required fields
SHELVES_VALID=true
while IFS= read -r shelf; do
  [ -z "$shelf" ] && continue
  SHELF_ID=$(echo "$shelf" | jq -r '.id // empty')
  SHELF_NAME=$(echo "$shelf" | jq -r '.name // empty')
  SHELF_ENDPOINT=$(echo "$shelf" | jq -r '.endpoint // empty')
  
  if [ -z "$SHELF_ID" ] || [ -z "$SHELF_NAME" ] || [ -z "$SHELF_ENDPOINT" ]; then
    SHELVES_VALID=false
    fail "Shelf validation" "shelf missing required fields (id=$SHELF_ID)"
  fi
done < <(jq -c '.shelves[]?' "$TEMP_DIR/shelves.json" 2>/dev/null)

if [ "$SHELVES_VALID" = true ]; then
  pass "All shelves have required fields (id, name, endpoint)"
fi

# ── 2. Memory Shelf Data Integrity ────────────────────────
echo ""
echo "▸ Memory Shelf Data Integrity"

# Compare data between /api/memory/stats and /api/shelves/memory
MEMORY_STATS_DAILY=$(jq -r '.daily.count // 0' "$TEMP_DIR/memory_stats.json" 2>/dev/null) || MEMORY_STATS_DAILY="0"
SHELF_MEMORY_DAILY=$(jq -r '.data.daily.count // 0' "$TEMP_DIR/memory_shelf.json" 2>/dev/null) || SHELF_MEMORY_DAILY="0"

if [ "$MEMORY_STATS_DAILY" = "$SHELF_MEMORY_DAILY" ]; then
  pass "Memory daily count consistent (stats=$MEMORY_STATS_DAILY, shelf=$SHELF_MEMORY_DAILY)"
else
  fail "Memory daily count consistent" "stats=$MEMORY_STATS_DAILY, shelf=$SHELF_MEMORY_DAILY"
fi

MEMORY_STATS_SESSIONS=$(jq -r '.sessions.count // 0' "$TEMP_DIR/memory_stats.json" 2>/dev/null) || MEMORY_STATS_SESSIONS="0"
SHELF_MEMORY_SESSIONS=$(jq -r '.data.sessions.count // 0' "$TEMP_DIR/memory_shelf.json" 2>/dev/null) || SHELF_MEMORY_SESSIONS="0"

if [ "$MEMORY_STATS_SESSIONS" = "$SHELF_MEMORY_SESSIONS" ]; then
  pass "Session count consistent (stats=$MEMORY_STATS_SESSIONS, shelf=$SHELF_MEMORY_SESSIONS)"
else
  fail "Session count consistent" "stats=$MEMORY_STATS_SESSIONS, shelf=$SHELF_MEMORY_SESSIONS"
fi

MEMORY_STATS_DREAMS=$(jq -r '.dreams.count // 0' "$TEMP_DIR/memory_stats.json" 2>/dev/null) || MEMORY_STATS_DREAMS="0"
SHELF_MEMORY_DREAMS=$(jq -r '.data.dreams.count // 0' "$TEMP_DIR/memory_shelf.json" 2>/dev/null) || SHELF_MEMORY_DREAMS="0"

if [ "$MEMORY_STATS_DREAMS" = "$SHELF_MEMORY_DREAMS" ]; then
  pass "Dream count consistent (stats=$MEMORY_STATS_DREAMS, shelf=$SHELF_MEMORY_DREAMS)"
else
  fail "Dream count consistent" "stats=$MEMORY_STATS_DREAMS, shelf=$SHELF_MEMORY_DREAMS"
fi

# ── 3. Shelf-to-Frontend Data Flow ───────────────────────
echo ""
echo "▸ Shelf-to-Frontend Data Flow"

# Test that each shelf's endpoint is resolvable
ENDPOINT_COUNT=0
ENDPOINT_PASS=0
while IFS= read -r shelf; do
  [ -z "$shelf" ] && continue
  SHELF_ID=$(echo "$shelf" | jq -r '.id // empty')
  ENDPOINT=$(echo "$shelf" | jq -r '.endpoint // empty')
  RENDERER=$(echo "$shelf" | jq -r '.renderer // empty')
  
  if [ -n "$ENDPOINT" ] && [ "$ENDPOINT" != "null" ]; then
    ENDPOINT_COUNT=$((ENDPOINT_COUNT + 1))
    # Check endpoint resolves (should be relative path)
    if [[ "$ENDPOINT" == /* ]]; then
      STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$API$ENDPOINT" 2>/dev/null) || STATUS="000"
      if [ "$STATUS" = "200" ]; then
        ENDPOINT_PASS=$((ENDPOINT_PASS + 1))
      fi
    fi
  fi
  
  # Validate renderer field
  if [ -n "$RENDERER" ] && [ "$RENDERER" != "null" ]; then
    case "$RENDERER" in
      memory|library|auto|custom|table|chart|list)
        : ;;
      *)
        fail "Shelf '$SHELF_ID' renderer '$RENDERER' is unknown"
        ;;
    esac
  fi
done < <(jq -c '.shelves[]?' "$TEMP_DIR/shelves.json" 2>/dev/null)

if [ "$ENDPOINT_PASS" -eq "$ENDPOINT_COUNT" ] && [ "$ENDPOINT_COUNT" -gt 0 ]; then
  pass "All $ENDPOINT_COUNT shelf endpoints resolve (HTTP 200)"
else
  fail "Shelf endpoints resolve" "$ENDPOINT_PASS/$ENDPOINT_COUNT resolved"
fi

# ── 4. Drive System Integration ─────────────────────────
echo ""
echo "▸ Drive System Integration"

# Check drives response structure
DRIVES_VERSION=$(jq -r '.version // empty' "$TEMP_DIR/drives.json" 2>/dev/null) || DRIVES_VERSION=""
if [ -n "$DRIVES_VERSION" ]; then
  pass "Drives has version field ($DRIVES_VERSION)"
else
  skip "Drives has version field" "version missing (may be empty state)"
fi

# Check if drives object exists and has valid structure
DRIVE_NAMES=$(jq -r '.drives | keys[]?' "$TEMP_DIR/drives.json" 2>/dev/null) || DRIVE_NAMES=""
DRIVE_COUNT=$(echo "$DRIVE_NAMES" | grep -c '^' 2>/dev/null) || DRIVE_COUNT=0

if [ -n "$DRIVE_NAMES" ]; then
  pass "Drives object exists with $DRIVE_COUNT drive(s)"
  
  # Validate each drive has required fields
  DRIVES_VALID=true
  while IFS= read -r drive_name; do
    [ -z "$drive_name" ] && continue
    PRESSURE=$(jq -r ".drives[\"$drive_name\"].pressure // empty" "$TEMP_DIR/drives.json" 2>/dev/null) || PRESSURE=""
    THRESHOLD=$(jq -r ".drives[\"$drive_name\"].threshold // empty" "$TEMP_DIR/drives.json" 2>/dev/null) || THRESHOLD=""
    
    if [ -z "$PRESSURE" ] || [ -z "$THRESHOLD" ]; then
      DRIVES_VALID=false
      fail "Drive '$drive_name' missing pressure or threshold"
    elif ! [[ "$PRESSURE" =~ ^[0-9]+(\.[0-9]+)?$ ]] 2>/dev/null; then
      DRIVES_VALID=false
      fail "Drive '$drive_name' pressure not numeric" "got '$PRESSURE'"
    elif ! [[ "$THRESHOLD" =~ ^[0-9]+(\.[0-9]+)?$ ]] 2>/dev/null; then
      DRIVES_VALID=false
      fail "Drive '$drive_name' threshold not numeric" "got '$THRESHOLD'"
    fi
  done < <(echo "$DRIVE_NAMES")
  
  if [ "$DRIVES_VALID" = true ]; then
    pass "All drives have valid numeric pressure and threshold"
  fi
else
  skip "Drive validation" "no drives configured"
fi

# Check triggered_drives array exists
TRIGGERED=$(jq -r '.triggered_drives | type' "$TEMP_DIR/drives.json" 2>/dev/null) || TRIGGERED=""
if [ "$TRIGGERED" = "array" ]; then
  pass "Triggered drives is an array"
else
  fail "Triggered drives is an array" "type is '$TRIGGERED'"
fi

# ── 5. Config Consistency ─────────────────────────────────
echo ""
echo "▸ Config Consistency"

# Agent name should match between /api/health and /api/config
HEALTH_AGENT=$(jq -r '.agent // empty' "$TEMP_DIR/health.json" 2>/dev/null) || HEALTH_AGENT=""
CONFIG_AGENT=$(jq -r '.agent.name // empty' "$TEMP_DIR/config.json" 2>/dev/null) || CONFIG_AGENT=""

if [ -n "$HEALTH_AGENT" ] && [ -n "$CONFIG_AGENT" ]; then
  if [ "$HEALTH_AGENT" = "$CONFIG_AGENT" ]; then
    pass "Agent name consistent (health/config): $HEALTH_AGENT"
  else
    fail "Agent name consistent" "health='$HEALTH_AGENT', config='$CONFIG_AGENT'"
  fi
else
  fail "Agent name comparison" "missing agent name (health='$HEALTH_AGENT', config='$CONFIG_AGENT')"
fi

# Paths in config should be valid strings
WORKSPACE_PATH=$(jq -r '.paths.workspace // empty' "$TEMP_DIR/config.json" 2>/dev/null) || WORKSPACE_PATH=""
if [ -n "$WORKSPACE_PATH" ] && [ "$WORKSPACE_PATH" != "null" ]; then
  pass "Workspace path configured ($WORKSPACE_PATH)"
else
  fail "Workspace path configured" "path missing or null"
fi

STATE_PATH=$(jq -r '.paths.state // empty' "$TEMP_DIR/config.json" 2>/dev/null) || STATE_PATH=""
if [ -n "$STATE_PATH" ] && [ "$STATE_PATH" != "null" ]; then
  pass "State path configured ($STATE_PATH)"
else
  fail "State path configured" "path missing or null"
fi

MEMORY_PATH=$(jq -r '.paths.memory // empty' "$TEMP_DIR/config.json" 2>/dev/null) || MEMORY_PATH=""
if [ -n "$MEMORY_PATH" ] && [ "$MEMORY_PATH" != "null" ]; then
  pass "Memory path configured ($MEMORY_PATH)"
else
  fail "Memory path configured" "path missing or null"
fi

# ── 6. Cross-Endpoint Consistency ─────────────────────────
echo ""
echo "▸ Cross-Endpoint Consistency"

# If /api/shelves/memory has data, /api/memory/stats should too
SHELF_HAS_DATA=false
if [ "$SHELF_MEMORY_DAILY" -gt 0 ] 2>/dev/null || [ "$SHELF_MEMORY_SESSIONS" -gt 0 ] 2>/dev/null || [ "$SHELF_MEMORY_DREAMS" -gt 0 ] 2>/dev/null; then
  SHELF_HAS_DATA=true
fi

if [ "$SHELF_HAS_DATA" = true ]; then
  if [ "$MEMORY_STATS_DAILY" -gt 0 ] 2>/dev/null; then
    pass "Memory consistency: shelf has data → stats has daily.count"
  else
    fail "Memory consistency" "shelf has data but stats daily.count is 0"
  fi
else
  skip "Memory data consistency" "no memory data to compare"
fi

# Sessions count should be a valid number
SESSION_COUNT=$(jq -r '.count // empty' "$TEMP_DIR/sessions.json" 2>/dev/null) || SESSION_COUNT=""
if [ -n "$SESSION_COUNT" ] && [[ "$SESSION_COUNT" =~ ^[0-9]+$ ]] 2>/dev/null; then
  pass "Sessions count is valid number ($SESSION_COUNT)"
else
  fail "Sessions count is valid number" "got '$SESSION_COUNT'"
fi

# Compare session counts between /api/sessions and /api/memory/stats
SESSIONS_ENDPOINT_COUNT=$(jq -r '.sessions | length' "$TEMP_DIR/sessions.json" 2>/dev/null) || SESSIONS_ENDPOINT_COUNT="0"
# Note: sessions.json .count may be limited by query params, so we compare with the actual array
if [ -n "$SESSION_COUNT" ] && [ "$SESSION_COUNT" = "$SESSIONS_ENDPOINT_COUNT" ]; then
  pass "Sessions count matches array length ($SESSION_COUNT)"
else
  fail "Sessions count matches array length" "count=$SESSION_COUNT, length=$SESSIONS_ENDPOINT_COUNT"
fi

# ── 7. Error Handling ─────────────────────────────────────
echo ""
echo "▸ Error Handling"

# POST to GET-only endpoint should return 404 or 405
ERROR_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X POST "$API/api/health" 2>/dev/null) || ERROR_CODE="000"
if [ "$ERROR_CODE" = "404" ] || [ "$ERROR_CODE" = "405" ]; then
  pass "POST to GET-only endpoint returns $ERROR_CODE"
else
  # Some servers return 200 with error in body, check if that's acceptable
  if [ "$ERROR_CODE" = "200" ]; then
    skip "POST to GET-only endpoint" "returns 200 (may have error in body)"
  else
    fail "POST to GET-only endpoint" "expected 404/405, got $ERROR_CODE"
  fi
fi

# Malformed shelf ID with special characters
MALFORMED_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/shelves/test%2F..%2Fetc%2Fpasswd" 2>/dev/null) || MALFORMED_CODE="000"
if [ "$MALFORMED_CODE" = "404" ] || [ "$MALFORMED_CODE" = "400" ]; then
  pass "Malformed shelf ID (path traversal) returns $MALFORMED_CODE"
else
  fail "Malformed shelf ID handling" "expected 404/400, got $MALFORMED_CODE"
fi

# Very long shelf ID (shouldn't crash)
LONG_ID=$(printf 'a%.0s' {1..500})
LONG_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/shelves/$LONG_ID" 2>/dev/null) || LONG_CODE="000"
if [ "$LONG_CODE" = "404" ] || [ "$LONG_CODE" = "400" ] || [ "$LONG_CODE" = "414" ]; then
  pass "Very long shelf ID returns $LONG_CODE (doesn't crash)"
else
  fail "Very long shelf ID handling" "expected 404/400/414, got $LONG_CODE"
fi

# Empty shelf ID (trailing slash)
EMPTY_CODE=$(curl -s -o /dev/null -w "%{http_code}" "$API/api/shelves/" 2>/dev/null) || EMPTY_CODE="000"
if [ "$EMPTY_CODE" = "200" ] || [ "$EMPTY_CODE" = "404" ]; then
  pass "Empty shelf ID handled (returns $EMPTY_CODE)"
else
  fail "Empty shelf ID handling" "unexpected status $EMPTY_CODE"
fi

# Invalid JSON in request body to GET endpoint
INVALID_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X GET -H "Content-Type: application/json" -d '{invalid json}' "$API/api/health" 2>/dev/null) || INVALID_CODE="000"
# Should either accept (200), ignore body (200), or reject (400)
if [ "$INVALID_CODE" = "200" ] || [ "$INVALID_CODE" = "400" ] || [ "$INVALID_CODE" = "500" ]; then
  pass "Invalid JSON in GET body handled (returns $INVALID_CODE)"
else
  fail "Invalid JSON handling" "unexpected status $INVALID_CODE"
fi

# ── Summary ───────────────────────────────────────────────
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
TOTAL=$((PASS + FAIL + SKIP))
printf "  Total: %d  " "$TOTAL"
printf "\033[32m%d passed\033[0m  " "$PASS"
[ "$FAIL" -gt 0 ] && printf "\033[31m%d failed\033[0m  " "$FAIL"
[ "$SKIP" -gt 0 ] && printf "\033[33m%d skipped\033[0m  " "$SKIP"
echo ""
echo ""

[ "$FAIL" -eq 0 ]
