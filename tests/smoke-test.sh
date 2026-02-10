#!/usr/bin/env bash
# F038 — Emergence Room Smoke Tests
# Usage: ./smoke-test.sh [api_url] [frontend_url]
# Defaults: http://127.0.0.1:8765  http://127.0.0.1:3000

set -euo pipefail

API="${1:-http://127.0.0.1:8765}"
FRONTEND="${2:-http://127.0.0.1:3000}"
PASS=0
FAIL=0
SKIP=0

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

echo ""
echo "🧪 Emergence Room — Smoke Tests"
echo "   API:      $API"
echo "   Frontend: $FRONTEND"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# ── Server Health ──────────────────────────────
echo "▸ Server Health"
check_status "$API/api/health" 200 "Health endpoint responds"
check_json   "$API/api/health" ".status" "Health status field"

# ── Config ─────────────────────────────────────
echo ""
echo "▸ Configuration"
check_status "$API/api/config" 200 "Config endpoint responds"
check_json   "$API/api/config" ".agent.name" "Agent name in config"

# ── Identity ───────────────────────────────────
echo ""
echo "▸ Identity"
check_status "$API/api/identity/self" 200 "Identity endpoint responds"

# ── Drives ─────────────────────────────────────
echo ""
echo "▸ Drives"
check_status "$API/api/drives" 200 "Drives endpoint responds"

# ── Memory ─────────────────────────────────────
echo ""
echo "▸ Memory"
check_status "$API/api/memory/stats" 200 "Memory stats endpoint responds"
check_json   "$API/api/memory/stats" ".daily.count" "Daily memory count"

# ── Sessions ───────────────────────────────────
echo ""
echo "▸ Sessions"
check_status "$API/api/sessions" 200 "Sessions endpoint responds"

# ── Shelves ────────────────────────────────────
echo ""
echo "▸ Shelf Discovery"
check_status "$API/api/shelves" 200 "Shelves list endpoint responds"
check_json   "$API/api/shelves" ".count" "Shelf count returned"

# Memory shelf (built-in)
MEMORY_BUILTIN=$(curl -sf "$API/api/shelves" 2>/dev/null | jq -r '.shelves[] | select(.id=="memory") | .isBuiltin' 2>/dev/null) || MEMORY_BUILTIN=""
if [ "$MEMORY_BUILTIN" = "true" ]; then
  pass "Memory shelf is built-in"
else
  fail "Memory shelf is built-in" "not found or not builtin"
fi

check_status "$API/api/shelves/memory" 200 "Memory shelf data responds"
check_json   "$API/api/shelves/memory" ".status" "Memory shelf status field"
check_json   "$API/api/shelves/memory" ".data.daily.count" "Memory shelf has daily count"

# 404 for missing shelf
check_status "$API/api/shelves/nonexistent" 404 "Missing shelf returns 404"

# Custom shelf discovery (if library exists)
LIBRARY_EXISTS=$(curl -sf "$API/api/shelves" 2>/dev/null | jq -r '.shelves[] | select(.id=="library") | .id' 2>/dev/null) || LIBRARY_EXISTS=""
if [ "$LIBRARY_EXISTS" = "library" ]; then
  pass "Library shelf discovered (custom)"
  check_status "$API/api/shelves/library" 200 "Library shelf data responds"
  check_json   "$API/api/shelves/library" ".data.currentlyReading" "Library has currentlyReading"
else
  skip "Library shelf not present (optional)"
fi

# ── Frontend ───────────────────────────────────
echo ""
echo "▸ Frontend"
FRONTEND_HTML=$(curl -sf "$FRONTEND" 2>/dev/null | head -1) || FRONTEND_HTML=""
if echo "$FRONTEND_HTML" | grep -q "DOCTYPE\|html" 2>/dev/null; then
  pass "Frontend serves HTML"
else
  fail "Frontend serves HTML" "no HTML response"
fi

# ── Summary ────────────────────────────────────
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
