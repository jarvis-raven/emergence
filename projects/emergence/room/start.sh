#!/bin/bash
# Start Room Dashboard Server

cd "$(dirname "$0")"

echo "🏠 Starting Room Dashboard..."
echo "📊 Nautilus workspace: ${OPENCLAW_WORKSPACE:-~/.openclaw/workspace}"
echo "🌐 Dashboard will be available at: http://localhost:${ROOM_PORT:-8765}"
echo ""

# Check if dependencies are installed
if ! python3 -c "import flask, flask_socketio" 2>/dev/null; then
    echo "📦 Installing dependencies..."
    python3 -m pip install -r requirements.txt -q
fi

# Start server
exec python3 server.py
