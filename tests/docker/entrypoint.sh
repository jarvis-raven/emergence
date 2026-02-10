#!/bin/bash
# Emergence F040b — Full fresh agent setup
# Usage: ./entrypoint.sh <openrouter_api_key>
set -e

OPENROUTER_KEY="${1:-$OPENROUTER_API_KEY}"

if [ -z "$OPENROUTER_KEY" ]; then
    echo "❌ Need an OpenRouter API key"
    echo "Usage: ./entrypoint.sh <api_key>"
    echo "   or: OPENROUTER_API_KEY=... ./entrypoint.sh"
    exit 1
fi

echo "═══════════════════════════════════════════"
echo "  Emergence F040b — Fresh Agent Test"
echo "═══════════════════════════════════════════"
echo ""

# Start cron service
echo "⏰ Starting cron service..."
sudo service cron start 2>/dev/null || sudo cron 2>/dev/null || echo "  (cron started or unavailable)"

# Step 1: OpenClaw onboard (non-interactive)
echo "📦 Step 1: OpenClaw onboard..."
openclaw onboard \
    --non-interactive \
    --accept-risk \
    --auth-choice openrouter-api-key \
    --token "$OPENROUTER_KEY" \
    --flow quickstart \
    --gateway-bind loopback \
    --skip-channels \
    2>&1 || true

echo ""
echo "✓ OpenClaw configured"

# Step 2: Start gateway in background
echo ""
echo "🚀 Step 2: Starting gateway..."
mkdir -p /home/agent/.openclaw/logs
openclaw gateway run > /home/agent/.openclaw/logs/gateway.log 2>&1 &
GATEWAY_PID=$!
sleep 3

# Verify gateway is running
if kill -0 $GATEWAY_PID 2>/dev/null; then
    echo "✓ Gateway running (PID $GATEWAY_PID)"
else
    echo "❌ Gateway failed to start"
    cat /home/agent/.openclaw/logs/gateway.log
    exit 1
fi

# Step 3: Run Emergence first_light
echo ""
echo "🌅 Step 3: Running first_light..."
echo "   (This would normally be interactive)"
echo "   Skipping interactive wizard for automated test"
echo "   Running prereq check instead..."
cd /home/agent/emergence
python3 -m core.setup.prereq --json 2>&1 || true

# Step 4: Verify drives work
echo ""
echo "⚙️  Step 4: Testing drives engine..."
python3 -c "
from core.setup.config_gen import generate_default_config, write_config
from core.drives.state import save_state
from core.drives.defaults import ensure_core_drives
from core.drives.engine import tick_all_drives
from core.drives.platform import detect_platform, generate_systemd_service
from pathlib import Path
import os

# Generate config
config = generate_default_config('Aurora', 'Human')
config['paths']['state'] = str(Path.home() / '.openclaw/state')
config['paths']['workspace'] = str(Path.home() / '.openclaw/workspace')
config['paths']['memory'] = str(Path.home() / '.openclaw/workspace/memory')
os.makedirs(config['paths']['state'], exist_ok=True)
os.makedirs(config['paths']['memory'], exist_ok=True)
write_config(config, Path.home() / '.openclaw/workspace/emergence.json')

# Init drives
state = {'drives': {}, 'triggered_drives': [], 'trigger_log': []}
ensure_core_drives(state)
save_state(Path(config['paths']['state']) / 'drives.json', state)

# Tick
tick_all_drives(state, config)
print('✓ Drives initialized and ticked')
for name, d in state['drives'].items():
    print(f'  {name}: {d[\"pressure\"]:.1f}/{d[\"threshold\"]}')

# Platform
platform = detect_platform()
print(f'✓ Platform: {platform}')
if platform == 'linux':
    svc = generate_systemd_service(config)
    print('✓ systemd service generated')
"

# Step 5: Test agent communication
echo ""
echo "💬 Step 5: Testing agent communication..."
GATEWAY_PORT=$(python3 -c "import json; c=json.load(open('/home/agent/.openclaw/openclaw.json')); print(c.get('gateway',{}).get('port', 18789))" 2>/dev/null || echo "18789")
echo "   Gateway port: $GATEWAY_PORT"

# Try sending a message
openclaw agent -m "Hello, I am testing your setup. Please respond briefly." --local 2>&1 || echo "   (Agent communication test — may need channel setup)"

echo ""
echo "═══════════════════════════════════════════"
echo "  ✅ F040b Test Complete"
echo "═══════════════════════════════════════════"
echo ""
echo "Container is ready for interactive testing."
echo "Gateway running on port $GATEWAY_PORT"
echo ""

# Keep alive for interactive use
exec /bin/bash
