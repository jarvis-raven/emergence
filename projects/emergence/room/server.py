"""
Room Dashboard Server
A real-time monitoring dashboard for Emergence agents.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask, render_template, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

from core.nautilus import config
from core.nautilus import gravity as gravity_module
from core.nautilus import chambers
from core.nautilus import doors
from core.nautilus import mirrors

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Get Nautilus configuration
workspace_dir = os.environ.get('OPENCLAW_WORKSPACE', str(Path.home() / '.openclaw' / 'workspace'))
state_dir = config.get_state_dir()


def get_nautilus_status() -> Dict[str, Any]:
    """Get comprehensive Nautilus status for the dashboard."""
    try:
        # Get gravity stats using Nautilus API
        db = gravity_module.get_db()
        cursor = db.cursor()
        
        # Total chunks and accesses
        cursor.execute("""
            SELECT 
                COUNT(*) as total_chunks,
                SUM(access_count) as total_accesses,
                COUNT(CASE WHEN superseded_by IS NOT NULL THEN 1 END) as superseded
            FROM gravity
        """)
        gravity_totals = cursor.fetchone()
        
        # Top memories by gravity score
        cursor.execute("""
            SELECT 
                path,
                access_count,
                reference_count,
                explicit_importance,
                last_accessed_at,
                chamber
            FROM gravity
            WHERE superseded_by IS NULL
            ORDER BY 
                (access_count * 1.0 + 
                 reference_count * 2.0 + 
                 explicit_importance * 5.0) DESC
            LIMIT 10
        """)
        top_memories = []
        for row in cursor.fetchall():
            path, access_count, ref_count, explicit, last_accessed, chamber = row
            score = access_count * 1.0 + ref_count * 2.0 + explicit * 5.0
            top_memories.append({
                'path': path,
                'score': round(score, 1),
                'accesses': access_count,
                'references': ref_count,
                'chamber': chamber,
                'last_accessed': last_accessed
            })
        
        # Chamber distribution
        cursor.execute("""
            SELECT 
                chamber,
                COUNT(*) as count
            FROM gravity
            WHERE superseded_by IS NULL
            GROUP BY chamber
        """)
        chamber_counts = {row[0]: row[1] for row in cursor.fetchall()}
        
        # Door coverage (tags)
        cursor.execute("""
            SELECT 
                COUNT(CASE WHEN tags != '[]' THEN 1 END) as tagged,
                COUNT(*) as total
            FROM gravity
            WHERE superseded_by IS NULL
        """)
        tag_stats = cursor.fetchone()
        tagged, total = tag_stats if tag_stats else (0, 0)
        
        # Get top contexts from tags
        cursor.execute("SELECT tags FROM gravity WHERE tags != '[]'")
        all_tags = []
        for row in cursor.fetchall():
            try:
                tags = json.loads(row[0])
                all_tags.extend(tags)
            except:
                pass
        
        # Count tag frequencies
        tag_freq = {}
        for tag in all_tags:
            tag_freq[tag] = tag_freq.get(tag, 0) + 1
        top_contexts = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)[:10]
        
        # Mirror statistics
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT event_key) as total_events,
                COUNT(CASE WHEN granularity = 'raw' THEN 1 END) as raw_count,
                COUNT(CASE WHEN granularity = 'summary' THEN 1 END) as summary_count,
                COUNT(CASE WHEN granularity = 'lesson' THEN 1 END) as lesson_count
            FROM mirrors
        """)
        mirror_stats = cursor.fetchone()
        
        # Recent promotions (corridor/vault additions in last 7 days)
        cursor.execute("""
            SELECT path, chamber, last_written_at
            FROM gravity
            WHERE chamber IN ('corridor', 'vault')
              AND superseded_by IS NULL
            ORDER BY last_written_at DESC
            LIMIT 5
        """)
        recent_promotions = []
        for row in cursor.fetchall():
            path, chamber, written_at = row
            recent_promotions.append({
                'path': path,
                'chamber': chamber,
                'promoted_at': written_at
            })
        
        # Database size
        db_path = config.get_gravity_db_path()
        db_size = db_path.stat().st_size if db_path.exists() else 0
        
        db.close()
        
        return {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'gravity': {
                'total_chunks': gravity_totals[0] or 0,
                'total_accesses': gravity_totals[1] or 0,
                'superseded': gravity_totals[2] or 0,
                'db_size_bytes': db_size,
                'top_memories': top_memories
            },
            'chambers': {
                'atrium': chamber_counts.get('atrium', 0),
                'corridor': chamber_counts.get('corridor', 0),
                'vault': chamber_counts.get('vault', 0),
                'recent_promotions': recent_promotions
            },
            'doors': {
                'tagged_files': tagged,
                'total_files': total,
                'coverage_pct': round((tagged / total * 100) if total > 0 else 0, 1),
                'top_contexts': [{'tag': tag, 'count': count} for tag, count in top_contexts]
            },
            'mirrors': {
                'total_events': mirror_stats[0] if mirror_stats else 0,
                'coverage': {
                    'raw': mirror_stats[1] if mirror_stats else 0,
                    'summary': mirror_stats[2] if mirror_stats else 0,
                    'lesson': mirror_stats[3] if mirror_stats else 0
                },
                'fully_mirrored': min(mirror_stats[1:4]) if mirror_stats else 0
            }
        }
    except Exception as e:
        print(f"Error getting Nautilus status: {e}")
        import traceback
        traceback.print_exc()
        return {
            'error': str(e),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }


@app.route('/')
def index():
    """Main dashboard page."""
    return render_template('dashboard.html')


@app.route('/api/nautilus/status')
def nautilus_status():
    """Get Nautilus system status."""
    status = get_nautilus_status()
    return jsonify(status)


@app.route('/api/health')
def health():
    """Health check endpoint."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'components': {
            'nautilus': 'operational',
            'database': 'connected'
        }
    })


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection."""
    print('Client connected')
    emit('connected', {'message': 'Connected to Room dashboard'})
    # Send initial status
    status = get_nautilus_status()
    emit('nautilus_update', status)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle WebSocket disconnection."""
    print('Client disconnected')


@socketio.on('request_update')
def handle_update_request():
    """Handle manual update request."""
    status = get_nautilus_status()
    emit('nautilus_update', status)


def broadcast_updates():
    """Background task to broadcast updates to all connected clients."""
    while True:
        socketio.sleep(30)  # Update every 30 seconds
        status = get_nautilus_status()
        socketio.emit('nautilus_update', status, namespace='/', broadcast=True)


def main():
    """Start the Room dashboard server."""
    port = int(os.environ.get('ROOM_PORT', 8765))
    host = os.environ.get('ROOM_HOST', '0.0.0.0')
    
    print(f"🏠 Room Dashboard starting on {host}:{port}")
    print(f"📊 Nautilus workspace: {workspace_dir}")
    print(f"💾 Nautilus state: {state_dir}")
    print(f"🌐 Dashboard: http://localhost:{port}")
    
    # Start background update task
    socketio.start_background_task(broadcast_updates)
    
    # Run server
    socketio.run(app, host=host, port=port, debug=True, allow_unsafe_werkzeug=True)


if __name__ == '__main__':
    main()
